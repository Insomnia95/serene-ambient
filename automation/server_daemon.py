#!/usr/bin/env python3
"""
Calm Veritas — DigitalOcean Server Daemon
Polls queue.json from GitHub every hour.
For each pending item: downloads 4K video + music, creates 10-hour loop with FFmpeg
(encoded at 4Mbps 4K), uploads to YouTube with SEO metadata, marks as done.

Usage (run as a background service):
    python server_daemon.py

Or with nohup for 24/7:
    nohup python server_daemon.py >> /var/log/calm-veritas.log 2>&1 &

Requirements:
    pip install google-api-python-client google-auth-oauthlib

Environment variables (set in /etc/environment by setup_server.sh):
    SERENE_TOKEN     — path to token.json (YouTube OAuth)
    SERENE_SECRETS   — path to client_secrets.json
    FREESOUND_TOKEN  — Freesound API token
    CALM_VERITAS_REPO — path to repo root (default: /root/serene)
"""

import json
import math
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ─── CONFIG ──────────────────────────────────────────────────────────────────

# Raw GitHub queue URL
QUEUE_URL = "https://raw.githubusercontent.com/Insomnia95/serene-ambient/main/data/queue.json"

# Local work directory on the server
WORK_DIR = Path("/tmp/serene_work")

# Repo root — needed to resolve local music paths (e.g. music/ocean.mp3)
REPO_DIR = Path(os.environ.get("CALM_VERITAS_REPO", "/root/serene"))

# Path to your token.json (from local OAuth, scp'd to server)
TOKEN_JSON = Path(os.environ.get("SERENE_TOKEN", Path.home() / "serene_token.json"))

# Path to client_secrets.json
CLIENT_SECRETS = Path(os.environ.get("SERENE_SECRETS", Path.home() / "client_secrets.json"))

# How often to poll queue (seconds)
POLL_INTERVAL = 3600  # 1 hour

# Loop length in seconds (4 hours)
LOOP_SECONDS = 14400

# YouTube category ID for "Film & Animation" (ambient content)
YT_CATEGORY_ID = "1"

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] {msg}", flush=True)

def fetch_json(url):
    req = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def download_file(url, dest_path, label="file"):
    log(f"  Downloading {label}: {url}")
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=60) as r, open(dest_path, "wb") as f:
        chunk = 65536
        while True:
            block = r.read(chunk)
            if not block:
                break
            f.write(block)
    log(f"  ✓ Saved {label} → {dest_path} ({os.path.getsize(dest_path) // 1024 // 1024} MB)")

def get_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, timeout=30
    )
    return float(result.stdout.strip())

def make_10h_loop(video_path, audio_path, out_path):
    """
    Create a 10-hour 4K loop encoded at 4Mbps (YouTube-ready).
    - Re-encodes with libx264 at 4Mbps, upscaled to 3840x2160
    - If audio_path is provided: mixes looped audio at 192k AAC
    - Output ~17 GB for 10h (fits on 50 GB disk)
    """
    dur = get_duration(video_path)
    repeats = math.ceil(LOOP_SECONDS / dur) + 1

    concat_file = out_path.with_suffix(".txt")
    with open(concat_file, "w") as f:
        for _ in range(repeats):
            f.write(f"file '{video_path}'\n")

    log(f"  Building {repeats}x loop (source: {dur:.1f}s → {LOOP_SECONDS//3600}h). Encoding at 4Mbps 4K...")

    if audio_path and Path(audio_path).exists():
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-stream_loop", "-1", "-i", str(audio_path),
            "-t", str(LOOP_SECONDS),
            "-c:v", "libx264", "-preset", "veryfast",
            "-b:v", "2500k", "-maxrate", "2500k", "-bufsize", "5000k",
            "-vf", "scale=1920:1080",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(out_path)
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-t", str(LOOP_SECONDS),
            "-c:v", "libx264", "-preset", "veryfast",
            "-b:v", "2500k", "-maxrate", "2500k", "-bufsize", "5000k",
            "-vf", "scale=1920:1080",
            "-an",
            str(out_path)
        ]

    result = subprocess.run(cmd)
    concat_file.unlink(missing_ok=True)

    if result.returncode != 0:
        raise RuntimeError("FFmpeg encoding failed")

    size_gb = os.path.getsize(out_path) / 1024 / 1024 / 1024
    log(f"  ✓ 10-hour loop created: {out_path} ({size_gb:.2f} GB)")

# ─── SEO METADATA ────────────────────────────────────────────────────────────

