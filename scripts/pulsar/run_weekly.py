#!/usr/bin/env python3
"""Weekly forward-looking synthesis from the week's daily reports.

Reads the last WEEKLY_LOOKBACK_DAYS of reports/physics-gen-daily/*.md, pulls the
⚡/🔧 entries, and asks qwen3.5-plus for a forward-looking weekly (themes / surprises
/ 5-axis heat / falsifiable watch-list) — per the VLA convention: weekly = scout,
not a retrospective index. Writes reports/weekly/YYYY-Www.md.

Usage:
    python3 scripts/pulsar/run_weekly.py
    PHYSGEN_DRY_RUN=1 python3 scripts/pulsar/run_weekly.py   # print to stdout, don't write
    PHYSGEN_DATE=2026-06-19 python3 scripts/pulsar/run_weekly.py   # override "today"

Requires: DASHSCOPE_API_KEY. Pure stdlib + urllib.
"""
from __future__ import annotations
import datetime
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _config import (
    REPORTS_DIR, WEEKLY_DIR, WEEKLY_TITLE, WEEKLY_LOOKBACK_DAYS, WEEKLY_RETENTION_WEEKS,
    WEEKLY_PROMPT_SYSTEM, DASHSCOPE_BASE_URL, LLM_MODEL, LLM_TIMEOUT,
    LLM_RETRY, LLM_RETRY_BACKOFF, today_str, is_dry_run, get_env,
)


def collect_week(today: datetime.date) -> tuple[list[str], list[Path]]:
    """Return (⚡/🔧 excerpt blocks, source files) for dailies within the lookback window."""
    cutoff = today - datetime.timedelta(days=WEEKLY_LOOKBACK_DAYS)
    blocks: list[str] = []
    used: list[Path] = []
    if not REPORTS_DIR.exists():
        return blocks, used
    for f in sorted(REPORTS_DIR.glob("*.md")):
        try:
            d = datetime.date.fromisoformat(f.stem)
        except ValueError:
            continue  # README.md etc.
        if not (cutoff <= d <= today):
            continue
        excerpt = _extract_load_bearing(f.read_text(encoding="utf-8"))
        if excerpt.strip():
            blocks.append(f"### {f.stem}\n{excerpt}")
            used.append(f)
    return blocks, used


def _extract_load_bearing(md: str) -> str:
    """Keep only the ⚡ and 🔧 tier sections (skip 📖 noise + the header banner)."""
    keep = False
    out: list[str] = []
    for line in md.splitlines():
        if line.startswith("## "):
            keep = line.startswith("## ⚡") or line.startswith("## 🔧")
        if keep:
            out.append(line)
    return "\n".join(out)


def call_qwen(system: str, user: str, api_key: str) -> str:
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        f"{DASHSCOPE_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    last_err = None
    for attempt in range(LLM_RETRY):
        try:
            with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as r:
                data = json.loads(r.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except (urllib.error.HTTPError, urllib.error.URLError, KeyError) as e:
            last_err = e
            print(f"  WARN: qwen weekly call failed (attempt {attempt+1}): {e}", file=sys.stderr)
            if attempt < LLM_RETRY - 1:
                time.sleep(LLM_RETRY_BACKOFF * (attempt + 1))
    raise RuntimeError(f"qwen weekly all {LLM_RETRY} attempts failed: {last_err}")


def iso_week_label(d: datetime.date) -> str:
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def prune_old(today: datetime.date) -> int:
    if not WEEKLY_DIR.exists():
        return 0
    cutoff = today - datetime.timedelta(weeks=WEEKLY_RETENTION_WEEKS)
    n = 0
    for f in WEEKLY_DIR.glob("*-W*.md"):
        try:
            # parse YYYY-Www back to a Monday date
            yr, wk = f.stem.split("-W")
            d = datetime.date.fromisocalendar(int(yr), int(wk), 1)
        except (ValueError, IndexError):
            continue
        if d < cutoff:
            f.unlink()
            n += 1
    return n


def main() -> int:
    today = datetime.date.fromisoformat(today_str())
    blocks, used = collect_week(today)
    if not blocks:
        print(f"  No daily reports in the last {WEEKLY_LOOKBACK_DAYS}d — skipping weekly.", file=sys.stderr)
        return 0

    start = today - datetime.timedelta(days=WEEKLY_LOOKBACK_DAYS)
    corpus = "\n\n".join(blocks)
    print(f"  Aggregating {len(used)} daily report(s) ({start}–{today})…", file=sys.stderr)

    api_key = get_env("DASHSCOPE_API_KEY")
    body = call_qwen(WEEKLY_PROMPT_SYSTEM, corpus, api_key)

    label = iso_week_label(today)
    header = (
        f"# {WEEKLY_TITLE} — {label}\n\n"
        f"> Pulsar 週度前瞻偵察 · {start} – {today} · 彙整 {len(used)} 份日報的 ⚡/🔧 · qwen3.5-plus 綜合\n"
        f"> 源檔：{', '.join(f.stem for f in used)}\n\n---\n\n"
    )
    footer = (
        f"\n\n---\n\n*Generated {datetime.datetime.now().isoformat(timespec='seconds')} · "
        f"`scripts/pulsar/run_weekly.py` · 前瞻偵察（非回顧索引）*\n"
    )
    md = header + body.strip() + footer

    if is_dry_run():
        print("\n" + md)
        print("  (dry run — not writing)", file=sys.stderr)
        return 0

    WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
    out = WEEKLY_DIR / f"{label}.md"
    out.write_text(md, encoding="utf-8")
    print(f"  Wrote {out}", file=sys.stderr)
    pruned = prune_old(today)
    if pruned:
        print(f"  Pruned {pruned} weekly report(s) older than {WEEKLY_RETENTION_WEEKS}w", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
