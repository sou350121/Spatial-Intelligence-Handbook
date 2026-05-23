#!/usr/bin/env python3
"""
Handbook Audit — Spatial-Intelligence-Handbook 自动质量门槛 lint。

7 个 check：
  1. Atlas 回灌完整度 — 10 个 atlas-bearing zone 的 dissection 必含 atlas 回灌 markers
  2. 14 项门槛 — 所有 *_dissection.md 必含 X-Ray / Eureka / Napkin / Worked Example /
                  Hidden Assumption / Interview Tip / Timeline 七大 anchor
  3. Broken Links — 所有 .md 内相对路径 markdown link 必须 resolve
  4. 计数一致性 — README.md 「13 zones · NN 篇」 == foundations/README.md 「NN 篇深度解析」
                  == 实际 find foundations -name '*.md' 排除 README + atlas 的数量
  5. License Attribution — 标 `教材出处` 引用 HKUST/ELEC5660/沈劭劼 教材的派生作品必含 BSD 3-Clause block
  6. UNVERIFIED 纪律 — UNVERIFIED 标记不能出现在纯标题 / 孤行 / 引言行（必须同一行带具体 claim）
  7. Stale TODO — README.md 顶层文件里的 `(TBD)` `(待补)` `(待写)` 列出（INFO，不 fail）

Exit code: 0 = 全 PASS（WARN/INFO 不阻塞）, 1 = 至少一项 FAIL。

只用 stdlib（pathlib / re / collections / sys）。Python 3.9+。
"""
from __future__ import annotations

import re
import sys
from collections import namedtuple
from datetime import datetime
from pathlib import Path
from typing import Iterable

CheckResult = namedtuple("CheckResult", ["name", "status", "summary", "details"])
# status ∈ {"PASS", "WARN", "FAIL", "INFO"}

# ----------------------------------------------------------------------
# 常量 / 规则配置
# ----------------------------------------------------------------------

# 已知有 github_failure_atlas.md 的 10 个 zone（其中 dissection 必须回灌 atlas）
ATLAS_BEARING_ZONES = [
    "foundations/3dgs-family",
    "foundations/classical-slam",
    "foundations/depth-foundation",
    "foundations/feed-forward-3d",
    "foundations/nerf-family",
    "foundations/pose-tracking",
    "foundations/semantic-3d",
    "foundations/vlm-spatial-reasoning",
    "foundations/world-model",
    "embodiments/aerial/vio",
]

# atlas 回灌 markers（任一即可）
ATLAS_RECALL_PATTERNS = [
    r"atlas\s*联动",
    r"GitHub-validated",
    r"GitHub\s*实地失败",
]

# 14 项门槛 — 简化为 7 个必须 anchor，每个用 OR 模式（中英任一即可）
# 之所以收 7 不收 14：14 项里有些是「至少一张表」「文末返回链接」这种结构性的，
# 用正则误伤率高；先以 7 个 anchor 卡住核心 narrative gate，其余靠人工 review。
FOURTEEN_ITEM_MARKERS = {
    "X-Ray": [r"X-Ray", r"X[- ]?[Rr]ay"],
    "Timeline": [r"📍.*[Tt]imeline", r"研究全景", r"时间线", r"時間線", r"Timeline"],
    "Eureka": [r"⚡\s*\*?\*?Eureka", r"Eureka\s*Moment", r"Eureka"],
    "Napkin": [r"📌\s*\*?\*?Napkin", r"Napkin\s*Formula", r"Napkin"],
    "Worked Example": [r"带数字走一遍", r"[Ww]orked\s*[Ee]xample", r"玩具例子"],
    "Hidden Assumptions": [r"[Hh]idden\s*[Aa]ssumption", r"隐含假设", r"隱含假設"],
    "Interview Tip": [r"面试\s*[Tt]ip", r"面試\s*[Tt]ip", r"[Ii]nterview\s*[Tt]ip"],
}

