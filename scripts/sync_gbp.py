#!/usr/bin/env python3
"""
sync_gbp.py — pull live data from Google Business Profile via Places API
and bake it into the static site.

Reads:
  - GOOGLE_PLACES_API_KEY (env)  — Google Cloud Places API (New) key
  - PLACE_ID              (env)  — your GBP Place ID (e.g. ChIJ...)

Writes:
  - Updates LocalBusiness JSON-LD on index.html (review array, aggregateRating, openingHoursSpecification, telephone, url)
  - Updates the visible review carousel on index.html (between GBP_SYNC_REVIEWS:start/end markers)
  - Regenerates /reviews/index.html with full review list
  - Downloads up to 8 latest photos to assets/gbp/photo-{n}.jpg
  - Updates /assets/gbp/last-sync.json with metadata so the page can show "last synced"

Idempotent. If nothing changed, the script exits 0 and prints "no changes".
Designed to run from a GitHub Action with the repo checked out at cwd.
"""

import os, sys, json, re, hashlib, urllib.request, urllib.parse, datetime, html, pathlib

API_KEY  = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
PLACE_ID = os.environ.get("PLACE_ID", "").strip()
ROOT     = pathlib.Path(os.environ.get("REPO_ROOT", ".")).resolve()

if not API_KEY or not PLACE_ID:
    print("ERROR: GOOGLE_PLACES_API_KEY and PLACE_ID must be set in the environment.")
    print("       Set them as repo secrets named GOOGLE_PLACES_API_KEY and PLACE_ID.")
    sys.exit(1)


