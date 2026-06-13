#!/usr/bin/env python3
"""Per-cluster representative sampling for the expert's first review pass.

For each consensus cluster, pick a few records in three roles:
  - medoid   : highest similarity to its own cluster centroid (most typical)
  - boundary : smallest margin = sim_own - sim_other (torn between two clusters)
  - outlier  : far from every centroid OR frequently called noise by HDBSCAN
               outlierness = max(1 - max_sim, noise_rate)

`score` is normalized to [0, 1] so higher always means a stronger example of the
role. Roles are selected independently, so a record may appear under more than
one role (rare).
"""
import argparse
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from sklearn.preprocessing import normalize


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--embeddings", required=True)
    ap.add_argument("--ensemble", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--n-medoid", type=int, default=3)
    ap.add_argument("--n-boundary", type=int, default=5)
    ap.add_argument("--n-outlier", type=int, default=3)
    args = ap.parse_args()

    ens = pq.read_table(args.ensemble).to_pandas()
    emb = pq.read_table(args.embeddings).to_pandas().set_index("sample_id")
    emb = emb.reindex(ens["sample_id"])              # align to ensemble order

    X = normalize(np.asarray(emb["embedding"].tolist(), dtype=np.float32))
    consensus = ens["consensus_label"].to_numpy()
    stability = ens["stability"].to_numpy()
    noise_rate = ens["noise_rate"].to_numpy()
    n = len(ens)

    # L2-normalized centroid per consensus cluster
    clusters = sorted(set(int(c) for c in consensus))
    col = {c: j for j, c in enumerate(clusters)}
    C = np.vstack([
        normalize(X[consensus == c].mean(axis=0, keepdims=True))[0]
        for c in clusters
    ])

    sims = X @ C.T                                    # [n_samples x n_clusters]
    own_col = np.array([col[int(c)] for c in consensus])
    sim_own = sims[np.arange(n), own_col]

    masked = sims.copy()
    masked[np.arange(n), own_col] = -np.inf
    sim_other = masked.max(axis=1)
    sim_other[~np.isfinite(sim_other)] = 0.0         # single-cluster case

    margin = sim_own - sim_other
    max_sim = np.maximum(sim_own, sim_other)
    outlierness = np.maximum(1.0 - max_sim, noise_rate)

    base = pd.DataFrame({
        "sample_id": ens["sample_id"].to_numpy(),
        "consensus_label": consensus.astype(int),
        "sim_own": sim_own, "sim_other": sim_other, "margin": margin,
        "stability": stability, "noise_rate": noise_rate, "max_sim": max_sim,
    })

    def pick(df, by, ascending, score, n):
        sel = df.sort_values(by, ascending=ascending).head(n).copy()
        sel["score"] = np.clip(score(sel), 0.0, 1.0)
        sel["rank"] = np.arange(1, len(sel) + 1)
        return sel

    base["outlierness"] = np.maximum(1.0 - base["max_sim"], base["noise_rate"])

    parts = []
    for c in clusters:
        g = base[base["consensus_label"] == c]
        parts.append(pick(g, "sim_own",     False, lambda d: d["sim_own"],      args.n_medoid).assign(role="medoid"))
        parts.append(pick(g, "margin",      True,  lambda d: 1.0 - d["margin"], args.n_boundary).assign(role="boundary"))
        parts.append(pick(g, "outlierness", False, lambda d: d["outlierness"],  args.n_outlier).assign(role="outlier"))

    out = pd.concat(parts, ignore_index=True)
    cols = ["sample_id", "consensus_label", "role", "score", "rank",
            "sim_own", "sim_other", "margin", "stability", "noise_rate", "max_sim"]
    out = out[cols]
    pq.write_table(pa.Table.from_pandas(out, preserve_index=False), args.output)

    counts = out.groupby("role")["sample_id"].count().to_dict()
    print(f"[representatives] {len(clusters)} clusters -> {len(out)} picks "
          f"({counts}) -> {args.output}")


if __name__ == "__main__":
    main()
