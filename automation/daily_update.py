#!/usr/bin/env python3
"""
Calm Veritas — Daily Automation Script
Run daily to discover new ambient videos, update the site, and queue them for YouTube.

Usage:
    python daily_update.py

Requirements:
    pip install requests

Environment / config at top of file:
    PEXELS_API_KEY  — your Pexels API key
    REPO_DIR        — absolute path to the cloned serene-ambient repo
"""

import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ─── CONFIG ──────────────────────────────────────────────────────────────────

PEXELS_API_KEY = "tVypT2VSxvRo8r5urjNUMDBVFVBhJFYeT0Q9E60LoKIzLOzW3a7FLZFA"

# Absolute path to the repo root (edit if different)
REPO_DIR = Path(os.environ.get("Calm Veritas_REPO", Path(__file__).parent.parent))

DB_PATH    = REPO_DIR / "data" / "videos_db.json"
QUEUE_PATH = REPO_DIR / "data" / "queue.json"
INDEX_PATH = REPO_DIR / "index.html"

# How many new videos to add per run (random within range)
MIN_NEW = 1
MAX_NEW = 4

PEXELS_BASE = "https://api.pexels.com/videos"

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def pexels_get(url, params=None):
    import urllib.request, urllib.parse
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": PEXELS_API_KEY})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def best_video_file(video_files):
    """Return the best 4K file, then best HD, from a Pexels video_files list."""
    uhd = [f for f in video_files if f.get("width", 0) >= 3840]
    hd  = [f for f in video_files if 1900 <= f.get("width", 0) <= 1921]
    if uhd:
        return max(uhd, key=lambda f: f.get("width", 0) * f.get("height", 0))
    if hd:
        return max(hd, key=lambda f: f.get("width", 0) * f.get("height", 0))
    return max(video_files, key=lambda f: f.get("width", 0) * f.get("height", 0))

def hd_src(src4k):
    """Convert 4K Pexels URL to 1080p."""
    import re
    s = re.sub(r'uhd_\d+_\d+_(\d+fps)', r'hd_1920_1080_\1', src4k)
    s = re.sub(r'hd_3840_2160_(\d+fps)',  r'hd_1920_1080_\1', s)
    s = re.sub(r'hd_4096_\d+_(\d+fps)',   r'hd_1920_1080_\1', s)
    return s

def slug(name):
    import re
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

def search_pexels(query, per_page=15):
    """Search Pexels videos, return list of raw video objects."""
    page = random.randint(1, 3)
    try:
        data = pexels_get(f"{PEXELS_BASE}/search", {
            "query": query,
            "per_page": per_page,
            "page": page,
            "orientation": "landscape",
            "size": "large"
        })
        return data.get("videos", [])
    except Exception as e:
        print(f"  [warn] Pexels search '{query}' failed: {e}")
        return []

def fetch_video_detail(video_id):
    """Fetch a single video's details (for proper thumbnail URL)."""
    try:
        return pexels_get(f"{PEXELS_BASE}/videos/{video_id}")
    except Exception as e:
        print(f"  [warn] Could not fetch video detail {video_id}: {e}")
        return None

def best_thumb(video):
    """Get the best thumbnail URL from a Pexels video object."""
    pics = video.get("video_pictures", [])
    if pics:
        return pics[0].get("picture", "")
    return video.get("image", "")

# ─── SITE REGENERATION ───────────────────────────────────────────────────────

CATEGORY_EMOJIS = {
    "ocean":    "🌊", "fire":     "🔥", "rain":     "🌧️",
    "forest":   "🌿", "winter":   "❄️", "stars":    "✨",
    "abstract": "🎨", "sunset":   "🌅", "waterfall":"💧",
    "desert":   "🏜️", "city":     "🌃", "underwater":"🐠",
    "aurora":   "🌌",
}

def generate_index(db):
    """Regenerate index.html from videos_db.json."""
    # Read the existing index.html
    html = INDEX_PATH.read_text(encoding="utf-8")

    # We'll replace the CATEGORIES JS object entirely
    # Build the new JS categories block
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

        cats_js_lines.append(f"  {{")
        cats_js_lines.append(f"    id: {cid!r}, name: {cname!r}, emoji: {cemoji!r},")
        cats_js_lines.append(f"    music: {cmusic!r},")
        cats_js_lines.append(f"    videos: [")
        cats_js_lines.append(",\n".join(videos_js))
        cats_js_lines.append(f"    ]")
        cats_js_lines.append(f"  }},")

    cats_js_lines.append("];")
    new_cats_js = "\n".join(cats_js_lines)

    # Replace block between markers
    import re
    pattern = r'(// === CATEGORIES START ===\n).*?(// === CATEGORIES END ===)'
    replacement = r'\g<1>' + new_cats_js + '\n// === CATEGORIES END ==='
    new_html, count = re.subn(pattern, replacement, html, flags=re.DOTALL)

    if count == 0:
        print("  [warn] Could not find CATEGORIES markers in index.html — skipping regen")
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

def queue_item(video_entry, category):
    """Build a queue item dict for the server daemon."""
    return {
        "id":           video_entry["id"],
        "name":         video_entry["name"],
        "category_id":  category["id"],
        "category_name":category["name"],
        "src_hd":       video_entry.get("src_hd", ""),
        "src_4k":       video_entry.get("src", ""),
        "music":        category.get("music", ""),
        "status":       "pending",
        "queued_at":    datetime.now(timezone.utc).isoformat(),
    }

