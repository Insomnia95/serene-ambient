#!/usr/bin/env python3
"""
Calm Veritas — Queue all existing videos for YouTube upload.
Run once to populate queue.json with all videos from videos_db.json.

Usage:
    python3 automation/queue_all_videos.py
"""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_DIR   = Path(__file__).parent.parent
DB_PATH    = REPO_DIR / "data" / "videos_db.json"
QUEUE_PATH = REPO_DIR / "data" / "queue.json"

def main():
    db    = json.loads(DB_PATH.read_text())
    queue = json.loads(QUEUE_PATH.read_text()) if QUEUE_PATH.exists() else {"version": 1, "items": []}

    existing_ids = {str(it["id"]) for it in queue.get("items", [])}
    added = 0

    for cat in db.get("categories", []):
        cid   = cat["id"]
        cname = cat["name"]
        music = cat.get("music", "")

        for video in cat.get("videos", []):
            vid_id = str(video["id"])
            if vid_id in existing_ids:
                continue

            item = {
                "id":            video["id"],
                "name":          video["name"],
                "category_id":   cid,
                "category_name": cname,
                "src_hd":        video.get("src_hd", ""),
                "src_4k":        video.get("src", ""),
                "music":         music,
                "status":        "pending",
                "queued_at":     datetime.now(timezone.utc).isoformat(),
            }
            queue["items"].append(item)
            existing_ids.add(vid_id)
            added += 1

    QUEUE_PATH.write_text(json.dumps(queue, indent=2, ensure_ascii=False))
    print(f"✓ Добавлено в очередь: {added} видео")
    print(f"  Всего в очереди: {len(queue['items'])}")

    # Push to GitHub so daemon picks it up
    try:
        subprocess.run(["git", "-C", str(REPO_DIR), "add", "data/queue.json"], check=True)
        subprocess.run(["git", "-C", str(REPO_DIR), "commit", "-m", f"Queue {added} videos for YouTube"], check=True)
        subprocess.run(["git", "-C", str(REPO_DIR), "push"], check=True)
        print("✓ Запушено в GitHub — демон начнёт обработку в течение часа")
    except subprocess.CalledProcessError as e:
        print(f"  [warn] git push не удался: {e}")
        print("  Запушь вручную: git add -A && git push")

if __name__ == "__main__":
    main()
