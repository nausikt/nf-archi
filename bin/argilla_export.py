#!/usr/bin/env python3
"""Package the bootstrapping prelabels + representatives into an Argilla dataset.

This is the last hop of the bootstrapping workflow: it turns the machine's best
guesses into a human review queue. Each record is one sample carrying

  - fields:      the original question/answer text (from dataset.jsonl)
  - suggestions: the anchor-consensus prelabels, ranked within each kind
                 (category -> single label, tags/flags -> multi-label), scored
                 by raw-embedding cosine — what the expert accepts or corrects
  - metadata:    consensus cluster, representative role, stability, batch

By default only the *representatives* (the curated per-cluster review subset)
are exported — that is the first expert pass. `--scope all` ships every sample.

Connection: the api key is read from $ARGILLA_API_KEY (never a CLI arg, so it
never lands in the Nextflow command line / logs); the url falls back to
$ARGILLA_API_URL. `--dry-run` builds and previews records without importing the
argilla SDK or touching the network.
"""
import argparse
import json
import math
import os

import pandas as pd
import pyarrow.parquet as pq

# The Argilla dataset is named "<PROJECT>-<version>"; the project is fixed and the
# version is bumped per expert pass (iterative bootstrapping), e.g. archi-bootstrap-v0.0.1.
PROJECT = "archi-bootstrap"

# anchor_kind (singular, as in prelabels/anchors_meta) -> Argilla question name
KIND_QUESTION = {"category": "category", "tag": "tags", "flag": "flags"}
MULTI_KINDS = {"tag", "flag"}
ROLE_PRIORITY = {"medoid": 0, "boundary": 1, "outlier": 2}


def read_jsonl(path):
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def clean_float(x):
    """NaN/inf -> None; everything else -> float (Argilla rejects NaN)."""
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def label_sets(anchor_meta_path, prelabels):
    """Per-kind ordered label names. Prefer anchors_meta (the full taxonomy, incl.
    anchors nobody was suggested), fall back to the names seen in prelabels."""
    by_kind = {}
    if anchor_meta_path and os.path.exists(anchor_meta_path):
        for m in read_jsonl(anchor_meta_path):
            by_kind.setdefault(m["kind"], [])
            if m["name"] not in by_kind[m["kind"]]:
                by_kind[m["kind"]].append(m["name"])
    else:
        for kind, grp in prelabels.groupby("anchor_kind"):
            by_kind[kind] = list(dict.fromkeys(grp["anchor_name"].tolist()))
    return by_kind


def suggestions_by_sample(prelabels, top_k_tags):
    """sample_id -> {kind: [(name, score), ...]} ranked, capped for multi kinds."""
    out = {}
    for sid, grp in prelabels.groupby("sample_id"):
        grp = grp.sort_values("rank")
        per_kind = {}
        for kind, kgrp in grp.groupby("anchor_kind"):
            picks = [(r["anchor_name"], clean_float(r["score"])) for _, r in kgrp.iterrows()]
            per_kind[kind] = picks if kind not in MULTI_KINDS else picks[:top_k_tags]
        out[str(sid)] = per_kind
    return out


def representative_roles(reps):
    """sample_id -> (primary_role, [all roles]) collapsing multi-role samples."""
    out = {}
    for sid, grp in reps.groupby("sample_id"):
        roles = list(dict.fromkeys(grp["role"].tolist()))
        primary = min(roles, key=lambda r: ROLE_PRIORITY.get(r, 99))
        out[str(sid)] = (primary, roles)
    return out


