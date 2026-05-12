#!/usr/bin/env python3
"""
Calm Veritas — Create YouTube Live Streams for multiple categories.
Creates up to 5 live broadcasts (YouTube limit) and generates start scripts.

Usage:
    python3 automation/create_streams.py                  # all categories (up to 5)
    python3 automation/create_streams.py ocean rain fire  # specific categories

After running:
    bash automation/start_streams.sh
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_DIR   = Path(__file__).parent.parent
DB_PATH    = REPO_DIR / "data" / "videos_db.json"
TOKEN_JSON = Path(os.environ.get("SERENE_TOKEN",  Path.home() / "serene_token.json"))
SECRETS    = Path(os.environ.get("SERENE_SECRETS", Path.home() / "client_secrets.json"))

MAX_STREAMS = 5

EMOJIS = {
    "ocean": "🌊", "fire": "🔥", "rain": "🌧️", "forest": "🌿",
    "winter": "❄️", "stars": "✨", "abstract": "🎨", "sunset": "🌅",
    "waterfall": "💧", "desert": "🏜️", "city": "🌃",
    "underwater": "🐠", "aurora": "🌌",
}

MOODS = {
    "ocean":     "Ocean Waves · Sleep & Focus",
    "fire":      "Fireplace · Cozy Ambience",
    "rain":      "Rain Sounds · Relax & Study",
    "forest":    "Forest Sounds · Nature",
    "winter":    "Winter Blizzard · Snow Ambience",
    "stars":     "Starry Night · Cosmic Drone",
    "abstract":  "Abstract Visuals · Meditation",
    "sunset":    "Golden Sunset · Peaceful",
    "waterfall": "Waterfall · Nature Sounds",
    "desert":    "Desert Wind · Silence",
    "city":      "Night City · Urban Ambience",
    "underwater":"Underwater · Ocean Depths",
    "aurora":    "Northern Lights · Arctic",
}

def get_youtube():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request

    SCOPES = ["https://www.googleapis.com/auth/youtube"]
    creds = None
    if TOKEN_JSON.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_JSON), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_JSON.write_text(creds.to_json())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(SECRETS), SCOPES)
            creds = flow.run_local_server(port=0)
            TOKEN_JSON.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)

def create_stream_for_category(yt, cat):
    cid   = cat["id"]
    cname = cat["name"]
    emoji = EMOJIS.get(cid, "▶️")
    mood  = MOODS.get(cid, f"{cname} Ambience")
    video = cat["videos"][0]
    music = cat.get("music", "")

    title = f"{emoji} {cname} Live · {mood} · Calm Veritas"
    description = f"""Live {cname.lower()} ambience streaming 24/7.

{emoji} Endless {cname.lower()} atmosphere for sleep, focus, and relaxation.
🌐 More ambient scenes: https://www.calm-veritas.com

#{cid} #live #ambient #relaxing #sleep #calmveritas
"""

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)

    # Create broadcast
    broadcast = yt.liveBroadcasts().insert(
        part="snippet,status,contentDetails",
        body={
            "snippet": {
                "title": title[:100],
                "description": description,
                "scheduledStartTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
            "contentDetails": {"enableAutoStart": True, "enableAutoStop": False}
        }
    ).execute()
    broadcast_id = broadcast["id"]

    # Create RTMP stream
    stream = yt.liveStreams().insert(
        part="snippet,cdn",
        body={
            "snippet": {"title": f"{cname} Stream"},
            "cdn": {
                "frameRate": "30fps",
                "resolution": "1080p",
                "ingestionType": "rtmp"
            }
        }
    ).execute()
    rtmp_url   = stream["cdn"]["ingestionInfo"]["ingestionAddress"]
    stream_key = stream["cdn"]["ingestionInfo"]["streamName"]
    rtmp_full  = f"{rtmp_url}/{stream_key}"

    # Bind
    yt.liveBroadcasts().bind(
        part="id,contentDetails",
        id=broadcast_id,
        streamId=stream["id"]
    ).execute()

    # Build FFmpeg command
    src_hd     = video.get("src_hd", video["src"])
    music_abs  = str(REPO_DIR / music) if music else None
    music_exists = music_abs and Path(music_abs).exists()

    if music_exists:
        ffmpeg_cmd = (
            f'ffmpeg -stream_loop -1 -re -i "{src_hd}" '
            f'-stream_loop -1 -i "{music_abs}" '
            f'-map 0:v -map 1:a '
            f'-vf scale=1920:1080 '
            f'-c:v libx264 -preset veryfast -b:v 4500k -maxrate 4500k -bufsize 9000k '
            f'-c:a aac -b:a 192k '
            f'-f flv "{rtmp_full}"'
        )
    else:
        ffmpeg_cmd = (
            f'ffmpeg -stream_loop -1 -re -i "{src_hd}" '
            f'-vf scale=1920:1080 '
            f'-c:v libx264 -preset veryfast -b:v 4500k -maxrate 4500k -bufsize 9000k '
            f'-an -f flv "{rtmp_full}"'
        )

    print(f"  ✓ {cname}: https://www.youtube.com/watch?v={broadcast_id}")
    print(f"  {'♪ with music' if music_exists else '[no music]'}")

    return cid, ffmpeg_cmd

def main():
    db = json.loads(DB_PATH.read_text())
    all_cats = db.get("categories", [])

    # Filter by args if given
    requested = sys.argv[1:]
    if requested:
        cats = [c for c in all_cats if c["id"] in requested]
    else:
        cats = [c for c in all_cats if c.get("videos")]

    cats = cats[:MAX_STREAMS]

    print(f"Calm Veritas — Creating {len(cats)} live stream(s)")
    print("Authenticating with YouTube...")
    yt = get_youtube()
    print("✓ YouTube API ready\n")

    streams = []
    for cat in cats:
        print(f"[{cat['id']}] {cat['name']}...")
        try:
            cid, cmd = create_stream_for_category(yt, cat)
            streams.append((cid, cmd))
        except Exception as e:
            print(f"  [error] {e}")

    # Write single start script for all streams
    script_path = REPO_DIR / "automation" / "start_streams.sh"
    lines = ["#!/bin/bash", "# Start all Calm Veritas live streams", ""]
    for cid, cmd in streams:
        log = f"/var/log/stream_{cid}.log"
        lines.append(f"echo 'Starting {cid} stream...'")
        lines.append(f"nohup {cmd} >> {log} 2>&1 &")
        lines.append(f"echo '  PID: '$!'  Log: {log}'")
        lines.append("")
    lines.append("echo 'All streams started!'")

    script_path.write_text("\n".join(lines) + "\n")
    script_path.chmod(0o755)

    print(f"\n✓ Script written: {script_path}")
    print(f"\nЗапусти все трансляции:")
    print(f"  bash automation/start_streams.sh")

if __name__ == "__main__":
    main()
