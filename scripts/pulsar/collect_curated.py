#!/usr/bin/env python3
"""Curated non-arxiv signal ingestion.

Fetches CURATED_FEEDS (GitHub release feeds + industry/lab/newsletter RSS discovered by
qwen scouts and live-vetted), parses generic RSS/Atom, dedups against a seen-cache, keeps
the last CURATED_LOOKBACK_DAYS, then runs a qwen relevance+signal gate (keep only
spatial-AI-relevant high-signal items). Writes reports/curated-signal/YYYY-MM-DD.md — the
non-arxiv layer of the handbook's intake (tool/model releases, industry posts, deep
essays arxiv doesn't carry).

Usage:
    python3 scripts/pulsar/collect_curated.py
    SPATIAL_DRY_RUN=1 python3 scripts/pulsar/collect_curated.py   # print, don't write/seen
Requires: DASHSCOPE_API_KEY. Pure stdlib + urllib.
"""
from __future__ import annotations
import datetime
import json
import re
import sys
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _config import (
    CURATED_FEEDS, CURATED_DIR, CURATED_SEEN, CURATED_LOOKBACK_DAYS, CURATED_RETENTION_DAYS,
    DASHSCOPE_BASE_URL, LLM_MODEL, LLM_TIMEOUT, LLM_RETRY, LLM_RETRY_BACKOFF,
    today_str, is_dry_run, get_env,
)

_TAG = re.compile(r"\{.*?\}")           # strip XML namespace
_HTML = re.compile(r"<[^>]+>")


def _local(tag: str) -> str:
    return _TAG.sub("", tag)


