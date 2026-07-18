#!/usr/bin/env python3
"""Spatial Atlas — the star-map data layer.

Every rated paper drops a 5-axis ontology coordinate into an append-only stream
(`reports/atlas/atlas.jsonl`). Over time this stream lets us *measure* the field
instead of just listing it: where the mass sits on the paradigm axis
(geometric → ... → world-model-as-policy), and how it drifts quarter over quarter.

This module is the single owner of that file. Two jobs:
  1. upsert(records)     — merge new coordinates in, dedup by arxiv id
  2. render_overview()   — regenerate the human/agent-readable summary page

CLI:
    python3 scripts/pulsar/atlas.py overview     # rebuild overview.md from atlas.jsonl
    python3 scripts/pulsar/atlas.py stats        # print distribution to stderr

Pure stdlib. Records are the source of truth; overview.md is derived.
"""
from __future__ import annotations
import datetime
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _config import ATLAS_DIR, ATLAS_JSONL, ATLAS_OVERVIEW, AXIS_VOCAB

# Axes with a natural ordering render left→right as classical→frontier so the
# reader sees the field's arc; the rest render by descending frequency.
ORDERED_AXES = ("paradigm", "time")


def make_record(paper: dict, date: str, source: str) -> dict:
    """Build one atlas record from a rated paper. Stable schema — write once."""
    return {
        "id": paper["id"],
        "date": date,
        "title": paper.get("title", ""),
        "link": paper.get("link", ""),
        "category": paper.get("category", ""),
        "rating": paper.get("rating", "📖"),
        "boost": bool(paper.get("boost", False)),
        "axes": paper.get("axes", {}),
        "reason": paper.get("reason", ""),
        "source": source,  # "pipeline" | "backfill"
    }


def load() -> list[dict]:
    """Read all atlas records. Tolerates blank/corrupt lines."""
    if not ATLAS_JSONL.exists():
        return []
    out = []
    for line in ATLAS_JSONL.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def upsert(records: list[dict]) -> tuple[int, int]:
    """Merge records into the stream, dedup by id (new write wins).

    Returns (added, updated). Rewrites the file sorted by (date, id) so diffs
    stay stable and append-order noise doesn't churn git.
    """
    existing = {r["id"]: r for r in load()}
    added = updated = 0
    for r in records:
        if r["id"] in existing:
            updated += 1
        else:
            added += 1
        existing[r["id"]] = r
    ordered = sorted(existing.values(), key=lambda r: (r.get("date", ""), r.get("id", "")))
    ATLAS_DIR.mkdir(parents=True, exist_ok=True)
    with ATLAS_JSONL.open("w", encoding="utf-8") as f:
        for r in ordered:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return added, updated


def _bar(n: int, peak: int, width: int = 24) -> str:
    if peak <= 0:
        return ""
    filled = round(width * n / peak)
    return "█" * filled + "·" * (width - filled)


def _axis_table(records: list[dict], axis: str) -> list[str]:
    counts = Counter(
        r.get("axes", {}).get(axis, "n/a")
        for r in records
        if r.get("axes", {}).get(axis, "n/a") != "n/a"
    )
    if not counts:
        return ["_(no coordinates yet)_", ""]
    if axis in ORDERED_AXES:
        # classical → frontier, following the controlled-vocab order
        items = [(v, counts.get(v, 0)) for v in AXIS_VOCAB[axis] if counts.get(v, 0)]
    else:
        items = counts.most_common()
    peak = max(n for _, n in items)
    lines = ["```", f"{'axis value':<26} count"]
    for val, n in items:
        lines.append(f"{val:<26} {_bar(n, peak)} {n}")
    lines.append("```")
    lines.append("")
    return lines


def _week_key(date_str: str) -> str:
    y, w, _ = datetime.date.fromisoformat(date_str).isocalendar()
    return f"{y}-W{w:02d}"


