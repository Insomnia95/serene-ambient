#!/usr/bin/env python3
"""
Calm Veritas — Download per-video music from Freesound.
Each video gets its own matching CC0 ambient track.
Music files saved as music/{video_id}.mp3

Usage:
    python3 automation/download_video_music.py

Requires: FREESOUND_TOKEN env var
"""

import json
import os
import re
import time
import urllib.request
import urllib.parse
from pathlib import Path

FREESOUND_TOKEN = os.environ.get("FREESOUND_TOKEN", "")
REPO_DIR  = Path(__file__).parent.parent
DB_PATH   = REPO_DIR / "data" / "videos_db.json"
MUSIC_DIR = REPO_DIR / "music"
INDEX_PATH = REPO_DIR / "index.html"

FREESOUND_BASE = "https://freesound.org/apiv2"

# Keywords per category to make search more specific
CATEGORY_MOOD = {
    "ocean":     "ocean waves water sea ambient relaxing",
    "fire":      "fire crackling fireplace flames ambient",
    "rain":      "rain falling drops ambient gentle",
    "forest":    "forest nature birds trees ambient",
    "winter":    "snow wind cold winter blizzard ambient",
    "stars":     "space cosmos night stars ambient drone",
    "abstract":  "ambient drone meditation electronic",
    "sunset":    "peaceful sunset golden ambient warm",
    "waterfall": "waterfall stream river nature ambient",
    "desert":    "desert wind sand dunes ambient",
    "city":      "city night urban rain ambient",
    "underwater":"underwater ocean bubbles sea ambient",
    "aurora":    "northern lights arctic ambient drone",
}

def build_query(video_name, cat_id):
    """Build a Freesound search query from video name + category mood."""
    mood = CATEGORY_MOOD.get(cat_id, f"{cat_id} ambient")
    # Take first 2 meaningful words from video name
    words = [w for w in video_name.split() if len(w) > 3][:2]
    if words:
        return f"{' '.join(words).lower()} {mood}"
    return mood

def freesound_search(query):
    if not FREESOUND_TOKEN:
        print("ERROR: set FREESOUND_TOKEN")
        return []
    params = urllib.parse.urlencode({
        "query": query,
        "filter": 'license:"Creative Commons 0" duration:[60 TO *]',
        "fields": "id,name,duration,previews,username",
        "page_size": 10,
        "token": FREESOUND_TOKEN,
    })
    try:
        req = urllib.request.Request(f"{FREESOUND_BASE}/search/text/?{params}")
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode()).get("results", [])
    except Exception as e:
        print(f"  [error] Freesound: {e}")
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
        print(f"  [error] Download: {e}")
        return False

def hd_src(src4k):
    s = re.sub(r'uhd_\d+_\d+_(\d+fps)', r'hd_1920_1080_\1', src4k)
    s = re.sub(r'hd_3840_2160_(\d+fps)', r'hd_1920_1080_\1', s)
    return s

def generate_index(db):
    """Regenerate index.html CATEGORIES block with per-video music."""
    html = INDEX_PATH.read_text(encoding="utf-8")
    EMOJIS = {
        "ocean":"🌊","fire":"🔥","rain":"🌧️","forest":"🌿","winter":"❄️",
        "stars":"✨","abstract":"🎨","sunset":"🌅","waterfall":"💧",
        "desert":"🏜️","city":"🌃","underwater":"🐠","aurora":"🌌",
    }
    cats_js_lines = ["const CATEGORIES = ["]
    for cat in db["categories"]:
        if not cat.get("videos"):
            continue
        cid    = cat["id"]
        cname  = cat["name"]
        cemoji = cat.get("emoji", EMOJIS.get(cid, "▶️"))
        cmusic = cat.get("music", "")
        videos_js = []
        for v in cat["videos"]:
            vsrc   = v["src"].replace("'", "\\'")
            vhd    = v.get("src_hd", hd_src(v["src"])).replace("'", "\\'")
            vname  = v["name"].replace("'", "\\'")
            vthumb = v.get("thumb", "").replace("'", "\\'")
            vmusic = v.get("music", "").replace("'", "\\'")
            videos_js.append(
                f"    {{ id:{v['id']!r}, name:{vname!r}, "
                f"thumb:{vthumb!r}, src:{vsrc!r}, src_hd:{vhd!r}, "
                f"music:{vmusic!r} }}"
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
    new_html, count = re.subn(
        pattern,
        r'\g<1>' + new_cats_js + '\n// === CATEGORIES END ===',
        html, flags=re.DOTALL
    )
    if count == 0:
        print("  [warn] CATEGORIES markers not found")
        return
    INDEX_PATH.write_text(new_html, encoding="utf-8")
    print("  ✓ index.html regenerated with per-video music")

def main():
    if not FREESOUND_TOKEN:
        print("ERROR: export FREESOUND_TOKEN=ваш_токен")
        return

    MUSIC_DIR.mkdir(exist_ok=True)
    db = json.loads(DB_PATH.read_text())
    updated = 0

    for cat in db.get("categories", []):
        cid   = cat["id"]
        cname = cat["name"]
        print(f"\n[{cid}] {cname} — {len(cat.get('videos', []))} видео")

        for v in cat.get("videos", []):
            vid_id = str(v["id"])
            vname  = v["name"]
            dest   = MUSIC_DIR / f"{vid_id}.mp3"
            rel    = f"music/{vid_id}.mp3"

            # Skip if already has music
            if v.get("music") and dest.exists():
                print(f"  ✓ {vname} — уже есть")
                continue

            query = build_query(vname, cid)
            print(f"  ♪ {vname} → поиск: '{query}'")
            results = freesound_search(query)

            if not results:
                print(f"    [warn] Ничего не найдено, пробуем категорийный запрос...")
                results = freesound_search(CATEGORY_MOOD.get(cid, f"{cid} ambient"))

            if not results:
                print(f"    [skip] Нет результатов")
                time.sleep(0.5)
                continue

            # Pick longest track (more ambient feel)
            sound = sorted(results, key=lambda x: x.get("duration", 0), reverse=True)[0]
            dur   = sound.get("duration", 0)
            name  = sound.get("name", "")
            user  = sound.get("username", "")

            print(f"    → '{name}' by {user} ({dur:.0f}s)")

            previews = sound.get("previews", {})
            url = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3")
            if not url:
                print(f"    [skip] Нет URL")
                time.sleep(0.5)
                continue

            if download_mp3(url, dest):
                size_kb = dest.stat().st_size // 1024
                print(f"    ✓ Сохранено: {rel} ({size_kb} KB)")
                v["music"] = rel
                updated += 1
            else:
                print(f"    [error] Не скачалось")

            time.sleep(1)  # rate limit

    # Save DB
    DB_PATH.write_text(json.dumps(db, indent=2, ensure_ascii=False))
    print(f"\n✓ Обновлено: {updated} видео")

    # Regenerate index.html
    generate_index(db)

    # Push to GitHub
    if updated > 0:
        import subprocess
        try:
            subprocess.run(["git", "-C", str(REPO_DIR), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(REPO_DIR), "commit", "-m",
                            f"Per-video music: {updated} tracks"], check=True)
            subprocess.run(["git", "-C", str(REPO_DIR), "push"], check=True)
            print("✓ Запушено в GitHub")
        except subprocess.CalledProcessError as e:
            print(f"  [warn] git push: {e}")

if __name__ == "__main__":
    main()
