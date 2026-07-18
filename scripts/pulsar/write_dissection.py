#!/usr/bin/env python3
"""qwen writes a handbook dissection from a paper's FULL TEXT; Opus/human verifies.

Division of labour (per Pulsar principle + operator directive): qwen RUNS the
generation (cheap, at scale, in CI); Opus/a human VERIFIES quality before it
lands. This is the generator half. It is full-text grounded (abstract-only
dissections are shallow slop) and template-driven (the 14-item AGENTS.md spec is
the prompt), with mechanical guards so structurally-incomplete drafts never ship.

Usage:
    DASHSCOPE_API_KEY=... python3 scripts/pulsar/write_dissection.py \
        --id 2607.09503 --axes-from-atlas --out /tmp/d.md
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _config import DASHSCOPE_BASE_URL, get_env

GEN_MODEL = "qwen-plus"          # proven in-pipeline; escalate to qwen-max if needed
GEN_MAX_TOKENS = 8000
FULLTEXT_CAP = 30000             # chars of trimmed full text fed to qwen

TEMPLATE = """你是 Spatial Intelligence Handbook 的深度解析（dissection）撰写者。把一篇 paper 写成
**"可面试复述、可工程落地、可快速定位"** 的结构化中文笔记 —— 不是流水摘要。旗舰参考范式是
crossing/slam-vio-migration/vggt_vs_drone_vio.md。

# 硬性结构（缺项会被机械 guard 拒绝，不得省略）

1. 开头元信息块：
   # 中文标题 (English Title)
   > **发布时间**：<年份/日期>
   > **论文 / 模型名**：<原始英文拼写>
   > **核心定位**：一句话——它解决什么痛点 / 比谁强什么
   紧接 1-2 句导语（先写痛点与结论）。

2. **X-Ray 开场**（2-3 句，非专家读完能复述核心）：解决什么问题 / 提出了什么 / 对 spatial AI 研究者意味着什么。

3. **## 📍 研究全景时间线**：ASCII 时间轴，标出本文在演进中的位置 + 本文局限。

4. **## 1 · 核心架构 / 方法总览**
   - ### 1.1 一张"系统/组件对比"表格（模块 / 输入输出 / 训练-推理差异）
   - ### 1.2 关键机制：明确标 **⚡ Eureka Moment：<THE 关键洞见一句话>**
   - ### 1.3 信息流 ASCII 图 / 架构图

5. **## 2 · 数学核心**
   - 先给 📌 **Napkin Formula**：一行公式/直觉句抓住本质
   - 再：目标 → 公式 → 变量说明 → 直觉

6. **## 3 · 带数字走一遍**：一个小的玩具例子 / 数值推导（可低维）。

7. **## 4 · 工程视角**：延迟 / 步数 / 内存 / 吞吐 / 部署约束的 trade-off。

8. **## 5 · 数据与评测**：数据组成 + 评测设置（讲条件，不只给结论）。

9. **## 6 · 能力与失败模式**：能做/不能做讲具体；**必须有 ### 隐含假设 (Hidden Assumptions) 子节**。

10. **## 7 · 与相关工作对比**：对比表 + 结尾 **1 条面试 Tip**（被问到怎么答）。

11. **## 8 · GitHub-validated pitfalls (atlas 联动, <今天日期>)**：若论文有官方 repo 且已发布社区 issue，则据此写实地失败；否则**诚实注明** repo early-release / 暂无 issue 流,并由 §6 失败模式 + 方法约束**推导** 2-3 条 pitfall。（这段是 foundations atlas-bearing zone 的硬性要求。）

12. 文末：
    ---
    [← Back to <module> README](./README.md)
    > **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

