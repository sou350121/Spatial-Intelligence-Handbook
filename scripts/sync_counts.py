#!/usr/bin/env python3
"""Recompute every handbook count from the filesystem and write it back.

Adding a dissection changes counts in five places the audit enforces (Check 4 /
11 / 12): README, foundations/overview, docs.json description (via
gen_mintlify_nav.py), and per-zone overview "N dissections". Rather than
increment (fragile), this recomputes from truth — so it also repairs any drift.
Run it after adding/removing a dissection, then regen nav + sync READMEs.

    python3 scripts/sync_counts.py
"""
from __future__ import annotations
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def foundations_count() -> int:
    """Match audit's count_actual_foundations: all foundations/*.md except
    README/overview/github_failure_atlas."""
    n = 0
    for md in (REPO / "foundations").rglob("*.md"):
        if md.name in ("README.md", "overview.md", "github_failure_atlas.md"):
            continue
        n += 1
    return n


def total_dissections() -> int:
    return sum(1 for _ in REPO.rglob("*_dissection.md"))


def sub_in_file(path: Path, pattern: str, repl_fn) -> bool:
    if not path.exists():
        return False
    s = path.read_text(encoding="utf-8")
    new = re.sub(pattern, repl_fn, s)
    if new != s:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def main() -> int:
    found = foundations_count()
    total = total_dissections()
    print(f"foundations={found}  total_dissections={total}")

    # README.md: "13 zones · N 篇"
    sub_in_file(REPO / "README.md", r"(13\s*zones?\s*·\s*)\d+(\s*篇)",
                lambda m: f"{m.group(1)}{found}{m.group(2)}")
    # foundations/overview.md: "N 篇深度解析"  (syncs to README via sync_readme)
    sub_in_file(REPO / "foundations" / "overview.md", r"\d+(\s*篇深度解析)",
                lambda m: f"{found}{m.group(1)}")
    # gen_mintlify_nav.py description: "N dissection / M 篇深度解析"
    sub_in_file(REPO / "scripts" / "gen_mintlify_nav.py",
                r"(\d+) dissection / (\d+) 篇深度解析",
                lambda m: f"{total} dissection / {found} 篇深度解析")
    # per-zone overview.md: English "N dissections" -> that zone's glob count
    for ov in REPO.rglob("overview.md"):
        if ".git" in ov.parts:
            continue
        zc = sum(1 for _ in ov.parent.glob("*_dissection.md"))
        if zc == 0:
            continue
        sub_in_file(ov, r"(?<![A-Za-z0-9])\d+(\s*dissections?)",
                    lambda m, zc=zc: f"{zc}{m.group(1)}")
    print("counts synced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
