#!/usr/bin/env python3
"""backup_snapshot.py — create a tagged annotated git tag of the current main branch.
Used by the weekly backup workflow. Tags are named backup-YYYY-MM-DD.
"""
import subprocess, datetime, os

today = datetime.date.today().isoformat()
tag = f"backup-{today}"
msg = f"Automated weekly backup snapshot — {today}"

# Skip if today's tag already exists
existing = subprocess.run(["git", "tag", "-l", tag], capture_output=True, text=True).stdout.strip()
if existing:
    print(f"  tag {tag} already exists — skipping")
    raise SystemExit(0)

# Create the tag
subprocess.run(["git", "tag", "-a", tag, "-m", msg], check=True)
subprocess.run(["git", "push", "origin", tag], check=True)
print(f"  created backup tag {tag}")
