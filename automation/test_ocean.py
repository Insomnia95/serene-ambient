#!/usr/bin/env python3
"""
Calm Veritas — Ocean Test Script
1. Uploads one 4K 10-hour loop to YouTube (Ocean category, first video)
2. Creates one YouTube Live Broadcast for Ocean and starts FFmpeg stream

Usage:
    python3 automation/test_ocean.py --loop      # just the loop upload
    python3 automation/test_ocean.py --stream    # just the live stream
    python3 automation/test_ocean.py             # both

Requirements:
    pip install google-api-python-client google-auth-oauthlib
    token.json + client_secrets.json in ~/
"""

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

REPO_DIR    = Path(__file__).parent.parent
DB_PATH     = REPO_DIR / "data" / "videos_db.json"
TOKEN_JSON  = Path(os.environ.get("SERENE_TOKEN",  Path.home() / "serene_token.json"))
SECRETS     = Path(os.environ.get("SERENE_SECRETS", Path.home() / "client_secrets.json"))
MUSIC_DIR   = REPO_DIR / "music"

LOOP_HOURS  = 4
LOOP_SECS   = LOOP_HOURS * 3600
YT_CATEGORY = "1"   # Film & Animation

# ─── YOUTUBE AUTH ─────────────────────────────────────────────────────────────

def get_youtube():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/youtube"]
    creds = None
    if TOKEN_JSON.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_JSON), SCOPES)
    if not creds or not creds.valid:
        from google.auth.transport.requests import Request
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_JSON.write_text(creds.to_json())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(SECRETS), SCOPES)
            creds = flow.run_local_server(port=0)
            TOKEN_JSON.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def download(url, dest, label="file"):
    print(f"  Downloading {label}...", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        while True:
            block = r.read(65536)
            if not block: break
            f.write(block)
    mb = os.path.getsize(dest) / 1024 / 1024
    print(f"  ✓ {label}: {mb:.1f} MB")

def get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True)
    return float(r.stdout.strip())

def get_ocean():
    db = json.loads(DB_PATH.read_text())
    cat = next(c for c in db["categories"] if c["id"] == "ocean")
    video = cat["videos"][0]
    music = cat.get("music", "")
    return cat, video, music

# ─── LOOP UPLOAD (4K via pipe) ────────────────────────────────────────────────

def upload_loop(yt, cat, video, music_path):
    print("\n=== 4K Loop Upload ===")
    print(f"Video: {video['name']} (id={video['id']})")

    tmp_dir = Path(tempfile.mkdtemp())
    vid_tmp = tmp_dir / "ocean_src.mp4"

    # Download 4K source
    src_4k = video["src"]
    download(src_4k, vid_tmp, "4K source")

    dur = get_duration(vid_tmp)
    repeats = math.ceil(LOOP_SECS / dur) + 1
    print(f"  Source duration: {dur:.1f}s → need {repeats} repeats for {LOOP_HOURS}h")

    # Write concat file
    concat_f = tmp_dir / "concat.txt"
    with open(concat_f, "w") as f:
        for _ in range(repeats):
            f.write(f"file '{vid_tmp}'\n")

    # Build metadata
    title = f"{video['name']} 🌊 | {LOOP_HOURS}-Hour Ocean Ambience | 1080p Loop | Calm Veritas"
    description = f"""{video['name']} — a seamless {LOOP_HOURS}-hour ambient loop.

🌊 Pure ocean atmosphere for sleep, focus, and relaxation.
No ads interruptions · Full HD · Best with headphones

🌐 More ambient scenes: https://www.calm-veritas.com

Video: Pexels (Free License) | Music: CC0

#ocean #ambient #relaxing #sleep #1080p #{LOOP_HOURS}hours #calmveritas #waves #nature
"""
    tags = ["ocean", "ambient", "relaxing", "sleep", "4K", "waves",
            "nature sounds", "10 hours", "calm veritas", "loop", "meditation"]

    # Encode at 1080p 2.5Mbps — ~4.5GB for 4h, fits easily on 50GB disk
    # Ambient video looks great at 1080p (slow movement, no fast cuts)
    loop_path = Path("/tmp/ocean_loop.mp4")
    print(f"  Encoding 1080p loop at 2.5Mbps → {loop_path} (~4.5GB, takes ~2-4h)...")

    music_abs = REPO_DIR / music_path if (music_path and (REPO_DIR / music_path).exists()) else None

    if music_abs:
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_f),
            "-stream_loop", "-1", "-i", str(music_abs),
            "-t", str(LOOP_SECS),
            "-c:v", "libx264", "-preset", "veryfast",
            "-b:v", "2500k", "-maxrate", "2500k", "-bufsize", "5000k",
            "-vf", "scale=1920:1080",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(loop_path)
        ]
    else:
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_f),
            "-t", str(LOOP_SECS),
            "-c:v", "libx264", "-preset", "veryfast",
            "-b:v", "2500k", "-maxrate", "2500k", "-bufsize", "5000k",
            "-vf", "scale=1920:1080",
            "-an",
            str(loop_path)
        ]

    result = subprocess.run(ffmpeg_cmd)
    if result.returncode != 0:
        print("  [error] FFmpeg failed")
        return None

    size_gb = loop_path.stat().st_size / 1024**3
    print(f"  ✓ Loop encoded: {size_gb:.1f} GB")

    # Upload from pipe
    from googleapiclient.http import MediaFileUpload
    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": YT_CATEGORY,
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    }
    media = MediaFileUpload(str(loop_path), mimetype="video/mp4", resumable=True, chunksize=16*1024*1024)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = req.next_chunk()
        if status:
            print(f"  Upload: {int(status.progress()*100)}%", end="\r")

    vid_id = response.get("id", "")
    print(f"\n  ✓ Loop uploaded: https://www.youtube.com/watch?v={vid_id}")

    # Cleanup
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)
    if loop_path.exists():
        loop_path.unlink()
        print("  ✓ Temp file deleted")
    return vid_id