def _paradigm_drift_table(records: list[dict], max_weeks: int = 8) -> list[str]:
    """Paradigm × ISO-week cross-table — the drift instrument itself.

    Rows follow the controlled-vocab order (classical → frontier), so the field
    moving toward world models literally reads as the table getting heavier
    toward the bottom rows as weeks advance.
    """
    buckets: dict[str, Counter] = {}
    for r in records:
        try:
            wk = _week_key(r.get("date", ""))
        except ValueError:
            continue
        v = r.get("axes", {}).get("paradigm", "n/a")
        if v == "n/a":
            continue
        buckets.setdefault(wk, Counter())[v] += 1
    if not buckets:
        return ["_(no coordinates yet)_", ""]
    weeks = sorted(buckets)[-max_weeks:]
    lines = [
        "| paradigm \\ week | " + " | ".join(w[5:] for w in weeks) + " |",  # show "W28"
        "|---|" + "---:|" * len(weeks),
    ]
    for v in AXIS_VOCAB["paradigm"]:
        cells = [(str(buckets[w][v]) if buckets[w][v] else "·") for w in weeks]
        lines.append(f"| {v} | " + " | ".join(cells) + " |")
    totals = [str(sum(buckets[w].values())) for w in weeks]
    lines.append("| **total** | " + " | ".join(f"**{t}**" for t in totals) + " |")
    lines.append("")
    return lines


def render_overview(records: list[dict]) -> str:
    total = len(records)
    dates = sorted({r.get("date", "") for r in records if r.get("date")})
    span = f"{dates[0]} → {dates[-1]}" if dates else "—"
    ratings = Counter(r.get("rating", "📖") for r in records)

    lines = [
        "# 🌌 Spatial Atlas — Ontology Coordinate Map",
        "",
        "> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.",
        "> The point is not the list — it is the **drift**: watch where mass accumulates on the",
        "> paradigm axis (geometric → … → world-model-as-policy) as the field moves.",
        "",
        f"**Coverage:** {total} papers · {span} · "
        f"⚡ {ratings.get('⚡', 0)} · 🔧 {ratings.get('🔧', 0)} · 📖 {ratings.get('📖', 0)}",
        "",
        "> Seed corpus — grows every weekday as the daily pipeline runs. "
        "Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).",
        "",
        "---",
        "",
        "## Paradigm axis — where the field sits",
        "",
        "_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._",
        "",
    ]
    lines += _axis_table(records, "paradigm")
    lines += [
        "### Paradigm drift by week",
        "",
        "_Rows ordered classical → frontier. The field moving toward world models reads as",
        "the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_",
        "",
    ]
    lines += _paradigm_drift_table(records)
    lines += ["## Time axis — batch → streaming frontier", ""]
    lines += _axis_table(records, "time")
    lines += ["## Problem axis — what is being solved", ""]
    lines += _axis_table(records, "problem")
    lines += ["## Representation axis", ""]
    lines += _axis_table(records, "representation")
    lines += ["## Sensor axis", ""]
    lines += _axis_table(records, "sensor")

    # Recent paradigm-frontier ⚡ picks — the leading edge, most-recent first.
    frontier = {"generative", "3R-SLAM-hybrid", "VLA", "world-model-as-policy"}
    edge = [
        r for r in sorted(records, key=lambda r: r.get("date", ""), reverse=True)
        if r.get("rating") == "⚡" and r.get("axes", {}).get("paradigm") in frontier
    ][:8]
    if edge:
        lines += ["---", "", "## ⚡ Leading edge (recent frontier-paradigm breakthroughs)", ""]
        for r in edge:
            para = r.get("axes", {}).get("paradigm", "?")
            lines.append(f"- **[{r['title']}]({r['link']})** — `{para}` · {r.get('date','')}")
            if r.get("reason"):
                lines.append(f"  - _{r['reason']}_")
        lines.append("")

    lines += [
        "---",
        "",
        "_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. "
        "Ratings here use the calibrated prompt and may differ from the archived daily reports._",
    ]
    return "\n".join(lines)


def write_overview() -> Path:
    records = load()
    ATLAS_DIR.mkdir(parents=True, exist_ok=True)
    ATLAS_OVERVIEW.write_text(render_overview(records), encoding="utf-8")
    return ATLAS_OVERVIEW


def _print_stats() -> None:
    records = load()
    print(f"  atlas: {len(records)} records", file=sys.stderr)
    for axis in AXIS_VOCAB:
        c = Counter(r.get("axes", {}).get(axis, "n/a") for r in records)
        print(f"    {axis}: {dict(c)}", file=sys.stderr)


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "overview"
    if cmd == "overview":
        p = write_overview()
        print(f"  Wrote {p} ({len(load())} records)", file=sys.stderr)
    elif cmd == "stats":
        _print_stats()
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
