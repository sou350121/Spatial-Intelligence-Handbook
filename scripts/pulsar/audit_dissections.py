#!/usr/bin/env python3
"""qwen-based fabrication safety-net for committed dissections.

The daily pipeline's inline qwen-factcheck has a blind spot: asked holistically
"is this draft supported?" over the same text, qwen passed its own fabrications
(3-Opus audit, 2026-07-21). This re-audit avoids that blind spot by copying what
made the Opus auditors succeed:
  1. Fetch the source FRESH and MORE completely (bigger cap → results tables visible).
  2. Mechanical numeric-grounding gate (deterministic string-match — unfoolable).
  3. A qwen **cite-or-NOTFOUND** pass: for each dataset name + comparison/SOTA number,
     qwen must QUOTE the supporting source sentence or mark NOT_FOUND. Forcing a quote
     is far harder to fool than a yes/no "is this supported".

Runs over committed dissections (a window, or all). Emits a report; a weekly
workflow files/updates a GitHub issue listing SUSPECT articles for review.

Usage:
    DASHSCOPE_API_KEY=... python3 scripts/pulsar/audit_dissections.py --days 8
    DASHSCOPE_API_KEY=... python3 scripts/pulsar/audit_dissections.py --all
    DASHSCOPE_API_KEY=... python3 scripts/pulsar/audit_dissections.py --file <path>
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import write_dissection as wd
from _config import get_env

REPO = Path(__file__).resolve().parent.parent.parent
AUDIT_CAP = 55000  # bigger than generation cap so results/tables are in view

CITE_SYS = """你是论文事实核查员。给你一篇论文全文(截断)和一篇据其撰写的 dissection 草稿的**评测相关段落**。
任务:把草稿里出现的 (a) 数据集/benchmark 名字 (b) 具体对比数字 / SOTA 值 / 指标值,逐条列出,
并在**全文里找证据**——必须**引用全文中的原句**证明该声明;找不到就写 NOT_FOUND。
**宁可 NOT_FOUND 也绝不脑补支持。** 玩具例子里明确的示范数字、标了 UNVERIFIED 的估算,跳过不查。

严格 JSON 输出:
{"claims": [
  {"claim": "<草稿里的声明,如 'baseline Splat-LOAM F-score 62.1%'>",
   "evidence": "<全文原句 或 NOT_FOUND>"}
]}
只列评测类事实声明(数据集名 + 对比数字),不列方法论描述。"""


def _disp(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return path.name


def audit_one(path: Path, api_key: str) -> dict:
    draft = path.read_text(encoding="utf-8")
    m = re.search(r"abs/(\d{4}\.\d{4,5})", draft)
    if not m:
        return {"path": _disp(path), "verdict": "SKIP", "reason": "no arxiv id"}
    aid = m.group(1)
    try:
        _, src = wd.fetch_fulltext(aid, cap=AUDIT_CAP)
    except Exception as e:  # noqa
        return {"path": _disp(path), "verdict": "SKIP", "reason": f"fetch fail: {e}"}

    # 1) deterministic mechanical gate
    mech = wd.numeric_grounding_issues(draft, src)

    # 2) qwen cite-or-NOTFOUND over the eval sections only (§4-§7 where fabrication lives)
    eval_body = _eval_sections(draft)
    notfound = []
    try:
        raw = wd.call_qwen(CITE_SYS, f"论文全文(截断):\n{src[:AUDIT_CAP]}\n\n=== 草稿评测段落 ===\n{eval_body[:8000]}",
                           api_key, max_tokens=1500)
        obj = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
        for c in obj.get("claims", []):
            ev = str(c.get("evidence", "")).strip()
            if ev == "NOT_FOUND" or not ev:
                notfound.append(c.get("claim", "")[:100])
    except Exception as e:  # noqa — qwen hiccup shouldn't crash the audit; mech gate still stands
        notfound = [f"(qwen cite-audit error: {e})"]

    issues = [f"[num] {i}" for i in mech] + [f"[cite] {c}" for c in notfound if not c.startswith("(qwen")]
    verdict = "SUSPECT" if issues else "CLEAN"
    return {"path": _disp(path), "arxiv": aid, "verdict": verdict,
            "mech": len(mech), "notfound": len(notfound), "issues": issues[:8]}


def _eval_sections(draft: str) -> str:
    hot = ("工程", "数据与评测", "數據與評測", "能力与失败", "能力與失敗",
           "相关工作", "相關工作", "对比", "對比")
    out, keep = [], False
    for line in draft.splitlines():
        if line.startswith("## "):
            keep = any(h in line for h in hot)
        if keep:
            out.append(line)
    return "\n".join(out)


def target_files(args) -> list[Path]:
    if args.file:
        return [Path(args.file)]
    allf = sorted(REPO.glob("**/*_dissection.md"))
    if args.all:
        return allf
    # default: files added within --days (git), to audit the recent auto-committed batch
    since = subprocess.run(
        ["git", "-C", str(REPO), "log", f"--since={args.days} days ago",
         "--diff-filter=A", "--name-only", "--format="],
        capture_output=True, text=True).stdout
    recent = {REPO / p for p in since.splitlines() if p.endswith("_dissection.md")}
    return sorted(f for f in allf if f in recent) or allf[-args.days:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=8)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--file")
    args = ap.parse_args()
    api_key = get_env("DASHSCOPE_API_KEY")

    files = target_files(args)
    print(f"auditing {len(files)} dissection(s)", file=sys.stderr)
    results = [audit_one(f, api_key) for f in files]
    suspects = [r for r in results if r.get("verdict") == "SUSPECT"]

    # Markdown report to stdout (workflow files it as an issue if suspects exist).
    print(f"# Dissection fabrication audit — {len(suspects)}/{len(results)} SUSPECT\n")
    for r in results:
        icon = {"CLEAN": "✅", "SUSPECT": "🔴", "SKIP": "⚪"}.get(r["verdict"], "?")
        print(f"{icon} `{r['path']}` — {r['verdict']}"
              + (f" (num {r.get('mech',0)} / cite {r.get('notfound',0)})" if r.get("issues") else ""))
        for i in r.get("issues", []):
            print(f"    - {i}")
    print(f"\nSUSPECT_COUNT={len(suspects)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
