#!/usr/bin/env python3
"""Weighted evidence-accumulation consensus over many per-run cluster members.

Intricate point #3 — the weighted co-association formula:

    co(i, j) = ( Σ_m  w_m · 1[ same_m(i, j) ] )  /  ( Σ_m  w_m )

where same_m(i,j) is true iff member m puts i and j in the SAME non-noise
cluster. This single formula subsumes:
  - filtering      : w_m = 0  drops a member entirely (numerator & denominator)
  - soft voting    : w_m in (0, ∞) weights a member by its quality
  - human curation : an explicit override pins w_m by run name

Default weights are derived semi-automatically (Tier-0 auto-drop) from each
member's quality metrics, then human overrides win. The resolved weights are
written out so the human can inspect and curate, then re-run (-resume).
"""
import argparse, json
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


def load_metrics(paths):
    by_run = {}
    for p in paths:
        with open(p) as fh:
            m = json.load(fh)
        by_run[m["run"]] = m
    return by_run


def base_weight(m, mode):
    """Soft-vote weight for a non-degenerate member."""
    if mode == "uniform":
        return 1.0
    if mode == "silhouette":                         # poor separation -> ~0
        s = m.get("silhouette")
        return 0.5 if s is None else max(0.0, float(s))
    raise ValueError(f"Unknown weight mode: {mode}")


def resolve_weights(names, metrics, policy, overrides):
    """Tier-0 auto-drop + human override -> (weight_vector, decision report)."""
    weights, report = [], []
    for run in names:
        m = metrics.get(run, {"run": run})
        reasons = []
        if m.get("n_clusters", 0) < policy["min_clusters"]:
            reasons.append("too_few_clusters")
        if m.get("noise_fraction", 0.0) > policy["max_noise"]:
            reasons.append("too_noisy")
        if m.get("largest_cluster_fraction", 0.0) > policy["max_dominance"]:
            reasons.append("dominant_cluster")

        auto = 0.0 if reasons else base_weight(m, policy["weight"])
        override = overrides.get(run)
        final = float(override) if override is not None else auto

        weights.append(final)
        report.append({
            **m,
            "auto_weight":  round(auto, 4),
            "override":     override,
            "final_weight": round(final, 4),
            "dropped":      final == 0.0,
            "reasons":      reasons,
        })
    return np.asarray(weights, dtype=np.float64), report


def co_association(labels, weights):
    """Weighted co-association: [n_runs x n_samples] -> [n_samples x n_samples]."""
    n = labels.shape[1]
    acc = np.zeros((n, n), dtype=np.float64)
    for L, w in zip(labels, weights):
        if w == 0.0:
            continue
        valid = L != -1
        same = (L[:, None] == L[None, :]) & valid[:, None] & valid[None, :]
        acc += w * same
    total = float(weights.sum())
    if total <= 0.0:
        raise SystemExit("All members were dropped (total weight 0); relax auto-drop "
                         "policy or set member_weights overrides.")
    acc /= total
    np.fill_diagonal(acc, 1.0)
    return acc, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True)    # per-run label parquets
    ap.add_argument("--metrics", nargs="+", required=True)   # per-run metrics jsons
    ap.add_argument("--output", required=True)
    ap.add_argument("--coassoc", required=True)
    ap.add_argument("--weights", required=True)              # resolved-weights report
    ap.add_argument("--threshold", type=float, default=0.5)  # min co-assoc to stay together
    ap.add_argument("--weight-mode", default="silhouette", choices=["uniform", "silhouette"])
    ap.add_argument("--min-clusters", type=int, default=2)
    ap.add_argument("--max-noise", type=float, default=0.6)
    ap.add_argument("--max-dominance", type=float, default=0.9)
    ap.add_argument("--overrides", default="{}")             # JSON {run: weight}
    args = ap.parse_args()

    ids, labels, names = load_members(args.inputs)
    metrics = load_metrics(args.metrics)
    policy = {"weight": args.weight_mode, "min_clusters": args.min_clusters,
              "max_noise": args.max_noise, "max_dominance": args.max_dominance}
    weights, report = resolve_weights(names, metrics, policy, json.loads(args.overrides))

    coassoc, total_w = co_association(labels, weights)
    dist = 1.0 - coassoc
    np.fill_diagonal(dist, 0.0)

    consensus = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=1.0 - args.threshold,
        metric="precomputed",
        linkage="average",
    ).fit_predict(dist).astype(int)

    # per-sample stability = mean (weighted) co-association with consensus mates
    stability = np.zeros(len(ids), dtype=np.float32)
    for c in np.unique(consensus):
        members = np.where(consensus == c)[0]
        if len(members) > 1:
            block = coassoc[np.ix_(members, members)].copy()
            np.fill_diagonal(block, np.nan)
            stability[members] = np.nanmean(block, axis=1).astype(np.float32)

    # per-sample noise_rate = weighted fraction of contributing members calling it noise
    is_noise = (labels == -1).astype(np.float64)
    noise_rate = ((weights[:, None] * is_noise).sum(axis=0) / total_w).astype(np.float32)

    n_contrib = int((weights > 0).sum())

    pq.write_table(pa.table({
        "sample_id":       pa.array(ids, pa.string()),
        "consensus_label": pa.array(consensus.tolist(), pa.int32()),
        "stability":       pa.array(stability.tolist(), pa.float32()),
        "noise_rate":      pa.array(noise_rate.tolist(), pa.float32()),
        "n_members":       pa.array([n_contrib] * len(ids), pa.int32()),
    }), args.output)

    pq.write_table(pa.table({
        "sample_id": pa.array(ids, pa.string()),
        "coassoc":   pa.array([row.tolist() for row in coassoc.astype(np.float32)],
                              pa.list_(pa.float32())),
    }), args.coassoc)

    with open(args.weights, "w") as fh:
        json.dump(report, fh, indent=2)

    k = len(np.unique(consensus))
    dropped = [r["run"] for r in report if r["dropped"]]
    print(f"[ensemble] {n_contrib}/{len(names)} members contribute "
          f"(dropped: {dropped or 'none'}) -> {k} consensus clusters @ threshold {args.threshold}")


if __name__ == "__main__":
    main()