# ─── LIVE STREAM ──────────────────────────────────────────────────────────────

def create_live_stream(yt, cat, video):
    print("\n=== Live Stream — Ocean ===")

    title = f"🌊 Ocean Waves Live · 4K Ambient · Calm Veritas"
    description = f"""Live ocean ambience streaming 24/7 — {video['name']}.

🌊 Endless ocean waves for sleep, focus, and relaxation.
🌐 More ambient scenes: https://www.calm-veritas.com

#ocean #live #ambient #relaxing #4K #sleep #calmveritas
"""

    # Create broadcast
    broadcast = yt.liveBroadcasts().insert(
        part="snippet,status,contentDetails",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "scheduledStartTime": "2026-01-01T00:00:00Z",
            },
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
            "contentDetails": {"enableAutoStart": True, "enableAutoStop": False}
        }
    ).execute()
    broadcast_id = broadcast["id"]
    print(f"  ✓ Broadcast: https://www.youtube.com/watch?v={broadcast_id}")

    # Create stream
    stream = yt.liveStreams().insert(
        part="snippet,cdn",
        body={
            "snippet": {"title": "Ocean Stream"},
            "cdn": {
                "frameRate": "30fps",
                "resolution": "1080p",   # server encodes at 1080p
                "ingestionType": "rtmp"
            }
        }
    ).execute()
    rtmp_url  = stream["cdn"]["ingestionInfo"]["ingestionAddress"]
    stream_key = stream["cdn"]["ingestionInfo"]["streamName"]
    rtmp_full  = f"{rtmp_url}/{stream_key}"

    # Bind stream to broadcast
    yt.liveBroadcasts().bind(
        part="id,contentDetails",
        id=broadcast_id,
        streamId=stream["id"]
    ).execute()

    print(f"  ✓ RTMP: {rtmp_url}/****")

    # Write FFmpeg command to file
    src_hd = video.get("src_hd", video["src"])
    ffmpeg_stream = (
        f'ffmpeg -stream_loop -1 -re -i "{src_hd}" '
        f'-vf scale=1920:1080 '
        f'-c:v libx264 -preset veryfast -b:v 4500k -maxrate 4500k -bufsize 9000k '
        f'-c:a aac -b:a 128k '
        f'-f flv "{rtmp_full}"'
    )

    stream_file = REPO_DIR / "automation" / "start_ocean_stream.sh"
    stream_file.write_text(f"#!/bin/bash\nnohup {ffmpeg_stream} >> /var/log/ocean_stream.log 2>&1 &\necho 'Stream started'\n")
    stream_file.chmod(0o755)
    print(f"  ✓ Stream script: {stream_file}")
    print(f"\n  To start streaming, run on server:")
    print(f"  bash automation/start_ocean_stream.sh")

    return broadcast_id, rtmp_full

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop",   action="store_true", help="Upload 4K loop only")
    parser.add_argument("--stream", action="store_true", help="Create live stream only")
    args = parser.parse_args()
    do_loop   = args.loop   or not (args.loop or args.stream)
    do_stream = args.stream or not (args.loop or args.stream)

    print("Calm Veritas — Ocean Test")
    print("Authenticating with YouTube...")
    yt = get_youtube()
    print("✓ YouTube API ready\n")

    cat, video, music = get_ocean()
    music_path = music  # e.g. "music/ocean.mp3"

    if do_loop:
        upload_loop(yt, cat, video, music_path)

    if do_stream:
        create_live_stream(yt, cat, video)

    print("\n=== Done ===")

if __name__ == "__main__":
    main()
