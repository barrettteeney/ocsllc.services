#!/usr/bin/env python3
"""
sync_instagram.py — pulls newest Instagram VIDEO posts (reels) and rebuilds the
"Our work" video gallery. Mirrors the sync_flickr.py pattern: download media ->
ffmpeg color-grade/compress + poster -> write a JSON manifest -> regenerate a
static page from a template baked into this script. Runs in GitHub Actions.

Reads (env):
  - IG_ACCESS_TOKEN   Instagram Graph API long-lived token   (CI secret)
  - IG_USER_ID        Instagram business/user id             (CI secret)
  - IG_API_BASE       default https://graph.instagram.com
  - MAX_CLIPS         default 6
  - REPO_ROOT         repo working dir

Writes:
  - assets/videos/clips/ig-<id>.mp4     (graded + compressed, muted)
  - assets/videos/posters/ig-<id>.jpg   (poster frame)
  - assets/videos/manifest.json         (newest MAX_CLIPS, newest first)
  - our-work/index.html                 (regenerated from the manifest)

No token? -> just regenerate the page from the EXISTING manifest (keeps the
seeded fallback clips) and exit. Idempotent: only new posts are downloaded.
"""
import os, re, json, subprocess, urllib.request, urllib.parse, pathlib, time

ROOT  = pathlib.Path(os.environ.get("REPO_ROOT", ".")).resolve()
TOKEN = os.environ.get("IG_ACCESS_TOKEN", "").strip()
UID   = os.environ.get("IG_USER_ID", "").strip()
BASE  = os.environ.get("IG_API_BASE", "https://graph.instagram.com").rstrip("/")
MAXC  = int(os.environ.get("MAX_CLIPS", "6"))

VID   = ROOT / "assets" / "videos"
CLIPS = VID / "clips"
POSTS = VID / "posters"
MANIFEST = VID / "manifest.json"
for d in (CLIPS, POSTS):
    d.mkdir(parents=True, exist_ok=True)

# Bright/airy color grade — matches the site's real-photo look.
GRADE = ("eq=contrast=1.05:brightness=0.03:saturation=1.12:gamma=1.05,"
         "curves=all='0/0.02 0.25/0.30 0.8/0.84 1/1',unsharp=5:5:0.4:5:5:0")
VF = GRADE + ",scale=720:1280:flags=lanczos"


def clean_caption(c):
    if not c:
        return "Fresh from the Flathead Valley"
    c = re.sub(r"#\w+", "", c).replace("\n", " ").strip()
    c = re.sub(r"\s+", " ", c)
    if len(re.sub(r"\W", "", c)) < 2:          # emoji-only / empty -> friendly default
        return "Streak-free in the Flathead Valley"
    return (c[:58] + "…") if len(c) > 59 else c


def load_manifest():
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text()).get("items", [])
        except Exception:
            return []
    return []


def fetch_media():
    fields = "id,caption,media_type,media_product_type,media_url,thumbnail_url,permalink,timestamp"
    url = f"{BASE}/{UID}/media?fields={fields}&limit={MAXC*3}&access_token={urllib.parse.quote(TOKEN)}"
    req = urllib.request.Request(url, headers={"User-Agent": "OCS-LLC-Site-Sync/1.0"})
    data = json.load(urllib.request.urlopen(req, timeout=40))
    return [m for m in data.get("data", []) if m.get("media_type") == "VIDEO" and m.get("media_url")]


def process(media_url, mp4, jpg):
    raw = str(mp4) + ".raw.mp4"
    urllib.request.urlretrieve(media_url, raw)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-an", "-t", "16",
                    "-vf", VF, "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
                    "-crf", "28", "-maxrate", "1800k", "-bufsize", "3600k", "-preset", "medium", "-movflags", "+faststart", str(mp4)], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1", "-i", raw,
                    "-frames:v", "1", "-vf", VF, str(jpg)], check=True)
    os.remove(raw)


