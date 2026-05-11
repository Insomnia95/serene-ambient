#!/usr/bin/env python3
"""
Calm Veritas — Daily Automation Script
Searches Pexels for 1-4 new ambient videos + Freesound for matching music,
updates the site, and queues everything for YouTube upload.

Usage:
    python daily_update.py

Requirements:
    pip install requests

Config:
    PEXELS_API_KEY    — Pexels API key
    FREESOUND_TOKEN   — Freesound API token (free at freesound.org)
    REPO_DIR          — path to repo root (auto-detected from script location)
"""

import json
import math
import os
import random
import re
import subprocess
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# ─── CONFIG ──────────────────────────────────────────────────────────────────

PEXELS_API_KEY  = "tVypT2VSxvRo8r5urjNUMDBVFVBhJFYeT0Q9E60LoKIzLOzW3a7FLZFA"
FREESOUND_TOKEN = os.environ.get("FREESOUND_TOKEN", "")  # set after getting key

REPO_DIR   = Path(os.environ.get("CALM_VERITAS_REPO", Path(__file__).parent.parent))
DB_PATH    = REPO_DIR / "data" / "videos_db.json"
QUEUE_PATH = REPO_DIR / "data" / "queue.json"
INDEX_PATH = REPO_DIR / "index.html"
MUSIC_DIR  = REPO_DIR / "music"

MIN_NEW = 1
MAX_NEW = 4

PEXELS_BASE   = "https://api.pexels.com/videos"
FREESOUND_BASE = "https://freesound.org/apiv2"

# Freesound search queries per category
MUSIC_QUERIES = {
    "ocean":      "ocean waves ambient",
    "fire":       "fireplace crackling ambient",
    "rain":       "rain falling ambient",
    "forest":     "forest nature birds ambient",
    "winter":     "wind snow winter ambient",
    "stars":      "space cosmos ambient drone",
    "abstract":   "ambient drone meditation",
    "sunset":     "golden hour ambient peaceful",
    "waterfall":  "waterfall stream nature",
    "desert":     "desert wind sand ambient",
    "city":       "city night rain ambient",
    "underwater": "underwater bubbles ocean ambient",
    "aurora":     "northern lights ambient drone",
}

CATEGORY_EMOJIS = {
    "ocean": "🌊", "fire": "🔥", "rain": "🌧️", "forest": "🌿",
    "winter": "❄️", "stars": "✨", "abstract": "🎨", "sunset": "🌅",
    "waterfall": "💧", "desert": "🏜️", "city": "🌃",
    "underwater": "🐠", "aurora": "🌌",
}

# ─── PEXELS ──────────────────────────────────────────────────────────────────

def pexels_get(url, params=None):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": PEXELS_API_KEY})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def best_video_file(video_files):
    uhd = [f for f in video_files if f.get("width", 0) >= 3840]
    hd  = [f for f in video_files if 1900 <= f.get("width", 0) <= 1921]
    if uhd:
        return max(uhd, key=lambda f: f.get("width", 0) * f.get("height", 0))
    if hd:
        return max(hd, key=lambda f: f.get("width", 0) * f.get("height", 0))
    return max(video_files, key=lambda f: f.get("width", 0) * f.get("height", 0))

def hd_src(src4k):
    s = re.sub(r'uhd_\d+_\d+_(\d+fps)', r'hd_1920_1080_\1', src4k)
    s = re.sub(r'hd_3840_2160_(\d+fps)', r'hd_1920_1080_\1', s)
    s = re.sub(r'hd_4096_\d+_(\d+fps)',  r'hd_1920_1080_\1', s)
    return s

def search_pexels(query, per_page=15):
    page = random.randint(1, 3)
    try:
        data = pexels_get(f"{PEXELS_BASE}/search", {
            "query": query, "per_page": per_page, "page": page,
            "orientation": "landscape", "size": "large"
        })
        return data.get("videos", [])
    except Exception as e:
        print(f"  [warn] Pexels search '{query}': {e}")
        return []

def fetch_video_detail(video_id):
    try:
        return pexels_get(f"{PEXELS_BASE}/videos/{video_id}")
    except:
        return None

def best_thumb(video):
    pics = video.get("video_pictures", [])
    if pics:
        return pics[0].get("picture", "")
    return video.get("image", "")

# ─── FREESOUND MUSIC ─────────────────────────────────────────────────────────

def freesound_search(query, duration_min=60):
    """Search Freesound for CC0 ambient tracks. Returns list of sound objects."""
    if not FREESOUND_TOKEN:
        print("  [warn] No FREESOUND_TOKEN set — skipping music search")
        return []
    try:
        params = urllib.parse.urlencode({
            "query": query,
            "filter": f'license:"Creative Commons 0" duration:[{duration_min} TO *]',
            "fields": "id,name,duration,previews,license,username",
            "page_size": 10,
            "token": FREESOUND_TOKEN,
        })
        req = urllib.request.Request(f"{FREESOUND_BASE}/search/text/?{params}")
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        return data.get("results", [])
    except Exception as e:
        print(f"  [warn] Freesound search '{query}': {e}")
        return []

