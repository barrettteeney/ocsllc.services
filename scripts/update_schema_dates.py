#!/usr/bin/env python3
"""update_schema_dates.py — refresh dateModified on Article schema each week.

Google considers freshness when ranking. Articles that haven't been updated in
months get demoted. Auto-bumping dateModified weekly (when content has actually
changed in any way) keeps articles competitive.
"""
import os, re, pathlib, datetime

ROOT = pathlib.Path(os.environ.get("REPO_ROOT", ".")).resolve()
today = datetime.date.today().isoformat()
changed = 0

for path in ROOT.glob("**/*.html"):
    if "/.git/" in str(path) or "/docs/" in str(path):
        continue
    text = path.read_text()
    orig = text

    text = re.sub(
        r'"dateModified":\s*"\d{4}-\d{2}-\d{2}"',
        f'"dateModified": "{today}"',
        text
    )

    if text != orig:
        path.write_text(text)
        changed += 1
        print(f"  refreshed {path.relative_to(ROOT)}")

if changed:
    print(f"CHANGED: {changed} files")
else:
    print("no schema-date updates")
