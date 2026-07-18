#!/usr/bin/env python3
"""LLM rate papers ⚡/🔧/📖/❌ via DashScope qwen3.5-plus.

Usage:
    python3 scripts/pulsar/collect.py | python3 scripts/pulsar/rate.py
    # or:
    python3 scripts/pulsar/rate.py --in papers.json --out rated.json

Reads JSON list from stdin, writes JSON list with added .rating / .reason / .tags
to stdout. Skips ❌ papers from output (configurable).

Requires: DASHSCOPE_API_KEY env var.
Pure stdlib + urllib for HTTP (no openai SDK to keep deps light).
"""
from __future__ import annotations
import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _config import (
    DASHSCOPE_BASE_URL, LLM_MODEL, LLM_TIMEOUT,
    LLM_RETRY, LLM_RETRY_BACKOFF,
    RATING_PROMPT_SYSTEM, AXIS_VOCAB, get_env,
)

VALID_RATINGS = {"⚡", "🔧", "📖", "❌"}


def clean_axes(raw: dict) -> dict:
    """Coerce the model's axes dict onto the controlled vocabulary.

    Off-vocab / missing values become 'n/a' so the atlas never accumulates
    junk coordinates. Case/space tolerant; the vocab is the source of truth.
    """
    axes: dict[str, str] = {}
    raw = raw if isinstance(raw, dict) else {}
    for axis, vocab in AXIS_VOCAB.items():
        val = str(raw.get(axis, "n/a")).strip()
        lut = {v.lower(): v for v in vocab}
        axes[axis] = lut.get(val.lower(), "n/a")
    return axes


def derive_tags(axes: dict) -> list[str]:
    """Human/agent-readable coordinate labels for markdown, e.g. 'paradigm: VLA'.
    Only non-n/a axes are shown; paradigm/time (the ordered axes) come first.
    """
    order = ["paradigm", "time", "problem", "representation", "sensor"]
    return [f"{a}: {axes[a]}" for a in order if axes.get(a, "n/a") != "n/a"]


def call_qwen(messages: list[dict], api_key: str) -> str:
    """Call DashScope qwen via OpenAI-compatible API. Return assistant text."""
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": 0.1,  # low temp for rating consistency
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        f"{DASHSCOPE_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    last_err = None
    for attempt in range(LLM_RETRY):
        try:
            with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as r:
                body = r.read().decode("utf-8")
            data = json.loads(body)
            return data["choices"][0]["message"]["content"]
        except (urllib.error.HTTPError, urllib.error.URLError, KeyError) as e:
            last_err = e
            code = getattr(e, "code", "n/a")
            print(f"  WARN: qwen call failed (attempt {attempt+1}, code={code}): {e}", file=sys.stderr)
            if attempt < LLM_RETRY - 1:
                time.sleep(LLM_RETRY_BACKOFF * (attempt + 1))
    raise RuntimeError(f"qwen all {LLM_RETRY} attempts failed: {last_err}")


def rate_one(paper: dict, api_key: str) -> dict:
    """Rate a single paper. Returns paper dict + .rating / .reason / .tags."""
    user_msg = (
        f"Title: {paper['title']}\n"
        f"Category: {paper.get('category', 'n/a')}\n"
        f"Abstract: {paper['abstract'][:1500]}"  # cap to avoid token bloat
    )
    if paper.get("boost"):
        user_msg += "\n(Title contains production/aerial/benchmark signal — boost priority.)"

    messages = [
        {"role": "system", "content": RATING_PROMPT_SYSTEM},
        {"role": "user", "content": user_msg},
    ]
    raw = call_qwen(messages, api_key)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # Best-effort recovery if model didn't return valid JSON
        print(f"  WARN: invalid JSON from qwen for {paper['id']}", file=sys.stderr)
        result = {"rating": "📖", "reason": "(parse error)", "axes": {}}

    rating = result.get("rating", "📖")
    paper["rating"] = rating if rating in VALID_RATINGS else "📖"
    paper["reason"] = result.get("reason", "")
    paper["axes"] = clean_axes(result.get("axes", {}))
    paper["tags"] = derive_tags(paper["axes"])  # display labels, back-compat
    return paper


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", help="input JSON file (default: stdin)")
    ap.add_argument("--out", dest="outfile", help="output JSON file (default: stdout)")
    ap.add_argument("--keep-rejects", action="store_true", help="keep ❌ rated papers in output")
    ap.add_argument("--max", type=int, default=80, help="cap papers to rate (avoid LLM cost blow up)")
    args = ap.parse_args()

    if args.infile:
        papers = json.loads(Path(args.infile).read_text())
    else:
        papers = json.loads(sys.stdin.read())

    if not papers:
        print("  (no papers to rate)", file=sys.stderr)
        out = []
    else:
        # Boost papers first, then by category priority
        cat_priority = {"cs.RO": 0, "cs.CV": 1, "cs.AI": 2, "cs.LG": 3}
        papers.sort(key=lambda p: (not p.get("boost"), cat_priority.get(p.get("category"), 9)))
        papers = papers[:args.max]

        api_key = get_env("DASHSCOPE_API_KEY")
        rated = []
        for i, p in enumerate(papers):
            print(f"  Rating {i+1}/{len(papers)}: {p['id']} ({p.get('category')})", file=sys.stderr)
            try:
                rated.append(rate_one(p, api_key))
            except Exception as e:
                print(f"  ERROR rating {p['id']}: {e}", file=sys.stderr)
                p["rating"] = "📖"
                p["reason"] = f"(rating error: {e})"
                p["axes"] = clean_axes({})
                p["tags"] = []
                rated.append(p)

        if not args.keep_rejects:
            out = [p for p in rated if p.get("rating") != "❌"]
            print(f"  Kept {len(out)}/{len(rated)} (dropped ❌)", file=sys.stderr)
        else:
            out = rated

    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.outfile:
        Path(args.outfile).write_text(text)
    else:
        print(text)

    # Summary
    if out:
        from collections import Counter
        ratings = Counter(p["rating"] for p in out)
        print(f"  Rating distribution: {dict(ratings)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