def build_records(args):
    """Pure assembly: returns (settings_spec, records_spec) as plain dicts so it
    can run without the argilla SDK (dry-run / tests)."""
    dataset = {str(r["sample_id"]): r for r in read_jsonl(args.dataset)}
    prelabels = pq.read_table(args.prelabels).to_pandas()
    ens = pq.read_table(args.ensemble).to_pandas().set_index("sample_id")

    label_by_kind = label_sets(args.anchor_meta, prelabels)
    sugg = suggestions_by_sample(prelabels, args.top_k_tags)

    # roles are always attached (even in 'all' scope, representative samples keep
    # their medoid/boundary/outlier tags); scope only decides which samples ship.
    roles = representative_roles(pq.read_table(args.representatives).to_pandas())
    sample_ids = list(roles.keys()) if args.scope == "representatives" else list(dataset.keys())

    # ---- settings spec (questions only for kinds that actually have anchors) ----
    questions = []
    for kind, qname in KIND_QUESTION.items():
        labels = label_by_kind.get(kind)
        if labels:
            questions.append({
                "name": qname,
                "kind": kind,
                "multi": kind in MULTI_KINDS,
                "labels": labels,
                "required": False,
            })
    # Argilla refuses to publish a dataset with no required question; make the
    # first available one (category if present) mandatory for the reviewer.
    if questions:
        questions[0]["required"] = True
    settings_spec = {"fields": ["question", "answer"], "questions": questions}

    # ---- record specs ----
    records = []
    skipped = 0
    for sid in sample_ids:
        row = dataset.get(sid)
        if row is None:
            skipped += 1
            continue
        e = ens.loc[sid] if sid in ens.index else None
        primary, all_roles = roles.get(sid, (None, []))

        metadata = {
            "sample_id": sid,
            "batch": row.get("batch"),
            "consensus_label": int(e["consensus_label"]) if e is not None else None,
            "stability": clean_float(e["stability"]) if e is not None else None,
            "role": primary,                       # primary role (medoid > boundary > outlier)
            "roles": all_roles or None,            # all sampling roles (multi-term, filterable)
        }

        record_sugg = []
        for q in questions:
            picks = sugg.get(sid, {}).get(q["kind"])
            if not picks:
                continue
            if q["multi"]:
                value = [n for n, _ in picks]
                score = [s for _, s in picks]
                if any(s is None for s in score):
                    score = None
            else:
                value, score = picks[0]
            record_sugg.append({"question": q["name"], "value": value, "score": score})

        records.append({
            "id": sid,
            "fields": {
                "question": str(row.get("question") or ""),
                "answer": str(row.get("answer") or ""),
            },
            "metadata": {k: v for k, v in metadata.items() if v is not None},
            "suggestions": record_sugg,
        })

    return settings_spec, records, skipped


def to_argilla_settings(settings_spec, guidelines):
    import argilla as rg

    fields = [
        rg.TextField(name="question", title="Question", use_markdown=True),
        rg.TextField(name="answer", title="Answer", use_markdown=True),
    ]
    questions = []
    for q in settings_spec["questions"]:
        cls = rg.MultiLabelQuestion if q["multi"] else rg.LabelQuestion
        questions.append(cls(name=q["name"], title=q["name"].capitalize(),
                             labels=q["labels"], required=q.get("required", False)))
    questions.append(rg.TextQuestion(name="note", title="Reviewer note", required=False))

    metadata = [
        rg.TermsMetadataProperty(name="sample_id"),
        rg.TermsMetadataProperty(name="batch"),
        rg.IntegerMetadataProperty(name="consensus_label"),
        rg.FloatMetadataProperty(name="stability"),
        rg.TermsMetadataProperty(name="role", options=list(ROLE_PRIORITY)),
        rg.TermsMetadataProperty(name="roles", options=list(ROLE_PRIORITY)),
    ]
    return rg.Settings(guidelines=guidelines, fields=fields,
                       questions=questions, metadata=metadata,
                       allow_extra_metadata=True)


def to_argilla_records(record_specs):
    import argilla as rg

    out = []
    for r in record_specs:
        suggestions = []
        for s in r["suggestions"]:
            try:
                suggestions.append(rg.Suggestion(s["question"], s["value"],
                                                 score=s["score"], agent="anchor-consensus"))
            except Exception:
                suggestions.append(rg.Suggestion(s["question"], s["value"],
                                                 agent="anchor-consensus"))
        out.append(rg.Record(id=r["id"], fields=r["fields"],
                             metadata=r["metadata"], suggestions=suggestions))
    return out