def download_music(sound, dest_path):
    """Download HQ preview MP3 from Freesound."""
    previews = sound.get("previews", {})
    url = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3")
    if not url:
        return False
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as r, open(dest_path, "wb") as f:
            while True:
                block = r.read(65536)
                if not block:
                    break
                f.write(block)
        return True
    except Exception as e:
        print(f"  [warn] Music download failed: {e}")
        return False

def ensure_category_music(cat_id, cat_name):
    """
    Make sure category has a music file in music/ folder.
    If not, search Freesound and download one.
    Returns path string relative to repo root (e.g. 'music/ocean.mp3').
    """
    MUSIC_DIR.mkdir(exist_ok=True)
    music_path = MUSIC_DIR / f"{cat_id}.mp3"

    if music_path.exists():
        print(f"  ♪ Music already exists: music/{cat_id}.mp3")
        return f"music/{cat_id}.mp3"

    query = MUSIC_QUERIES.get(cat_id, f"{cat_name} ambient")
    print(f"  ♪ Searching music for [{cat_id}]: '{query}'")
    results = freesound_search(query, duration_min=60)

    if not results:
        print(f"  [warn] No music found for {cat_id}")
        return ""

    # Pick a random result from top 5
    sound = random.choice(results[:5])
    print(f"  ♪ Downloading: '{sound['name']}' ({sound['duration']:.0f}s) by {sound['username']}")

    if download_music(sound, music_path):
        print(f"  ✓ Music saved: music/{cat_id}.mp3")
        return f"music/{cat_id}.mp3"
    return ""

# ─── SITE REGENERATION ───────────────────────────────────────────────────────

def generate_index(db):
    html = INDEX_PATH.read_text(encoding="utf-8")
    cats_js_lines = ["const CATEGORIES = ["]

    for cat in db["categories"]:
        cid    = cat["id"]
        cname  = cat["name"]
        cemoji = cat.get("emoji", CATEGORY_EMOJIS.get(cid, "▶️"))
        cmusic = cat.get("music", "")
        videos = cat.get("videos", [])

        videos_js = []
        for v in videos:
            vsrc  = v["src"].replace("'", "\\'")
            vhd   = v.get("src_hd", hd_src(v["src"])).replace("'", "\\'")
            vname = v["name"].replace("'", "\\'")
            vthumb= v.get("thumb", "").replace("'", "\\'")
            videos_js.append(
                f"    {{ id:{v['id']!r}, name:{vname!r}, "
                f"thumb:{vthumb!r}, src:{vsrc!r}, src_hd:{vhd!r} }}"
            )

        cats_js_lines.append("  {")
        cats_js_lines.append(f"    id: {cid!r}, name: {cname!r}, emoji: {cemoji!r},")
        cats_js_lines.append(f"    music: {cmusic!r},")
        cats_js_lines.append("    videos: [")
        cats_js_lines.append(",\n".join(videos_js))
        cats_js_lines.append("    ]")
        cats_js_lines.append("  },")

    cats_js_lines.append("];")
    new_cats_js = "\n".join(cats_js_lines)

    pattern = r'(// === CATEGORIES START ===\n).*?(// === CATEGORIES END ===)'
    new_html, count = re.subn(
        pattern,
        r'\g<1>' + new_cats_js + '\n// === CATEGORIES END ===',
        html,
        flags=re.DOTALL
    )

    if count == 0:
        print("  [warn] CATEGORIES markers not found in index.html — skipping")
        return False

    INDEX_PATH.write_text(new_html, encoding="utf-8")
    print("  ✓ index.html regenerated")
    return True

# ─── QUEUE ───────────────────────────────────────────────────────────────────

def load_queue():
    if QUEUE_PATH.exists():
        return json.loads(QUEUE_PATH.read_text())
    return {"version": 1, "items": []}

def save_queue(q):
    QUEUE_PATH.write_text(json.dumps(q, indent=2, ensure_ascii=False))

def make_queue_item(video_entry, category):
    return {
        "id":            video_entry["id"],
        "name":          video_entry["name"],
        "category_id":   category["id"],
        "category_name": category["name"],
        "src_hd":        video_entry.get("src_hd", ""),
        "src_4k":        video_entry.get("src", ""),
        "music":         category.get("music", ""),
        "status":        "pending",
        "queued_at":     datetime.now(timezone.utc).isoformat(),
    }

