#!/usr/bin/env python3
"""
make_release.py — автообновление RELEASE_NOTES.md
"""

import subprocess
import datetime
import os

VERSION_FILE = ".version"
RELEASE_NOTES = "RELEASE_NOTES.md"
GITHUB_REPO = "tekswirl25/sd-colab-gallery"  # поменяй, если репо другое

def get_last_commit():
    sha = subprocess.check_output(
        ["git", "log", "-1", "--pretty=%H"], text=True
    ).strip()
    short_sha = sha[:7]
    msg = subprocess.check_output(
        ["git", "log", "-1", "--pretty=%s"], text=True
    ).strip()
    return msg, sha, short_sha

def get_date():
    return datetime.date.today().strftime("%Y-%m-%d")

def bump_version():
    if not os.path.exists(VERSION_FILE):
        version = "0.1.0"
    else:
        with open(VERSION_FILE) as f:
            version = f.read().strip()
    major, minor, patch = map(int, version.lstrip("v").split("."))
    patch += 1
    new_version = f"v{major}.{minor}.{patch}"
    with open(VERSION_FILE, "w") as f:
        f.write(new_version)
    return new_version

def append_release_notes(version, date, msg, sha, short_sha):
    if not os.path.exists(RELEASE_NOTES):
        with open(RELEASE_NOTES, "w") as f:
            f.write("# Release Notes\n\n")

    url = f"https://github.com/{GITHUB_REPO}/commit/{sha}"
    entry = f"* {msg} ([{short_sha}]({url}))\n"

    if msg.startswith("add:"):
        section = "### ✨ Added"
    elif msg.startswith("change:"):
        section = "### 🔄 Changed"
    elif msg.startswith("fix:"):
        section = "### 🛠 Fixed"
    else:
        section = None

    with open(RELEASE_NOTES, "r") as f:
        content = f.read()

    header = f"## {version} ({date})"
    if header in content:
        # дописываем в существующую секцию
        parts = content.split(header, 1)
        before, after = parts[0], parts[1]
        if section and section in after:
            after = after.replace(section, section + "\n" + entry, 1)
        else:
            after = f"\n{section or ''}\n\n{entry}\n" + after
        new_content = before + header + after
    else:
        # новая версия
        sec_block = f"\n{section or ''}\n\n{entry}" if section else f"\n{entry}"
        new_content = content + f"\n## {version} ({date})\n{sec_block}\n"

    with open(RELEASE_NOTES, "w") as f:
        f.write(new_content)

if __name__ == "__main__":
    msg, sha, short_sha = get_last_commit()
    date = get_date()
    version = bump_version()
    append_release_notes(version, date, msg, sha, short_sha)