def main():
    if not TOKEN or not UID:
        items = load_manifest()
        print(f"No IG token configured — regenerating page from existing manifest ({len(items)} items).")
        regenerate_page(items)
        return

    existing = {it["id"]: it for it in load_manifest()}
    media = fetch_media()
    print(f"Fetched {len(media)} videos from Instagram.")

    items, added = [], 0
    for m in media[:MAXC]:
        mid = m["id"]
        fn = "ig-" + re.sub(r"[^0-9A-Za-z]", "", mid)
        mp4, jpg = CLIPS / f"{fn}.mp4", POSTS / f"{fn}.jpg"
        if mid in existing and mp4.exists():
            it = existing[mid]
        else:
            try:
                process(m["media_url"], mp4, jpg)
                added += 1
                print(f"  + {fn}.mp4")
            except Exception as e:
                print(f"  ! process failed {mid}: {e}")
                continue
            it = {"id": mid,
                  "clip": f"/assets/videos/clips/{fn}.mp4",
                  "poster": f"/assets/videos/posters/{fn}.jpg",
                  "caption": clean_caption(m.get("caption")),
                  "permalink": m.get("permalink", ""),
                  "ts": m.get("timestamp", "")}
        items.append(it)

    items.sort(key=lambda x: x.get("ts", ""), reverse=True)
    MANIFEST.write_text(json.dumps({"updated": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    "items": items}, indent=2))
    regenerate_page(items)

    keep_mp4 = {pathlib.PurePosixPath(i["clip"]).name for i in items}
    keep_jpg = {pathlib.PurePosixPath(i["poster"]).name for i in items}
    for f in CLIPS.glob("ig-*.mp4"):
        if f.name not in keep_mp4:
            f.unlink()
    for f in POSTS.glob("ig-*.jpg"):
        if f.name not in keep_jpg:
            f.unlink()

    print(f"CHANGED: {added} new clip(s); manifest has {len(items)}." if added else "no changes")


# ---------------------------------------------------------------------------
PAGE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="index, follow, max-image-preview:large">
    <meta name="theme-color" content="#0CC0DF">
    <title>Our Work | OCS LLC Window Cleaning</title>
    <meta name="description" content="Real window-cleaning clips from across the Flathead Valley — Kalispell, Whitefish, Columbia Falls, and Bigfork. Auto-synced from our Instagram.">
    <link rel="canonical" href="https://ocsllc.services/our-work/">
    <meta property="og:type" content="website">
    <meta property="og:title" content="Our Work | OCS LLC Window Cleaning">
    <meta property="og:description" content="Real clips from real jobs across the Flathead Valley.">
    <meta property="og:url" content="https://ocsllc.services/our-work/">
    <meta property="og:image" content="https://ocsllc.services/assets/og.png">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Our Work | OCS LLC">
    <script type="application/ld+json">
__VIDEO_LD__
    </script>
    <script type="application/ld+json">
