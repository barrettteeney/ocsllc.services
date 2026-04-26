#!/usr/bin/env python3
"""rank_tracker.py — query Bing for key terms, find ocsllc.services position.

Free, no API key required. Bing public SERPs are accessible via direct HTTP.
Logs results to assets/rank-history.json so we have a longitudinal record.
"""
import os, re, json, urllib.request, urllib.parse, datetime, pathlib, time

ROOT = pathlib.Path(os.environ.get("REPO_ROOT", ".")).resolve()
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
DOMAIN = "ocsllc.services"

KEY_TERMS = [
    "window cleaning kalispell",
    "window cleaning whitefish",
    "window cleaning columbia falls",
    "window cleaning bigfork",
    "pressure washing kalispell",
    "pressure washing flathead valley",
    "post construction window cleaning kalispell",
    "commercial window cleaning kalispell",
    "ocs llc window cleaning",
    "window cleaning montana",
]


def bing_rank(query):
    url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}&count=30&cc=us"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
        with urllib.request.urlopen(req, timeout=20) as r:
            html = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return {"error": str(e)[:120], "rank": None}

    # Find result links (Bing wraps them in <h2><a href="...">)
    links = re.findall(r\'<h2[^>]*>\\s*<a href="([^"]+)"\', html)
    for i, link in enumerate(links, 1):
        if DOMAIN in link:
            return {"rank": i, "url": link, "total_results": len(links)}
    return {"rank": None, "total_results": len(links)}


def main():
    today = datetime.date.today().isoformat()
    history_path = ROOT / "assets" / "rank-history.json"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text())
        except Exception:
            history = []
    else:
        history = []

    snapshot = {"date": today, "results": {}}
    for term in KEY_TERMS:
        print(f"  checking: {term}")
        snapshot["results"][term] = bing_rank(term)
        time.sleep(2)  # politeness — don\'t hammer Bing

    # Replace today\'s entry if present
    history = [h for h in history if h.get("date") != today]
    history.append(snapshot)
    history.sort(key=lambda h: h["date"])
    history = history[-90:]  # keep last 90 snapshots
    history_path.write_text(json.dumps(history, indent=2))

    # Summarise
    print(f"\n=== Rank snapshot {today} ===")
    for term, r in snapshot["results"].items():
        rank = r.get("rank")
        marker = "🟢" if rank and rank <= 3 else ("🟡" if rank and rank <= 10 else "🔴")
        print(f"  {marker} #{rank if rank else \'NR\'}  {term}")

    # Compare with last snapshot
    if len(history) >= 2:
        prev = history[-2]["results"]
        cur = history[-1]["results"]
        regressions = []
        for term in KEY_TERMS:
            pr = prev.get(term, {}).get("rank")
            cr = cur.get(term, {}).get("rank")
            if pr and cr and cr > pr + 5:
                regressions.append(f"  ⚠️ {term}: was #{pr}, now #{cr}")
        if regressions:
            print("\n=== Regressions vs last week ===")
            for r in regressions:
                print(r)


if __name__ == "__main__":
    main()
