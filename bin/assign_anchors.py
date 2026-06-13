#!/usr/bin/env python3
"""Rank taxonomy anchors against each sample (and each consensus cluster), per kind.

Per-sample: top-k nearest anchors *within each kind* (category/tag/flag) by
cosine -> ranked suggestions for the expert's first pass. Per-cluster: the same,
against the consensus centroid (the reconcile view). Ranking within kind keeps
the mutually-exclusive categories from being crowded out by the many tags/flags.

All similarity is computed in the RAW embedding space (where the model is
calibrated). umap3 is borrowed only for *placement* on the dashboard:
  - points.parquet        (A): per-sample drawing row = umap3 (x,y,z) + the top-1
                               anchor per kind + consensus/stability, so dots can
                               be colored by their assignment.
  - anchor_points.parquet (B): each anchor placed at the centroid (in umap3) of
                               the samples that pick it #1 within its kind; an
                               anchor nobody picks falls back to its top-k nearest
                               samples by raw cosine.
"""
import argparse
import json
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from sklearn.preprocessing import normalize


def load_vectors(path):
    t = pq.read_table(path)
    ids = t.column("sample_id").to_pylist()
    X = normalize(np.asarray(t.column("embedding").to_pylist(), dtype=np.float32))
    return ids, X


def load_umap3(path, order):
    """umap3 (x,y,z) aligned to `order` -> [n_samples x 3]."""
    t = pq.read_table(path).to_pandas().set_index("sample_id").reindex(order)
    return t[["x", "y", "z"]].to_numpy(dtype=np.float32)


def read_jsonl(path):
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def ranked(sim_row, idxs, k):
    """Top-k anchor indices from idxs by descending similarity, as (rank, idx)."""
    local = sorted(idxs, key=lambda ai: -sim_row[ai])[:k]
    return list(enumerate(local, start=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--embeddings", required=True)
    ap.add_argument("--anchors", required=True)
    ap.add_argument("--anchor-meta", required=True)
    ap.add_argument("--ensemble", required=True)
    ap.add_argument("--umap3", required=True)
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--prelabels", required=True)
    ap.add_argument("--cluster-suggestions", required=True)
    ap.add_argument("--points", required=True)          # A: per-sample drawing table
    ap.add_argument("--anchor-points", required=True)   # B: anchor marker positions
    args = ap.parse_args()

    s_ids, Xs = load_vectors(args.embeddings)
    a_ids, Xa = load_vectors(args.anchors)
    meta = {m["id"]: m for m in read_jsonl(args.anchor_meta)}

    # group anchor row-indices by kind, preserving file order
    kinds = {}
    for ai, aid in enumerate(a_ids):
        kinds.setdefault(meta.get(aid, {}).get("kind", "unknown"), []).append(ai)

    ens = pq.read_table(args.ensemble).to_pandas().set_index("sample_id")
    sims = Xs @ Xa.T                       # cosine, [n_samples x n_anchors]

    # ---- per-sample ranked suggestions, within each kind (tidy/long) ----
    rows = []
    for si, sid in enumerate(s_ids):
        e = ens.loc[sid] if sid in ens.index else None
        for kind, idxs in kinds.items():
            for rank, ai in ranked(sims[si], idxs, min(args.top_k, len(idxs))):
                aid = a_ids[ai]
                rows.append({
                    "sample_id":       sid,
                    "anchor_kind":     kind,
                    "rank":            rank,
                    "anchor_id":       aid,
                    "anchor_name":     meta.get(aid, {}).get("name"),
                    "score":           float(sims[si, ai]),
                    "consensus_label": int(e["consensus_label"]) if e is not None else None,
                    "stability":       float(e["stability"]) if e is not None else None,
                })
    pre = pd.DataFrame(rows)
    pq.write_table(pa.Table.from_pandas(pre, preserve_index=False), args.prelabels)

    # ---- per-cluster suggestions, within each kind (reconcile view) ----
    cons = ens["consensus_label"].reindex(s_ids).to_numpy()
    stab = ens["stability"].reindex(s_ids).to_numpy()
    clusters = []
    for c in sorted({int(x) for x in cons}):
        members = np.where(cons == c)[0]
        centroid = normalize(Xs[members].mean(axis=0, keepdims=True))[0]
        csim = centroid @ Xa.T
        by_kind = {
            kind: [
                {"anchor_id": a_ids[ai], "name": meta.get(a_ids[ai], {}).get("name"),
                 "rank": rank, "score": float(csim[ai])}
                for rank, ai in ranked(csim, idxs, min(args.top_k, len(idxs)))
            ]
            for kind, idxs in kinds.items()
        }
        clusters.append({
            "consensus_label": c,
            "size": int(len(members)),
            "mean_stability": float(np.nanmean(stab[members])),
            "suggestions": by_kind,
        })
    with open(args.cluster_suggestions, "w") as fh:
        json.dump(clusters, fh, indent=2)

    # ---- A: per-sample drawing table (umap3 coords + top-1 anchor per kind) ----
    V = load_umap3(args.umap3, s_ids)
    top1 = {kind: np.asarray(idxs)[sims[:, idxs].argmax(axis=1)]
            for kind, idxs in kinds.items()}
    points = {
        "sample_id":       s_ids,
        "x": V[:, 0], "y": V[:, 1], "z": V[:, 2],
        "consensus_label": cons.astype(int),
        "stability":       stab.astype(np.float32),
    }
    for kind, best_ai in top1.items():
        points[f"top_{kind}"]       = [meta.get(a_ids[ai], {}).get("name") for ai in best_ai]
        points[f"top_{kind}_score"] = [float(sims[si, ai]) for si, ai in enumerate(best_ai)]
    pq.write_table(pa.Table.from_pandas(pd.DataFrame(points), preserve_index=False), args.points)

    # ---- B: anchor markers = centroid (in umap3) of samples that pick it #1 ----
    support = {ai: [] for ai in range(len(a_ids))}
    for best_ai in top1.values():
        for si, ai in enumerate(best_ai):
            support[int(ai)].append(si)
    apoints = []
    for ai, aid in enumerate(a_ids):
        members, placement = support[ai], "assigned"
        if not members:                                  # nobody ranks it #1
            members = list(np.argsort(-sims[:, ai])[:min(args.top_k, len(s_ids))])
            placement = "fallback"
        c = V[members].mean(axis=0)
        apoints.append({
            "anchor_id":   aid,
            "anchor_kind": meta.get(aid, {}).get("kind", "unknown"),
            "anchor_name": meta.get(aid, {}).get("name"),
            "x": float(c[0]), "y": float(c[1]), "z": float(c[2]),
            "n_support":   len(members),
            "placement":   placement,
        })
    pq.write_table(pa.Table.from_pandas(pd.DataFrame(apoints), preserve_index=False), args.anchor_points)

    summary = ", ".join(f"{k}:{len(v)}" for k, v in kinds.items())
    print(f"[assign] {len(s_ids)} samples x {len(a_ids)} anchors ({summary}), "
          f"top-{args.top_k}/kind -> {args.prelabels}; "
          f"{len(clusters)} clusters -> {args.cluster_suggestions}; "
          f"points -> {args.points}; anchor markers -> {args.anchor_points}")


if __name__ == "__main__":
    main()
