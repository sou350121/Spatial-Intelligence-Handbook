#!/usr/bin/env python3
"""Orchestrate one dissection: qwen writes, a workflow opens a PR, Opus/human verifies.

pick perception ⚡ from the atlas → qwen classify a zone → qwen write the full
dissection from arXiv full text → structural guard → place the file. The caller
(a GitHub Actions workflow) then opens a PR so an Opus/human reviewer verifies the
facts, confirms the zone, and merges (merge triggers the mechanical count-sync).

Nothing auto-lands on main: the "Opus 验" gate is the PR review.

Usage:
    DASHSCOPE_API_KEY=... python3 scripts/pulsar/run_dissection.py            # place + emit PR metadata
    DASHSCOPE_API_KEY=... python3 scripts/pulsar/run_dissection.py --dry      # /tmp preview, no placement
"""
from __future__ import annotations
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _config import get_env
import write_dissection as wd

REPO = Path(__file__).resolve().parent.parent.parent
ATLAS = REPO / "reports" / "atlas" / "atlas.jsonl"

# Zones a Spatial dissection can land in (perception territory). qwen picks one.
ZONES = [
    "foundations/feed-forward-3d", "foundations/3dgs-family", "foundations/nerf-family",
    "foundations/depth-foundation", "foundations/classical-slam", "foundations/pose-tracking",
    "foundations/semantic-3d", "foundations/world-model", "foundations/vlm-spatial-reasoning",
    "foundations/sensor-physics", "foundations/spatial-math",
    "embodiments/aerial", "embodiments/driving", "embodiments/manipulation", "embodiments/marine",
]


def covered_slugs() -> set[str]:
    out = set()
    for f in REPO.glob("**/*_dissection.md"):
        out.add(re.sub(r"[^a-z0-9]+", "", f.name.replace("_dissection.md", "").lower())[:40])
    return out


def classify_zone(title: str, axes: dict, api_key: str) -> str:
    prompt = (
        "从下面固定列表里选**一个**最贴切的目录给这篇 spatial-AI 论文归档，只输出目录字符串本身:\n"
        + "\n".join(ZONES)
        + f"\n\n论文标题: {title}\nontology: {json.dumps(axes, ensure_ascii=False)}\n只输出一个目录路径。"
    )
    ans = wd.call_qwen("你是 Spatial-Handbook 的归档分类器，只输出一个目录路径。", prompt,
                       api_key, max_tokens=40).strip().strip("`").strip()
    for z in ZONES:
        if z in ans:
            return z
    return "foundations/feed-forward-3d"  # safe default


def write_one(cand: dict, api_key: str, dry: bool) -> str | None:
    """Generate one guarded + fact-checked dissection; place it. Return rel path or None."""
    aid, axes, title0 = cand["id"], cand["axes"], cand["title"]
    print(f"  candidate: {cand['rating']} {title0[:58]} ({aid})", file=sys.stderr)
    zone = classify_zone(title0, axes, api_key)
    try:
        title, text = wd.fetch_fulltext(aid)
    except Exception as e:
        print(f"  skip {aid}: full text fetch failed ({e})", file=sys.stderr)
        return None
    today = datetime.date.today().isoformat()
    user = (f"arXiv id: {aid}\nTitle: {title}\nontology 5-axis: {json.dumps(axes, ensure_ascii=False)}\n"
            f"今天日期: {today}\n\n论文全文（已截断）:\n{text}")

    # generate → structural guard → qwen fact-check; regenerate on either failure.
    for attempt in range(3):
        md = wd.call_qwen(wd.TEMPLATE, user, api_key)
        md = re.sub(r"^```markdown\s*|\s*```$", "", md.strip()).replace("<module>", zone.split("/")[-1])
        full = wd.ontology_header(axes) + md + f"\n\n<!-- source: https://arxiv.org/abs/{aid} -->\n"
        missing = wd.structural_guard(full)
        if missing:
            print(f"  attempt {attempt+1}: guard missing {missing}; regen", file=sys.stderr)
            continue
        ok, issues = wd.factcheck(full, text, api_key)
        if not ok:
            print(f"  attempt {attempt+1}: factcheck flagged {issues[:2]}; regen", file=sys.stderr)
            continue
        # passed both gates
        if dry:
            Path("/tmp/dry_dissection.md").write_text(full)
            print(f"  DRY ok · {zone} · guard+factcheck PASS", file=sys.stderr)
            return f"{zone}/(dry)"
        slug = re.sub(r"[^a-z0-9]+", "_", title0.lower()).strip("_")[:50]
        rel = f"{zone}/{slug}_dissection.md"
        (REPO / rel).write_text(full, encoding="utf-8")
        print(f"  placed {rel}", file=sys.stderr)
        return rel
    print(f"  skip {aid}: failed guard/factcheck after retries", file=sys.stderr)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--count", type=int, default=1, help="dissections to write this run")
    args = ap.parse_args()
    api_key = get_env("DASHSCOPE_API_KEY")

    placed = []
    for _ in range(args.count):
        cand = wd.pick_candidate(ATLAS, covered_slugs() | {re.sub(r'[^a-z0-9]+','',Path(p).name.replace('_dissection.md','').lower())[:40] for p in placed})
        if not cand:
            print("NO_CANDIDATE (pool exhausted)", file=sys.stderr)
            break
        rel = write_one(cand, api_key, args.dry)
        if rel and not args.dry:
            placed.append(rel)
        if args.dry:
            break
    for p in placed:
        print(f"path={p}")
    print(f"placed={len(placed)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
