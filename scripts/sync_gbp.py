#!/usr/bin/env python3
"""
sync_gbp.py v3 — pulls OCS LLC's Google Business Profile via the **OAuth Business
Profile API** and bakes it into the static site. (Places API / Maps scrape can't see
service-area businesses like OCS, so v3 uses owner-authenticated OAuth instead.)

Reads from environment (GitHub Secrets in CI):
  GBP_CLIENT_ID, GBP_CLIENT_SECRET, GBP_REFRESH_TOKEN  — OAuth (scope business.manage)
  GBP_ACCOUNT_ID, GBP_LOCATION_ID                      — numeric IDs
  REPO_ROOT                                            — repo root (default ".")

Updates (idempotent — prints "no changes" if nothing differs):
  - index.html  #business JSON-LD : aggregateRating, openingHoursSpecification, review[]
  - index.html  homepage carousel : between <!-- GBP_HOME:start/end -->
  - reviews/index.html full list   : between <!-- GBP_LIST:start/end --> + last-update stamp
  - assets/gbp/last-sync.json
"""
import os, re, json, html, datetime, urllib.parse, urllib.request, urllib.error, pathlib

ROOT = pathlib.Path(os.environ.get("REPO_ROOT", ".")).resolve()
CID  = os.environ.get("GBP_CLIENT_ID", "").strip()
SEC  = os.environ.get("GBP_CLIENT_SECRET", "").strip()
RT   = os.environ.get("GBP_REFRESH_TOKEN", "").strip()
ACC  = os.environ.get("GBP_ACCOUNT_ID", "").strip()
LOC  = os.environ.get("GBP_LOCATION_ID", "").strip()
MAPS_URI = "https://www.google.com/maps/place/OCS+LLC/data=!4m2!3m1!1s0x2ba17fade10a7f9b:0x7b5721a0f9b3ddf4"

STAR = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_FROM_API = {"MONDAY": "Monday", "TUESDAY": "Tuesday", "WEDNESDAY": "Wednesday",
                "THURSDAY": "Thursday", "FRIDAY": "Friday", "SATURDAY": "Saturday", "SUNDAY": "Sunday"}


def access_token():
    data = urllib.parse.urlencode({
        "client_id": CID, "client_secret": SEC,
        "refresh_token": RT, "grant_type": "refresh_token"}).encode()
    r = json.load(urllib.request.urlopen(
        urllib.request.Request("https://oauth2.googleapis.com/token", data=data), timeout=30))
    return r["access_token"]


def api(url, tok):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} {url}\n  {e.read().decode()[:300]}")
        return None


def hhmm(t):
    return f"{t.get('hours', 0):02d}:{t.get('minutes', 0):02d}"


def fetch():
    tok = access_token()
    out = {"rating": None, "review_count": None, "hours": [], "reviews": []}

    # reviews (v4)
    rev = api(f"https://mybusiness.googleapis.com/v4/accounts/{ACC}/locations/{LOC}/reviews", tok)
    if rev:
        out["rating"] = rev.get("averageRating")
        out["review_count"] = rev.get("totalReviewCount")
        for r in rev.get("reviews", []):
            body = (r.get("comment") or "").strip()
            if not body:
                continue
            out["reviews"].append({
                "author": (r.get("reviewer") or {}).get("displayName") or "Google customer",
                "rating": STAR.get(r.get("starRating", "FIVE"), 5),
                "body": re.sub(r"\s+", " ", body),
                "when": (r.get("createTime") or "")[:10],
            })

    # hours (Business Information v1)
    loc = api(f"https://mybusinessbusinessinformation.googleapis.com/v1/locations/{LOC}?readMask=regularHours", tok)
    if loc:
        for p in (loc.get("regularHours") or {}).get("periods", []):
            d = DAY_FROM_API.get(p.get("openDay", ""))
            if d:
                out["hours"].append({"day": d, "opens": hhmm(p.get("openTime", {})),
                                     "closes": hhmm(p.get("closeTime", {}))})
    return out


def grouped_hours_spec(hours):
    """Collapse identical day hours into schema.org OpeningHoursSpecification entries."""
    by = {h["day"]: (h["opens"], h["closes"]) for h in hours}
    buckets = {}
    for day in DAYS:
        if day in by:
            buckets.setdefault(by[day], []).append(day)
    specs = []
    for (opens, closes), days in buckets.items():
        specs.append({"@type": "OpeningHoursSpecification",
                      "dayOfWeek": days if len(days) > 1 else days[0],
                      "opens": opens, "closes": closes})
    return specs


