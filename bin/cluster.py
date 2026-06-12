#!/usr/bin/env python3
"""Run one configured clustering algorithm on full (L2-normalized) embeddings."""
import argparse, json
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from sklearn.preprocessing import normalize


def cluster(X, run, seed):
    algo = run["algorithm"]
    if algo == "hdbscan":
        import hdbscan
        return hdbscan.HDBSCAN(
            min_cluster_size=int(run.get("min_cluster_size", 5)),
            min_samples=run.get("min_samples"),       # None -> defaults to min_cluster_size
            metric="euclidean",                        # on L2-normalized X == cosine
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
            metric=run.get("metric", "cosine"),
            linkage=run.get("linkage", "average"),     # 'ward' needs euclidean; use average for cosine
        ).fit_predict(X)
    raise ValueError(f"Unknown algorithm: {algo}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--run", required=True)            # JSON spec
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    run = json.loads(args.run)
    table = pq.read_table(args.input)
    ids = table.column("sample_id").to_pylist()
    X = normalize(np.asarray(table.column("embedding").to_pylist(), dtype=np.float32))

    labels = cluster(X, run, args.seed).astype(int)

    pq.write_table(pa.table({
        "sample_id": pa.array(ids, pa.string()),
        "label":     pa.array(labels.tolist(), pa.int32()),
        "run":       pa.array([run["name"]] * len(ids), pa.string()),
    }), args.output)

    n_clusters = len(set(labels.tolist()) - {-1})
    print(f"[{run['name']}] {n_clusters} clusters, {(labels == -1).sum()} noise -> {args.output}")


if __name__ == "__main__":
    main()
