#!/usr/bin/env python3
"""
indexnow_ping.py — notify search engines (Bing, Yandex, others) of URL changes.

IndexNow is a free, open protocol. We POST a list of changed URLs to a single
endpoint; participating search engines fetch and re-index them.

Reads:
- INDEXNOW_KEY  — the key string (also matches the filename at the site root)
- CHANGED_URLS  — newline-separated list of URLs (passed in from the workflow)
- HOST          — defaults to ocsllc.services
"""
import os, sys, json, urllib.request

KEY  = os.environ.get("INDEXNOW_KEY", "").strip()
HOST = os.environ.get("HOST", "ocsllc.services").strip()
URLS = [u.strip() for u in os.environ.get("CHANGED_URLS", "").splitlines() if u.strip()]

if not KEY:
    print("INDEXNOW_KEY not set; skipping.")
    sys.exit(0)

if not URLS:
    # Default to the canonical sitemap entries for a full re-ping
    URLS = [f"https://{HOST}/"]

payload = {
    "host": HOST,
    "key":  KEY,
    "keyLocation": f"https://{HOST}/{KEY}.txt",
    "urlList": URLS[:10000]
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(
    "https://api.indexnow.org/indexnow",
    data=data,
    headers={"Content-Type": "application/json; charset=utf-8"},
    method="POST"
)

try:
    with urllib.request.urlopen(req, timeout=15) as r:
        print(f"IndexNow: HTTP {r.status} for {len(URLS)} URL(s)")
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")[:200]
    print(f"IndexNow HTTP {e.code}: {e.reason} — {body}")
    if e.code in (200, 202):
        sys.exit(0)
    sys.exit(0)  # don't fail the workflow on IndexNow errors
except Exception as e:
    print(f"IndexNow error: {e}")
    sys.exit(0)
