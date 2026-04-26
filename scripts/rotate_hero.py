#!/usr/bin/env python3
"""rotate_hero.py — pick a different homepage hero photo each day.

Reads:  assets/photos/manifest.json
Writes: index.html (updates the inline url() in the hero-photo style)
        about/index.html, pricing/index.html, gallery/index.html, etc.

Idempotent — only updates the file if the chosen photo differs from current.
"""
import os, re, json, hashlib, datetime, pathlib

ROOT = pathlib.Path(os.environ.get("REPO_ROOT", ".")).resolve()
manifest_path = ROOT / "assets" / "photos" / "manifest.json"

if not manifest_path.exists():
    print("no manifest yet; skipping")
    raise SystemExit(0)

manifest = json.loads(manifest_path.read_text())
if not manifest:
    print("manifest empty; skipping")
    raise SystemExit(0)

# Use today\'s ISO week as the seed so the photo changes weekly, not daily — daily
# rotation is too noisy on a small business site.
today = datetime.date.today()
week_seed = int(hashlib.md5(today.strftime("%G-W%V").encode()).hexdigest(), 16)

# Each page gets a different photo from the manifest; rotate weekly
PAGES = [
    ("index.html",                  None),  # homepage
    ("about/index.html",            None),
    ("pricing/index.html",          None),
    ("schedule/index.html",         None),
    ("reviews/index.html",          None),
    ("gallery/index.html",          None),
    ("blog/index.html",             None),
]

changed_count = 0
for rel, _ in PAGES:
    p = ROOT / rel
    if not p.exists():
        continue
    # Pick a photo by hashing (rel + week_seed)
    idx = (week_seed + hash(rel)) % len(manifest)
    chosen = manifest[idx]["file"]

    text = p.read_text()
    new = re.sub(
        r'background-image:\s*url\([\'"]/assets/photos/[^\'")]+[\'"]\)',
        f"background-image: url('/assets/photos/{chosen}')",
        text
    )
    if new != text:
        p.write_text(new)
        print(f"  rotated {rel} -> {chosen}")
        changed_count += 1

if changed_count:
    print(f"CHANGED: {changed_count} pages rotated")
else:
    print("no rotation changes (already up to date for this week)")
