#!/usr/bin/env python3
"""
add_media.py — publish your own photos/videos to the Our Work page (fallback for Instagram).

Drop files in  our-work-media/  then run:  python3 scripts/add_media.py
 - videos (.mp4 .mov .m4v)  -> web-compressed mp4 + poster, tap-to-play with sound
 - photos (.jpg .jpeg .png .heic) -> optimized jpg, opens full size on click
Captions (optional): our-work-media/captions.txt   ->   filename | caption

Rebuilds the Our Work gallery = YOUR media (first) + the Instagram clips already there.
Removing a file from our-work-media/ and re-running takes it off the site. Idempotent.
"""
import os, re, json, html, subprocess, pathlib

ROOT  = pathlib.Path(__file__).resolve().parent.parent
DROP  = ROOT / "our-work-media"
OUT   = ROOT / "assets" / "our-work" / "manual"
PAGE  = ROOT / "our-work" / "index.html"
VIDEXT = {".mp4", ".mov", ".m4v", ".webm", ".avi"}
IMGEXT = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"}

def slugify(name):
    s = re.sub(r"\.[^.]+$", "", name).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "item"

def captions():
    m = {}
    f = DROP / "captions.txt"
    if f.exists():
        for line in f.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "|" in line:
                fn, cap = line.split("|", 1)
                m[fn.strip()] = cap.strip()
    return m

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def process():
    OUT.mkdir(parents=True, exist_ok=True)
    caps = captions()
    items = []
    files = sorted(f for f in os.listdir(DROP)
                   if pathlib.Path(f).suffix.lower() in (VIDEXT | IMGEXT))
    for fn in files:
        src = DROP / fn
        slug = slugify(fn)
        ext = pathlib.Path(fn).suffix.lower()
        cap = caps.get(fn, "")
        if ext in VIDEXT:
            mp4 = OUT / f"{slug}.mp4"; jpg = OUT / f"{slug}.jpg"
            r = run(["ffmpeg","-y","-i",str(src),
                     "-vf","scale='min(1080,iw)':-2:flags=lanczos",
                     "-c:v","libx264","-crf","26","-preset","medium","-movflags","+faststart",
                     "-c:a","aac","-b:a","128k",str(mp4)])
            if r.returncode != 0:
                print(f"  ! video failed {fn}: {r.stderr[-200:]}"); continue
            run(["ffmpeg","-y","-i",str(mp4),"-frames:v","1","-q:v","3",str(jpg)])
            items.append({"type":"video","src":f"/assets/our-work/manual/{slug}.mp4",
                          "poster":f"/assets/our-work/manual/{slug}.jpg","caption":cap})
            print(f"  + video  {fn} -> {slug}.mp4")
        else:
            jpg = OUT / f"{slug}.jpg"
            r = run(["sips","-Z","1280","-s","format","jpeg",str(src),"--out",str(jpg)])
            if r.returncode != 0:
                # fallback to ffmpeg for the resize/convert if sips is unavailable
                r2 = run(["ffmpeg","-y","-i",str(src),"-vf","scale='min(1280,iw)':-2",str(jpg)])
                if r2.returncode != 0:
                    print(f"  ! photo failed {fn}"); continue
            items.append({"type":"image","src":f"/assets/our-work/manual/{slug}.jpg",
                          "poster":f"/assets/our-work/manual/{slug}.jpg","caption":cap})
            print(f"  + photo  {fn} -> {slug}.jpg")
    (OUT / "manifest.json").write_text(json.dumps(items, indent=2))
    return items

def card(it):
    cap = html.escape(it["caption"]) if it["caption"] else ""
    capspan = f'<span class="vid-cap">{cap}</span>' if cap else ""
    if it["type"] == "video":
        return (f'<button class="vid-card" data-clip="{it["src"]}" aria-label="Play: {cap or "OCS LLC"}">'
                f'<video src="{it["src"]}" poster="{it["poster"]}" muted loop playsinline preload="none"></video>'
                f'<span class="vid-play">&#9658;</span>{capspan}</button>')
    return (f'<a class="vid-card" href="{it["src"]}" target="_blank" rel="noopener" aria-label="{cap or "Photo"}">'
            f'<img src="{it["src"]}" alt="{cap}" loading="lazy">{capspan}</a>')

def rebuild_gallery(manual_items):
    h = PAGE.read_text()
    m = re.search(r"<!-- GALLERY:start -->(.*?)<!-- GALLERY:end -->", h, re.S)
    if not m:
        print("  ! GALLERY markers missing on the page"); return
    # keep the Instagram cards already on the page (those pointing at /assets/videos/clips/)
    ig_cards = re.findall(r'<button class="vid-card"[^>]*data-clip="/assets/videos/clips/[^>]*>.*?</button>',
                          m.group(1), re.S)
    manual_cards = [card(it) for it in manual_items]
    inner = "\n".join(manual_cards + ig_cards)
    h = h[:m.start(1)] + "\n" + inner + "\n" + h[m.end(1):]
    total = len(manual_cards) + len(ig_cards)
    h = re.sub(r'<p class="mb-6 text-gray-700">[^<]*</p>',
               f'<p class="mb-6 text-gray-700">{total} from real jobs across the Flathead Valley · tap any to view</p>',
               h, count=1)
    PAGE.write_text(h)
    print(f"  gallery rebuilt: {len(manual_cards)} of yours + {len(ig_cards)} from Instagram = {total}")

def main():
    if not DROP.exists():
        print("Create our-work-media/ and drop files in it first."); return
    print("Processing our-work-media/ …")
    items = process()
    rebuild_gallery(items)
    print("Done.")

if __name__ == "__main__":
    main()
