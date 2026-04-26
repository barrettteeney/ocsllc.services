#!/usr/bin/env python3
"""build_image_sitemap.py — generate /image-sitemap.xml from photo manifest.

Google supports image sitemaps separately from the URL sitemap. This helps
photos appear in Google Image Search results.
"""
import os, json, pathlib, datetime

ROOT = pathlib.Path(os.environ.get("REPO_ROOT", ".")).resolve()
manifest_path = ROOT / "assets" / "photos" / "manifest.json"

if not manifest_path.exists():
    print("no manifest yet; writing empty image-sitemap")
    manifest = []
else:
    manifest = json.loads(manifest_path.read_text())

today = datetime.date.today().isoformat()

lines = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
         '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">']

# Each page that displays photos gets the photos listed against it for image SEO.
# Photos appear most prominently on the gallery page, so list them all there.
gallery_url = "https://ocsllc.services/gallery/"
lines.append(f"  <url>")
lines.append(f"    <loc>{gallery_url}</loc>")
lines.append(f"    <lastmod>{today}</lastmod>")
for p in manifest:
    img_url = f"https://ocsllc.services/assets/photos/{p['file']}"
    title = p.get("title", "OCS LLC work")
    caption = p.get("alt", "Window cleaning by OCS LLC")
    # XML-escape
    title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    caption = caption.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    lines.append(f"    <image:image>")
    lines.append(f"      <image:loc>{img_url}</image:loc>")
    lines.append(f"      <image:title>{title}</image:title>")
    lines.append(f"      <image:caption>{caption}</image:caption>")
    lines.append(f"    </image:image>")
lines.append(f"  </url>")

# Homepage with hero image
lines.append(f"  <url>")
lines.append(f"    <loc>https://ocsllc.services/</loc>")
lines.append(f"    <lastmod>{today}</lastmod>")
lines.append(f"    <image:image>")
lines.append(f"      <image:loc>https://ocsllc.services/assets/og.png</image:loc>")
lines.append(f"      <image:title>OCS LLC — Window Cleaning &amp; Pressure Washing</image:title>")
lines.append(f"      <image:caption>Branded share image for OCS LLC, Kalispell MT</image:caption>")
lines.append(f"    </image:image>")
lines.append(f"  </url>")

lines.append("</urlset>")

out = ROOT / "image-sitemap.xml"
new_content = "\n".join(lines) + "\n"
old = out.read_text() if out.exists() else ""
if old != new_content:
    out.write_text(new_content)
    print(f"  image-sitemap.xml: {len(manifest)} images")
else:
    print("no image-sitemap changes")
