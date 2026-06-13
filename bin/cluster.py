#!/usr/bin/env python3
"""Run one configured clustering algorithm and report per-member quality metrics.

Input space matters (intricate point #2 — normalization changes meaning):
  - cosine    : L2-normalize, then euclidean == cosine. For RAW embeddings.
  - euclidean : cluster the coordinates as-is. For UMAP-reduced space — do NOT
                re-normalize, that would distort the geometry UMAP built.
"""
import argparse, json
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from sklearn.preprocessing import normalize
from sklearn.metrics import silhouette_score


def cluster(X, run, seed, metric):
    algo = run["algorithm"]
    if algo == "hdbscan":
        import hdbscan
        return hdbscan.HDBSCAN(
            min_cluster_size=int(run.get("min_cluster_size", 5)),
            min_samples=run.get("min_samples"),       # None -> defaults to min_cluster_size
            metric="euclidean",                        # plain euclidean on the given space
        ).fit_predict(X)
    if algo == "kmeans":
        from sklearn.cluster import KMeans
        return KMeans(n_clusters=int(run["n_clusters"]),
                      random_state=seed, n_init="auto").fit_predict(X)
    if algo == "agglomerative":
        from sklearn.cluster import AgglomerativeClustering
        return AgglomerativeClustering(
            n_clusters=int(run["n_clusters"]) if run.get("n_clusters") else None,
            distance_threshold=run.get("distance_threshold"),
            metric=metric,
            linkage=run.get("linkage", "average"),     # 'ward' needs euclidean
        ).fit_predict(X)
    raise ValueError(f"Unknown algorithm: {algo}")


def member_metrics(run, labels, X, sil_metric):
    """Per-member quality signals — the basis for future ensemble weighting."""
    n = len(labels)
    sizes = np.bincount(labels[labels != -1]) if (labels != -1).any() else np.array([])
    n_clusters = int(len(sizes))
    noise = int((labels == -1).sum())

    mask = labels != -1
    sil = None
    if 2 <= len(set(labels[mask].tolist())) < int(mask.sum()):
        sil = round(float(silhouette_score(X[mask], labels[mask], metric=sil_metric)), 4)

    return {
        "run":                      run["name"],
        "algorithm":                run["algorithm"],
        "n_samples":                n,
        "n_clusters":               n_clusters,
        "noise":                    noise,
        "noise_fraction":           round(noise / n, 4),
        "largest_cluster_fraction": round(float(sizes.max() / n), 4) if n_clusters else 0.0,
        "silhouette":               sil,            # null when undefined (< 2 clusters)
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--run", required=True)            # JSON spec
    ap.add_argument("--metrics", required=True)        # per-member metrics JSON (one line)
    ap.add_argument("--space", choices=["cosine", "euclidean"], default="cosine")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    run = json.loads(args.run)
    table = pq.read_table(args.input)
    ids = table.column("sample_id").to_pylist()
    X = np.asarray(table.column("embedding").to_pylist(), dtype=np.float32)

    if args.space == "cosine":
        X = normalize(X)
        agglo_metric, sil_metric = run.get("metric", "cosine"), "cosine"
    else:                                              # reduced UMAP space
        agglo_metric, sil_metric = "euclidean", "euclidean"

    labels = cluster(X, run, args.seed, agglo_metric).astype(int)

    pq.write_table(pa.table({
        "sample_id": pa.array(ids, pa.string()),
        "label":     pa.array(labels.tolist(), pa.int32()),
        "run":       pa.array([run["name"]] * len(ids), pa.string()),
    }), args.output)

    metrics = member_metrics(run, labels, X, sil_metric)
    with open(args.metrics, "w") as fh:
        json.dump(metrics, fh)

    print(f"[{run['name']}] {metrics['n_clusters']} clusters, {metrics['noise']} noise, "
          f"sil={metrics['silhouette']} ({args.space}) -> {args.output}")


if __name__ == "__main__":
    main()