# 计数一致性 regex
COUNT_README_RE = re.compile(r"13\s*zones?\s*·\s*(\d+)\s*篇")
COUNT_FOUNDATIONS_RE = re.compile(r"(\d+)\s*篇深度解析")

# 计数实际值：foundations 下所有 *.md，排除 overview/README + atlas
def count_actual_foundations(repo_root: Path) -> int:
    found = repo_root / "foundations"
    cnt = 0
    for md in found.rglob("*.md"):
        if md.name in ("README.md", "overview.md"):
            continue
        if md.name == "github_failure_atlas.md":
            continue
        cnt += 1
    return cnt


# License attribution：派生 HKUST 教材的文档必须含 BSD
# 触发条件：文档同时含「教材出处」+ HKUST/ELEC5660/沈劭劼 关键词 → 必须有 BSD 3-Clause
DERIVATIVE_TRIGGER_RE = re.compile(r"教材出处")
HKUST_TOKEN_RE = re.compile(r"HKUST|ELEC5660|沈劭劼")
BSD_BLOCK_RE = re.compile(r"BSD\s*3-Clause")

# UNVERIFIED 纪律：suspicious = 行被 trim 后是 `UNVERIFIED` / `### UNVERIFIED` / `> UNVERIFIED` / 等无 claim 形式
UNVERIFIED_SUSPICIOUS_RE = re.compile(
    r"^\s*(?:[#>*\-]+\s*)*`?UNVERIFIED`?\s*$"
)

# Stale TODO
STALE_TODO_RE = re.compile(r"\((?:TBD|待補|待补|待写|待寫)\)")


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def iter_markdown_files(repo_root: Path) -> Iterable[Path]:
    """遍历仓库所有 .md，排除 .git / node_modules / 隐藏目录。"""
    for md in repo_root.rglob("*.md"):
        # 跳过 .git / hidden / node_modules
        parts = md.relative_to(repo_root).parts
        if any(p.startswith(".") and p not in {"."} for p in parts):
            continue
        if "node_modules" in parts:
            continue
        yield md


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def find_any(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text) for p in patterns)


# ----------------------------------------------------------------------
# Check 1 — Atlas 回灌完整度
# ----------------------------------------------------------------------


def check_1_atlas_recall(repo_root: Path) -> CheckResult:
    missing: list[str] = []
    total = 0
    for zone_rel in ATLAS_BEARING_ZONES:
        zone = repo_root / zone_rel
        if not zone.exists():
            continue
        for md in zone.glob("*_dissection.md"):
            total += 1
            text = read_text(md)
            if not find_any(ATLAS_RECALL_PATTERNS, text):
                missing.append(str(md.relative_to(repo_root)))
    ok = total - len(missing)
    if missing:
        return CheckResult(
            name="Atlas Recall",
            status="FAIL",
            summary=f"{ok}/{total} dissections 有 atlas 回灌，{len(missing)} 缺失",
            details=[f"  缺 atlas 回灌：{p}（加 `atlas 联动` 或 `GitHub-validated` 段）" for p in missing],
        )
    return CheckResult(
        name="Atlas Recall",
        status="PASS",
        summary=f"{total}/{total} dissections 都有 atlas 回灌",
        details=[],
    )


# ----------------------------------------------------------------------
# Check 2 — 14 项门槛
# ----------------------------------------------------------------------


def check_2_fourteen_item_gate(repo_root: Path) -> CheckResult:
    issues: list[tuple[str, list[str]]] = []
    total = 0
    for md in repo_root.rglob("*_dissection.md"):
        # 排除 atlas 名义带 _dissection 的（实际无；防御）
        if md.name == "github_failure_atlas.md":
            continue
        total += 1
        text = read_text(md)
        missing = [name for name, pats in FOURTEEN_ITEM_MARKERS.items() if not find_any(pats, text)]
        if missing:
            issues.append((str(md.relative_to(repo_root)), missing))
    ok = total - len(issues)
    if issues:
        details = [f"  {p} — 缺 {', '.join(m)}" for p, m in issues]
        return CheckResult(
            name="14-item Gate",
            status="FAIL",
            summary=f"{ok}/{total} dissections 满 7 项 anchor，{len(issues)} 缺 marker",
            details=details,
        )
    return CheckResult(
        name="14-item Gate",
        status="PASS",
        summary=f"{total}/{total} dissections 满 7 项 anchor",
        details=[],
    )


