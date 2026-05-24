#!/usr/bin/env python3
"""Fetch arxiv RSS → keyword filter A → dedup against seen_ids.json → return list.

Usage:
    python3 scripts/pulsar/collect.py            # → stdout JSON list
    python3 scripts/pulsar/collect.py > out.json # save for next stage

Pure stdlib (urllib + xml.etree). No external deps.
"""
from __future__ import annotations
import datetime
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _config import (
    ARXIV_FEEDS, KEYWORDS_A, KEYWORDS_B_BOOST, KEYWORDS_C_REJECT,
    DEDUP_FILE, DEDUP_WINDOW_DAYS, SKIP_WEEKENDS, today_str,
)


def fetch_rss(url: str, timeout: int = 30) -> str:
    """Fetch RSS feed. Returns body text or empty string on error."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 PulsarSpatial/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  WARN: fetch failed {url}: {e}", file=sys.stderr)
        return ""


def parse_arxiv_rss(xml_text: str) -> list[dict]:
    """Parse arxiv RSS 2.0. Return list of {id, title, abstract, link, category}."""
    if not xml_text.strip():
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"  WARN: XML parse error: {e}", file=sys.stderr)
        return []

    out = []
    # RSS items live at channel/item; arxiv uses dc namespace
    ns = {"dc": "http://purl.org/dc/elements/1.1/"}
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        desc = (item.findtext("description") or "").strip()
        link = (item.findtext("link") or "").strip()
        # arxiv ID from link: http://arxiv.org/abs/2511.12345
        m = re.search(r"abs/(\d{4}\.\d{4,5})", link)
        arxiv_id = m.group(1) if m else link.rsplit("/", 1)[-1]
        out.append({
            "id": arxiv_id,
            "title": title,
            "abstract": _strip_html(desc),
            "link": link,
        })
    return out


def _strip_html(s: str) -> str:
    """Best-effort HTML strip for arxiv abstracts."""
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def passes_keyword_a(paper: dict) -> bool:
    """Layer A: at least one keyword in title OR abstract."""
    text = (paper["title"] + " " + paper["abstract"]).lower()
    return any(kw.lower() in text for kw in KEYWORDS_A)


def fails_keyword_c(paper: dict) -> bool:
    """Layer C: any reject keyword in title → drop."""
    title = paper["title"].lower()
    return any(kw.lower() in title for kw in KEYWORDS_C_REJECT)


def has_boost(paper: dict) -> bool:
    """Layer B: title has production / aerial / benchmark signal → boost priority."""
    title = paper["title"].lower()
    return any(kw.lower() in title for kw in KEYWORDS_B_BOOST)


def load_seen() -> dict[str, str]:
    """Load dedup cache. Format: {arxiv_id: date_seen}."""
    if not DEDUP_FILE.exists():
        return {}
    try:
        return json.loads(DEDUP_FILE.read_text())
    except Exception:
        return {}


def save_seen(seen: dict[str, str]) -> None:
    """Save dedup cache, pruning entries older than DEDUP_WINDOW_DAYS."""
    cutoff = datetime.date.today() - datetime.timedelta(days=DEDUP_WINDOW_DAYS)
    pruned = {k: v for k, v in seen.items() if v >= cutoff.isoformat()}
    DEDUP_FILE.parent.mkdir(parents=True, exist_ok=True)
    DEDUP_FILE.write_text(json.dumps(pruned, indent=2))


def collect_today() -> list[dict]:
    """Main: fetch all RSS, apply A/C filter, dedup, return new papers."""
    today = today_str()

    # Skip weekends (arxiv doesn't post Sat/Sun)
    if SKIP_WEEKENDS:
        dt = datetime.date.fromisoformat(today)
        if dt.weekday() >= 5:
            print(f"  SKIP: {today} is weekend", file=sys.stderr)
            return []

    seen = load_seen()
    all_papers = []
    cat_counts = {}

    for category, url in ARXIV_FEEDS.items():
        xml = fetch_rss(url)
        papers = parse_arxiv_rss(xml)
        for p in papers:
            p["category"] = category
        all_papers.extend(papers)
        cat_counts[category] = len(papers)

    print(f"  Fetched: {sum(cat_counts.values())} papers across {len(ARXIV_FEEDS)} feeds", file=sys.stderr)
    for c, n in cat_counts.items():
        print(f"    {c}: {n}", file=sys.stderr)

    # Dedup against seen
    new_papers = [p for p in all_papers if p["id"] not in seen]
    print(f"  After dedup: {len(new_papers)} new (was {len(all_papers)})", file=sys.stderr)

    # Layer A: must contain spatial AI keyword
    pass_a = [p for p in new_papers if passes_keyword_a(p)]
    print(f"  Pass keyword-A filter: {len(pass_a)}", file=sys.stderr)

    # Layer C: drop reject titles
    final = [p for p in pass_a if not fails_keyword_c(p)]
    print(f"  Pass keyword-C reject: {len(final)}", file=sys.stderr)

    # Tag boost flag
    for p in final:
        p["boost"] = has_boost(p)

    # Record IDs as seen
    for p in final:
        seen[p["id"]] = today
    save_seen(seen)

    print(f"  Total to rate: {len(final)}", file=sys.stderr)
    return final


def main() -> int:
    papers = collect_today()
    print(json.dumps(papers, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
