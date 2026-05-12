#!/usr/bin/env python3
"""
Calm Veritas — Fix Broken Video URLs
Checks all videos in videos_db.json, refreshes any that return 403/404 via Pexels API.
Run from repo root: python3 automation/fix_broken_videos.py

Then commit and push to redeploy.
"""

import json
import re
import time
import urllib.request
import urllib.error
from pathlib import Path

PEXELS_API_KEY = "tVypT2VSxvRo8r5urjNUMDBVFVBhJFYeT0Q9E60LoKIzLOzW3a7FLZFA"
REPO_DIR  = Path(__file__).parent.parent
DB_PATH   = REPO_DIR / "data" / "videos_db.json"
INDEX_PATH = REPO_DIR / "index.html"

def check_url(url):
    """Return HTTP status code for a URL."""
    try:
        req = urllib.request.Request(url, method='HEAD')
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0

def pexels_get_video(video_id):
    """Fetch fresh video data from Pexels API."""
    url = f"https://api.pexels.com/videos/videos/{video_id}"
    req = urllib.request.Request(url, headers={"Authorization": PEXELS_API_KEY})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"    [error] Pexels API failed for {video_id}: {e}")
        return None

def best_file(video_files, prefer_4k=True):
    """Pick best video file URL."""
    uhd = [f for f in video_files if f.get("width", 0) >= 3840]
    hd  = [f for f in video_files if 1900 <= f.get("width", 0) <= 1921]
    if prefer_4k and uhd:
        return max(uhd, key=lambda f: f["width"] * f["height"])
    if hd:
        return max(hd, key=lambda f: f["width"] * f["height"])
    return max(video_files, key=lambda f: f.get("width", 0))

def hd_src(src4k):
    s = re.sub(r'uhd_\d+_\d+_(\d+fps)', r'hd_1920_1080_\1', src4k)
    s = re.sub(r'hd_3840_2160_(\d+fps)', r'hd_1920_1080_\1', s)
    s = re.sub(r'hd_4096_\d+_(\d+fps)',  r'hd_1920_1080_\1', s)
    return s

def generate_index(db):
    html = INDEX_PATH.read_text(encoding="utf-8")
    EMOJIS = {
        "ocean":"🌊","fire":"🔥","rain":"🌧️","forest":"🌿","winter":"❄️",
        "stars":"✨","abstract":"🎨","sunset":"🌅","waterfall":"💧",
        "desert":"🏜️","city":"🌃","underwater":"🐠","aurora":"🌌",
    }
    cats_js_lines = ["const CATEGORIES = ["]
    for cat in db["categories"]:
        cid = cat["id"]; cname = cat["name"]
        cemoji = cat.get("emoji", EMOJIS.get(cid, "▶️"))
        cmusic = cat.get("music", "")
        videos_js = []
        for v in cat.get("videos", []):
            vsrc  = v["src"].replace("'", "\\'")
            vhd   = v.get("src_hd", hd_src(v["src"])).replace("'", "\\'")
            vname = v["name"].replace("'", "\\'")
            vthumb= v.get("thumb", "").replace("'", "\\'")
            videos_js.append(
                f"    {{ id:{v['id']!r}, name:{vname!r}, "
                f"thumb:{vthumb!r}, src:{vsrc!r}, src_hd:{vhd!r} }}"
            )
        cats_js_lines += [
            "  {",
            f"    id: {cid!r}, name: {cname!r}, emoji: {cemoji!r},",
            f"    music: {cmusic!r},",
            "    videos: [",
            ",\n".join(videos_js),
            "    ]",
            "  },",
        ]
    cats_js_lines.append("];")
    new_cats_js = "\n".join(cats_js_lines)
    pattern = r'(// === CATEGORIES START ===\n).*?(// === CATEGORIES END ===)'
    new_html, count = re.subn(pattern, r'\g<1>' + new_cats_js + '\n// === CATEGORIES END ===', html, flags=re.DOTALL)
    if count == 0:
        print("  [warn] CATEGORIES markers not found — skipping index.html update")
        return
    INDEX_PATH.write_text(new_html, encoding="utf-8")
    print("  ✓ index.html regenerated")

def main():
    db = json.loads(DB_PATH.read_text())
    fixed = 0
    removed = 0

    for cat in db["categories"]:
        print(f"\n[{cat['id']}] {cat['name']} — {len(cat['videos'])} videos")
        valid_videos = []

        for v in cat["videos"]:
            vid_id = v["id"]
            src_hd = v.get("src_hd", hd_src(v.get("src", "")))
            print(f"  Checking {vid_id}: ", end="", flush=True)

            status = check_url(src_hd)
            print(f"HTTP {status}", end=" ")

            if status == 200:
                print("✓")
                valid_videos.append(v)
                time.sleep(0.2)
                continue

            # Broken — try to refresh via Pexels API
            print("→ refreshing via API...", end=" ", flush=True)
            data = pexels_get_video(vid_id)

            if not data or not data.get("video_files"):
                print("✗ not found on Pexels — removing")
                removed += 1
                # Remove from known_ids too
                db["known_ids"] = [x for x in db.get("known_ids", []) if str(x) != str(vid_id)]
                time.sleep(0.5)
                continue

            files = data["video_files"]
            best4k = best_file(files, prefer_4k=True)
            new_src = best4k.get("link", v["src"])
            new_hd  = hd_src(new_src)

            # Update thumbnail too
            pics = data.get("video_pictures", [])
            new_thumb = pics[0]["picture"] if pics else v.get("thumb", "")

            v["src"]    = new_src
            v["src_hd"] = new_hd
            v["thumb"]  = new_thumb
            valid_videos.append(v)
            fixed += 1
            print(f"✓ fixed")
            time.sleep(0.5)

        cat["videos"] = valid_videos

    # Save DB
    DB_PATH.write_text(json.dumps(db, indent=2, ensure_ascii=False))
    print(f"\n✓ Done — {fixed} fixed, {removed} removed")

    # Regenerate index.html
    generate_index(db)

    if fixed > 0 or removed > 0:
        import subprocess
        try:
            subprocess.run(["git", "-C", str(REPO_DIR), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(REPO_DIR), "commit", "-m",
                            f"Fix broken videos: {fixed} fixed, {removed} removed"], check=True)
            subprocess.run(["git", "-C", str(REPO_DIR), "push"], check=True)
            print("✓ Запушено в GitHub — Vercel задеплоит автоматически")
        except subprocess.CalledProcessError as e:
            print(f"  [warn] git push не удался: {e}")
            print("  Запушь вручную: git add -A && git commit -m 'Fix broken video URLs' && git push")
    else:
        print("\nВсе видео в порядке, пуш не нужен.")

if __name__ == "__main__":
    main()
