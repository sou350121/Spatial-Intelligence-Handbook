#!/usr/bin/env python3
"""LLM rate papers ⚡/🔧/📖/❌ — DeepSeek deepseek-flash, qwen fallback.

Usage:
    python3 scripts/pulsar/collect.py | python3 scripts/pulsar/rate.py
    # or:
    python3 scripts/pulsar/rate.py --in papers.json --out rated.json

Reads JSON list from stdin, writes JSON list with added .rating / .reason / .tags
to stdout. Skips ❌ papers from output (configurable).

Requires: DEEPSEEK_API_KEY (primary) and/or DASHSCOPE_API_KEY (fallback).
Pure stdlib + urllib for HTTP (no openai SDK to keep deps light).
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _llm
from _config import RATING_PROMPT_SYSTEM, AXIS_VOCAB, get_env

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
    """Rate one paper. DeepSeek primary, qwen fallback (see _llm.py).

    Name kept for the call sites (backfill_atlas.py imports rate.rate_one).
    `require_json="object"` is what makes an HTTP 200 with an unparseable body
    fall back to qwen instead of silently becoming a 📖 placeholder.
    """
    return _llm.chat(messages, temperature=0.1,  # low temp for rating consistency
                     require_json="object", qwen_key=api_key, label="rate")


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
        # _llm.chat(require_json=...) already salvaged and re-serialised this,
        # so a decode error here means both providers were exhausted upstream
        # (which raises) — kept as belt-and-braces only.
        result = json.loads(raw)
    except json.JSONDecodeError:
        print(f"  WARN: invalid JSON for {paper['id']}", file=sys.stderr)
        result = {"rating": "📖", "reason": "(parse error)", "axes": {}}

    rating = result.get("rating", "📖")
    paper["rating"] = rating if rating in VALID_RATINGS else "📖"
    paper["reason"] = result.get("reason", "")
    paper["axes"] = clean_axes(result.get("axes", {}))
    paper["tags"] = derive_tags(paper["axes"])  # display labels, back-compat
    # Which model actually answered — the report banner used to hardcode
    # "qwen3.5-plus" and kept claiming it through 8 days of 401s.
    paper["model"] = _llm.LAST_MODEL
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

        # Optional: _llm falls back to qwen only if this is set. An absent or
        # dead DashScope key is no longer fatal on its own (DeepSeek is primary),
        # but it must not be silently pretended-away either — _llm logs it.
        api_key = get_env("DASHSCOPE_API_KEY", required=False)
        if not api_key:
            print("  NOTE: DASHSCOPE_API_KEY not set — qwen fallback disabled "
                  "(DeepSeek only)", file=sys.stderr)
        rated = []
        failed = 0
        for i, p in enumerate(papers):
            print(f"  Rating {i+1}/{len(papers)}: {p['id']} ({p.get('category')})", file=sys.stderr)
            try:
                rated.append(rate_one(p, api_key))
            except Exception as e:
                # Per-paper resilience is deliberate: one bad abstract or one
                # timeout must not lose the other 79. What was NOT deliberate is
                # what happens when EVERY call fails — 2026-08-31..09-07 each
                # shipped a committed report of 80 papers, ⚡0 🔧0 📖80, every
                # line "(rating error: … HTTP Error 401)". The all-failed guard
                # below turns that into a red run instead.
                failed += 1
                print(f"  ERROR rating {p['id']}: {e}", file=sys.stderr)
                p["rating"] = "📖"
                p["reason"] = f"(rating error: {e})"
                p["axes"] = clean_axes({})
                p["tags"] = []
                rated.append(p)

        if failed and failed == len(papers):
            print(f"  FATAL: all {failed} rating call(s) failed — refusing to emit a "
                  f"placeholder report. Check DEEPSEEK_API_KEY / DASHSCOPE_API_KEY.",
                  file=sys.stderr)
            return 1
        if failed:
            print(f"  WARN: {failed}/{len(papers)} paper(s) could not be rated "
                  f"(kept as 📖 with the error inline)", file=sys.stderr)

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