def fetch(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 PulsarCurated/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _text(el) -> str:
    return (el.text or "").strip() if el is not None else ""


def _parse_date(s: str) -> datetime.date | None:
    s = s.strip()
    if not s:
        return None
    try:                                    # Atom ISO8601
        return datetime.date.fromisoformat(s[:10])
    except ValueError:
        pass
    try:                                    # RSS RFC822
        return parsedate_to_datetime(s).date()
    except (TypeError, ValueError):
        return None


def parse_feed(xml_text: str) -> list[dict]:
    """Generic RSS 2.0 / RDF / Atom parser → [{title, link, date, summary}]."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    items: list[dict] = []
    nodes = [e for e in root.iter() if _local(e.tag) in ("item", "entry")]
    for n in nodes:
        title = link = summary = date_s = ""
        for c in n:
            lt = _local(c.tag)
            if lt == "title":
                title = _text(c)
            elif lt == "link":
                link = c.get("href") or _text(c) or link
            elif lt in ("pubDate", "published", "updated", "date") and not date_s:
                date_s = _text(c)
            elif lt in ("summary", "description", "content") and not summary:
                summary = _HTML.sub(" ", _text(c))[:400]
        d = _parse_date(date_s)
        if title:
            items.append({"title": title.strip(), "link": link.strip(),
                          "date": d.isoformat() if d else "", "summary": summary.strip()})
    return items


def call_qwen(system: str, user: str, api_key: str) -> str:
    payload = {"model": LLM_MODEL, "messages": [
        {"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.2}
    req = urllib.request.Request(
        f"{DASHSCOPE_BASE_URL}/chat/completions", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}, method="POST")
    last = None
    for attempt in range(LLM_RETRY):
        try:
            with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as r:
                return json.loads(r.read().decode())["choices"][0]["message"]["content"]
        except (urllib.error.HTTPError, urllib.error.URLError, KeyError) as e:
            last = e
            if attempt < LLM_RETRY - 1:
                time.sleep(LLM_RETRY_BACKOFF * (attempt + 1))
    raise RuntimeError(f"qwen curated gate failed: {last}")


GATE_SYS = """你是 Spatial Intelligence Handbook 的策展信號守門員。輸入是若干來自非 arxiv 源（GitHub release / 產業博客 / 實驗室 / newsletter）的條目。
判斷每條是否與**空间智能**（SLAM/VIO/3D重建/NeRF/3DGS/depth/feed-forward 3D/VLA/世界模型/位姿/追踪/传感器/空间推理；无人机 aerial anchor）相关**且**是高信号（真进展/重要发布/深度洞见），排除营销、无关、纯招聘、重复公告。
只输出严格 JSON:{"items":[{"i":<输入序号>,"keep":true/false,"tier":"🔥 或 📌","why":"一句话中文说明为何值得看,keep=false时留空"}]}
🔥=重大(新工具/模型发布、范式级洞见);📌=值得注意。宁缺勿滥,大多数博客/release 是 📌 或被 drop。"""


def gate(items: list[dict], api_key: str) -> list[dict]:
    """qwen relevance+signal gate. Batches of 15. Returns items with tier/why on keepers."""
    kept: list[dict] = []
    for start in range(0, len(items), 15):
        batch = items[start:start + 15]
        lines = [f'{i}. [{it["source"]}] {it["title"]}  —  {it["summary"][:160]}'
                 for i, it in enumerate(batch)]
        try:
            raw = call_qwen(GATE_SYS, "\n".join(lines), api_key)
            verdicts = json.loads(re.search(r"\{.*\}", raw, re.S).group(0)).get("items", [])
        except Exception as e:
            print(f"  WARN: gate batch failed ({e}); keeping none of this batch", file=sys.stderr)
            continue
        vmap = {v["i"]: v for v in verdicts if isinstance(v, dict) and "i" in v}
        for i, it in enumerate(batch):
            v = vmap.get(i)
            if v and v.get("keep"):
                kept.append({**it, "tier": v.get("tier", "📌"), "why": v.get("why", "")})
    return kept


def load_seen() -> dict:
    if CURATED_SEEN.exists():
        try:
            return json.loads(CURATED_SEEN.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def main() -> int:
    today = datetime.date.fromisoformat(today_str())
    cutoff = today - datetime.timedelta(days=CURATED_LOOKBACK_DAYS)
    seen = load_seen()
    fresh: list[dict] = []
    per_feed = {}
    for name, url, ftype, subfield in CURATED_FEEDS:
        try:
            items = parse_feed(fetch(url))
        except Exception as e:
            print(f"  WARN: {name} fetch/parse failed: {e}", file=sys.stderr)
            continue
        n_new = 0
        for it in items:
            key = it["link"] or f'{name}:{it["title"]}'
            d = datetime.date.fromisoformat(it["date"]) if it["date"] else today
            if key in seen or d < cutoff:
                continue
            fresh.append({**it, "source": name, "type": ftype, "subfield": subfield, "key": key})
            n_new += 1
        per_feed[name] = (len(items), n_new)
    print(f"  {len(CURATED_FEEDS)} feeds → {len(fresh)} fresh items (last {CURATED_LOOKBACK_DAYS}d, deduped)",
          file=sys.stderr)

    if not fresh:
        print("  No fresh curated items — skipping digest.", file=sys.stderr)
        return 0

    api_key = get_env("DASHSCOPE_API_KEY")
    kept = gate(fresh, api_key)
    print(f"  qwen gate: {len(fresh)} → {len(kept)} kept", file=sys.stderr)

    # ---- render digest ----
    hi = [k for k in kept if k["tier"].startswith("🔥")]
    lo = [k for k in kept if not k["tier"].startswith("🔥")]
    md = [f"# Spatial Curated Signal — {today}", "",
          f"> Pulsar 非 arxiv 策展信號 · {len(CURATED_FEEDS)} 源 (GitHub release / 產業 / 實驗室 / newsletter) · "
          f"qwen 相關性+信號閘 {len(fresh)}→{len(kept)} · window {CURATED_LOOKBACK_DAYS}d", "", "---", ""]
    for label, group in (("## 🔥 重大信號", hi), ("## 📌 值得注意", lo)):
        if not group:
            continue
        md.append(label + "\n")
        for k in sorted(group, key=lambda x: x.get("subfield", "")):
            date = f" · {k['date']}" if k["date"] else ""
            md.append(f"- **[{k['source']}]** [{k['title']}]({k['link']}){date}  \n  {k['why']}")
        md.append("")
    md += ["---", f"\n*Generated {datetime.datetime.now().isoformat(timespec='seconds')} · "
           f"`scripts/pulsar/collect_curated.py` · 非 arxiv 高質量信號*\n"]
    out_text = "\n".join(md)

    if is_dry_run():
        print("\n" + out_text)
        print("  (dry run — not writing / not updating seen)", file=sys.stderr)
        return 0

    CURATED_DIR.mkdir(parents=True, exist_ok=True)
    (CURATED_DIR / f"{today}.md").write_text(out_text, encoding="utf-8")
    print(f"  Wrote {CURATED_DIR / f'{today}.md'}", file=sys.stderr)
    # update seen (all fresh keys, kept or not — don't re-surface dropped items)
    for it in fresh:
        seen[it["key"]] = today.isoformat()
    # prune seen older than retention
    keep_after = (today - datetime.timedelta(days=CURATED_RETENTION_DAYS)).isoformat()
    seen = {k: v for k, v in seen.items() if v >= keep_after}
    CURATED_SEEN.parent.mkdir(parents=True, exist_ok=True)
    CURATED_SEEN.write_text(json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8")
    # prune old digests
    if CURATED_DIR.exists():
        for f in CURATED_DIR.glob("*.md"):
            try:
                fd = datetime.date.fromisoformat(f.stem)
            except ValueError:
                continue
            if fd < today - datetime.timedelta(days=CURATED_RETENTION_DAYS):
                f.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main())
