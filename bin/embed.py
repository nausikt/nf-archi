#!/usr/bin/env python3
"""Embed dataset questions via an Ollama embedding endpoint -> parquet."""
import argparse, json, sys
import httpx
import pyarrow as pa
import pyarrow.parquet as pq


def read_jsonl(path):
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def embed_batch(client, endpoint, model, texts):
    resp = client.post(f"{endpoint}/api/embed", json={"model": model, "input": texts})
    resp.raise_for_status()
    return resp.json()["embeddings"]

def build_text(record, fields):
    parts = [str(record[f]) for f in fields if record.get(f)]
    return "\n\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--text-fields", default="question",
                    help="Comma-separated record fields concatenated before embedding")
    ap.add_argument("--batch-size", type=int, default=64)
    args = ap.parse_args()

    fields  = [f.strip() for f in args.text_fields.split(",") if f.strip()]
    records = read_jsonl(args.input)
    ids   = [r["sample_id"] for r in records]
    texts = [build_text(r, fields) for r in records]

    vectors = []
    with httpx.Client(timeout=120) as client:
        for i in range(0, len(texts), args.batch_size):
            vectors.extend(embed_batch(client, args.endpoint, args.model, texts[i:i + args.batch_size]))

    if not vectors:
        sys.exit("No embeddings returned from endpoint")
    dim = len(vectors[0])

    table = pa.table({
        "sample_id":   pa.array(ids, pa.string()),
        "embedding":   pa.array(vectors, pa.list_(pa.float32())),
        "model":       pa.array([args.model] * len(ids), pa.string()),
        "dim":         pa.array([dim] * len(ids), pa.int32()),
        "text_fields": pa.array([",".join(fields)] * len(ids), pa.string()),
    })
    pq.write_table(table, args.output)
    print(f"Wrote {len(ids)} embeddings (dim={dim}, fields={fields}) -> {args.output}")

if __name__ == "__main__":
    main()