# ----------------------------------------------------------------------
# Check 3 — Broken Links
# ----------------------------------------------------------------------

RELATIVE_LINK_RE = re.compile(r"\]\((\.{1,2}/[^)\s#]+)(#[^)]*)?\)")
FENCE_RE = re.compile(r"^```")


def strip_fenced_code_blocks(text: str) -> str:
    """剥掉 ``` 包裹的 fenced code block，避免把模板里的示例链接当真链接。"""
    out: list[str] = []
    inside = False
    for line in text.splitlines():
        if FENCE_RE.match(line.lstrip()):
            inside = not inside
            out.append("")  # 保留行号位置
            continue
        out.append("" if inside else line)
    return "\n".join(out)


def check_3_broken_links(repo_root: Path) -> CheckResult:
    broken: list[str] = []
    total = 0
    for md in iter_markdown_files(repo_root):
        text = strip_fenced_code_blocks(read_text(md))
        for m in RELATIVE_LINK_RE.finditer(text):
            total += 1
            rel_path = m.group(1)
            # 解析 link 起点
            try:
                target = (md.parent / rel_path).resolve()
                # 必须在仓库内（防越界）
                target.relative_to(repo_root.resolve())
            except (ValueError, OSError):
                broken.append(f"{md.relative_to(repo_root)} → {rel_path}（解析失败）")
                continue
            if not target.exists():
                broken.append(f"{md.relative_to(repo_root)} → {rel_path}")
    ok = total - len(broken)
    if broken:
        details = [f"  断链：{b}" for b in broken[:50]]
        if len(broken) > 50:
            details.append(f"  …还有 {len(broken) - 50} 条未列出")
        return CheckResult(
            name="Broken Links",
            status="FAIL",
            summary=f"{ok}/{total} relative links resolve，{len(broken)} 条断链",
            details=details,
        )
    return CheckResult(
        name="Broken Links",
        status="PASS",
        summary=f"{total}/{total} relative links resolve",
        details=[],
    )


# ----------------------------------------------------------------------
# Check 4 — 计数一致性
# ----------------------------------------------------------------------


def check_4_count_consistency(repo_root: Path) -> CheckResult:
    readme = read_text(repo_root / "README.md")
    foundations_readme = read_text(repo_root / "foundations" / "overview.md")

    m_readme = COUNT_README_RE.search(readme)
    m_found = COUNT_FOUNDATIONS_RE.search(foundations_readme)

    if not m_readme:
        return CheckResult(
            name="Count Consistency",
            status="FAIL",
            summary="README.md 找不到 `13 zones · NN 篇` 计数声明",
            details=["  修复：在 README.md 维持 `13 zones · NN 篇` 格式（mermaid + details 双处）"],
        )
    if not m_found:
        return CheckResult(
            name="Count Consistency",
            status="FAIL",
            summary="foundations/overview.md 找不到 `NN 篇深度解析` 计数声明",
            details=["  修复：在 foundations/overview.md 顶部 keep `**NN 篇深度解析**` 行"],
        )

    declared_readme = int(m_readme.group(1))
    declared_found = int(m_found.group(1))
    actual = count_actual_foundations(repo_root)

    if declared_readme == declared_found == actual:
        return CheckResult(
            name="Count Consistency",
            status="PASS",
            summary=f"README={declared_readme}, foundations/README={declared_found}, actual={actual}",
            details=[],
        )
    return CheckResult(
        name="Count Consistency",
        status="FAIL",
        summary=f"三个数对不上：README={declared_readme}, foundations/README={declared_found}, actual={actual}",
        details=[
            f"  actual = `find foundations -name '*.md' ! -name README.md ! -name github_failure_atlas.md | wc -l` = {actual}",
            "  修复：要么补 dissection，要么同步两份 README 的数字",
        ],
    )