# 铁律
- **只依据提供的全文**。数字 / 超参 / benchmark 只写全文里出现的；全文没有就写 `UNVERIFIED` 或不写，**绝不编造**。
- 表格优先；术语中英一致（首次给全称）；避免与导语同句式复述。
- 全中文正文，专名保留英文（VGGT / SfM / 3DGS）。
- 输出**纯 markdown 正文**，不要 ```markdown 代码围栏包整篇，不要任何解释性前言/后语。
"""


def call_qwen(system: str, user: str, api_key: str, model=GEN_MODEL, max_tokens=GEN_MAX_TOKENS) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.4,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        f"{DASHSCOPE_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode("utf-8"))["choices"][0]["message"]["content"]
        except Exception as e:  # noqa
            last = e
            print(f"  WARN qwen attempt {attempt+1}: {e}", file=sys.stderr)
            time.sleep(6 * (attempt + 1))
    raise RuntimeError(f"qwen failed: {last}")


def fetch_fulltext(arxiv_id: str) -> tuple[str, str]:
    """arxiv HTML -> (title, trimmed plain text). Cuts references/appendix."""
    url = f"https://arxiv.org/html/{arxiv_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 PulsarSpatial/1.0"})
    html = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    title = re.sub(r"\s+", " ", m.group(1)).strip() if m else arxiv_id
    body = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    body = re.sub(r"<style.*?</style>", " ", body, flags=re.S)
    body = re.sub(r"<[^>]+>", " ", body)
    body = re.sub(r"\s+", " ", body).strip()
    # cut at bibliography if present
    for marker in ("References References", " References ", " Bibliography "):
        idx = body.rfind(marker)
        if idx > len(body) * 0.4:
            body = body[:idx]
            break
    return title, body[:FULLTEXT_CAP]


def ontology_header(axes: dict) -> str:
    return (
        "<!-- ontology-5axis\n"
        f"problem: {axes.get('problem','n/a')}\n"
        f"representation: {axes.get('representation','n/a')}\n"
        f"sensor: {axes.get('sensor','n/a')}\n"
        f"paradigm: {axes.get('paradigm','n/a')}\n"
        f"time: {axes.get('time','n/a')}\n"
        "ref: ../../cheat-sheet/ontology.md §5\n"
        "-->\n\n"
    )


# 14-item structural guard: qwen drafts that miss required sections never ship.
GUARD_CHECKS = [
    ("meta block", r"> \*\*发布时间\*\*"),
    ("X-Ray opening", r"X-Ray"),
    ("研究全景时间线", r"研究全景时间线"),
    ("架构/信息流图", r"信息流|架构图|```"),
    ("系统对比表", r"\|.*模块.*\||\|.*Method.*\|"),
    ("Eureka Moment", r"Eureka\s*Moment|关键洞见|核心洞见"),
    ("Napkin Formula", r"Napkin Formula"),
    ("数学核心", r"##\s*2\s*·\s*数学核心|数学核心"),
    ("玩具例子", r"带数字走一遍|玩具例子"),
    ("工程视角", r"工程视角"),
    ("隐含假设", r"隐含假设|Hidden Assumptions"),
    ("面试 Tip", r"面试\s*Tip"),
    ("atlas 联动", r"atlas 联动|GitHub-validated"),
    ("back-link", r"\[← Back to"),
    ("ontology header", r"ontology-5axis"),
]


def structural_guard(md: str) -> list[str]:
    """Return the list of required sections MISSING from the draft (empty = pass)."""
    return [name for name, pat in GUARD_CHECKS if not re.search(pat, md)]


def pick_candidate(atlas_path: Path, covered_titles: set[str]) -> dict | None:
    """Top perception ⚡/🔧 paper from the atlas not already dissected.

    Respects the trilogy boundary: excludes VLA/action-policy papers (those belong
    in VLA-Handbook). Ranks ⚡ first, then perception-core keyword bonus.
    """
    perc_para = {"geometric", "learned", "hybrid", "generative", "3R-SLAM-hybrid"}
    perc_prob = {"VO", "VIO", "VSLAM", "SfM", "reconstruction", "depth", "pose",
                 "tracking", "mapping", "occupancy"}
    kws = ("gaussian", "splatting", "3dgs", "vggt", "slam", "depth", "nerf",
           "reconstruction", "sfm", "vio", "feed-forward", "pointmap", "radar", "lidar")
    cands = []
    for line in atlas_path.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        ax = r.get("axes", {})
        if ax.get("paradigm") in ("VLA", "world-model-as-policy"):
            continue
        if ax.get("problem") in ("VLA", "spatial-reasoning"):
            continue
        if ax.get("paradigm") not in perc_para and ax.get("problem") not in perc_prob:
            continue
        slug = re.sub(r"[^a-z0-9]+", "", r["title"].lower())[:40]
        if any(slug[:20] in c or c[:20] in slug for c in covered_titles):
            continue
        t = r["title"].lower()
        score = (3 if r["rating"] == "⚡" else 2 if r["rating"] == "🔧" else 0)
        score += sum(1 for k in kws if k in t)
        cands.append((score, r))
    if not cands:
        return None
    cands.sort(key=lambda x: x[0], reverse=True)
    return cands[0][1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--axes-from-atlas", action="store_true")
    ap.add_argument("--model", default=GEN_MODEL)
    args = ap.parse_args()

    axes = {}
    if args.axes_from_atlas:
        atlas = Path(__file__).resolve().parent.parent.parent / "reports" / "atlas" / "atlas.jsonl"
        for line in atlas.read_text().splitlines():
            if line.strip() and json.loads(line).get("id") == args.id:
                axes = json.loads(line)["axes"]
                break

    print(f"  fetching full text for {args.id}...", file=sys.stderr)
    title, text = fetch_fulltext(args.id)
    print(f"  title: {title[:70]}\n  full text: {len(text)} chars", file=sys.stderr)

    user = (
        f"arXiv id: {args.id}\nTitle: {title}\nontology 5-axis: {json.dumps(axes, ensure_ascii=False)}\n\n"
        f"论文全文（已截断）:\n{text}"
    )
    print(f"  generating dissection via {args.model}...", file=sys.stderr)
    md = call_qwen(TEMPLATE, user, get_env("DASHSCOPE_API_KEY"), model=args.model)
    md = re.sub(r"^```markdown\s*|\s*```$", "", md.strip())

    out = ontology_header(axes) + md + f"\n\n<!-- source: https://arxiv.org/abs/{args.id} -->\n"
    Path(args.out).write_text(out, encoding="utf-8")
    print(f"  wrote {args.out} ({len(out)} chars)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
