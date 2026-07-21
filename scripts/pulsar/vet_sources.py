"""Mechanically vet scout candidates: fetch every feed_url + homepage, classify.
qwen hallucinates URLs even with search — only LIVE, parseable feeds are integrable."""
import json, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

results = json.load(open("/tmp/scout_results.json"))
# flatten + dedup by (feed_url or homepage)
cands, seen = [], set()
for r in results:
    for s in r.get("sources", []):
        key = (s.get("feed_url") or s.get("homepage") or "").rstrip("/").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        cands.append(s)
print(f"{len(cands)} unique candidates after dedup")


def probe(url, want_feed):
    if not url or not url.startswith("http"):
        return "no-url", 0
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 PulsarScout/1.0"})
        with urllib.request.urlopen(req, timeout=25) as resp:
            status = resp.status
            body = resp.read(8000).decode("utf-8", "replace").lower()
        if want_feed:
            if any(t in body for t in ("<rss", "<feed", "<rdf", "<atom", "<item>", "<entry")):
                return "live-feed", status
            return "live-notfeed", status
        return "live", status
    except urllib.error.HTTPError as e:
        return f"http-{e.code}", e.code
    except Exception as e:
        return f"err-{type(e).__name__}", 0


def vet(s):
    feed = s.get("feed_url")
    fstat, fcode = (probe(feed, True) if feed and feed != "null" else ("no-feed", 0))
    hstat, hcode = probe(s.get("homepage"), False)
    return {**s, "feed_status": fstat, "home_status": hstat}


with ThreadPoolExecutor(max_workers=10) as ex:
    vetted = list(ex.map(vet, cands))

json.dump(vetted, open("/tmp/vetted_sources.json", "w"), ensure_ascii=False, indent=2)

live_feeds = [v for v in vetted if v["feed_status"] == "live-feed"]
live_home_nofeed = [v for v in vetted if v["feed_status"] in ("no-feed", "live-notfeed") and v["home_status"] == "live"]
dead = [v for v in vetted if v["feed_status"].startswith(("http-", "err-")) and v["home_status"] != "live"]

print(f"\n✅ LIVE + parseable feeds: {len(live_feeds)}")
for v in sorted(live_feeds, key=lambda x: x.get("subfield", "")):
    print(f"   [{v.get('subfield','?'):16}] {v['name'][:38]:38} {v['feed_url']}")
print(f"\n📄 live homepage, no usable feed: {len(live_home_nofeed)}  (registry-worthy)")
for v in live_home_nofeed:
    print(f"   [{v.get('type','?'):12}] {v['name'][:40]:40} {v.get('homepage','')}")
print(f"\n❌ dead / hallucinated (both feed+home fail): {len(dead)}")
for v in dead:
    print(f"   {v['name'][:40]:40} feed={v['feed_status']} home={v['home_status']}")
