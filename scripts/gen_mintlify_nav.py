#!/usr/bin/env python3
"""Generate docs.json (Mintlify v3) from repo directory structure.

Run from repo root:
    python3 scripts/gen_mintlify_nav.py > docs.json

All .md files (except CHANGELOG-like) are included. Structure mirrors directory tree.
Top-level files (README, ONBOARDING, CONTRIBUTING, AGENTS) go under "Get Started" tab.
Each subdirectory becomes a tab; sub-subdirectories become nested groups.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Tab structure: each entry = (tab_name, root_dir_or_None_for_top_level, icon)
# Order matters for sidebar display.
TABS = [
    ("Get Started", None, "rocket"),         # top-level md
    ("Foundations", "foundations", "layer-group"),
    ("Embodiments", "embodiments", "robot"),
    ("Crossing", "crossing", "shuffle"),
    ("Cheat Sheet", "cheat-sheet", "map"),
    ("Deployment", "deployment", "screwdriver-wrench"),
    ("Benchmarks", "benchmarks", "ruler"),
    ("Bridge to VLA", "bridge-to-vla", "bridge"),
    ("Companies", "companies", "building"),
    ("Reports", "reports", "file-lines"),
    ("Docs", "docs", "book"),
    ("Changelog", "changelog", "clock-rotate-left"),
]

# Files at repo root that go under "Get Started" — order matters.
TOP_LEVEL_ORDER = ["ONBOARDING", "README", "CONTRIBUTING", "AGENTS"]

# Files excluded entirely.
# - LOGIC_AUDIT_*: status / audit dumps
# - README: Mintlify silently drops ALL README.md files at build time;
#           sub-folders use overview.md as canonical landing page,
#           README.md is a mirror for GitHub folder-browsing UX.
EXCLUDE_PATTERNS = {"LOGIC_AUDIT_2026-05-22", "README"}


def page_id(path: Path) -> str:
    """Return the Mintlify page id: repo-relative path WITH .md extension.

    Mintlify serves .md files at URL paths that include the .md suffix (e.g.
    `/foundations/README.md`). If we strip the extension in docs.json, the
    sidebar generates `/foundations/README` which 404s. Keep the extension
    so sidebar clicks resolve.
    """
    rel = path.relative_to(REPO_ROOT)
    # Mintlify keeps the .md suffix in the served URL, but serves .mdx files
    # extensionless (e.g. changelog/overview.mdx → page id "changelog/overview").
    if rel.suffix == ".mdx":
        return str(rel.with_suffix(""))
    return str(rel)


def humanize(name: str) -> str:
    """Turn `slam-vio-migration` / `feed_forward_3d` into `Slam Vio Migration`."""
    cleaned = name.replace("-", " ").replace("_", " ")
    return " ".join(w.capitalize() for w in cleaned.split())


def collect_md(d: Path) -> list[Path]:
    """Return sorted .md files directly under d (non-recursive), overview/README first.

    Mintlify drops README.md silently, so most directories use overview.md as the
    landing page. We sort overview.md (or README.md at repo root) first so it
    becomes the directory's default landing page in sidebar.
    """
    files = [p for p in d.glob("*.md") if p.stem not in EXCLUDE_PATTERNS]
    files += [p for p in d.glob("*.mdx") if p.stem not in EXCLUDE_PATTERNS]
    files.sort(key=lambda p: (p.stem not in ("overview", "README"), p.stem.lower()))
    return files


def collect_subdirs(d: Path) -> list[Path]:
    """Return sorted subdirectories of d that contain at least one .md."""
    subs = []
    for child in sorted(d.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith("."):
            continue
        # has any .md anywhere inside?
        if any(child.rglob("*.md")):
            subs.append(child)
    return subs


def build_group(d: Path, group_name: str | None = None) -> dict:
    """Build a Mintlify group dict for directory `d`.

    Pages = .md files directly under d. Subdirs become nested groups.
    """
    pages: list = []

    # Direct files
    for f in collect_md(d):
        pages.append(page_id(f))

    # Nested subdirs → nested groups (no further recursion needed for current depth)
    for sub in collect_subdirs(d):
        sub_pages = [page_id(f) for f in collect_md(sub)]
        # If sub has its own sub-subdirs, recurse one more level (rare).
        sub_sub_dirs = collect_subdirs(sub)
        for ssub in sub_sub_dirs:
            ssub_pages = [page_id(f) for f in collect_md(ssub)]
            if ssub_pages:
                sub_pages.append({"group": humanize(ssub.name), "pages": ssub_pages})
        if sub_pages:
            pages.append({"group": humanize(sub.name), "pages": sub_pages})

    return {"group": group_name or humanize(d.name), "pages": pages}


def build_top_level_group() -> dict:
    """Top-level md files in a fixed order, plus any others alphabetically."""
    root_files = collect_md(REPO_ROOT)
    ordered_pages = []
    seen = set()
    for stem in TOP_LEVEL_ORDER:
        for f in root_files:
            if f.stem == stem:
                ordered_pages.append(page_id(f))
                seen.add(f.stem)
                break
    for f in root_files:
        if f.stem not in seen:
            ordered_pages.append(page_id(f))
    return {"group": "Start here", "pages": ordered_pages}


def main() -> int:
    tabs_json = []
    for tab_name, dir_name, icon in TABS:
        if dir_name is None:
            group = build_top_level_group()
            tabs_json.append({"tab": tab_name, "icon": icon, "groups": [group]})
            continue

        d = REPO_ROOT / dir_name
        if not d.exists():
            print(f"WARN: missing dir {dir_name}", file=sys.stderr)
            continue

        # Direct files under the tab dir → put into a top group named after the dir.
        direct_files = collect_md(d)
        groups = []
        if direct_files:
            groups.append({"group": "Overview", "pages": [page_id(f) for f in direct_files]})
        # Reports: dated archives under reports/<sub>/ (e.g. reports/spatial-daily/*.md)
        # are archive content, NOT individual sidebar pages — surfaced via the landing
        # page + RSS. Only the landing page(s) directly under reports/ appear in nav,
        # so the sidebar never bloats with hundreds of dated entries.
        subdirs = [] if dir_name == "reports" else collect_subdirs(d)
        for sub in subdirs:
            g = build_group(sub)
            # Skip empty groups (e.g. sub-folder with only README.md, which is excluded)
            if g.get("pages"):
                groups.append(g)
        tabs_json.append({"tab": tab_name, "icon": icon, "groups": groups})

    docs = {
        "$schema": "https://mintlify.com/docs.json",
        "theme": "mint",
        "name": "Spatial Intelligence Handbook",
        "description": "Spatial AI for manipulation / aerial / driving / marine — 47 dissection / 93 篇深度解析 / 5-axis ontology v3.2 / GitHub-validated atlas",
        "colors": {
            "primary": "#0EA5E9",
            "light": "#38BDF8",
            "dark": "#0369A1",
        },
        "favicon": "/favicon.svg",
        "navigation": {"tabs": tabs_json},
        "navbar": {
            "links": [
                {"label": "GitHub", "href": "https://github.com/sou350121/Spatial-Intelligence-Handbook"},
                {"label": "VLA-Handbook", "href": "https://github.com/sou350121/VLA-Handbook"},
                {"label": "Physics-Gen", "href": "https://github.com/sou350121/Physics-Controllable-Generation-Handbook"},
            ]
        },
        "footer": {
            "socials": {
                "github": "https://github.com/sou350121/Spatial-Intelligence-Handbook",
            }
        },
    }

    # Sanity: count all pages, compare against repo md count
    def count_pages(node) -> int:
        if isinstance(node, str):
            return 1
        if isinstance(node, dict):
            if "pages" in node:
                return sum(count_pages(p) for p in node["pages"])
            if "groups" in node:
                return sum(count_pages(g) for g in node["groups"])
        return 0

    total_in_nav = sum(count_pages(t) for t in tabs_json)

    def in_nav_scope(p: Path) -> bool:
        if ".git" in p.parts or p.stem in EXCLUDE_PATTERNS:
            return False
        rel = p.relative_to(REPO_ROOT)
        # dated report archives are intentionally not nav pages
        if rel.parts[:1] == ("reports",) and len(rel.parts) >= 3:
            return False
        return True

    repo_md_count = sum(1 for p in [*REPO_ROOT.rglob("*.md"), *REPO_ROOT.rglob("*.mdx")]
                        if in_nav_scope(p))

    print(json.dumps(docs, indent=2, ensure_ascii=False))
    print(f"\n# nav pages: {total_in_nav}, repo md (ex-excluded): {repo_md_count}",
          file=sys.stderr)
    if total_in_nav != repo_md_count:
        print(f"# WARNING: mismatch — some md not in nav", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