def stars(n):
    return "&#9733;" * int(n) + "&#9734;" * (5 - int(n))


def trim(s, n=150):
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0]
    return cut.rstrip(".,;:") + "…"


# ---------- site updates ----------

def update_index(d):
    p = ROOT / "index.html"
    text = p.read_text(); orig = text

    # 1) #business JSON-LD
    m = re.search(r'<script type="application/ld\+json">\s*(\{.*?"@id":\s*"https://ocsllc\.services/#business".*?\})\s*</script>',
                  text, re.DOTALL)
    if m:
        try:
            block = json.loads(m.group(1))
        except Exception:
            block = None
        if block is not None:
            if d.get("rating") and d.get("review_count"):
                block["aggregateRating"] = {"@type": "AggregateRating",
                    "ratingValue": str(d["rating"]), "bestRating": "5", "worstRating": "1",
                    "reviewCount": str(d["review_count"])}
            if d.get("hours"):
                block["openingHoursSpecification"] = grouped_hours_spec(d["hours"])
            if d.get("reviews"):
                block["review"] = [
                    {"@type": "Review",
                     "author": {"@type": "Person", "name": r["author"]},
                     "reviewRating": {"@type": "Rating", "ratingValue": str(r["rating"]), "bestRating": "5"},
                     "reviewBody": r["body"]}
                    for r in d["reviews"][:6]]
            new = json.dumps(block, indent=2)
            text = text[:m.start()] + f'<script type="application/ld+json">\n{new}\n    </script>' + text[m.end():]

    # 2) homepage carousel (between markers)
    if d.get("reviews"):
        cards = []
        for i, r in enumerate(d["reviews"][:6]):
            cls = "review-card active" if i == 0 else "review-card"
            cards.append(f'<div class="{cls}"><div class="stars">{stars(r["rating"])}</div>'
                         f'<p class="italic mt-1">"{html.escape(trim(r["body"]))}"</p>'
                         f'<p class="mt-2 text-sm font-semibold">- {html.escape(r["author"])}</p></div>')
        text = re.sub(r'<!-- GBP_HOME:start -->.*?<!-- GBP_HOME:end -->',
                      "<!-- GBP_HOME:start -->\n" + "\n".join(cards) + "\n<!-- GBP_HOME:end -->",
                      text, flags=re.DOTALL)

    if text != orig:
        p.write_text(text); print("  updated index.html"); return True
    return False


def update_reviews_page(d):
    p = ROOT / "reviews" / "index.html"
    if not d.get("reviews"):
        return False
    text = p.read_text(); orig = text

    cards = []
    for r in d["reviews"]:
        cards.append(
            '            <div class="review-card">\n'
            f'                <div class="stars">{stars(r["rating"])}</div>\n'
            f'                <p class="italic mt-1">"{html.escape(r["body"])}"</p>\n'
            f'                <p class="mt-2 text-sm font-semibold">— {html.escape(r["author"])}</p>\n'
            '            </div>')
    text = re.sub(r'<!-- GBP_LIST:start -->.*?<!-- GBP_LIST:end -->',
                  "<!-- GBP_LIST:start -->\n" + "\n".join(cards) + "\n            <!-- GBP_LIST:end -->",
                  text, flags=re.DOTALL)

    stamp = datetime.datetime.utcnow().strftime("%B %d, %Y").replace(" 0", " ")
    text = re.sub(r'(id="gbp-last-update">)[^<]*(</span>)', rf'\g<1>{stamp}\g<2>', text)

    if text != orig:
        p.write_text(text); print("  updated reviews/index.html"); return True
    return False


def main():
    if not all([CID, SEC, RT, ACC, LOC]):
        print("::warning::GBP OAuth env not set; skipping sync."); return
    d = fetch()
    print(f"  rating={d['rating']} count={d['review_count']} reviews={len(d['reviews'])} hours={len(d['hours'])}")
    if not d["reviews"]:
        print("no reviews fetched — aborting (nothing written)."); return

    changed = update_index(d) | update_reviews_page(d)

    out_dir = ROOT / "assets" / "gbp"; out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "last-sync.json").write_text(json.dumps({
        "last_sync_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "rating": d["rating"], "review_count": d["review_count"],
        "reviews_shown": len(d["reviews"]), "maps_uri": MAPS_URI}, indent=2))

    print("CHANGED" if changed else "no changes")


if __name__ == "__main__":
    main()
