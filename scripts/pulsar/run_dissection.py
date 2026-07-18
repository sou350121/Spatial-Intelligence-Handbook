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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    api_key = get_env("DASHSCOPE_API_KEY")

    cand = wd.pick_candidate(ATLAS, covered_slugs())
    if not cand:
        print("NO_CANDIDATE", file=sys.stderr)
        return 0
    aid, axes, title0 = cand["id"], cand["axes"], cand["title"]
    print(f"  candidate: {cand['rating']} {title0[:60]} ({aid})", file=sys.stderr)

    zone = classify_zone(title0, axes, api_key)
    print(f"  zone: {zone}", file=sys.stderr)

    title, text = wd.fetch_fulltext(aid)
    today = datetime.date.today().isoformat()
    user = (f"arXiv id: {aid}\nTitle: {title}\nontology 5-axis: {json.dumps(axes, ensure_ascii=False)}\n"
            f"今天日期: {today}\n\n论文全文（已截断）:\n{text}")

    # qwen is stochastic — regenerate a few times until the structural guard passes.
    full, missing = "", ["(not generated)"]
    for attempt in range(3):
        md = wd.call_qwen(wd.TEMPLATE, user, api_key)
        md = re.sub(r"^```markdown\s*|\s*```$", "", md.strip()).replace("<module>", zone.split("/")[-1])
        full = wd.ontology_header(axes) + md + f"\n\n<!-- source: https://arxiv.org/abs/{aid} -->\n"
        missing = wd.structural_guard(full)
        if not missing:
            break
        print(f"  guard attempt {attempt+1} missing {missing}; regenerating", file=sys.stderr)
    if missing:
        print(f"GUARD_FAIL after retries: {missing}", file=sys.stderr)
        return 2  # workflow: don't open a PR for a structurally-incomplete draft

    slug = re.sub(r"[^a-z0-9]+", "_", title0.lower()).strip("_")[:50]
    rel = f"{zone}/{slug}_dissection.md"
    if args.dry:
        Path("/tmp/dry_dissection.md").write_text(full)
        print(f"DRY ok · would place at {rel} · {len(full)} chars · guard PASS", file=sys.stderr)
        return 0

    (REPO / rel).write_text(full, encoding="utf-8")
    # Emit PR metadata for the workflow (GITHUB_OUTPUT style key=value).
    print(f"path={rel}")
    print(f"arxiv={aid}")
    print(f"title={title0[:80]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