# ─── GIT ─────────────────────────────────────────────────────────────────────

def git_push(message):
    try:
        subprocess.run(["git", "-C", str(REPO_DIR), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(REPO_DIR), "commit", "-m", message], check=True)
        subprocess.run(["git", "-C", str(REPO_DIR), "push"], check=True)
        print(f"  ✓ Pushed: {message}")
    except subprocess.CalledProcessError as e:
        print(f"  [warn] git failed: {e}")

# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"\n=== Calm Veritas Daily Update — {today} ===\n")

    db = json.loads(DB_PATH.read_text())
    known_ids = set(str(x) for x in db.get("known_ids", []))
    queue = load_queue()

    target_count = random.randint(MIN_NEW, MAX_NEW)
    print(f"Target: {target_count} new video(s)\n")

    added = []
    active_cats    = db.get("categories", [])
    candidate_cats = db.get("candidate_categories", [])
    pool = active_cats * 2 + candidate_cats
    random.shuffle(pool)
    tried = set()

    for cat in pool:
        if len(added) >= target_count:
            break
        cid = cat["id"]
        if cid in tried:
            continue
        tried.add(cid)

        # ── Search video ──────────────────────────────────────────────
        queries = cat.get("queries", [cat.get("name", cid)])
        query   = random.choice(queries)
        print(f"[{cid}] Video search: '{query}'")
        videos = search_pexels(query)
        random.shuffle(videos)

        found_video = None
        for v in videos:
            vid_id = str(v.get("id", ""))
            if not vid_id or vid_id in known_ids:
                continue
            files = v.get("video_files", [])
            if not files:
                continue
            best = best_video_file(files)
            w = best.get("width", 0)
            if w < 1280:
                continue

            detail = fetch_video_detail(vid_id)
            thumb  = best_thumb(detail or v)
            src4k  = best.get("link", "")
            srchd  = hd_src(src4k)
            tags   = v.get("tags", [])
            vname  = " ".join(t.capitalize() for t in tags[:3]) if tags else query.title()

            found_video = {
                "id": vid_id, "name": vname,
                "quality": "4K" if w >= 3840 else "HD",
                "thumb": thumb, "src": src4k, "src_hd": srchd,
            }
            known_ids.add(vid_id)
            print(f"  ✓ Video: '{vname}' (id={vid_id}, {w}px)")
            time.sleep(0.3)
            break

        if not found_video:
            print(f"  [skip] No new video found for [{cid}]")
            continue

        # ── Search music (parallel step) ──────────────────────────────
        music_path = ensure_category_music(cid, cat.get("name", cid))

        # Update category music path in DB if we found one
        if music_path:
            for c in db["categories"]:
                if c["id"] == cid and not c.get("music"):
                    c["music"] = music_path
            for c in db.get("candidate_categories", []):
                if c["id"] == cid and not c.get("music"):
                    c["music"] = music_path
            cat["music"] = music_path

        # ── Promote candidate category if enough videos ───────────────
        cat_ids = [c["id"] for c in db["categories"]]
        if cid not in cat_ids:
            existing_new = [a for a in added if a.get("_cat_id") == cid]
            if len(existing_new) + 1 >= 3:
                new_cat = {
                    "id": cid, "name": cat["name"],
                    "emoji": cat.get("emoji", CATEGORY_EMOJIS.get(cid, "▶️")),
                    "music": music_path,
                    "queries": cat.get("queries", []),
                    "videos": [],
                }
                db["categories"].append(new_cat)
                db["candidate_categories"] = [
                    c for c in db.get("candidate_categories", []) if c["id"] != cid
                ]
                print(f"  🎉 New category promoted: {cat['name']}")

        # Add video to category
        for c in db["categories"]:
            if c["id"] == cid:
                c["videos"].append(found_video)
                break

        found_video["_cat_id"] = cid
        added.append(found_video)

    if not added:
        print("No new videos found today.")
        return

    # Save DB
    db["known_ids"] = sorted(known_ids)
    db["last_updated"] = today
    DB_PATH.write_text(json.dumps(db, indent=2, ensure_ascii=False))
    print(f"\n✓ DB updated: {len(added)} new video(s)")

    # Regenerate site
    generate_index(db)

    # Append to queue
    for entry in added:
        cid = entry.pop("_cat_id")
        cat_obj = next(
            (c for c in db["categories"] if c["id"] == cid),
            {"id": cid, "name": cid, "music": ""}
        )
        queue["items"].append(make_queue_item(entry, cat_obj))

    save_queue(queue)
    print(f"✓ Queue updated: {len(added)} item(s) ready for YouTube")

    git_push(f"[auto] Add {len(added)} video(s) — {today}")
    print("\n=== Done ===\n")

if __name__ == "__main__":
    main()