# ----------------------------------------------------------------------
# Check 5 — License Attribution
# ----------------------------------------------------------------------


def check_5_license_attribution(repo_root: Path) -> CheckResult:
    missing: list[str] = []
    total = 0
    for md in iter_markdown_files(repo_root):
        text = read_text(md)
        # 触发：同时含「教材出处」和 HKUST/ELEC5660/沈劭劼
        if DERIVATIVE_TRIGGER_RE.search(text) and HKUST_TOKEN_RE.search(text):
            total += 1
            if not BSD_BLOCK_RE.search(text):
                missing.append(str(md.relative_to(repo_root)))
    if total == 0:
        return CheckResult(
            name="License Attribution",
            status="PASS",
            summary="0/0 文件需 HKUST 教材引用（无派生 trigger）",
            details=[],
        )
    if missing:
        return CheckResult(
            name="License Attribution",
            status="FAIL",
            summary=f"{total - len(missing)}/{total} HKUST 取材文档含 BSD block，{len(missing)} 缺失",
            details=[f"  缺 BSD 3-Clause：{p}" for p in missing],
        )
    return CheckResult(
        name="License Attribution",
        status="PASS",
        summary=f"{total}/{total} HKUST 教材引用文档带 BSD block",
        details=[],
    )


# ----------------------------------------------------------------------
# Check 6 — UNVERIFIED 纪律
# ----------------------------------------------------------------------


def check_6_unverified_discipline(repo_root: Path) -> CheckResult:
    suspicious: list[str] = []
    for md in iter_markdown_files(repo_root):
        text = read_text(md)
        for i, line in enumerate(text.splitlines(), start=1):
            if "UNVERIFIED" not in line:
                continue
            if UNVERIFIED_SUSPICIOUS_RE.match(line):
                suspicious.append(f"{md.relative_to(repo_root)}:{i}  `{line.strip()}`")
    if suspicious:
        return CheckResult(
            name="UNVERIFIED Discipline",
            status="WARN",
            summary=f"{len(suspicious)} 处 UNVERIFIED 无具体 claim",
            details=[f"  可疑：{s}（应改为 `具体数字 UNVERIFIED` 而非孤行 / 标题）" for s in suspicious[:30]],
        )
    return CheckResult(
        name="UNVERIFIED Discipline",
        status="PASS",
        summary="所有 UNVERIFIED 都附具体 claim",
        details=[],
    )


# ----------------------------------------------------------------------
# Check 7 — Stale TODO
# ----------------------------------------------------------------------


def check_7_stale_todo(repo_root: Path) -> CheckResult:
    hits: list[str] = []
    target_files = [
        repo_root / "README.md",
        repo_root / "foundations" / "overview.md",
        repo_root / "embodiments" / "overview.md",
        repo_root / "crossing" / "overview.md",
    ]
    for tf in target_files:
        if not tf.exists():
            continue
        text = read_text(tf)
        for i, line in enumerate(text.splitlines(), start=1):
            if STALE_TODO_RE.search(line):
                hits.append(f"{tf.relative_to(repo_root)}:{i}  {line.strip()[:120]}")
    return CheckResult(
        name="Stale TODO",
        status="INFO",
        summary=f"{len(hits)} 处 (TBD)/(待补)/(待写) — roadmap 正常",
        details=[f"  {h}" for h in hits[:20]],
    )


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