CATEGORY_KEYWORDS = {
    "ocean":     ["ocean", "sea", "waves", "water", "coastal", "beach"],
    "fire":      ["fire", "fireplace", "flames", "campfire", "cozy"],
    "rain":      ["rain", "rainfall", "storm", "thunder", "nature"],
    "forest":    ["forest", "nature", "trees", "woods", "green"],
    "winter":    ["winter", "snow", "cold", "ice", "blizzard"],
    "stars":     ["stars", "night sky", "galaxy", "cosmos", "space"],
    "abstract":  ["abstract", "art", "motion", "visual", "meditative"],
    "sunset":    ["sunset", "golden hour", "dusk", "sunrise", "sky"],
    "waterfall": ["waterfall", "river", "stream", "cascade", "water"],
    "desert":    ["desert", "sand", "dunes", "arid", "sahara"],
    "city":      ["city", "urban", "cityscape", "night", "neon"],
    "underwater":["underwater", "ocean", "sea life", "coral", "fish"],
    "aurora":    ["aurora", "northern lights", "borealis", "sky", "night"],
}

CATEGORY_MOODS = {
    "ocean":     "Relaxing Ocean Sounds",
    "fire":      "Cozy Fire Ambience",
    "rain":      "Calming Rain Sounds",
    "forest":    "Peaceful Forest Sounds",
    "winter":    "Peaceful Winter Ambience",
    "stars":     "Cosmic Night Ambience",
    "abstract":  "Mesmerizing Visual Loop",
    "sunset":    "Golden Sunset Ambience",
    "waterfall": "Calming Waterfall Sounds",
    "desert":    "Desert Silence Ambience",
    "city":      "Night City Ambience",
    "underwater":"Peaceful Underwater Sounds",
    "aurora":    "Northern Lights Ambience",
}

CATEGORY_EMOJIS = {
    "ocean":     "🌊", "fire":      "🔥", "rain":      "🌧️",
    "forest":    "🌿", "winter":    "❄️", "stars":     "✨",
    "abstract":  "🎨", "sunset":    "🌅", "waterfall": "💧",
    "desert":    "🏜️", "city":      "🌃", "underwater":"🐠",
    "aurora":    "🌌",
}

def build_yt_metadata(item):
    cid    = item.get("category_id", "")
    cname  = item.get("category_name", cid.title())
    vname  = item.get("name", cname)
    emoji  = CATEGORY_EMOJIS.get(cid, "▶️")
    mood   = CATEGORY_MOODS.get(cid, f"Relaxing {cname} Ambience")
    kws    = CATEGORY_KEYWORDS.get(cid, [cname.lower()])

    title = (
        f"{vname} {emoji} | 4-Hour Ambient Loop | {mood} | Calm Veritas"
    )

    description = f"""{vname} — a beautiful 10-hour ambient loop from Calm Veritas.

{emoji} Perfect for: sleep, focus, meditation, study, relaxation, background ambience.

Watch more ambient scenes on our website: https://www.calm-veritas.com

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎬 What you'll experience:
This seamless 10-hour loop brings you {mood.lower()} to fill your space with calm and beauty. Let the visuals and sounds carry you away.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌐 Calm Veritas — Free Ambient Video Collection
Visit: https://www.calm-veritas.com
Browse ocean, fire, rain, forest, winter, stars, and abstract ambience videos.

Video source: Pexels (Free License) | Source: Pexels.com

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

#{cname.lower().replace(' ','')} #ambience #relaxing #sleep #lofi #ambient #10hours #serene #4K #{mood.split()[0].lower()} #{' #'.join(kws[:4])}
"""

    tags = [
        vname, cname, "ambient", "relaxing", "sleep music",
        "4 hours", "4K", "loop", "Calm Veritas", mood,
        "study music", "focus", "meditation", "background",
    ] + kws[:6]

    return title[:100], description, list(dict.fromkeys(tags))[:30]

# ─── YOUTUBE UPLOAD ──────────────────────────────────────────────────────────

def get_youtube_service():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = None

    if TOKEN_JSON.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_JSON), SCOPES)

    if not creds or not creds.valid:
        from google.auth.transport.requests import Request
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_JSON.write_text(creds.to_json())
        else:
            if not CLIENT_SECRETS.exists():
                raise FileNotFoundError(
                    f"client_secrets.json not found at {CLIENT_SECRETS}. "
                    "Follow SETUP.txt to create it."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
            creds = flow.run_local_server(port=0)
            TOKEN_JSON.write_text(creds.to_json())

    return build("youtube", "v3", credentials=creds)

def upload_to_youtube(yt, video_path, title, description, tags):
    from googleapiclient.http import MediaFileUpload

    log(f"  Uploading to YouTube: {title}")
    body = {
        "snippet": {
            "title":       title[:100],
            "description": description,
            "tags":        tags,
            "categoryId":  YT_CATEGORY_ID,
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        }
    }

    media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True, chunksize=10*1024*1024)
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            log(f"    Upload progress: {pct}%")

    vid_id = response.get("id", "")
    log(f"  ✓ Uploaded: https://www.youtube.com/watch?v={vid_id}")
    return vid_id

