#!/usr/bin/env python3
"""health_check.py — daily site uptime + schema sanity check.

Pings every page in the sitemap, validates JSON-LD parses, checks for required
elements (h1, OG meta). Exits non-zero on any failure so the workflow can open
a GitHub issue.
"""
import os, re, sys, json, urllib.request, pathlib

UA = "OCS-LLC-Healthcheck/1.0 (+https://ocsllc.services)"
ROOT = pathlib.Path(os.environ.get("REPO_ROOT", ".")).resolve()
BASE = "https://ocsllc.services"

sitemap = (ROOT / "sitemap.xml").read_text() if (ROOT / "sitemap.xml").exists() else ""
urls = re.findall(r"<loc>([^<]+)</loc>", sitemap)
if not urls:
    urls = [BASE + "/"]

print(f"Health-checking {len(urls)} URLs...")

problems = []
checked = 0

for url in urls:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            status = r.status
            body = r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        problems.append(f"  HTTP {e.code} on {url}")
        continue
    except Exception as e:
        problems.append(f"  Error fetching {url}: {e}")
        continue

    checked += 1
    if status != 200:
        problems.append(f"  HTTP {status} on {url}")
        continue

    if "<h1" not in body:
        problems.append(f"  Missing <h1> on {url}")
    if 'name="viewport"' not in body:
        problems.append(f"  Missing viewport meta on {url}")
    if 'property="og:title"' not in body:
        problems.append(f"  Missing og:title on {url}")

    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', body, re.DOTALL)
    for i, b in enumerate(blocks):
        try:
            json.loads(b)
        except json.JSONDecodeError as e:
            problems.append(f"  Invalid JSON-LD #{i} on {url}: {e}")

print(f"Checked {checked}/{len(urls)} URLs successfully")
if problems:
    print("\nPROBLEMS:")
    for p in problems:
        print(p)
    sys.exit(1)
print("All healthy.")
