#!/usr/bin/env python3
"""Pull OCS LLC's Google reviews into assets/data/reviews.json.

Runs on a schedule from .github/workflows/site.yml, then build.py bakes the file into the
pages. It uses the same owner sign-in as the old site's sync bot (Google Business Profile API),
read from environment variables (GitHub Secrets in CI):

  GBP_CLIENT_ID, GBP_CLIENT_SECRET, GBP_REFRESH_TOKEN, GBP_ACCOUNT_ID, GBP_LOCATION_ID

Safety: any failure exits non-zero and leaves the file alone, so a Google outage can never
blank out the reviews on the site. The file is only rewritten when something really changed.
"""
import datetime
import json
import os
import pathlib
import re
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "assets" / "data" / "reviews.json"
STARS = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}


def access_token(env):
    body = urllib.parse.urlencode({
        "client_id": env["GBP_CLIENT_ID"],
        "client_secret": env["GBP_CLIENT_SECRET"],
        "refresh_token": env["GBP_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    request = urllib.request.Request("https://oauth2.googleapis.com/token", data=body)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)["access_token"]


def get_json(url, token):
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch_pages(env, token, get=get_json):
    """Yield every page of reviews, newest first."""
    base = (f"https://mybusiness.googleapis.com/v4/accounts/{env['GBP_ACCOUNT_ID']}"
            f"/locations/{env['GBP_LOCATION_ID']}/reviews?pageSize=50&orderBy=updateTime%20desc")
    url = base
    while True:
        page = get(url, token)
        yield page
        next_token = page.get("nextPageToken")
        if not next_token:
            return
        url = f"{base}&pageToken={urllib.parse.quote(next_token)}"


def clean_comment(comment):
    """Tidy whitespace. For translated reviews, keep the reviewer's original words."""
    comment = comment or ""
    if "(Original)" in comment:
        comment = comment.split("(Original)", 1)[1]
    elif "(Translated by Google)" in comment:
        comment = comment.split("(Translated by Google)", 1)[0]
    return re.sub(r"\s+", " ", comment).strip()


def parse(pages):
    """Turn API pages into the site's data. Star-only reviews count but have nothing to show."""
    rating = count = None
    reviews = []
    for page in pages:
        if rating is None:
            rating = page.get("averageRating")
            count = page.get("totalReviewCount")
        for item in page.get("reviews", []):
            body = clean_comment(item.get("comment"))
            if body:
                reviews.append({
                    "author": (item.get("reviewer") or {}).get("displayName") or "Google customer",
                    "rating": STARS.get(item.get("starRating"), 5),
                    "body": body,
                })
    return rating, count, reviews


def merge(current, rating, count, reviews, today):
    """Return the new file contents, or None when nothing changed."""
    if rating is None or not count or not reviews:
        raise ValueError("Google returned no reviews; keeping the current file")
    updated = dict(current, rating=rating, review_count=count, reviews=reviews)
    if all(updated.get(key) == current.get(key) for key in ("rating", "review_count", "reviews")):
        return None
    updated["synced"] = today
    return updated


def main():
    names = ("GBP_CLIENT_ID", "GBP_CLIENT_SECRET", "GBP_REFRESH_TOKEN", "GBP_ACCOUNT_ID", "GBP_LOCATION_ID")
    env = {name: os.environ.get(name, "").strip() for name in names}
    missing = [name for name in names if not env[name]]
    if missing:
        print("Missing settings: " + ", ".join(missing), file=sys.stderr)
        return 1
    current = json.loads(DATA.read_text())
    rating, count, reviews = parse(fetch_pages(env, access_token(env)))
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    updated = merge(current, rating, count, reviews, today)
    if updated is None:
        print("No review changes.")
        return 0
    DATA.write_text(json.dumps(updated, ensure_ascii=False, indent=1) + "\n")
    print(f"Updated: {count} reviews, {len(reviews)} with text, rating {rating}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
