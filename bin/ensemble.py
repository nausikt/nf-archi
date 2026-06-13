#!/usr/bin/env python3
"""Evidence-accumulation consensus over many per-run cluster label files.

For each pair of samples, co-association = fraction of runs that place them in
the SAME (non-noise) cluster. Consensus = average-linkage hierarchical cut on
distance = 1 - co_association. HDBSCAN noise (-1) agrees with nobody.
"""
import argparse
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from sklearn.cluster import AgglomerativeClustering


def load_members(paths):
    """Return (sample_ids, label_matrix [n_runs x n_samples], run_names)."""
    order, idx = None, None
    rows, names = [], []
    for p in sorted(paths):
        t = pq.read_table(p)
        ids = t.column("sample_id").to_pylist()
        if order is None:
            order = ids
            idx = {s: i for i, s in enumerate(order)}
        assert set(ids) == set(idx), f"{p}: sample_id set differs from first member"
        vec = np.empty(len(order), dtype=np.int64)
        for s, l in zip(ids, t.column("label").to_pylist()):
            vec[idx[s]] = l
        rows.append(vec)
        names.append(t.column("run").to_pylist()[0])
    return order, np.vstack(rows), names


def co_association(labels):
    """labels: [n_runs x n_samples] int, -1 = noise. -> [n_samples x n_samples] in [0,1]."""
    n = labels.shape[1]
    acc = np.zeros((n, n), dtype=np.float64)
    for L in labels:
        valid = L != -1
        same = (L[:, None] == L[None, :]) & valid[:, None] & valid[None, :]
        acc += same
    acc /= labels.shape[0]
    np.fill_diagonal(acc, 1.0)
    return acc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--coassoc", required=True)
    ap.add_argument("--threshold", type=float, default=0.5)  # min co-assoc to stay together
    args = ap.parse_args()

    ids, labels, names = load_members(args.inputs)
    coassoc = co_association(labels)
    dist = 1.0 - coassoc
    np.fill_diagonal(dist, 0.0)

    consensus = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=1.0 - args.threshold,
        metric="precomputed",
        linkage="average",
    ).fit_predict(dist).astype(int)

    # per-sample stability = mean co-association with consensus cluster-mates
    stability = np.zeros(len(ids), dtype=np.float32)
    for c in np.unique(consensus):
        members = np.where(consensus == c)[0]
        if len(members) > 1:
            block = coassoc[np.ix_(members, members)].copy()
            np.fill_diagonal(block, np.nan)
            stability[members] = np.nanmean(block, axis=1).astype(np.float32)

    # per-sample noise_rate = fraction of runs that called it noise (-1, HDBSCAN)
    noise_rate = (labels == -1).mean(axis=0).astype(np.float32)

    pq.write_table(pa.table({
        "sample_id":       pa.array(ids, pa.string()),
        "consensus_label": pa.array(consensus.tolist(), pa.int32()),
        "stability":       pa.array(stability.tolist(), pa.float32()),
        "noise_rate":      pa.array(noise_rate.tolist(), pa.float32()),
        "n_members":       pa.array([labels.shape[0]] * len(ids), pa.int32()),
    }), args.output)

    pq.write_table(pa.table({
        "sample_id": pa.array(ids, pa.string()),
        "coassoc":   pa.array([row.tolist() for row in coassoc.astype(np.float32)],
                              pa.list_(pa.float32())),
    }), args.coassoc)

    k = len(np.unique(consensus))
    print(f"[ensemble] {labels.shape[0]} members ({','.join(names)}) "
          f"-> {k} consensus clusters @ threshold {args.threshold}")


if __name__ == "__main__":
    main()
