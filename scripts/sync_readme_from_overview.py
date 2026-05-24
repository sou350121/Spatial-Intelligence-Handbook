#!/usr/bin/env python3
"""Sync README.md ← overview.md across all sub-directories.

Why two files:
- Mintlify silently drops any README.md from build (GitHub convention 衝突)
- GitHub renders README.md when browsing a folder

So we keep BOTH:
- overview.md = canonical Mintlify-facing landing page (in docs.json nav)
- README.md  = exact mirror, GitHub-facing folder index (excluded from Mintlify nav)

This script copies overview.md → README.md in every sub-folder. Run:
    python3.11 scripts/sync_readme_from_overview.py

Pre-commit / CI integration: audit Check 10 (README sync) fails if any folder's
README.md ≠ overview.md.
"""

from __future__ import annotations
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def collect_overview_folders() -> list[Path]:
    """Return list of folders containing overview.md (not the repo root)."""
    folders = []
    for ov in REPO_ROOT.rglob("overview.md"):
        if ".git" in ov.parts:
            continue
        folders.append(ov.parent)
    return sorted(folders)


def sync_one(folder: Path) -> str:
    """Copy overview.md → README.md in this folder. Return status."""
    overview = folder / "overview.md"
    readme = folder / "README.md"
    content = overview.read_text(encoding="utf-8")

    if readme.exists():
        existing = readme.read_text(encoding="utf-8")
        if existing == content:
            return "unchanged"
        readme.write_text(content, encoding="utf-8")
        return "updated"
    else:
        readme.write_text(content, encoding="utf-8")
        return "created"


def main() -> int:
    folders = collect_overview_folders()
    print(f"Syncing README.md ← overview.md in {len(folders)} folders...\n")
    stats = {"created": 0, "updated": 0, "unchanged": 0}
    for f in folders:
        status = sync_one(f)
        stats[status] += 1
        rel = f.relative_to(REPO_ROOT)
        print(f"  {status:10s}  {rel}/README.md")
    print(f"\n{stats['created']} created · {stats['updated']} updated · {stats['unchanged']} unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
