#!/usr/bin/env python3
"""
sync_gbp.py v2 — pulls live data from a Google Business Profile.

Two-tier strategy:
1. Try the official Places API (New) using a Place ID.
2. Fall back to scraping the public Google Maps page via the FID
   (works for service-area businesses that the Places API filters out).

Reads from environment:
  - PLACE_ID       — required. Either:
                      * "ChIJ..."   Place ID (modern format), OR
                      * "0x...:0x..." FID (Google Maps internal feature ID), OR
                      * a https://www.google.com/maps/... URL containing either
  - GOOGLE_PLACES_API_KEY — optional. If set, used for photo download.

Updates:
  - LocalBusiness JSON-LD on index.html (review, aggregateRating, openingHoursSpecification)
  - Visible review carousel on index.html (between GBP_SYNC_REVIEWS markers)
  - /reviews/index.html (full review list)
  - assets/gbp/photo-{1..8}.jpg + assets/gbp/last-sync.json

Idempotent: prints "no changes" if nothing differs.
"""

import os, sys, re, json, html, hashlib, urllib.request, urllib.parse, datetime, pathlib, ssl


PLACE_ID_RAW = os.environ.get("PLACE_ID", "").strip()
API_KEY      = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
ROOT         = pathlib.Path(os.environ.get("REPO_ROOT", ".")).resolve()

if not PLACE_ID_RAW:
    print("ERROR: PLACE_ID env var must be set.")
    sys.exit(1)


# -----------------------------------------------------------------
# Resolve any input form to (api_id, ftid) where one or both may be set
# -----------------------------------------------------------------

def parse_place_id(raw):
    """Return (api_place_id, ftid) — at least one will be non-None."""
    raw = raw.strip()
    # Maps URL?
    if "google.com/maps" in raw:
        m = re.search(r'!1s(0x[0-9a-fA-F]+:0x[0-9a-fA-F]+)', raw)
        if m:
            return None, m.group(1)
        m = re.search(r'place_id=(ChIJ[A-Za-z0-9_-]+)', raw)
        if m:
            return m.group(1), None
        m = re.search(r'ftid=(0x[0-9a-fA-F]+:0x[0-9a-fA-F]+)', raw)
        if m:
            return None, m.group(1)
    # Pure FID?
    if re.match(r'^0x[0-9a-fA-F]+:0x[0-9a-fA-F]+$', raw):
        return None, raw
    # ChIJ-like Place ID
    if raw.startswith("ChIJ") or raw.startswith("Eo") or raw.startswith("G"):
        return raw, None
    raise SystemExit(f"PLACE_ID not in a recognised format: {raw[:40]}…")


API_ID, FTID = parse_place_id(PLACE_ID_RAW)
print(f"Resolved: api_id={API_ID}  ftid={FTID}")


UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def http_get(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        return r.read().decode("utf-8", errors="replace")


# -----------------------------------------------------------------
# Path 1: Places API (when available + API_ID present)
# -----------------------------------------------------------------

def fetch_via_places_api():
    if not API_ID or not API_KEY:
        return None
    url = f"https://places.googleapis.com/v1/places/{urllib.parse.quote(API_ID)}"
    fields = "id,displayName,formattedAddress,nationalPhoneNumber,websiteUri,regularOpeningHours,rating,userRatingCount,reviews,photos,googleMapsUri"
    req = urllib.request.Request(
        url,
        headers={"X-Goog-Api-Key": API_KEY, "X-Goog-FieldMask": fields,
                 "Accept": "application/json", "User-Agent": UA}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  Places API HTTP {e.code}: {e.reason}; falling back to scrape.")
        return None
    except Exception as e:
        print(f"  Places API error: {e}; falling back to scrape.")
        return None

    return normalise_places_api(data)


def normalise_places_api(p):
    out = {
        "name": (p.get("displayName") or {}).get("text"),
        "address": p.get("formattedAddress"),
        "phone": p.get("nationalPhoneNumber"),
        "website": p.get("websiteUri"),
        "google_maps_uri": p.get("googleMapsUri"),
        "rating": p.get("rating"),
        "review_count": p.get("userRatingCount"),
        "hours": [],
        "reviews": [],
        "photos": []
    }
    rh = p.get("regularOpeningHours") or {}
    DAY_MAP = {"MONDAY":"Monday","TUESDAY":"Tuesday","WEDNESDAY":"Wednesday",
               "THURSDAY":"Thursday","FRIDAY":"Friday","SATURDAY":"Saturday","SUNDAY":"Sunday"}
    for period in rh.get("periods", []):
        opn = period.get("open", {}); cls = period.get("close", {})
        d = DAY_MAP.get(opn.get("day", ""))
        if not d:
            continue
        out["hours"].append({
            "day": d,
            "opens":  f"{opn.get('hour',0):02d}:{opn.get('minute',0):02d}",
            "closes": f"{cls.get('hour',23):02d}:{cls.get('minute',59):02d}" if cls else "23:59"
        })
    for r in (p.get("reviews") or [])[:10]:
        body = (r.get("text") or {}).get("text") or (r.get("originalText") or {}).get("text") or ""
        if not body.strip():
            continue
        out["reviews"].append({
            "author": (r.get("authorAttribution") or {}).get("displayName") or "Google customer",
            "rating": r.get("rating", 5),
            "body": body.strip()
        })
    for ph in (p.get("photos") or [])[:8]:
        out["photos"].append({"name": ph.get("name")})
    return out


# -----------------------------------------------------------------
# Path 2: Maps page scrape (works for SABs that Places API filters out)
# -----------------------------------------------------------------

def fetch_via_maps_scrape():
    if not FTID:
        return None
    # Use a Maps URL that resolves to the place by ftid
    url = f"https://www.google.com/maps/place/data=!4m2!3m1!1s{FTID}?hl=en"
    print(f"  scraping {url[:80]}…")
    try:
        body = http_get(url, {"Accept-Language": "en-US,en;q=0.9"})
    except Exception as e:
        print(f"  scrape failed: {e}")
        return None

    # Maps embeds a giant array `window.APP_INITIALIZATION_STATE` containing
    # most place data. The reviews array is at a known nested path.
    out = {
        "name": None, "address": None, "phone": None, "website": None,
        "google_maps_uri": url, "rating": None, "review_count": None,
        "hours": [], "reviews": [], "photos": []
    }

    # Page <title>: "OCS LLC - Google Maps"
    t = re.search(r'<title>([^<]+?)\s*-\s*Google Maps</title>', body)
    if t:
        out["name"] = html.unescape(t.group(1).strip())

    # Phone number — the page has aria-labels with phone number
    p = re.search(r'href="tel:([+\d]+)"', body)
    if p:
        out["phone"] = p.group(1)

    # Aggregate rating + review count from JSON-LD or text
    # Maps doesn't embed JSON-LD, but the rating appears as text:
    # "5.0 (14)" pattern in the JSON arrays
    rating = re.search(r'\\"5\\\\\.\\d\\\\\s*\\\\\((\\d+)\\\\\)', body)
    rcount = re.search(r'(\d+)\s+review', body, re.IGNORECASE)
    rscore = re.search(r'rating-stars-container.*?aria-label=["\']([\d.]+) star', body, re.DOTALL)

    # Try to extract from APP_INITIALIZATION_STATE
    state = re.search(r'window\.APP_INITIALIZATION_STATE\s*=\s*(\[.*?\]);', body, re.DOTALL)
    if state:
        s = state.group(1)
        # Reviews block: look for arrays starting with author + body
        # Pattern: ["Some Reviewer Name", ..., null, [N stars, ...], "review body"]
        # Maps obfuscates this; instead use the fallback: extract all ".jpg" CDN photo URLs
        photo_urls = re.findall(r'https://lh\d\.googleusercontent\.com/[^"]+', s)
        seen = set()
        for u in photo_urls:
            base = u.split('=')[0]
            if base in seen: continue
            seen.add(base)
            if "photo" in u or "p/" in u or len(out["photos"]) < 8:
                out["photos"].append({"url": base + "=w1200"})
            if len(out["photos"]) >= 8:
                break

    # Reviews: simpler regex over the page body — Maps puts review text in
    # base64-like JSON. We grab review bodies via the structured pattern:
    # "Helpful (n)" / "Like" buttons are near each review. Reviews are in the JSON.
    # Best-effort extraction:
    rev_blocks = re.findall(r'\["([^"]{20,400})",\d{10,},(?:null|"[^"]*"),(\d)', body)
    for bod, rating_s in rev_blocks[:10]:
        out["reviews"].append({
            "author": "Google customer",
            "rating": int(rating_s),
            "body": html.unescape(bod.replace("\\\\u003c", "<").replace("\\\\u003e", ">"))
        })

    return out


# -----------------------------------------------------------------
# Apply the resolved data to the site
# -----------------------------------------------------------------

def update_index_html(d):
    p = ROOT / "index.html"
    if not p.exists():
        return False
    text = p.read_text(); orig = text

    # LocalBusiness JSON-LD block
    m = re.search(
        r'(<script type="application/ld\+json">\s*\{[^<]*?"@id":\s*"https://ocsllc\.services/#business"[^<]*?\})\s*</script>',
        text, re.DOTALL
    )
    if m:
        try:
            block = json.loads(re.search(r'\{.*\}', m.group(1), re.DOTALL).group(0))
        except Exception:
            block = None
        if block is not None:
            if d.get("rating") and d.get("review_count"):
                block["aggregateRating"] = {
                    "@type": "AggregateRating",
                    "ratingValue": str(d["rating"]),
                    "bestRating": "5", "worstRating": "1",
                    "reviewCount": str(d["review_count"])
                }
            if d.get("hours"):
                # group by hours into days
                block["openingHoursSpecification"] = [
                    {"@type": "OpeningHoursSpecification", "dayOfWeek": h["day"],
                     "opens": h["opens"], "closes": h["closes"]}
                    for h in d["hours"]
                ]
            if d.get("phone"):
                ph = re.sub(r"\D", "", d["phone"])
                if len(ph) == 10:
                    block["telephone"] = "+1-" + ph
            if d.get("reviews"):
                block["review"] = [
                    {"@type": "Review",
                     "author": {"@type": "Person", "name": r["author"]},
                     "reviewRating": {"@type": "Rating", "ratingValue": str(r["rating"]), "bestRating": "5"},
                     "reviewBody": r["body"]}
                    for r in d["reviews"][:8]
                ]
            new_block = json.dumps(block, indent=2)
            new_script = f'<script type="application/ld+json">\n{new_block}\n    </script>'
            text = text[:m.start()] + new_script + text[m.end():]

    # Visible review carousel
    if d.get("reviews"):
        cards = []
        for r in d["reviews"][:3]:
            cards.append(f'''                <div class="review-card">
                    <div class="stars">&#9733;&#9733;&#9733;&#9733;&#9733;</div>
                    <p class="italic mt-1">"{html.escape(r["body"])}"</p>
                    <p class="mt-2 text-sm font-semibold">— {html.escape(r["author"])}</p>
                </div>''')
        if cards:
            new_section = "<!-- GBP_SYNC_REVIEWS:start -->\n" + "\n".join(cards) + "\n                <!-- GBP_SYNC_REVIEWS:end -->"
            text = re.sub(
                r'<!-- GBP_SYNC_REVIEWS:start -->.*?<!-- GBP_SYNC_REVIEWS:end -->',
                new_section, text, flags=re.DOTALL
            )

    if text != orig:
        p.write_text(text)
        print("  updated index.html")
        return True
    return False


def update_reviews_page(d):
    p = ROOT / "reviews" / "index.html"
    if not p.exists() or not d.get("reviews"):
        return False
    text = p.read_text(); orig = text

    cards = []
    for r in d["reviews"][:50]:
        cards.append(f'''            <div class="review-card">
                <div class="stars">&#9733;&#9733;&#9733;&#9733;&#9733;</div>
                <p class="italic mt-1">"{html.escape(r["body"])}"</p>
                <p class="mt-2 text-sm font-semibold">— {html.escape(r["author"])}</p>
            </div>''')

    pattern = re.compile(
        r'(<p class="breadcrumbs">.*?</p>\s*<p class="mb-4 text-gray-600 text-sm">[^<]*</p>\s*)(.*?)(<div class="cta-box)',
        re.DOTALL
    )
    m = pattern.search(text)
    if m:
        last = datetime.datetime.utcnow().strftime("%B %-d, %Y")
        text = re.sub(
            r'<p class="mb-4 text-gray-600 text-sm">[^<]*</p>',
            f'<p class="mb-4 text-gray-600 text-sm">Synced from Google Business Profile · last update {last} · <a class="underline text-custom-cyan" href="{html.escape(d.get("google_maps_uri") or "https://www.google.com/maps")}" target="_blank" rel="noopener">Read on Google</a></p>',
            text, count=1
        )
        text = re.sub(pattern, lambda mm: mm.group(1) + "\n".join(cards) + "\n\n            " + mm.group(3), text, count=1)

    if text != orig:
        p.write_text(text)
        print("  updated reviews/index.html")
        return True
    return False


def update_photos(d):
    photos = d.get("photos") or []
    if not photos:
        return False
    out_dir = ROOT / "assets" / "gbp"
    out_dir.mkdir(parents=True, exist_ok=True)
    changed = False
    for i, ph in enumerate(photos[:8]):
        url = ph.get("url")
        if not url and ph.get("name") and API_KEY:
            # Resolve via Places API
            try:
                meta_url = f"https://places.googleapis.com/v1/{ph['name']}/media?maxWidthPx=1200&key={urllib.parse.quote(API_KEY)}&skipHttpRedirect=true"
                meta = json.loads(http_get(meta_url))
                url = meta.get("photoUri")
            except Exception as e:
                print(f"  photo {i} resolve failed: {e}")
        if not url:
            continue
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read()
        except Exception as e:
            print(f"  photo {i} download failed: {e}")
            continue
        path = out_dir / f"photo-{i+1}.jpg"
        old = path.read_bytes() if path.exists() else b""
        if hashlib.sha256(data).hexdigest() != hashlib.sha256(old).hexdigest():
            path.write_bytes(data)
            print(f"  saved {path.relative_to(ROOT)} ({len(data):,} bytes)")
            changed = True
    return changed


def write_metadata(d):
    out_dir = ROOT / "assets" / "gbp"
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "last_sync_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "place_id_raw": PLACE_ID_RAW,
        "name": d.get("name"),
        "rating": d.get("rating"),
        "review_count": d.get("review_count"),
        "review_fetched": len(d.get("reviews") or []),
        "photo_count": len(d.get("photos") or []),
        "google_maps_uri": d.get("google_maps_uri")
    }
    (out_dir / "last-sync.json").write_text(json.dumps(meta, indent=2))


def main():
    d = fetch_via_places_api()
    if not d:
        d = fetch_via_maps_scrape()
    if not d:
        print("ERROR: could not fetch place via API or scrape.")
        sys.exit(1)

    print(f"  name={d.get('name')!r} rating={d.get('rating')} reviews={len(d.get('reviews') or [])} photos={len(d.get('photos') or [])}")

    changed = False
    changed |= update_index_html(d)
    changed |= update_reviews_page(d)
    changed |= update_photos(d)
    write_metadata(d)

    print("CHANGED" if changed else "no changes")


if __name__ == "__main__":
    main()