# ─── GIT ─────────────────────────────────────────────────────────────────────

def git_push(message):
    try:
        subprocess.run(["git", "-C", str(REPO_DIR), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(REPO_DIR), "commit", "-m", message], check=True)
        subprocess.run(["git", "-C", str(REPO_DIR), "push"], check=True)
        print(f"  ✓ Pushed to GitHub: {message}")
    except subprocess.CalledProcessError as e:
        print(f"  [warn] git operation failed: {e}")

# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"\n=== Calm Veritas Daily Update — {today} ===\n")

    # Load DB
    db = json.loads(DB_PATH.read_text())
    known_ids = set(str(x) for x in db.get("known_ids", []))

    # Load queue
    queue = load_queue()

    # Decide how many new videos to add
    target_count = random.randint(MIN_NEW, MAX_NEW)
    print(f"Target: {target_count} new video(s) today\n")

    added = []

    # Pool of categories to search (existing + candidates)
    active_cats  = db.get("categories", [])
    candidate_cats = db.get("candidate_categories", [])

    # Build a weighted pool: prefer active cats (2x) over candidate cats (1x)
    pool = active_cats * 2 + candidate_cats
    random.shuffle(pool)

    tried_cat_ids = set()

    for cat in pool:
        if len(added) >= target_count:
            break

        cid = cat["id"]
        if cid in tried_cat_ids:
            continue
        tried_cat_ids.add(cid)

        queries = cat.get("queries", [cat.get("name", cid)])
        query   = random.choice(queries)
        print(f"Searching category [{cid}] with query: '{query}'")

        videos = search_pexels(query)
        random.shuffle(videos)

        for v in videos:
            if len(added) >= target_count:
                break

            vid_id = str(v.get("id", ""))
            if not vid_id or vid_id in known_ids:
                continue

            files = v.get("video_files", [])
            if not files:
                continue

            # Need at least 1080p
            best = best_video_file(files)
            w = best.get("width", 0)
            if w < 1280:
                print(f"  skip {vid_id}: resolution too low ({w}px)")
                continue

            # Get better thumbnail via detail endpoint
            detail = fetch_video_detail(vid_id)
            thumb  = best_thumb(detail or v)

            src4k = best.get("link", "")
            srchd = hd_src(src4k)

            # Auto-generate a name from Pexels tags / user / query
            tags = v.get("tags", [])
            if tags:
                name_parts = [t.capitalize() for t in tags[:3]]
                vname = " ".join(name_parts)
            else:
                vname = query.title()

            entry = {
                "id":     vid_id,
                "name":   vname,
                "quality":"4K" if w >= 3840 else "HD",
                "thumb":  thumb,
                "src":    src4k,
                "src_hd": srchd,
            }

            # Determine target category
            # If cat is a candidate and not yet in active_cats, promote it
            cat_ids = [c["id"] for c in db["categories"]]
            if cid not in cat_ids:
                # Promote candidate to active only if we have ≥3 videos in it
                existing_new = [a for a in added if a["_cat_id"] == cid]
                if len(existing_new) + 1 >= 3:
                    # Promote
                    new_cat = {
                        "id":      cid,
                        "name":    cat["name"],
                        "emoji":   cat.get("emoji", CATEGORY_EMOJIS.get(cid, "▶️")),
                        "music":   cat.get("music", ""),
                        "queries": cat.get("queries", []),
                        "videos":  [],
                    }
                    db["categories"].append(new_cat)
                    db["candidate_categories"] = [
                        c for c in db.get("candidate_categories", []) if c["id"] != cid
                    ]
                    print(f"  🎉 New category promoted: {cat['name']}")

            # Add to the right category
            for c in db["categories"]:
                if c["id"] == cid:
                    c["videos"].append(entry)
                    break

            known_ids.add(vid_id)
            entry["_cat_id"] = cid  # temp field for grouping
            added.append(entry)
            print(f"  ✓ Added [{cid}] '{vname}' (id={vid_id}, {w}px)")

            time.sleep(0.3)  # gentle rate limiting

    if not added:
        print("No new videos found today. Try again tomorrow.")
        return

    # Update DB metadata
    db["known_ids"] = sorted(known_ids)
    db["last_updated"] = today

    # Save DB
    DB_PATH.write_text(json.dumps(db, indent=2, ensure_ascii=False))
    print(f"\n✓ videos_db.json updated ({len(added)} new video(s))")

    # Regenerate index.html
    generate_index(db)

    # Append to queue
    for entry in added:
        cid = entry.pop("_cat_id")
        cat_obj = next((c for c in db["categories"] if c["id"] == cid), {"id": cid, "name": cid, "music": ""})
        queue["items"].append(queue_item(entry, cat_obj))

    save_queue(queue)
    print(f"✓ queue.json updated ({len(added)} item(s) queued for YouTube)")

    # Git commit + push (triggers Vercel deploy)
    git_push(f"[auto] Add {len(added)} new video(s) — {today}")

    print("\n=== Done ===\n")

if __name__ == "__main__":
    main()