def fetch_place_details():
    """Use the Places API (New) Place Details endpoint."""
    url = f"https://places.googleapis.com/v1/places/{urllib.parse.quote(PLACE_ID)}"
    field_mask = ",".join([
        "id",
        "displayName",
        "formattedAddress",
        "internationalPhoneNumber",
        "nationalPhoneNumber",
        "websiteUri",
        "regularOpeningHours",
        "rating",
        "userRatingCount",
        "reviews",
        "photos",
        "googleMapsUri"
    ])
    req = urllib.request.Request(
        url,
        headers={
            "X-Goog-Api-Key": API_KEY,
            "X-Goog-FieldMask": field_mask,
            "Accept": "application/json"
        }
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_photo(photo_resource_name, max_w=1200):
    """Resolve a photo resource name to bytes."""
    url = f"https://places.googleapis.com/v1/{photo_resource_name}/media?maxWidthPx={max_w}&key={urllib.parse.quote(API_KEY)}&skipHttpRedirect=true"
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    photo_uri = data.get("photoUri")
    if not photo_uri:
        return None
    with urllib.request.urlopen(photo_uri, timeout=30) as r:
        return r.read()


# Map Google "DAY_OF_WEEK" to Schema.org day names
DAY_MAP = {
    "MONDAY": "Monday", "TUESDAY": "Tuesday", "WEDNESDAY": "Wednesday",
    "THURSDAY": "Thursday", "FRIDAY": "Friday", "SATURDAY": "Saturday", "SUNDAY": "Sunday"
}

def hours_to_schema(regular_hours):
    """Convert Google regularOpeningHours -> openingHoursSpecification array."""
    if not regular_hours:
        return None
    periods = regular_hours.get("periods", [])
    out = []
    for p in periods:
        opn = p.get("open", {})
        cls = p.get("close", {})
        day = DAY_MAP.get(opn.get("day", ""))
        if not day:
            continue
        opens = f"{opn.get('hour', 0):02d}:{opn.get('minute', 0):02d}"
        closes = f"{cls.get('hour', 0):02d}:{cls.get('minute', 0):02d}" if cls else "23:59"
        out.append({"@type": "OpeningHoursSpecification", "dayOfWeek": day, "opens": opens, "closes": closes})
    return out or None


def update_index_html(place):
    """Patch the homepage's LocalBusiness JSON-LD and the testimonial carousel."""
    index_path = ROOT / "index.html"
    if not index_path.exists():
        print(f"WARN: {index_path} not found, skipping homepage update.")
        return False

    text = index_path.read_text(encoding="utf-8")
    orig = text

    # Find the LocalBusiness JSON-LD block. We rely on the unique @id to locate it.
    pattern = re.compile(
        r'(<script type="application/ld\+json">\s*\{[^<]*?"@id":\s*"https://ocsllc\.services/#business"[^<]*?\})\s*</script>',
        re.DOTALL
    )
    m = pattern.search(text)
    if not m:
        print("WARN: Could not find LocalBusiness JSON-LD block on index.html")
    else:
        try:
            block = json.loads(re.search(r'\{.*\}', m.group(1), re.DOTALL).group(0))
        except Exception as e:
            print(f"WARN: failed to parse existing LocalBusiness JSON-LD: {e}")
            block = None

        if block is not None:
            # Update fields
            if place.get("nationalPhoneNumber"):
                block["telephone"] = "+1-" + re.sub(r"\D", "", place["nationalPhoneNumber"])[-10:]
            if place.get("websiteUri"):
                block["url"] = place["websiteUri"]

            if place.get("rating") and place.get("userRatingCount"):
                block["aggregateRating"] = {
                    "@type": "AggregateRating",
                    "ratingValue": str(place["rating"]),
                    "bestRating": "5",
                    "worstRating": "1",
                    "reviewCount": str(place["userRatingCount"])
                }

            ohs = hours_to_schema(place.get("regularOpeningHours"))
            if ohs:
                block["openingHoursSpecification"] = ohs

            reviews = place.get("reviews", []) or []
            if reviews:
                block["review"] = []
                for r in reviews[:8]:
                    author = r.get("authorAttribution", {}).get("displayName") or "Google customer"
                    body = (r.get("text", {}) or {}).get("text", "") or r.get("originalText", {}).get("text", "")
                    body = body.strip()
                    if not body:
                        continue
                    rating = r.get("rating", 5)
                    block["review"].append({
                        "@type": "Review",
                        "author": {"@type": "Person", "name": author},
                        "reviewRating": {"@type": "Rating", "ratingValue": str(rating), "bestRating": "5"},
                        "reviewBody": body
                    })

            new_block = json.dumps(block, indent=2)
            new_script = f'<script type="application/ld+json">\n{new_block}\n    </script>'
            text = text[:m.start()] + new_script + text[m.end():]

    # Update the visible review carousel (between markers)
    reviews = place.get("reviews", []) or []
    if reviews:
        cards = []
        for r in reviews[:3]:
            author = r.get("authorAttribution", {}).get("displayName") or "Google customer"
            body = (r.get("text", {}) or {}).get("text", "") or r.get("originalText", {}).get("text", "")
            body = body.strip()
            if not body:
                continue
            cards.append(f'''                <div class="review-card">
                    <div class="stars">&#9733;&#9733;&#9733;&#9733;&#9733;</div>
                    <p class="italic mt-1">"{html.escape(body)}"</p>
                    <p class="mt-2 text-sm font-semibold">— {html.escape(author)}</p>
                </div>''')
        if cards:
            new_section = "<!-- GBP_SYNC_REVIEWS:start -->\n" + "\n".join(cards) + "\n                <!-- GBP_SYNC_REVIEWS:end -->"
            text = re.sub(
                r'<!-- GBP_SYNC_REVIEWS:start -->.*?<!-- GBP_SYNC_REVIEWS:end -->',
                new_section,
                text,
                flags=re.DOTALL
            )

    if text != orig:
        index_path.write_text(text, encoding="utf-8")
        print("  updated index.html")
        return True
    return False


def update_reviews_page(place):
    """Regenerate /reviews/index.html with full review list."""
    reviews_path = ROOT / "reviews" / "index.html"
    if not reviews_path.exists():
        print(f"WARN: {reviews_path} not found, skipping reviews page update.")
        return False

    reviews = place.get("reviews", []) or []
    if not reviews:
        print("  (no reviews returned by Places API)")
        return False

    text = reviews_path.read_text(encoding="utf-8")
    orig = text

    # Build review cards block
    cards = []
    for r in reviews[:50]:
        author = r.get("authorAttribution", {}).get("displayName") or "Google customer"
        body = (r.get("text", {}) or {}).get("text", "") or r.get("originalText", {}).get("text", "")
        body = body.strip()
        if not body:
            continue
        cards.append(f'''            <div class="review-card">
                <div class="stars">&#9733;&#9733;&#9733;&#9733;&#9733;</div>
                <p class="italic mt-1">"{html.escape(body)}"</p>
                <p class="mt-2 text-sm font-semibold">— {html.escape(author)}</p>
            </div>''')
    if not cards:
        return False
    new_block = "\n".join(cards)

    # Replace the existing review-card block (between breadcrumbs <p> and the cta-box)
    pattern = re.compile(
        r'(<p class="breadcrumbs">.*?</p>\s*<p class="mb-4 text-gray-600 text-sm">[^<]*</p>\s*)(.*?)(<div class="cta-box)',
        re.DOTALL
    )
    m = pattern.search(text)
    if not m:
        print("WARN: Could not locate review block in reviews page")
        return False

    last_sync = datetime.datetime.utcnow().strftime("%B %-d, %Y")
    intro = re.sub(
        r'<p class="mb-4 text-gray-600 text-sm">[^<]*</p>',
        f'<p class="mb-4 text-gray-600 text-sm">Synced from our Google Business Profile · last update {last_sync} · <a class="underline text-custom-cyan" href="{html.escape(place.get("googleMapsUri", "https://www.google.com/maps"))}" target="_blank" rel="noopener">Read on Google</a></p>',
        text,
        count=1
    )
    text = re.sub(
        pattern,
        lambda mm: mm.group(1) + new_block + "\n\n            " + mm.group(3),
        intro,
        count=1
    )

    if text != orig:
        reviews_path.write_text(text, encoding="utf-8")
        print("  updated reviews/index.html")
        return True
    return False


def update_photos(place):
    """Download up to 8 latest photos to assets/gbp/."""
    photos = place.get("photos", []) or []
    if not photos:
        return False
    out_dir = ROOT / "assets" / "gbp"
    out_dir.mkdir(parents=True, exist_ok=True)
    changed = False
    for i, p in enumerate(photos[:8]):
        name = p.get("name")
        if not name:
            continue
        try:
            data = fetch_photo(name)
        except Exception as e:
            print(f"  photo {i} fetch failed: {e}")
            continue
        if not data:
            continue
        path = out_dir / f"photo-{i+1}.jpg"
        old = path.read_bytes() if path.exists() else b""
        if hashlib.sha256(data).hexdigest() != hashlib.sha256(old).hexdigest():
            path.write_bytes(data)
            print(f"  saved {path.relative_to(ROOT)}  ({len(data):,} bytes)")
            changed = True
    return changed


def write_metadata(place):
    out_dir = ROOT / "assets" / "gbp"
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "last_sync_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "place_id": PLACE_ID,
        "rating": place.get("rating"),
        "user_rating_count": place.get("userRatingCount"),
        "review_count": len(place.get("reviews") or []),
        "photo_count": len(place.get("photos") or []),
        "google_maps_uri": place.get("googleMapsUri")
    }
    (out_dir / "last-sync.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def main():
    print(f"Fetching place {PLACE_ID}...")
    place = fetch_place_details()
    print(f"  rating={place.get('rating')} reviews={len(place.get('reviews') or [])} photos={len(place.get('photos') or [])}")

    changed = False
    changed |= update_index_html(place)
    changed |= update_reviews_page(place)
    changed |= update_photos(place)
    write_metadata(place)

    if changed:
        print("CHANGED")
    else:
        print("no changes")


if __name__ == "__main__":
    main()
