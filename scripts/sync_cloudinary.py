#!/usr/bin/env python3
"""
sync_cloudinary.py — pulls new photos from Cloudinary 'ocsllc-website' folder
and merges them into the gallery alongside Flickr photos.

Reads from environment:
  - CLOUDINARY_CLOUD_NAME
  - CLOUDINARY_API_KEY
  - CLOUDINARY_API_SECRET
  - REPO_ROOT

Writes:
  - assets/photos/cl-<public-id>.jpg for each new image
  - merges into assets/photos/manifest.json
  - regenerates gallery/index.html via the same template as sync_flickr.py
"""
import os, sys, json, urllib.request, urllib.parse, base64, datetime, pathlib, re

CLOUD = os.environ.get("CLOUDINARY_CLOUD_NAME", "").strip()
KEY   = os.environ.get("CLOUDINARY_API_KEY", "").strip()
SEC   = os.environ.get("CLOUDINARY_API_SECRET", "").strip()
ROOT  = pathlib.Path(os.environ.get("REPO_ROOT", ".")).resolve()

if not (CLOUD and KEY and SEC):
    print("Cloudinary creds not set; skipping (you can ignore this until cloudinary is configured).")
    sys.exit(0)

OUT = ROOT / "assets" / "photos"
OUT.mkdir(parents=True, exist_ok=True)


def cloudinary_get(path, params=None):
    qs = "?" + urllib.parse.urlencode(params) if params else ""
    url = f"https://api.cloudinary.com/v1_1/{CLOUD}{path}{qs}"
    auth = base64.b64encode(f"{KEY}:{SEC}".encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_photos():
    """List images in the ocsllc-website folder."""
    try:
        data = cloudinary_get("/resources/image", {"prefix": "ocsllc-website/", "max_results": 200, "type": "upload"})
    except urllib.error.HTTPError as e:
        print(f"  Cloudinary API error: HTTP {e.code} — {e.read().decode()[:200]}")
        return []
    except Exception as e:
        print(f"  Cloudinary error: {e}")
        return []
    return data.get("resources", [])


def download(url, dest):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    if len(data) < 1000:
        return False
    dest.write_bytes(data)
    return True


def regenerate_gallery(manifest):
    """Reuse the gallery template from sync_flickr.py."""
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import sync_flickr
        sync_flickr.regenerate_gallery(manifest)
    except Exception as e:
        print(f"  WARN: gallery regenerate failed: {e}")


def main():
    photos = fetch_photos()
    print(f"Found {len(photos)} Cloudinary images")

    manifest_path = OUT / "manifest.json"
    manifest = []
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
        except Exception:
            manifest = []

    new_count = 0
    cloudinary_ids = set()

    for p in photos:
        pid = p.get("public_id", "").replace("/", "-")
        cloudinary_ids.add(pid)
        secure_url = p.get("secure_url")
        if not secure_url:
            continue

        local_name = f"cl-{pid}.jpg"
        local = OUT / local_name

        if not local.exists():
            try:
                download(secure_url, local)
                print(f"  + {local_name}")
                new_count += 1
            except Exception as e:
                print(f"  download fail {local_name}: {e}")
                continue

        # Add or update manifest entry
        existing_idx = next((i for i, e in enumerate(manifest) if e.get("file") == local_name), None)
        entry = {
            "id":      f"cl-{pid}",
            "file":    local_name,
            "title":   p.get("display_name") or p.get("public_id", "").rsplit("/", 1)[-1],
            "alt":     f"OCS LLC: {p.get('public_id', '').rsplit('/', 1)[-1]}",
            "page":    secure_url,
            "pubDate": p.get("created_at")
        }
        if existing_idx is not None:
            manifest[existing_idx] = entry
        else:
            manifest.append(entry)

    # Sort newest first
    manifest.sort(key=lambda x: x.get("pubDate") or "", reverse=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    regenerate_gallery(manifest)

    if new_count > 0:
        print(f"CHANGED: {new_count} new Cloudinary photos")
    else:
        print("no Cloudinary changes")


if __name__ == "__main__":
    main()
