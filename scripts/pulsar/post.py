#!/usr/bin/env python3
"""Generate daily markdown report + push to Telegram.

Usage:
    python3 scripts/pulsar/rate.py | python3 scripts/pulsar/post.py
    # or:
    python3 scripts/pulsar/post.py --in rated.json

Outputs:
    reports/spatial-daily/YYYY-MM-DD.md  (full report)
    Telegram message (top REPORT_TOP_N picks, summary only)

Requires: TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID env vars.
Skips TG push (and exits 0) if SPATIAL_DRY_RUN=1.
"""
from __future__ import annotations
import argparse
import datetime
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _config import (
    REPORTS_DIR, REPORT_TOP_N, REPORT_RETENTION_DAYS,
    TG_API, TG_PARSE_MODE, TG_MAX_LEN,
    today_str, is_dry_run, get_env,
)

RATING_ORDER = {"⚡": 0, "🔧": 1, "📖": 2, "❌": 3}


def sort_papers(papers: list[dict]) -> list[dict]:
    """Sort by rating priority then boost flag then category."""
    cat_priority = {"cs.RO": 0, "cs.CV": 1, "cs.AI": 2, "cs.LG": 3}
    return sorted(
        papers,
        key=lambda p: (
            RATING_ORDER.get(p.get("rating", "📖"), 9),
            not p.get("boost", False),
            cat_priority.get(p.get("category"), 9),
        ),
    )


def build_markdown(papers: list[dict], date: str) -> str:
    """Generate the full daily report markdown."""
    sorted_papers = sort_papers(papers)
    by_rating: dict[str, list] = {"⚡": [], "🔧": [], "📖": []}
    for p in sorted_papers:
        r = p.get("rating", "📖")
        if r in by_rating:
            by_rating[r].append(p)

    lines = [
        f"# Spatial Daily — {date}",
        "",
        f"> Pulsar pipeline auto-generated. {len(papers)} papers rated; "
        f"⚡ {len(by_rating['⚡'])} · 🔧 {len(by_rating['🔧'])} · 📖 {len(by_rating['📖'])}",
        f"> Sources: arxiv cs.RO / cs.CV / cs.AI / cs.LG · Filter: keyword-A ∩ ¬reject-C · Rate: qwen3.5-plus",
        "",
        "---",
        "",
    ]

    for tier_label, tier_long in [("⚡", "Load-bearing"), ("🔧", "Engineering"), ("📖", "Reference")]:
        bucket = by_rating[tier_label]
        if not bucket:
            continue
        lines.append(f"## {tier_label} {tier_long} ({len(bucket)})")
        lines.append("")
        for p in bucket:
            cat = p.get("category", "?")
            boost = " ⭐" if p.get("boost") else ""
            tags = " · ".join(p.get("tags", [])) or ""
            tags_str = f" *[{tags}]*" if tags else ""
            lines.append(f"- **[{p['title']}]({p['link']})** ({p['id']} · {cat}){boost}")
            if p.get("reason"):
                lines.append(f"  - _{p['reason']}_{tags_str}")
            lines.append("")
        lines.append("---")
        lines.append("")

    lines.append(f"*Generated {datetime.datetime.now().isoformat(timespec='seconds')} · "
                 f"`scripts/pulsar/` standalone pipeline · Phase 1*")
    return "\n".join(lines)


def write_report(md: str, date: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / f"{date}.md"
    out.write_text(md, encoding="utf-8")
    return out


def prune_old_reports() -> int:
    """Delete reports older than REPORT_RETENTION_DAYS. Returns count deleted."""
    if not REPORTS_DIR.exists():
        return 0
    cutoff = datetime.date.today() - datetime.timedelta(days=REPORT_RETENTION_DAYS)
    count = 0
    for f in REPORTS_DIR.glob("*.md"):
        try:
            d = datetime.date.fromisoformat(f.stem)
            if d < cutoff:
                f.unlink()
                count += 1
        except ValueError:
            continue
    return count


def build_tg_message(papers: list[dict], date: str) -> str:
    """Compact TG message: top N picks only."""
    sorted_papers = sort_papers(papers)
    # Only ⚡ and 🔧 worth TG push (📖 too noisy)
    push_papers = [p for p in sorted_papers if p.get("rating") in ("⚡", "🔧")][:REPORT_TOP_N]

    if not push_papers:
        return ""

    lines = [
        f"<b>📡 Spatial Daily — {date}</b>",
        f"<i>Top {len(push_papers)} of {len(papers)} rated</i>",
        "",
    ]
    for p in push_papers:
        cat = p.get("category", "?")
        boost = " ⭐" if p.get("boost") else ""
        tags = " · ".join(p.get("tags", [])[:2])  # first 2 tags for brevity
        tags_str = f" <code>[{tags}]</code>" if tags else ""
        # Escape HTML
        title = (p["title"]
                 .replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;"))
        reason = (p.get("reason", "")
                  .replace("&", "&amp;")
                  .replace("<", "&lt;")
                  .replace(">", "&gt;"))
        lines.append(f"{p.get('rating', '📖')} <a href=\"{p['link']}\">{title}</a>")
        lines.append(f"   <i>{cat}</i>{boost}{tags_str}")
        if reason:
            lines.append(f"   {reason}")
        lines.append("")

    lines.append(f"📂 Full report: <code>reports/spatial-daily/{date}.md</code>")

    msg = "\n".join(lines)
    if len(msg) > TG_MAX_LEN:
        msg = msg[:TG_MAX_LEN - 100] + "\n\n...(truncated)"
    return msg


def push_to_telegram(msg: str) -> None:
    if not msg.strip():
        print("  (no message to push)", file=sys.stderr)
        return
    token = get_env("TELEGRAM_BOT_TOKEN")
    chat_id = get_env("TELEGRAM_CHAT_ID")
    payload = {
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": TG_PARSE_MODE,
        "disable_web_page_preview": True,
    }
    req = urllib.request.Request(
        TG_API.format(token=token),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode("utf-8")
            data = json.loads(body)
            if not data.get("ok"):
                print(f"  WARN: TG returned not-ok: {data}", file=sys.stderr)
            else:
                print(f"  Pushed to TG (msg_id={data['result'].get('message_id')})", file=sys.stderr)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  ERROR: TG HTTP {e.code}: {body[:300]}", file=sys.stderr)
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", help="input JSON (default: stdin)")
    args = ap.parse_args()

    if args.infile:
        papers = json.loads(Path(args.infile).read_text())
    else:
        papers = json.loads(sys.stdin.read())

    date = today_str()

    if not papers:
        print(f"  No papers to post for {date}", file=sys.stderr)
        return 0

    md = build_markdown(papers, date)
    out_path = write_report(md, date)
    print(f"  Wrote {out_path}", file=sys.stderr)

    pruned = prune_old_reports()
    if pruned:
        print(f"  Pruned {pruned} old report(s) older than {REPORT_RETENTION_DAYS}d", file=sys.stderr)

    if is_dry_run():
        print(f"  (dry run — skipping TG push)", file=sys.stderr)
        return 0

    tg_msg = build_tg_message(papers, date)
    if tg_msg:
        push_to_telegram(tg_msg)
    else:
        print(f"  (no ⚡/🔧 papers, skipping TG push)", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