# ─── QUEUE MANAGEMENT ────────────────────────────────────────────────────────

DONE_PATH = WORK_DIR / "done.json"

def load_done():
    if DONE_PATH.exists():
        return set(json.loads(DONE_PATH.read_text()).get("done", []))
    return set()

def save_done(done_set):
    DONE_PATH.write_text(json.dumps({"done": sorted(done_set)}, indent=2))

# ─── PROCESS ONE ITEM ────────────────────────────────────────────────────────

def process_item(item, yt):
    vid_id = item.get("id")
    vname  = item.get("name", "Video")
    # Prefer 4K source for encoding; fall back to HD
    src_url = item.get("src_4k") or item.get("src_hd", "")
    music   = item.get("music", "")   # e.g. "music/ocean.mp3" (relative to repo)

    if not src_url:
        log(f"  [skip] No video URL for {vid_id}")
        return False

    log(f"\n--- Processing: {vname} (id={vid_id}) ---")
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    video_tmp = WORK_DIR / f"{vid_id}_video.mp4"
    loop_out  = WORK_DIR / f"{vid_id}_10h.mp4"

    try:
        # Download 4K video
        download_file(src_url, video_tmp, "4K video")

        # Resolve music: relative path from repo (e.g. music/ocean.mp3)
        local_music = None
        if music:
            if music.startswith("http"):
                music_tmp_path = WORK_DIR / f"{vid_id}_music.mp3"
                try:
                    download_file(music, music_tmp_path, "music")
                    local_music = music_tmp_path
                except Exception as e:
                    log(f"  [warn] Could not download music: {e}")
            else:
                # Local path relative to repo (git pull keeps it fresh)
                candidate = REPO_DIR / music
                if candidate.exists():
                    local_music = candidate
                    log(f"  ♪ Using local music: {candidate}")
                else:
                    log(f"  [warn] Music file not found: {candidate}")

        # Create 10h loop
        make_10h_loop(video_tmp, local_music, loop_out)

        # Build YouTube metadata
        title, description, tags = build_yt_metadata(item)
        log(f"  Title: {title}")

        # Upload
        yt_id = upload_to_youtube(yt, loop_out, title, description, tags)

        return True

    except Exception as e:
        log(f"  [error] Failed to process {vid_id}: {e}")
        import traceback; traceback.print_exc()
        return False

    finally:
        # Clean up local temp files to save disk space
        # (never delete local_music if it's in the repo, only if it was downloaded to WORK_DIR)
        for f in [video_tmp, loop_out]:
            if f and Path(f).exists():
                Path(f).unlink()
                log(f"  Cleaned up: {f}")

# ─── MAIN LOOP ───────────────────────────────────────────────────────────────

def main():
    log("=== Calm Veritas Server Daemon started ===")
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    yt = None  # lazily initialized on first item

    while True:
        log(f"Polling queue from GitHub...")
        try:
            queue = fetch_json(QUEUE_URL)
        except Exception as e:
            log(f"[error] Could not fetch queue: {e}. Retrying in {POLL_INTERVAL}s.")
            time.sleep(POLL_INTERVAL)
            continue

        items    = queue.get("items", [])
        done_set = load_done()
        pending  = [it for it in items if it.get("status") == "pending" and str(it.get("id")) not in done_set]

        log(f"Queue: {len(items)} total, {len(pending)} pending, {len(done_set)} done")

        if pending:
            # Initialize YouTube service once
            if yt is None:
                log("Initializing YouTube API...")
                try:
                    yt = get_youtube_service()
                    log("✓ YouTube API ready")
                except Exception as e:
                    log(f"[error] Could not init YouTube: {e}")
                    time.sleep(POLL_INTERVAL)
                    continue

            for item in pending:
                vid_id = str(item.get("id"))
                success = process_item(item, yt)
                if success:
                    done_set.add(vid_id)
                    save_done(done_set)
                    log(f"✓ Completed: {vid_id}")
                else:
                    log(f"[warn] Failed: {vid_id} — will retry next cycle")

                time.sleep(5)  # brief pause between items

        else:
            log("No pending items.")

        log(f"Sleeping {POLL_INTERVAL // 3600}h until next check...\n")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