def check_8_mintlify_nav_coverage(repo_root: Path) -> CheckResult:
    """每个 repo 内 .md 必须出现在 docs.json nav；docs.json 引用的 page 必须存在。

    跳过：repo_root 下 LOGIC_AUDIT_* / docs.json 不存在时（INFO）。
    """
    import json

    docs_json = repo_root / "docs.json"
    if not docs_json.exists():
        return CheckResult(
            name="Mintlify Nav",
            status="INFO",
            summary="docs.json 不存在；跳过（如未设置 Mintlify 部署可忽略）",
            details=[],
        )

    try:
        cfg = json.loads(docs_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return CheckResult(
            name="Mintlify Nav",
            status="FAIL",
            summary=f"docs.json 解析失败：{e}",
            details=[],
        )

    # Walk nav, collect all string page ids
    nav_pages: set[str] = set()

    def walk(node):
        if isinstance(node, str):
            nav_pages.add(node)
        elif isinstance(node, dict):
            for k in ("pages", "groups", "tabs"):
                if k in node:
                    for child in node[k]:
                        walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(cfg.get("navigation", {}))

    # All md files in repo (excl. some)
    # NOTE: page ids in docs.json keep the .md extension (see gen_mintlify_nav.py
    # page_id docstring for why), so we compare with extension here too.
    excluded_stems = {"LOGIC_AUDIT_2026-05-22"}
    repo_md: set[str] = set()
    for md in repo_root.rglob("*.md"):
        if ".git" in md.parts:
            continue
        if md.stem in excluded_stems:
            continue
        repo_md.add(str(md.relative_to(repo_root)))

    missing_in_nav = sorted(repo_md - nav_pages)
    missing_files = sorted(nav_pages - repo_md)

    details = []
    if missing_in_nav:
        details.append(f"  {len(missing_in_nav)} md not in docs.json nav:")
        for p in missing_in_nav[:10]:
            details.append(f"    - {p}")
        if len(missing_in_nav) > 10:
            details.append(f"    ... and {len(missing_in_nav) - 10} more")
    if missing_files:
        details.append(f"  {len(missing_files)} nav entries with no matching file:")
        for p in missing_files[:10]:
            details.append(f"    - {p}")
        if len(missing_files) > 10:
            details.append(f"    ... and {len(missing_files) - 10} more")

    if missing_in_nav or missing_files:
        return CheckResult(
            name="Mintlify Nav",
            status="FAIL",
            summary=f"{len(missing_in_nav)} orphan md + {len(missing_files)} dangling nav entries — run `python3 scripts/gen_mintlify_nav.py > docs.json`",
            details=details,
        )

    return CheckResult(
        name="Mintlify Nav",
        status="PASS",
        summary=f"all {len(repo_md)} md present in docs.json nav (no orphans, no dangling)",
        details=[],
    )


CHECKS = [
    check_1_atlas_recall,
    check_2_fourteen_item_gate,
    check_3_broken_links,
    check_4_count_consistency,
    check_5_license_attribution,
    check_6_unverified_discipline,
    check_7_stale_todo,
    check_8_mintlify_nav_coverage,
]


STATUS_GLYPH = {
    "PASS": "PASS",
    "WARN": "WARN",
    "FAIL": "FAIL",
    "INFO": "INFO",
}


def main() -> int:
    # 假设 script 装在 <repo>/scripts/handbook_audit.py
    repo_root = Path(__file__).resolve().parent.parent
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"=== Handbook Audit ({today}) ===\n")

    results: list[CheckResult] = []
    for i, fn in enumerate(CHECKS, start=1):
        try:
            res = fn(repo_root)
        except Exception as e:  # 防御：单个 check 崩了不影响其他
            res = CheckResult(
                name=fn.__name__,
                status="FAIL",
                summary=f"check raised exception: {e!r}",
                details=[],
            )
        results.append(res)
        print(f"[CHECK {i} / {res.name}] {STATUS_GLYPH[res.status]}  {res.summary}")
        for line in res.details:
            print(line)
        print()

    counts = {"PASS": 0, "WARN": 0, "FAIL": 0, "INFO": 0}
    for r in results:
        counts[r.status] += 1

    print(
        f"Total: {counts['PASS']} PASS / {counts['WARN']} WARN / "
        f"{counts['FAIL']} FAIL / {counts['INFO']} INFO"
    )
    exit_code = 1 if counts["FAIL"] > 0 else 0
    print(f"Exit code: {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