def upload(settings_spec, record_specs, args):
    import argilla as rg

    api_url = args.api_url or os.environ.get("ARGILLA_API_URL")
    api_key = os.environ.get("ARGILLA_API_KEY") or args.api_key
    if not api_url or not api_key:
        raise SystemExit("[argilla] missing connection: set --api-url/$ARGILLA_API_URL "
                         "and $ARGILLA_API_KEY")

    client = rg.Argilla(api_url=api_url, api_key=api_key)

    # ensure the target workspace exists (create needs an owner/admin key)
    workspace = client.workspaces(name=args.workspace)
    if workspace is None:
        try:
            workspace = rg.Workspace(name=args.workspace, client=client).create()
            print(f"[argilla] created workspace '{args.workspace}'")
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(
                f"[argilla] workspace '{args.workspace}' does not exist and could not be "
                f"created ({exc}). Create it in the Argilla UI / with an owner key, or "
                f"point --argilla.workspace at an existing one."
            ) from exc

    existing = client.datasets(name=args.dataset_name, workspace=args.workspace)
    if existing is not None and args.overwrite:
        existing.delete()
        existing = None

    if existing is None:
        settings = to_argilla_settings(settings_spec, args.guidelines)
        dataset = rg.Dataset(name=args.dataset_name, workspace=args.workspace, settings=settings)
        dataset.create()
    else:
        dataset = existing  # append / update by record id

    dataset.records.log(to_argilla_records(record_specs))
    return f"{api_url.rstrip('/')}/dataset/{dataset.id}/annotation-mode"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, help="dataset.jsonl (original text)")
    ap.add_argument("--prelabels", required=True, help="prelabels.parquet")
    ap.add_argument("--representatives", required=True, help="representatives.parquet")
    ap.add_argument("--ensemble", required=True, help="ensemble.parquet (consensus)")
    ap.add_argument("--anchor-meta", default=None, help="anchors_meta.jsonl (full label sets)")
    ap.add_argument("--scope", choices=["representatives", "all"], default="representatives")
    ap.add_argument("--top-k-tags", type=int, default=5)
    ap.add_argument("--api-url", default=None)
    ap.add_argument("--api-key", default=None, help="prefer $ARGILLA_API_KEY")
    ap.add_argument("--workspace", default="argilla")
    ap.add_argument("--version", default="v0.0.1",
                    help=f"dataset version suffix; dataset name = {PROJECT}-<version>")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--guidelines", default="Review the anchor-consensus suggestions: "
                    "confirm the category, adjust tags/flags, and add a note when unsure.")
    ap.add_argument("--dry-run", action="store_true",
                    help="build + preview records without contacting Argilla")
    ap.add_argument("--output", required=True, help="summary json")
    args = ap.parse_args()

    args.dataset_name = f"{PROJECT}-{args.version}"

    settings_spec, records, skipped = build_records(args)

    n_sugg = sum(len(r["suggestions"]) for r in records)
    summary = {
        "dataset_name": args.dataset_name,
        "workspace": args.workspace,
        "scope": args.scope,
        "n_records": len(records),
        "n_suggestions": n_sugg,
        "n_skipped_no_text": skipped,
        "questions": [q["name"] for q in settings_spec["questions"]],
        "dry_run": args.dry_run,
    }

    if args.dry_run:
        summary["preview"] = records[:3]
        summary["url"] = None
        print(f"[argilla] DRY-RUN: {len(records)} records ({args.scope}), "
              f"{n_sugg} suggestions, questions={summary['questions']}")
    else:
        summary["url"] = upload(settings_spec, records, args)
        print(f"[argilla] pushed {len(records)} records to "
              f"'{args.workspace}/{args.dataset_name}' -> {summary['url']}")

    with open(args.output, "w") as fh:
        json.dump(summary, fh, indent=2)


if __name__ == "__main__":
    main()
