#!/usr/bin/env python3
"""
sync_flickr.py — pulls new photos from Barrett's Flickr feed and updates the gallery.

Reads:
  - FLICKR_USER_ID (env, defaults to 202677555@N02)
  - REPO_ROOT (env)

Writes:
  - assets/photos/<photo_id>.jpg for each new photo
  - assets/photos/manifest.json with metadata for all photos
  - gallery/index.html regenerated from the manifest

Idempotent — only downloads photos that aren't already present.
"""
import os, re, json, urllib.request, hashlib, pathlib

USER_ID = os.environ.get("FLICKR_USER_ID", "202677555@N02").strip()
ROOT    = pathlib.Path(os.environ.get("REPO_ROOT", ".")).resolve()
UA      = "Mozilla/5.0 (compatible; OCS-LLC-Site-Sync/1.0; +https://ocsllc.services)"

OUT     = ROOT / "assets" / "photos"
OUT.mkdir(parents=True, exist_ok=True)


def fetch_feed():
    url = f"https://www.flickr.com/services/feeds/photos_public.gne?id={USER_ID}&format=rss_200"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8")


def parse_items(xml):
    items = re.split(r'<item>', xml)[1:]
    out = []
    for it in items:
        title = re.search(r'<title>([^<]+)</title>', it)
        link = re.search(r'<link>([^<]+)</link>', it)
        # Prefer larger size; fall back to smaller
        img_b = re.search(r'<media:content url="(https://live\.staticflickr\.com/[^"]+_b\.jpg)"', it)
        img_z = re.search(r'<media:content url="(https://live\.staticflickr\.com/[^"]+_z\.jpg)"', it)
        img_m = re.search(r'<media:content url="(https://live\.staticflickr\.com/[^"]+_m\.jpg)"', it)
        pubd = re.search(r'<pubDate>([^<]+)</pubDate>', it)
        media_type = re.search(r'<media:content[^>]+type="(image|video)/', it)
        if not (title and link and (img_b or img_z or img_m)):
            continue
        # Skip videos for now
        if media_type and media_type.group(1) == "video":
            continue
        # Skip "whatwedosymbols" — those are icons, not gallery photos
        if "whatwedosymbols" in title.group(1):
            continue
        # Skip screen recordings
        if "ScreenRecording" in title.group(1):
            continue

        photo_url = (img_b or img_z or img_m).group(1)
        # Extract photo ID from the URL: live.staticflickr.com/<server>/<id>_<secret>_<size>.jpg
        m = re.search(r'/(\d+)_([a-f0-9]+)_[a-z]\.jpg', photo_url)
        if not m:
            continue
        photo_id, secret = m.group(1), m.group(2)
        out.append({
            "id":    photo_id,
            "secret": secret,
            "title": title.group(1).strip(),
            "url":   photo_url,
            "page":  link.group(1).strip(),
            "pubDate": pubd.group(1).strip() if pubd else None
        })
    return out


