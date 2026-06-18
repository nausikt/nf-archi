#!/usr/bin/env python3
"""Concatenate parquet shards into a single file, sorted for determinism.

Used to fold the per-chunk embedding shards (one per input batch/month, embedded
in parallel) back into one embeddings.parquet for the reduction stage.
"""
import argparse

import pyarrow as pa
import pyarrow.parquet as pq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True, help="parquet shards")
    ap.add_argument("--output", required=True)
    ap.add_argument("--sort-by", default="sample_id",
                    help="column to sort the merged table by (skipped if absent)")
    args = ap.parse_args()

    table = pa.concat_tables((pq.read_table(p) for p in args.inputs),
                             promote_options="default")
    if args.sort_by in table.column_names:
        table = table.sort_by(args.sort_by)
    pq.write_table(table, args.output)
    print(f"[merge] {len(args.inputs)} shards, {table.num_rows} rows -> {args.output}")


if __name__ == "__main__":
    main()
