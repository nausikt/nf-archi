#!/usr/bin/env python3
"""Rank taxonomy anchors against each sample (and each consensus cluster), per kind.

Per-sample: top-k nearest anchors *within each kind* (category/tag/flag) by
cosine -> ranked suggestions for the expert's first pass. Per-cluster: the same,
against the consensus centroid (the reconcile view). Ranking within kind keeps
the mutually-exclusive categories from being crowded out by the many tags/flags.
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
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--prelabels", required=True)
    ap.add_argument("--cluster-suggestions", required=True)
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

    summary = ", ".join(f"{k}:{len(v)}" for k, v in kinds.items())
    print(f"[assign] {len(s_ids)} samples x {len(a_ids)} anchors ({summary}), "
          f"top-{args.top_k}/kind -> {args.prelabels}; "
          f"{len(clusters)} clusters -> {args.cluster_suggestions}")


if __name__ == "__main__":
    main()
