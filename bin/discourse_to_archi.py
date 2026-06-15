#!/usr/bin/env python3
"""Convert Discourse thread JSON (cms-talk topic API dumps) into the archi-queries
extended format, keeping a link back to the source thread.

One record per topic:
  - question : the topic title + the opening post (the asker's message)
  - answer   : the rest of the thread's posts, concatenated (the replies)
  - sources  : [the cms-talk URL]   (sources_match_field = ["url"])
  - external_source / external_url / external_id : provenance back to the thread

Single-post topics (announcements with no replies) fall back to title -> question,
opening post -> answer, so nothing is dropped.

Output is chunked by topic month into <prefix>.<YYYY-MM>.json files, so the embed
step can fan out over the months in parallel. The output validates against
schemas/inputs/raw_archi_query_format_extended.json.

Stdlib only (no deps). Example:
    ./bin/discourse_to_archi.py 'raw/**/*.json' -o assets/inputs/crab-talk --prefix crab-talk
"""
import argparse
import glob
import html
import json
import os
import sys
from html.parser import HTMLParser

DEFAULT_BASE_URL = "https://cms-talk.web.cern.ch"
_BLOCK = {"p", "div", "li", "tr", "br", "blockquote", "h1", "h2", "h3", "h4", "pre"}


class _TextExtractor(HTMLParser):
    """Discourse `cooked` is HTML; pull readable text, blocks -> newlines."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        elif tag in _BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        elif tag in _BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(cooked):
    parser = _TextExtractor()
    parser.feed(cooked or "")
    lines = (ln.strip() for ln in "".join(parser.parts).splitlines())
    return "\n".join(ln for ln in lines if ln).strip()


def iter_topics(obj):
    """Yield topic-like dicts from a parsed file (a topic, or a list of topics)."""
    if isinstance(obj, list):
        for item in obj:
            yield from iter_topics(item)
    elif isinstance(obj, dict) and ("post_stream" in obj or "title" in obj):
        yield obj


def posts_of(topic):
    return topic.get("post_stream", {}).get("posts") or topic.get("posts") or []


def topic_month(topic, posts):
    """YYYY-MM from the topic (or first post) creation time; 'undated' if absent."""
    ts = topic.get("created_at") or (posts[0].get("created_at") if posts else None)
    return ts[:7] if isinstance(ts, str) and len(ts) >= 7 else "undated"


def convert(topic, base_url):
    posts = posts_of(topic)
    if not posts:
        return None

    title = html.unescape(topic.get("fancy_title") or topic.get("title") or "").strip()
    first = html_to_text(posts[0].get("cooked"))
    rest = [t for t in (html_to_text(p.get("cooked")) for p in posts[1:]) if t]

    if rest:
        question = "\n\n".join(x for x in (title, first) if x).strip()
        answer = "\n\n".join(rest).strip()
    else:  # single-post thread: title is the question, the lone post is the answer
        question = title or first
        answer = first
    if not question or not answer:
        return None

    post_url = posts[0].get("post_url") or f"/t/{topic.get('slug')}/{topic.get('id')}"
    url = base_url.rstrip("/") + post_url

    record = {
        "question": question,
        "answer": answer,
        "sources": [url],
        "sources_match_field": ["url"],
        "external_source": "discourse",
        "external_url": url,
    }
    if topic.get("id") is not None:
        record["external_id"] = str(topic["id"])
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="*", default=["raw/**/*.json"],
                    help="glob(s) of Discourse JSON files (default: raw/**/*.json)")
    ap.add_argument("-o", "--output-dir", default=".",
                    help="directory for the monthly chunk files (default: .)")
    ap.add_argument("--prefix", default="cms-talk",
                    help="chunk filename prefix -> <prefix>.<YYYY-MM>.json (default: cms-talk)")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL,
                    help=f"Discourse site root for URLs (default: {DEFAULT_BASE_URL})")
    args = ap.parse_args()

    groups, n_files, n_skip = {}, 0, 0
    for pattern in args.inputs:
        for path in sorted(glob.glob(pattern, recursive=True)):
            n_files += 1
            try:
                with open(path) as fh:
                    obj = json.load(fh)
            except (OSError, json.JSONDecodeError) as exc:
                print(f"[discourse] skip {path}: {exc}", file=sys.stderr)
                continue
            for topic in iter_topics(obj):
                rec = convert(topic, args.base_url)
                if rec:
                    groups.setdefault(topic_month(topic, posts_of(topic)), []).append(rec)
                else:
                    n_skip += 1

    os.makedirs(args.output_dir, exist_ok=True)
    total = 0
    for month, records in sorted(groups.items()):
        out_path = os.path.join(args.output_dir, f"{args.prefix}.{month}.json")
        with open(out_path, "w") as fh:
            fh.write(json.dumps(records, indent=2, ensure_ascii=False) + "\n")
        total += len(records)
        print(f"[discourse] {out_path}: {len(records)} records", file=sys.stderr)

    print(f"[discourse] {n_files} files -> {total} records in {len(groups)} month(s) "
          f"({n_skip} topics skipped: no title/answer)", file=sys.stderr)


if __name__ == "__main__":
    main()
