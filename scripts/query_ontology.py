#!/usr/bin/env python3
"""Query handbook by ontology 5-axis coordinates.

每篇 *_dissection.md 頂部有 <!-- ontology-5axis ... --> header (由
inject_ontology_headers.py 注入；由 audit Check 9 enforce)。
本腳本掃描所有 dissection，按用戶 query 過濾。

Examples:
    # 列所有 dissection 的座標
    python3.11 scripts/query_ontology.py --list

    # 過濾：paradigm 含 Learned
    python3.11 scripts/query_ontology.py --paradigm Learned

    # 過濾：sensor 含 IMU
    python3.11 scripts/query_ontology.py --sensor IMU

    # 多軸 AND
    python3.11 scripts/query_ontology.py --paradigm Filter --time Streaming

    # 全文 free-text query 任一 axis
    python3.11 scripts/query_ontology.py --any "feed-forward"
"""

from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HEADER_MARKER = "<!-- ontology-5axis"
HEADER_END = "-->"
AXES = ["problem", "representation", "sensor", "paradigm", "time"]


def parse_header(text: str) -> dict[str, str] | None:
    """Parse ontology-5axis header from beginning of file. Returns dict or None."""
    if not text.lstrip().startswith(HEADER_MARKER):
        return None
    start = text.find(HEADER_MARKER)
    end = text.find(HEADER_END, start + len(HEADER_MARKER))
    if end < 0:
        return None
    block = text[start + len(HEADER_MARKER) : end]
    result = {}
    for line in block.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"(\w+):\s*(.+)", line)
        if m:
            result[m.group(1)] = m.group(2).strip()
    return result if all(ax in result for ax in AXES) else None


def collect_all() -> list[tuple[Path, dict[str, str]]]:
    out = []
    for md in REPO_ROOT.rglob("*_dissection.md"):
        if ".git" in md.parts:
            continue
        text = md.read_text(encoding="utf-8")
        header = parse_header(text)
        if header:
            out.append((md, header))
    return out


def matches(header: dict[str, str], filters: dict[str, str]) -> bool:
    """Word-boundary aware match (避 'IMU' 誤匹 'simulator' 的 'imu' 子串)."""
    for axis, needle in filters.items():
        if axis == "any":
            haystack = " | ".join(header[a] for a in AXES)
        else:
            haystack = header.get(axis, "")
        # Build regex: word boundary on both sides for alphanumeric needle
        # For needles with special chars (e.g. "3D"), still wrap with non-alpha lookarounds
        pattern = r"(?<![A-Za-z0-9])" + re.escape(needle) + r"(?![A-Za-z0-9])"
        if not re.search(pattern, haystack, re.IGNORECASE):
            return False
    return True


def format_entry(path: Path, header: dict[str, str]) -> str:
    rel = path.relative_to(REPO_ROOT)
    out = [f"📄 {rel}"]
    for ax in AXES:
        out.append(f"     {ax:14s} {header[ax]}")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Query handbook dissections by ontology 5-axis coordinates",
    )
    ap.add_argument("--problem", help="filter: problem axis contains")
    ap.add_argument("--representation", "--repr", help="filter: representation axis contains")
    ap.add_argument("--sensor", help="filter: sensor axis contains")
    ap.add_argument("--paradigm", help="filter: paradigm axis contains")
    ap.add_argument("--time", help="filter: time axis contains")
    ap.add_argument("--any", dest="any_", help="filter: any axis contains")
    ap.add_argument("--list", action="store_true", help="list all (no filter)")
    ap.add_argument(
        "--summary",
        action="store_true",
        help="compact summary table (1 line per dissection)",
    )
    args = ap.parse_args()

    filters = {}
    if args.problem:
        filters["problem"] = args.problem
    if args.representation:
        filters["representation"] = args.representation
    if args.sensor:
        filters["sensor"] = args.sensor
    if args.paradigm:
        filters["paradigm"] = args.paradigm
    if args.time:
        filters["time"] = args.time
    if args.any_:
        filters["any"] = args.any_

    if not (filters or args.list):
        ap.print_help()
        print("\nNo filter provided. Use --list or pass at least one --axis.")
        return 1

    all_entries = collect_all()
    matched = [(p, h) for p, h in all_entries if matches(h, filters)]

    if not matched:
        print(f"No dissection matches.")
        print(f"Total scanned: {len(all_entries)}")
        return 0

    if args.summary:
        print(f"{'Method':50s}  {'Problem':30s}  {'Paradigm':40s}  Time")
        print("-" * 140)
        for path, h in matched:
            name = path.stem.replace("_dissection", "")
            print(f"{name:50s}  {h['problem'][:30]:30s}  {h['paradigm'][:40]:40s}  {h['time']}")
    else:
        for path, h in matched:
            print(format_entry(path, h))
            print()

    print(f"\nMatched {len(matched)} / {len(all_entries)} dissections.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
