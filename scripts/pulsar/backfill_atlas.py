#!/usr/bin/env python3
"""One-shot: seed the atlas from already-archived daily reports.

The daily .md archives only record *which* axes fired (coarse tags), not the
structured coordinate values the star-map needs, and the arxiv RSS window has
long since rolled past those papers. So we re-fetch each paper's abstract from
the arxiv **API** (id_list query, works for any id regardless of RSS window),
re-rate it with the calibrated prompt, and drop full 5-axis coordinates into
the atlas — marked source="backfill" so it's honest about provenance.

Usage:
    DASHSCOPE_API_KEY=... python3 scripts/pulsar/backfill_atlas.py            # all report dates
    DASHSCOPE_API_KEY=... python3 scripts/pulsar/backfill_atlas.py 2026-07-07 # one date
    DASHSCOPE_API_KEY=... python3 scripts/pulsar/backfill_atlas.py --limit 5  # smoke test

Idempotent: re-running upserts by id (backfill records get overwritten by real
pipeline records later if the same paper ever recurs).
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _config import REPORTS_DIR, get_env
import rate
import atlas
from collect import has_boost

ARXIV_API = "http://export.arxiv.org/api/query?id_list={ids}&max_results={n}"
# Primary abstract source: Semantic Scholar batch endpoint. One POST returns up
# to 500 papers and its rate limits are far friendlier than arxiv's id_list
# (which throttles bulk pulls into a 429 penalty box). arxiv stays as fallback
# for papers S2 hasn't indexed yet (very fresh submissions).
S2_BATCH_API = "https://api.semanticscholar.org/graph/v1/paper/batch?fields=title,abstract"
# "(2607.02764 · cs.RO)" — id + category straight from the archived report line
ID_CAT_RE = re.compile(r"\((\d{4}\.\d{4,5})\s*·\s*(cs\.\w+)\)")
ATOM = "{http://www.w3.org/2005/Atom}"


def ids_from_report(md_path: Path) -> list[tuple[str, str]]:
    """Extract (arxiv_id, category) pairs from one daily report, in order, deduped."""
    seen = set()
    out = []
    for m in ID_CAT_RE.finditer(md_path.read_text(encoding="utf-8")):
        aid, cat = m.group(1), m.group(2)
        if aid not in seen:
            seen.add(aid)
            out.append((aid, cat))
    return out


def fetch_abstracts_s2(ids: list[str], attempts: int = 3) -> dict[str, dict]:
    """Semantic Scholar batch → {id: {title, abstract, link}}.

    One POST per 500 ids. Missing papers come back as null entries (aligned
    with input order); papers can also have title but null abstract — both
    fall through to the arxiv fallback.
    """
    out: dict[str, dict] = {}
    for i in range(0, len(ids), 500):
        batch = ids[i:i + 500]
        payload = json.dumps({"ids": [f"ARXIV:{a}" for a in batch]}).encode("utf-8")
        req = urllib.request.Request(
            S2_BATCH_API, data=payload,
            headers={"Content-Type": "application/json",
                     "User-Agent": "PulsarSpatialBackfill/1.0"},
            method="POST",
        )
        body = ""
        for attempt in range(attempts):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    body = r.read().decode("utf-8", errors="replace")
                break
            except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
                code = getattr(e, "code", "n/a")
                wait = 30 * (attempt + 1) if code == 429 else 8 * (attempt + 1)
                print(f"  WARN: S2 batch {code}/{e} (attempt {attempt+1}/{attempts}), retry in {wait}s",
                      file=sys.stderr)
                if attempt < attempts - 1:
                    time.sleep(wait)
        if not body:
            continue
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            print("  WARN: S2 returned non-JSON, skipping batch", file=sys.stderr)
            continue
        if not isinstance(data, list):
            print(f"  WARN: S2 unexpected response shape: {str(data)[:120]}", file=sys.stderr)
            continue
        for aid, item in zip(batch, data):
            if item and item.get("abstract"):
                title = re.sub(r"\s+", " ", (item.get("title") or "").strip())
                out[aid] = {"title": title,
                            "abstract": re.sub(r"\s+", " ", item["abstract"].strip()),
                            "link": f"https://arxiv.org/abs/{aid}"}
    return out


def _fetch_chunk(batch: list[str], attempts: int = 5) -> str:
    """One arxiv API call with retry/backoff.

    arxiv throttles bulk id_list access with 503/429 (and sometimes a 302 →
    read-timeout). 429 lands you in a penalty box for a while, so back off
    hard on it; other transients get a shorter wait. Read timeouts raise
    TimeoutError (an OSError, not URLError) mid-stream, so catch OSError too.
    """
    url = ARXIV_API.format(ids=",".join(batch), n=len(batch))
    req = urllib.request.Request(url, headers={"User-Agent": "PulsarSpatialBackfill/1.0"})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            wait = (30 if e.code == 429 else 8) * (attempt + 1)
            print(f"  WARN: arxiv HTTP {e.code} (attempt {attempt+1}/{attempts}), retry in {wait}s",
                  file=sys.stderr)
        except (urllib.error.URLError, OSError) as e:  # incl. TimeoutError mid-read
            wait = 10 * (attempt + 1)
            print(f"  WARN: arxiv net error {e} (attempt {attempt+1}/{attempts}), retry in {wait}s",
                  file=sys.stderr)
        if attempt < attempts - 1:
            time.sleep(wait)
    return ""


def fetch_abstracts(ids: list[str], chunk: int = 25) -> dict[str, dict]:
    """arxiv API id_list query → {id: {title, abstract, link}}. Polite chunking + retry."""
    out: dict[str, dict] = {}
    n_chunks = (len(ids) + chunk - 1) // chunk
    for i in range(0, len(ids), chunk):
        batch = ids[i:i + chunk]
        xml = _fetch_chunk(batch)
        if not xml:
            print(f"  WARN: arxiv chunk {i//chunk + 1}/{n_chunks} gave up, {len(batch)} ids skipped",
                  file=sys.stderr)
            time.sleep(4)
            continue
        root = ET.fromstring(xml)
        for entry in root.iter(f"{ATOM}entry"):
            raw_id = (entry.findtext(f"{ATOM}id") or "").strip()
            m = re.search(r"abs/(\d{4}\.\d{4,5})", raw_id)
            if not m:
                continue
            aid = m.group(1)
            title = re.sub(r"\s+", " ", (entry.findtext(f"{ATOM}title") or "").strip())
            summary = re.sub(r"\s+", " ", (entry.findtext(f"{ATOM}summary") or "").strip())
            out[aid] = {"title": title, "abstract": summary, "link": f"https://arxiv.org/abs/{aid}"}
        print(f"  arxiv API: chunk {i//chunk + 1}/{n_chunks} → {len(batch)} ids, {len(out)} resolved so far",
              file=sys.stderr)
        if i + chunk < len(ids):
            time.sleep(4)  # arxiv rate-limit courtesy
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dates", nargs="*", help="report dates YYYY-MM-DD (default: all)")
    ap.add_argument("--limit", type=int, default=0, help="cap papers per date (smoke test)")
    ap.add_argument("--force", action="store_true",
                    help="re-rate even ids already in the atlas (default: skip = resumable)")
    args = ap.parse_args()

    reports = sorted(REPORTS_DIR.glob("*.md"))
    reports = [p for p in reports if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem)]
    if args.dates:
        wanted = set(args.dates)
        reports = [p for p in reports if p.stem in wanted]
    if not reports:
        print("  No matching reports found.", file=sys.stderr)
        return 0

    # Resume: skip ids already coordinated so a re-run after a kill is cheap and
    # idempotent (qwen is the only real cost). --force re-rates everything.
    have = set() if args.force else {r["id"] for r in atlas.load()}
    if have:
        print(f"  Resume: {len(have)} ids already in atlas will be skipped (use --force to re-rate)",
              file=sys.stderr)

    api_key = get_env("DASHSCOPE_API_KEY")
    total_added = total_updated = 0

    for rp in reports:
        date = rp.stem
        pairs = [(aid, cat) for aid, cat in ids_from_report(rp) if aid not in have]
        if args.limit:
            pairs = pairs[:args.limit]
        if not pairs:
            print(f"  {date}: nothing new to rate, skip", file=sys.stderr)
            continue
        print(f"\n=== {date}: {len(pairs)} papers ===", file=sys.stderr)
        ids = [aid for aid, _ in pairs]
        meta = fetch_abstracts_s2(ids)
        missing = [aid for aid in ids if aid not in meta]
        print(f"  S2 resolved {len(meta)}/{len(ids)}"
              + (f"; arxiv fallback for {len(missing)}" if missing else ""), file=sys.stderr)
        if missing:
            meta.update(fetch_abstracts(missing))

        records = []
        for idx, (aid, cat) in enumerate(pairs):
            m = meta.get(aid)
            if not m or not m["abstract"]:
                print(f"  skip {aid}: no abstract from API", file=sys.stderr)
                continue
            paper = {
                "id": aid, "title": m["title"], "abstract": m["abstract"],
                "link": m["link"], "category": cat,
            }
            paper["boost"] = has_boost(paper)
            print(f"  rate {idx+1}/{len(pairs)}: {aid}", file=sys.stderr)
            try:
                rate.rate_one(paper, api_key)
            except Exception as e:
                print(f"  ERROR rating {aid}: {e}", file=sys.stderr)
                continue
            if paper.get("rating") == "❌":
                continue  # match pipeline: ❌ never enters the atlas
            records.append(atlas.make_record(paper, date, source="backfill"))

        added, updated = atlas.upsert(records)
        total_added += added
        total_updated += updated
        print(f"  {date}: atlas +{added} / {updated} updated", file=sys.stderr)

    atlas.write_overview()
    print(f"\nBackfill done: +{total_added} new / {total_updated} updated. Overview regenerated.",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
