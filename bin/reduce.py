#!/usr/bin/env python3
"""Chained dimensionality reduction: PCA -> UMAP.

One shared PCA pre-reduction feeds two UMAP projections:
  - clustering space: UMAP(n_components, min_dist~0.0) -> reduced.parquet
      (vector kept in column 'embedding' so Cluster stays space-agnostic)
  - viz space:        UMAP(3, min_dist~0.1)            -> umap3.parquet (x, y, z)

PCA denoises and shrinks the ambient dimension so UMAP's kNN graph is built on
meaningful distances (mitigates high-dim distance concentration).
"""
import argparse
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from sklearn.decomposition import PCA
import umap


def pca_reduce(X, n, seed):
    # PCA can keep at most min(n_samples, n_features) - 1 components
    n = max(2, min(n, X.shape[0] - 1, X.shape[1]))
    return PCA(n_components=n, random_state=seed).fit_transform(X), n


def umap_reduce(Xp, n_components, n_neighbors, min_dist, seed):
    nn = max(2, min(n_neighbors, Xp.shape[0] - 1))   # n_neighbors must be < n_samples
    return umap.UMAP(
        n_components=n_components,
        n_neighbors=nn,
        min_dist=min_dist,
        metric="cosine",
        random_state=seed,            # deterministic (disables UMAP parallelism)
    ).fit_transform(Xp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--reduced", required=True)
    ap.add_argument("--umap3", required=True)
    ap.add_argument("--pca-components", type=int, default=50)
    ap.add_argument("--n-components", type=int, default=10)     # clustering space dim
    ap.add_argument("--n-neighbors", type=int, default=10)
    ap.add_argument("--min-dist", type=float, default=0.0)
    ap.add_argument("--viz-n-neighbors", type=int, default=15)
    ap.add_argument("--viz-min-dist", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    table = pq.read_table(args.input)
    ids = table.column("sample_id").to_pylist()
    X = np.asarray(table.column("embedding").to_pylist(), dtype=np.float32)

    Xp, pca_n = pca_reduce(X, args.pca_components, args.seed)

    # clustering space: tight (min_dist~0) to preserve density for HDBSCAN
    cl = umap_reduce(Xp, args.n_components, args.n_neighbors, args.min_dist, args.seed)
    params = f"pca{pca_n}_umap{args.n_components}_nn{args.n_neighbors}_md{args.min_dist}"
    pq.write_table(pa.table({
        "sample_id": pa.array(ids, pa.string()),
        "embedding": pa.array(cl.astype(np.float32).tolist(), pa.list_(pa.float32())),
        "method":    pa.array(["pca+umap"] * len(ids), pa.string()),
        "params":    pa.array([params] * len(ids), pa.string()),
    }), args.reduced)

    # viz space: spread (min_dist~0.1), exactly 3D for the dashboard
    viz = umap_reduce(Xp, 3, args.viz_n_neighbors, args.viz_min_dist, args.seed)
    pq.write_table(pa.table({
        "sample_id": pa.array(ids, pa.string()),
        "x": pa.array(viz[:, 0].astype(np.float32).tolist(), pa.float32()),
        "y": pa.array(viz[:, 1].astype(np.float32).tolist(), pa.float32()),
        "z": pa.array(viz[:, 2].astype(np.float32).tolist(), pa.float32()),
    }), args.umap3)

    print(f"[reduce] {tuple(X.shape)} -> PCA{pca_n} -> "
          f"UMAP{args.n_components} (cluster, md={args.min_dist}) + UMAP3 (viz, md={args.viz_min_dist}) "
          f"-> {args.reduced}, {args.umap3}")


if __name__ == "__main__":
    main()
