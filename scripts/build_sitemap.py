#!/usr/bin/env python3
"""
build_sitemap.py — auto-regenerate sitemap.xml from index.html files in the repo.

Walks the repo, finds every index.html, derives the URL, dates with today's date.
Skips drafts, hidden dirs, .github/, docs/, and assets/.
"""
import os, sys, datetime, pathlib

BASE = "https://ocsllc.services"
ROOT = pathlib.Path(os.environ.get("REPO_ROOT", ".")).resolve()

SKIP_DIRS = {".git", ".github", "docs", "assets", "scripts", "node_modules"}

def url_for(path: pathlib.Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if rel == "index.html":
        return f"{BASE}/"
    if rel.endswith("/index.html"):
        return f"{BASE}/{rel[:-len('index.html')]}"
    if rel == "404.html":
        return None  # 404 not in sitemap
    return f"{BASE}/{rel}"

def priority_for(url: str) -> str:
    if url == f"{BASE}/":
        return "1.0"
    # Town pages or top-level service pages: /town/ or /services/x/
    parts = [p for p in url.replace(BASE, "").split("/") if p]
    if len(parts) == 1:
        return "0.9"
    if len(parts) == 2 and parts[0] == "services":
        return "0.85"
    if len(parts) == 2:  # town × service combos
        return "0.75"
    return "0.6"

def main():
    today = datetime.date.today().isoformat()
    urls = []
    for root, dirs, files in os.walk(ROOT):
        rootp = pathlib.Path(root)
        # filter directories
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS]
        for f in files:
            if f == "index.html":
                p = rootp / f
                u = url_for(p)
                if u:
                    urls.append(u)

    urls = sorted(set(urls))
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        out.append(f'  <url>\n    <loc>{u}</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>{priority_for(u)}</priority>\n  </url>')
    out.append('</urlset>\n')
    new_xml = "\n".join(out)

    sitemap_path = ROOT / "sitemap.xml"
    old = sitemap_path.read_text() if sitemap_path.exists() else ""
    if old.strip() != new_xml.strip():
        sitemap_path.write_text(new_xml)
        print(f"  sitemap.xml updated ({len(urls)} URLs)")
        sys.exit(0)
    print(f"  sitemap.xml unchanged ({len(urls)} URLs)")

if __name__ == "__main__":
    main()