def download(photo, dest):
    req = urllib.request.Request(photo["url"], headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    if len(data) < 5000:
        return False  # likely an error page
    dest.write_bytes(data)
    return True


def main():
    xml = fetch_feed()
    items = parse_items(xml)
    print(f"Found {len(items)} photos in Flickr feed")

    manifest_path = OUT / "manifest.json"
    existing = {}
    if manifest_path.exists():
        try:
            existing = {p["id"]: p for p in json.loads(manifest_path.read_text())}
        except Exception:
            existing = {}

    new_count = 0
    new_manifest = []
    for p in items:
        local = OUT / f"{p['id']}.jpg"
        # Build the alt text from the Flickr title or sensible default
        alt = p["title"]
        if alt.startswith("IMG_") or alt.startswith("DSC"):
            alt = "Window cleaning project photo by OCS LLC"
        else:
            alt = f"OCS LLC: {alt}"

        if not local.exists() or p["id"] not in existing:
            ok = download(p, local)
            if ok:
                new_count += 1
                print(f"  + {p['id']}.jpg ({p['title']})")
        new_manifest.append({
            "id":    p["id"],
            "file":  f"{p['id']}.jpg",
            "title": p["title"],
            "alt":   alt,
            "page":  p["page"],
            "pubDate": p["pubDate"]
        })

    # Sort newest first by pubDate
    new_manifest.sort(key=lambda x: x.get("pubDate") or "", reverse=True)
    manifest_path.write_text(json.dumps(new_manifest, indent=2))

    # Regenerate gallery/index.html
    regenerate_gallery(new_manifest)

    if new_count > 0:
        print(f"CHANGED: {new_count} new photos")
    else:
        print("no changes")


GALLERY_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="index, follow, max-image-preview:large">
    <meta name="theme-color" content="#0CC0DF">

    <title>Gallery | OCS LLC Window Cleaning &amp; Pressure Washing</title>
    <meta name="description" content="Photos from window cleaning, post-construction, and pressure washing jobs in Kalispell, Whitefish, Columbia Falls, and Bigfork. {n} photos, auto-synced from our Flickr feed.">
    <link rel="canonical" href="https://ocsllc.services/gallery/">

    <meta property="og:type" content="website">
    <meta property="og:title" content="Gallery | OCS LLC Window Cleaning &amp; Pressure Washing">
    <meta property="og:description" content="{n} photos from real jobs across the Flathead Valley.">
    <meta property="og:url" content="https://ocsllc.services/gallery/">
    <meta property="og:image" content="https://ocsllc.services/assets/og.png">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Gallery | OCS LLC">

    <script type="application/ld+json">
{image_gallery_ld}
    </script>
    <script type="application/ld+json">
{breadcrumbs_ld}
    </script>

    <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='16' fill='%230CC0DF'/%3E%3Ctext x='50' y='62' font-family='Arial,sans-serif' font-size='44' font-weight='700' text-anchor='middle' fill='white'%3EO%3C/text%3E%3C/svg%3E">
    <link rel="manifest" href="/manifest.webmanifest">
    <link rel="apple-touch-icon" sizes="180x180" href="/assets/apple-touch-icon.png">
    <link rel="preconnect" href="https://cdn.tailwindcss.com" crossorigin>

    <script src="https://cdn.tailwindcss.com" defer></script>
    <style>
        body {{ font-family: 'Garet', sans-serif; margin: 0; padding: 0; min-height: 100vh; display: flex; flex-direction: column; }}
        .bg-custom-cyan {{ background-color: #0CC0DF; }}
        .container {{ width: 90%; max-width: 1280px; margin: 0 auto; padding: 0 1rem; }}
        section {{ padding: clamp(2rem, 5vw, 4rem) 0; }}
        .nav-container {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; width: 90%; max-width: 1200px; margin: 0 auto; padding: 1rem; gap: 0.5rem; }}
        .contact-info {{ display: flex; flex-direction: column; align-items: flex-end; gap: 0.25rem; font-size: 0.95rem; }}
        .contact-info a {{ color: #fff; text-decoration: none; }}
        .hero-mini {{ background: linear-gradient(135deg, #0CC0DF 0%, #0aa3bd 100%); color: white; padding: clamp(2rem, 6vw, 4rem) 1rem; text-align: center; }}
        .hero-mini h1 {{ font-size: clamp(1.75rem, 5vw, 3rem); font-weight: 800; margin-bottom: 0.75rem; }}
        .hero-mini p {{ font-size: clamp(1rem, 2.5vw, 1.25rem); max-width: 760px; margin: 0 auto 1.25rem; }}
        .breadcrumbs {{ font-size: 0.875rem; color: #6b7280; margin-bottom: 1rem; }}
        .breadcrumbs a {{ color: #0CC0DF; text-decoration: none; }}
        .gallery-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1rem; margin-top: 1rem; }}
        .gal-card {{ display: block; aspect-ratio: 4/3; overflow: hidden; border-radius: 10px; background: #f3f4f6; cursor: zoom-in; transition: transform 0.25s, box-shadow 0.25s; }}
        .gal-card img {{ width: 100%; height: 100%; object-fit: cover; transition: transform 0.4s; }}
        .gal-card:hover {{ transform: translateY(-3px); box-shadow: 0 12px 28px rgba(0,0,0,0.15); }}
        .gal-card:hover img {{ transform: scale(1.05); }}
        .lightbox {{ position: fixed; inset: 0; background: rgba(0,0,0,0.92); display: none; z-index: 100; align-items: center; justify-content: center; cursor: zoom-out; }}
        .lightbox.open {{ display: flex; }}
        .lightbox img {{ max-width: 92vw; max-height: 92vh; object-fit: contain; box-shadow: 0 20px 60px rgba(0,0,0,0.5); }}
        .lightbox .lb-close {{ position: absolute; top: 1.5rem; right: 1.5rem; color: white; font-size: 2rem; cursor: pointer; background: rgba(255,255,255,0.1); border-radius: 50%; width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; }}
        .lightbox .lb-prev, .lightbox .lb-next {{ position: absolute; top: 50%; transform: translateY(-50%); color: white; font-size: 3rem; cursor: pointer; padding: 1rem; user-select: none; }}
        .lightbox .lb-prev {{ left: 1rem; }}
        .lightbox .lb-next {{ right: 1rem; }}
        .cta-box {{ background: #0CC0DF; color: white; border-radius: 12px; padding: clamp(1.5rem, 4vw, 2.5rem); text-align: center; margin: 2rem 0; }}
        .cta-box .btn-white {{ background: white; color: black; padding: 0.75rem 1.5rem; border-radius: 8px; font-weight: 600; text-decoration: none; display: inline-block; }}
        .cta-box .tel-link {{ color: white; text-decoration: underline; display: block; margin-top: 0.75rem; font-weight: 600; }}
        .mobile-call-bar {{ display: none; }}
        @media (max-width: 720px) {{
            .mobile-call-bar {{ display: flex; position: fixed; bottom: 0; left: 0; right: 0; background: #0CC0DF; color: white; padding: 0.85rem 1rem; z-index: 50; box-shadow: 0 -4px 12px rgba(0,0,0,0.18); justify-content: center; align-items: center; gap: 1rem; font-weight: 700; text-decoration: none; font-size: 1rem; }}
            body {{ padding-bottom: 60px; }}
            .nav-container {{ flex-direction: column; align-items: flex-start; gap: 0.5rem; }}
        }}
    </style>
</head>
<body class="bg-gray-50 text-black">
    <nav class="bg-custom-cyan text-white p-4 sticky top-0 z-10">
        <div class="container nav-container">
            <a href="/" class="text-lg font-bold">OCS LLC</a>
            <div class="contact-info">
                <p><a href="tel:+14066072151">(406) 607-2151</a></p>
                <p><a href="mailto:barrett@ocsllc.services">barrett@ocsllc.services</a></p>
            </div>
        </div>
    </nav>

    <section class="hero-mini">
        <h1>Recent work</h1>
        <p>Real photos from real jobs across the Flathead Valley. Auto-synced daily from our Flickr feed.</p>
    </section>

    <section class="bg-white">
        <div class="container">
            <p class="breadcrumbs"><a href="/">Home</a> &rsaquo; Gallery</p>
            <p class="mb-6 text-gray-700">{n} photos · click any to expand · use arrow keys to flip through</p>

            <div class="gallery-grid">
{cards}
            </div>

            <div class="cta-box mt-12">
                <h2 class="text-2xl font-bold mb-2">Want your place to look like this?</h2>
                <p>Get a fast, fair, no-pressure quote.</p>
                <a href="/#quote" class="btn-white">Get a Free Estimate</a>
                <a href="tel:+14066072151" class="tel-link">Or call (406) 607-2151</a>
            </div>
        </div>
    </section>

    <footer class="bg-custom-cyan text-white py-8 mt-auto">
        <div class="container text-center">
            <p>&copy; 2025 OCS LLC / Licensed and Insured</p>
            <p class="mt-2">Contact: <a class="underline" href="mailto:barrett@ocsllc.services">barrett@ocsllc.services</a> | <a class="underline" href="tel:+14066072151">(406) 607-2151</a></p>
        </div>
    </footer>

    <a href="tel:+14066072151" class="mobile-call-bar">📞 Call (406) 607-2151</a>

    <div id="lightbox" class="lightbox" aria-hidden="true">
        <span class="lb-close">×</span>
        <span class="lb-prev">‹</span>
        <img src="" alt="">
        <span class="lb-next">›</span>
    </div>

    <script>
        const cards = document.querySelectorAll('.gal-card');
        const lb = document.getElementById('lightbox');
        const lbImg = lb.querySelector('img');
        let cur = 0;
        const urls = Array.from(cards).map(c => c.href);
        const alts = Array.from(cards).map(c => c.querySelector('img').alt);
        function show(i) {{ cur = (i + urls.length) % urls.length; lbImg.src = urls[cur]; lbImg.alt = alts[cur]; lb.classList.add('open'); }}
        function hide() {{ lb.classList.remove('open'); }}
        cards.forEach((c, i) => c.addEventListener('click', e => {{ e.preventDefault(); show(i); }}));
        lb.querySelector('.lb-close').addEventListener('click', hide);
        lb.querySelector('.lb-prev').addEventListener('click', e => {{ e.stopPropagation(); show(cur-1); }});
        lb.querySelector('.lb-next').addEventListener('click', e => {{ e.stopPropagation(); show(cur+1); }});
        lb.addEventListener('click', e => {{ if (e.target === lb) hide(); }});
        document.addEventListener('keydown', e => {{
            if (!lb.classList.contains('open')) return;
            if (e.key === 'Escape') hide();
            if (e.key === 'ArrowLeft') show(cur-1);
            if (e.key === 'ArrowRight') show(cur+1);
        }});
    </script>
</body>
</html>
'''


def regenerate_gallery(manifest):
    cards = "\n".join(
        f'                <a href="/assets/photos/{p["file"]}" class="gal-card"><img src="/assets/photos/{p["file"]}" alt="{p["alt"]}" loading="lazy" decoding="async"></a>'
        for p in manifest
    )
    image_gallery_ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "ImageGallery",
        "name": "OCS LLC Window Cleaning — Recent Work Gallery",
        "description": "Photos from real window cleaning, post-construction, and pressure washing jobs across the Flathead Valley.",
        "image": [f"https://ocsllc.services/assets/photos/{p['file']}" for p in manifest]
    }, indent=2)
    breadcrumbs_ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://ocsllc.services/"},
            {"@type": "ListItem", "position": 2, "name": "Gallery", "item": "https://ocsllc.services/gallery/"}
        ]
    }, indent=2)

    html = GALLERY_TEMPLATE.format(
        n=len(manifest),
        cards=cards,
        image_gallery_ld=image_gallery_ld,
        breadcrumbs_ld=breadcrumbs_ld
    )
    gallery_path = ROOT / "gallery" / "index.html"
    gallery_path.parent.mkdir(parents=True, exist_ok=True)
    gallery_path.write_text(html)


if __name__ == "__main__":
    main()
