"""Vet round-2 candidates. Repos → releases.atom (live + recent?). Feeds → live+parseable."""
import json, re, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

res = json.load(open("/tmp/scout_feeds_results.json"))
repos, feeds, seenr, seenf = [], [], set(), set()
for r in res:
    for x in r.get("repos", []):
        k = (x.get("owner_repo") or "").strip().strip("/").lower()
        if k and "/" in k and k not in seenr:
            seenr.add(k); repos.append(x)
    for x in r.get("feeds", []):
        u = (x.get("feed_url") or "").strip().rstrip("/").lower()
        if u.startswith("http") and u not in seenf:
            seenf.add(u); feeds.append(x)
print(f"{len(repos)} unique repos, {len(feeds)} unique feeds to vet")


def fetch(url, n=6000):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 PulsarScout/1.0"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.status, resp.read(n).decode("utf-8", "replace")


def vet_repo(x):
    owner_repo = x["owner_repo"].strip().strip("/")
    for kind in ("releases", "tags"):
        url = f"https://github.com/{owner_repo}/{kind}.atom"
        try:
            st, body = fetch(url, 8000)
        except Exception:
            continue
        n_entry = body.count("<entry")
        if n_entry >= 1:
            dates = re.findall(r"<updated>(\d{4}-\d{2}-\d{2})", body)
            latest = max(dates) if dates else "?"
            return {**x, "feed_url": url, "kind": kind, "entries": n_entry, "latest": latest, "status": "live"}
    return {**x, "feed_url": f"https://github.com/{owner_repo}/releases.atom", "status": "no-feed"}


def vet_feed(x):
    try:
        st, body = fetch(x["feed_url"])
        low = body.lower()
        if any(t in low for t in ("<rss", "<feed", "<rdf", "<item>", "<entry")):
            dates = re.findall(r"(\d{4}-\d{2}-\d{2})", body)
            return {**x, "status": "live-feed", "latest": max(dates) if dates else "?"}
        return {**x, "status": "live-notfeed"}
    except urllib.error.HTTPError as e:
        return {**x, "status": f"http-{e.code}"}
    except Exception as e:
        return {**x, "status": f"err-{type(e).__name__}"}


with ThreadPoolExecutor(max_workers=8) as ex:
    vr = list(ex.map(vet_repo, repos))
    vf = list(ex.map(vet_feed, feeds))
json.dump({"repos": vr, "feeds": vf}, open("/tmp/vetted_feeds.json", "w"), ensure_ascii=False, indent=2)

live_repos = [r for r in vr if r["status"] == "live"]
# freshness: released/tagged in 2024+
fresh = [r for r in live_repos if r.get("latest", "?") >= "2024-01-01"]
live_feeds = [f for f in vf if f["status"] == "live-feed"]
print(f"\n✅ repos with live release/tag atom: {len(live_repos)} ({len(fresh)} fresh 2024+)")
for r in sorted(fresh, key=lambda x: x.get("latest", ""), reverse=True)[:40]:
    print(f"   {r['latest']}  {r['kind']:8} [{r.get('subfield','?'):14}] {r['owner_repo']}")
print(f"\n✅ live parseable non-repo feeds: {len(live_feeds)}")
for f in live_feeds:
    print(f"   [{f.get('type','?'):11}] {f['name'][:36]:36} {f['feed_url']}")
print(f"\n❌ dead repos: {len(vr)-len(live_repos)} | dead feeds: {len(vf)-len(live_feeds)}")
