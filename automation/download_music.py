#!/usr/bin/env python3
"""
Calm Veritas — One-time music downloader.
Downloads one CC0 ambient track per category from Freesound.
Run once on the server after setting FREESOUND_TOKEN.

Usage:
    export FREESOUND_TOKEN="your_token"
    python3 automation/download_music.py
"""

import json
import os
import random
import time
import urllib.request
import urllib.parse
from pathlib import Path

FREESOUND_TOKEN = os.environ.get("FREESOUND_TOKEN", "")
REPO_DIR  = Path(__file__).parent.parent
DB_PATH   = REPO_DIR / "data" / "videos_db.json"
MUSIC_DIR = REPO_DIR / "music"

FREESOUND_BASE = "https://freesound.org/apiv2"

MUSIC_QUERIES = {
    "ocean":      "ocean waves relaxing ambient",
    "fire":       "fireplace crackling cozy",
    "rain":       "rain falling gentle ambient",
    "forest":     "forest birds nature ambient",
    "winter":     "wind snow blizzard ambient",
    "stars":      "space cosmos drone ambient",
    "abstract":   "ambient drone meditation pad",
    "sunset":     "peaceful ambient sunset drone",
    "waterfall":  "waterfall stream river nature",
    "desert":     "desert wind sand ambient",
    "city":       "city night rain ambient",
    "underwater": "underwater ocean bubbles ambient",
    "aurora":     "northern lights drone ambient",
}

def freesound_search(query):
    if not FREESOUND_TOKEN:
        print("ERROR: FREESOUND_TOKEN not set. Run: export FREESOUND_TOKEN='your_token'")
        return []
    params = urllib.parse.urlencode({
        "query": query,
        "filter": 'license:"Creative Commons 0" duration:[60 TO *]',
        "fields": "id,name,duration,previews,license,username",
        "page_size": 15,
        "token": FREESOUND_TOKEN,
    })
    try:
        req = urllib.request.Request(f"{FREESOUND_BASE}/search/text/?{params}")
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode()).get("results", [])
    except Exception as e:
        print(f"  [error] Freesound search failed: {e}")
        return []

def download_mp3(url, dest):
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
            while True:
                block = r.read(65536)
                if not block:
                    break
                f.write(block)
        return True
    except Exception as e:
        print(f"  [error] Download failed: {e}")
        return False

def main():
    if not FREESOUND_TOKEN:
        print("ERROR: Set FREESOUND_TOKEN first:\n  export FREESOUND_TOKEN='your_token'")
        return

    MUSIC_DIR.mkdir(exist_ok=True)
    db = json.loads(DB_PATH.read_text())

    all_cats = db.get("categories", []) + db.get("candidate_categories", [])
    print(f"\n=== Calm Veritas Music Downloader ===")
    print(f"Categories to process: {len(all_cats)}\n")

    updated = 0

    for cat in all_cats:
        cid   = cat["id"]
        cname = cat.get("name", cid)
        dest  = MUSIC_DIR / f"{cid}.mp3"
        rel_path = f"music/{cid}.mp3"

        if dest.exists():
            size_kb = dest.stat().st_size // 1024
            print(f"[{cid}] Already exists ({size_kb} KB) — skipping")
            if not cat.get("music"):
                cat["music"] = rel_path
                updated += 1
            continue

        query = MUSIC_QUERIES.get(cid, f"{cname} ambient")
        print(f"[{cid}] Searching: '{query}'")
        results = freesound_search(query)

        if not results:
            print(f"  [warn] No results — skipping {cid}")
            time.sleep(1)
            continue

        # Pick best result: prefer longer tracks
        results_sorted = sorted(results, key=lambda x: x.get("duration", 0), reverse=True)
        sound = results_sorted[0]
        dur   = sound.get("duration", 0)
        name  = sound.get("name", "unknown")
        user  = sound.get("username", "unknown")

        print(f"  Found: '{name}' by {user} ({dur:.0f}s)")

        previews = sound.get("previews", {})
        url = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3")

        if not url:
            print(f"  [warn] No preview URL — skipping")
            time.sleep(1)
            continue

        print(f"  Downloading...")
        if download_mp3(url, dest):
            size_kb = dest.stat().st_size // 1024
            print(f"  ✓ Saved music/{cid}.mp3 ({size_kb} KB)")
            cat["music"] = rel_path
            updated += 1
        else:
            print(f"  [warn] Failed to download for {cid}")

        time.sleep(1)  # rate limiting

    # Save updated DB
    DB_PATH.write_text(json.dumps(db, indent=2, ensure_ascii=False))
    print(f"\n✓ Done. {updated} categories updated in videos_db.json")
    print(f"Music files saved to: {MUSIC_DIR}")
    print(f"\nNext step — push to GitHub:")
    print(f"  git add -A && git commit -m 'Add ambient music tracks' && git push")

if __name__ == "__main__":
    main()