__BREADCRUMBS_LD__
    </script>
    <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='16' fill='%230CC0DF'/%3E%3Ctext x='50' y='62' font-family='Arial,sans-serif' font-size='44' font-weight='700' text-anchor='middle' fill='white'%3EO%3C/text%3E%3C/svg%3E">
    <link rel="manifest" href="/manifest.webmanifest">
    <link rel="apple-touch-icon" sizes="180x180" href="/assets/apple-touch-icon.png">
    <link rel="preconnect" href="https://cdn.tailwindcss.com" crossorigin>
    <script src="https://cdn.tailwindcss.com" defer></script>
    <style>
        body { font-family: 'Garet', sans-serif; margin: 0; padding: 0; min-height: 100vh; display: flex; flex-direction: column; }
        .bg-custom-cyan { background-color: #0CC0DF; }
        .container { width: 90%; max-width: 1280px; margin: 0 auto; padding: 0 1rem; }
        section { padding: clamp(2rem, 5vw, 4rem) 0; }
        .nav-container { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; width: 90%; max-width: 1200px; margin: 0 auto; padding: 1rem; gap: 0.5rem; }
        .contact-info { display: flex; flex-direction: column; align-items: flex-end; gap: 0.25rem; font-size: 0.95rem; }
        .contact-info a { color: #fff; text-decoration: none; }
        .hero-mini { background: linear-gradient(135deg, #0CC0DF 0%, #0aa3bd 100%); color: white; padding: clamp(2rem, 6vw, 4rem) 1rem; text-align: center; }
        .hero-mini h1 { font-size: clamp(1.75rem, 5vw, 3rem); font-weight: 800; margin-bottom: 0.75rem; }
        .hero-mini p { font-size: clamp(1rem, 2.5vw, 1.25rem); max-width: 760px; margin: 0 auto 1.25rem; }
        .breadcrumbs { font-size: 0.875rem; color: #6b7280; margin-bottom: 1rem; }
        .breadcrumbs a { color: #0CC0DF; text-decoration: none; }
        .vid-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem; margin-top: 1rem; }
        .vid-card { position: relative; display: block; aspect-ratio: 9/16; overflow: hidden; border: 0; padding: 0; border-radius: 12px; background: #0b1220; cursor: pointer; box-shadow: 0 4px 14px rgba(15,42,62,.08); transition: transform .25s, box-shadow .25s; }
        .vid-card video { width: 100%; height: 100%; object-fit: cover; display: block; }
        .vid-card:hover { transform: translateY(-3px); box-shadow: 0 14px 32px rgba(0,0,0,.18); }
        .vid-card .vid-cap { position: absolute; left: 0; right: 0; bottom: 0; padding: .85rem .7rem .6rem; color: #fff; font-size: .85rem; font-weight: 600; text-align: left; line-height: 1.25; background: linear-gradient(transparent, rgba(0,0,0,.7)); }
        .vid-card .vid-play { position: absolute; top: 10px; right: 10px; width: 30px; height: 30px; border-radius: 50%; background: rgba(0,0,0,.45); color: #fff; display: grid; place-items: center; font-size: .8rem; }
        .lightbox { position: fixed; inset: 0; background: rgba(0,0,0,0.93); display: none; z-index: 100; align-items: center; justify-content: center; }
        .lightbox.open { display: flex; }
        .lightbox video { max-width: 92vw; max-height: 88vh; border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.5); background:#000; }
        .lightbox .lb-close { position: absolute; top: 1.5rem; right: 1.5rem; color: white; font-size: 2rem; cursor: pointer; background: rgba(255,255,255,0.12); border-radius: 50%; width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; }
        .lightbox .lb-prev, .lightbox .lb-next { position: absolute; top: 50%; transform: translateY(-50%); color: white; font-size: 3rem; cursor: pointer; padding: 1rem; user-select: none; }
        .lightbox .lb-prev { left: 1rem; } .lightbox .lb-next { right: 1rem; }
        .cta-box { background: #0CC0DF; color: white; border-radius: 12px; padding: clamp(1.5rem, 4vw, 2.5rem); text-align: center; margin: 2rem 0; }
        .cta-box .btn-white { background: white; color: black; padding: 0.75rem 1.5rem; border-radius: 8px; font-weight: 600; text-decoration: none; display: inline-block; }
        .cta-box .tel-link { color: white; text-decoration: underline; display: block; margin-top: 0.75rem; font-weight: 600; }
        .mobile-call-bar { display: none; }
        @media (max-width: 720px) {
            .mobile-call-bar { display: flex; position: fixed; bottom: 0; left: 0; right: 0; background: #0CC0DF; color: white; padding: 0.85rem 1rem; z-index: 50; box-shadow: 0 -4px 12px rgba(0,0,0,0.18); justify-content: center; align-items: center; gap: 1rem; font-weight: 700; text-decoration: none; font-size: 1rem; }
            body { padding-bottom: 60px; }
            .nav-container { flex-direction: column; align-items: flex-start; gap: 0.5rem; }
        }
        @media (prefers-reduced-motion: reduce) { .vid-card video { } }
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
        <h1>Our work</h1>
        <p>Real clips from real jobs across the Flathead Valley — fresh from our Instagram.</p>
    </section>

    <section class="bg-white">
        <div class="container">
            <p class="breadcrumbs"><a href="/">Home</a> &rsaquo; Our Work</p>
            <p class="mb-6 text-gray-700">__N__ clips · tap any to play with sound</p>

            <div class="vid-grid">
__CARDS__
            </div>

            <div class="cta-box mt-12">
                <h2 class="text-2xl font-bold mb-2">Want your windows to look like this?</h2>
                <p>Get a fast, fair, no-pressure quote.</p>
                <a href="/#quote" class="btn-white">Get a Free Estimate</a>
                <a href="tel:+14066072151" class="tel-link">Or call (406) 607-2151</a>
            </div>
        </div>
    </section>

    <footer class="bg-custom-cyan text-white py-8 mt-auto">
        <div class="container text-center">
            <p>&copy; 2026 OCS LLC / Licensed and Insured</p>
            <p class="mt-2">Contact: <a class="underline" href="mailto:barrett@ocsllc.services">barrett@ocsllc.services</a> | <a class="underline" href="tel:+14066072151">(406) 607-2151</a></p>
        </div>
    </footer>

    <a href="tel:+14066072151" class="mobile-call-bar">📞 Call (406) 607-2151</a>

    <div id="lightbox" class="lightbox" aria-hidden="true">
        <span class="lb-close">×</span>
        <span class="lb-prev">‹</span>
        <video src="" playsinline controls></video>
        <span class="lb-next">›</span>
    </div>

    <script>
        var cards = Array.prototype.slice.call(document.querySelectorAll('.vid-card'));
        var srcs = cards.map(function(c){ return c.getAttribute('data-clip'); });
        var lb = document.getElementById('lightbox');
        var lbVid = lb.querySelector('video');
        var cur = 0;
        var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

        function open(i){ cur = (i + srcs.length) % srcs.length; lbVid.src = srcs[cur]; lb.classList.add('open');
            var p = lbVid.play(); if (p && p.catch) p.catch(function(){}); }
        function close(){ lb.classList.remove('open'); lbVid.pause(); lbVid.removeAttribute('src'); lbVid.load(); }
        cards.forEach(function(c, i){ c.addEventListener('click', function(){ open(i); }); });
        lb.querySelector('.lb-close').addEventListener('click', close);
        lb.querySelector('.lb-prev').addEventListener('click', function(e){ e.stopPropagation(); open(cur-1); });
        lb.querySelector('.lb-next').addEventListener('click', function(e){ e.stopPropagation(); open(cur+1); });
        lb.addEventListener('click', function(e){ if (e.target === lb) close(); });
        document.addEventListener('keydown', function(e){
            if (!lb.classList.contains('open')) return;
            if (e.key === 'Escape') close();
            if (e.key === 'ArrowLeft') open(cur-1);
            if (e.key === 'ArrowRight') open(cur+1);
        });

        // Lazy muted-autoplay the grid cards while in view (skipped under reduced-motion).
        if (!reduce && 'IntersectionObserver' in window) {
            var io = new IntersectionObserver(function(es){ es.forEach(function(e){
                var v = e.target.querySelector('video');
                if (e.isIntersecting) { var p = v.play(); if (p && p.catch) p.catch(function(){}); }
                else { v.pause(); }
            }); }, { threshold: 0.4 });
            cards.forEach(function(c){ io.observe(c); });
        }
    </script>
</body>
</html>
'''


def regenerate_page(items):
    cards = "\n".join(
        '                <button class="vid-card" data-clip="{clip}" aria-label="Play: {capattr}">'
        '<video src="{clip}" poster="{poster}" muted loop playsinline preload="none"></video>'
        '<span class="vid-play">&#9658;</span><span class="vid-cap">{cap}</span></button>'.format(
            clip=i["clip"], poster=i["poster"],
            cap=_esc(i.get("caption", "")), capattr=_escattr(i.get("caption", "")))
        for i in items
    )
    video_ld = json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "VideoObject",
                "name": i.get("caption") or "OCS LLC window cleaning",
                "description": (i.get("caption") or "Window cleaning in the Flathead Valley by OCS LLC."),
                "thumbnailUrl": "https://ocsllc.services" + i["poster"],
                "contentUrl": "https://ocsllc.services" + i["clip"],
                "uploadDate": (i.get("ts") or "2026-01-01"),
                "publisher": {"@type": "Organization", "name": "OCS LLC",
                              "url": "https://ocsllc.services/"}
            } for i in items
        ]
    }, indent=2)
    breadcrumbs_ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://ocsllc.services/"},
            {"@type": "ListItem", "position": 2, "name": "Our Work", "item": "https://ocsllc.services/our-work/"}
        ]
    }, indent=2)

    html = (PAGE.replace("__CARDS__", cards)
                .replace("__N__", str(len(items)))
                .replace("__VIDEO_LD__", video_ld)
                .replace("__BREADCRUMBS_LD__", breadcrumbs_ld))
    out = ROOT / "our-work" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    print(f"Regenerated {out} with {len(items)} clip(s).")


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

def _escattr(s):
    return _esc(s).replace('"', "&quot;")


if __name__ == "__main__":
    main()
