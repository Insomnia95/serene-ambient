#!/usr/bin/env python3
"""
SERENE — YouTube Live Stream Creator
=====================================
Creates a YouTube live broadcast for every ambient video,
then prints the FFmpeg command to start each stream.

SETUP (one-time):
1. Go to https://console.cloud.google.com
2. Create a project → Enable "YouTube Data API v3"
3. Create credentials → OAuth 2.0 Desktop app
4. Download as client_secrets.json → put in this folder
5. pip install google-api-python-client google-auth-oauthlib
6. python create_streams.py

On first run, a browser window opens for Google login.
After that, token.json is saved and reused automatically.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

# ── VIDEO DATA WITH YOUTUBE METADATA ─────────────────────────────────────────
# Each entry: title, description, tags, HD stream URL (1080p — stable for streaming)

BASE = "https://videos.pexels.com/video-files/"

def hd(vid_id, fps, w="1920", h="1080"):
    return f"{BASE}{vid_id}/{vid_id}-hd_{w}_{h}_{fps}fps.mp4"

def desc(scene, category, mood, scene_desc):
    return f"""{scene} — {scene_desc}

Perfect for focus, study, relaxation, meditation, and sleep. No ads during playback. Loops continuously.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
♾ Loops 24/7 · 🎧 Best with headphones · 🖥 Full HD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌐 Full collection: https://www.calm-veritas.com

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

#{category.lower().replace(' ', '')} #ambient #relaxing #{mood} #lofi #study #sleep #meditation #backgroundvideo #serene"""

VIDEOS = [
    # ── OCEAN ────────────────────────────────────────────────────────────────
    {
        "key": "ocean_1",
        "title": "Deep Ocean Waves 🌊 | 4K Ocean Ambience | Relaxing Sea Sounds | SERENE",
        "description": desc("Deep Ocean Waves", "Ocean", "relaxing",
            "Endless deep ocean waves rolling to shore in 4K Ultra HD."),
        "tags": ["ocean waves","ambient","relaxing","4k","sea sounds","study music","sleep sounds","meditation","lofi","background video","ocean ambience","wave sounds"],
        "src": hd("16727103", "60"),
    },
    {
        "key": "ocean_2",
        "title": "Aerial Beach View 🌊 | 4K Drone Ocean Footage | Peaceful Ambience | SERENE",
        "description": desc("Aerial Beach", "Ocean", "peaceful",
            "Stunning 4K aerial drone footage over a pristine beach and turquoise water."),
        "tags": ["aerial beach","drone footage","ocean","4k","ambient","relaxing","beach sounds","coastal","peaceful","study"],
        "src": hd("29052984", "30"),
    },
    {
        "key": "ocean_3",
        "title": "Breaking Surf 🌊 | 4K Ocean Waves | Study & Relax Background | SERENE",
        "description": desc("Breaking Surf", "Ocean", "study",
            "Powerful waves breaking on the shore in crisp 4K Ultra HD detail."),
        "tags": ["breaking waves","surf","ocean","4k","ambient","study","relax","wave sounds","beach","focus"],
        "src": hd("6624689", "25"),
    },
    {
        "key": "ocean_4",
        "title": "Open Sea 🌊 | 4K Endless Ocean | Relaxing Ambient Background | SERENE",
        "description": desc("Open Sea", "Ocean", "calm",
            "The vast open sea stretching to the horizon — pure calm in Ultra HD."),
        "tags": ["open sea","ocean","horizon","4k","ambient","relaxing","calm","meditation","background","peaceful"],
        "src": hd("3446616", "25"),
    },
    {
        "key": "ocean_5",
        "title": "Tropical Shore 🌊 | 4K Crystal Clear Beach | Paradise Ambience | SERENE",
        "description": desc("Tropical Shore", "Ocean", "tropical",
            "Crystal-clear tropical waters lapping a white sand beach in 4K."),
        "tags": ["tropical beach","paradise","crystal water","4k","ambient","relaxing","beach","tropical","holiday vibes","calm"],
        "src": hd("33840319", "30"),
    },
    {
        "key": "ocean_6",
        "title": "Wave Close-Up 🌊 | 4K Macro Ocean | Satisfying Water Loop | SERENE",
        "description": desc("Wave Close-up", "Ocean", "satisfying",
            "A mesmerizing close-up of ocean waves — water texture in perfect 4K detail."),
        "tags": ["wave closeup","macro water","ocean","4k","satisfying","ambient","relaxing","water loop","asmr","meditative"],
        "src": hd("32760161", "30"),
    },

    # ── FIRE ─────────────────────────────────────────────────────────────────
    {
        "key": "fire_1",
        "title": "Winter Fireplace 🔥 | 4K Cozy Fireplace | Crackling Fire Sounds | SERENE",
        "description": desc("Winter Fireplace", "Fire", "cozy",
            "A warm crackling fireplace on a snowy winter evening — the ultimate cozy ambience."),
        "tags": ["fireplace","crackling fire","cozy","winter","4k","ambient","relaxing","fire sounds","asmr","study","sleep","hygge"],
        "src": hd("35481118", "30"),
    },
    {
        "key": "fire_2",
        "title": "Indoor Fireplace 🔥 | 4K Warm Fire | Study & Relax Background | SERENE",
        "description": desc("Indoor Fire", "Fire", "warm",
            "A beautifully lit indoor fireplace casting warm amber light — perfect loop."),
        "tags": ["indoor fireplace","warm fire","4k","ambient","study","relax","fire background","cozy room","lofi"],
        "src": hd("6984877", "24"),
    },
    {
        "key": "fire_3",
        "title": "Open Flame 🔥 | 4K Bonfire Ambience | Outdoor Fire Sounds | SERENE",
        "description": desc("Open Flame", "Fire", "outdoor",
            "A raw open flame burning brightly — elemental fire in stunning 4K detail."),
        "tags": ["open flame","bonfire","fire","4k","ambient","outdoor","camping","nature","relaxing","meditation"],
        "src": hd("11353677", "30"),
    },
    {
        "key": "fire_4",
        "title": "Bonfire Night 🔥 | 4K Night Campfire | Outdoor Relaxation | SERENE",
        "description": desc("Bonfire Night", "Fire", "night",
            "A roaring bonfire under the night sky — warmth and crackling in perfect 4K."),
        "tags": ["bonfire night","campfire","night fire","4k","ambient","outdoor","camping","stars","relaxing","sleep sounds"],
        "src": hd("17062878", "24"),
    },
    {
        "key": "fire_5",
        "title": "Glowing Embers 🔥 | 4K Fire Embers | Deep Relaxation Ambience | SERENE",
        "description": desc("Glowing Embers", "Fire", "meditative",
            "Slowly glowing and fading embers — hypnotic fire ambience in Ultra HD."),
        "tags": ["fire embers","glowing embers","4k","ambient","meditative","relaxing","hypnotic","asmr","deep relaxation","sleep"],
        "src": hd("31055868", "25"),
    },

    # ── RAIN ─────────────────────────────────────────────────────────────────
    {
        "key": "rain_1",
        "title": "Rain on Window 🌧 | 4K Rainy Day | Study & Focus Ambience | SERENE",
        "description": desc("Rainy Window", "Rain", "focus",
            "Raindrops streaking down a window — the classic study and focus background."),
        "tags": ["rain on window","rainy day","4k","study","focus","ambient","rain sounds","asmr","relaxing","cozy"],
        "src": hd("15454042", "25"),
    },
    {
        "key": "rain_2",
        "title": "Autumn Rain 🌧 | 4K Fall Rainfall | Cozy Season Ambience | SERENE",
        "description": desc("Autumn Rain", "Rain", "autumn",
            "Soft autumn rain falling on golden leaves — the coziest season ambience."),
        "tags": ["autumn rain","fall rain","4k","ambient","cozy","rainy day","seasonal","autumn vibes","study","lofi"],
        "src": hd("5197762", "25"),
    },
    {
        "key": "rain_3",
        "title": "City Rain 🌧 | 4K Urban Rainfall | Night City Ambience | SERENE",
        "description": desc("City Rain", "Rain", "urban",
            "Rain falling on city streets at night — moody urban ambience in 4K."),
        "tags": ["city rain","urban rain","night city","4k","ambient","moody","street","relaxing","lofi","study"],
        "src": hd("28628298", "25"),
    },
    {
        "key": "rain_4",
        "title": "Heavy Rain 🌧 | 4K Downpour | Deep Focus Background | SERENE",
        "description": desc("Heavy Rain", "Rain", "intense",
            "A powerful rainstorm captured in 4K — immersive and deeply relaxing."),
        "tags": ["heavy rain","downpour","4k","ambient","deep focus","study","rainstorm","sleep sounds","asmr","meditation"],
        "src": hd("13619802", "60"),
    },
    {
        "key": "rain_5",
        "title": "Rain on Glass 🌧 | 4K Water Drops | Satisfying Rain Loop | SERENE",
        "description": desc("Rain on Glass", "Rain", "satisfying",
            "Raindrops on glass in hypnotic macro detail — endlessly satisfying 4K loop."),
        "tags": ["rain on glass","water drops","macro rain","4k","satisfying","ambient","asmr","relaxing","meditative","loop"],
        "src": hd("6520303", "30"),
    },

    # ── FOREST ───────────────────────────────────────────────────────────────
    {
        "key": "forest_1",
        "title": "Forest Light 🌿 | 4K Sunlit Forest | Nature Ambience | SERENE",
        "description": desc("Forest Light", "Forest", "nature",
            "Dappled sunlight filtering through a lush forest canopy in 4K Ultra HD."),
        "tags": ["forest light","sunlit forest","nature","4k","ambient","relaxing","trees","woodland","birdsong","meditation"],
        "src": hd("35982732", "25"),
    },
    {
        "key": "forest_2",
        "title": "Deep Forest 🌿 | 4K Dense Woodland | Nature Meditation | SERENE",
        "description": desc("Deep Forest", "Forest", "meditative",
            "A deep, ancient forest — dense canopy and peaceful silence in 4K."),
        "tags": ["deep forest","woodland","nature","4k","ambient","meditation","trees","green","relax","peaceful"],
        "src": hd("13234202", "24"),
    },
    {
        "key": "forest_3",
        "title": "Forest Path 🌿 | 4K Nature Trail | Walking Ambience | SERENE",
        "description": desc("Forest Path", "Forest", "peaceful",
            "A winding forest path leading into the trees — peaceful nature walk in 4K."),
        "tags": ["forest path","nature trail","walking","4k","ambient","peaceful","nature","trees","relaxing","study"],
        "src": hd("14050551", "24"),
    },
    {
        "key": "forest_4",
        "title": "Woodland 🌿 | 4K Forest Ambience | Nature Background | SERENE",
        "description": desc("Woodland", "Forest", "calm",
            "A serene woodland scene — gently swaying branches and filtered light in 4K."),
        "tags": ["woodland","forest","nature","4k","ambient","calm","trees","relaxing","background","green"],
        "src": hd("2711092", "24"),
    },
    {
        "key": "forest_5",
        "title": "Forest Mist 🌿 | 4K Misty Forest | Atmospheric Nature Loop | SERENE",
        "description": desc("Forest Mist", "Forest", "atmospheric",
            "Morning mist rolling through an ancient forest — ethereal and calming in 4K."),
        "tags": ["forest mist","misty forest","fog","4k","ambient","atmospheric","nature","mystery","meditation","ethereal"],
        "src": hd("13210975", "24"),
    },

    # ── WINTER ───────────────────────────────────────────────────────────────
    {
        "key": "winter_1",
        "title": "Falling Snow ❄️ | 4K Snowfall | Winter Relaxation Ambience | SERENE",
        "description": desc("Falling Snow", "Winter", "peaceful",
            "Gentle snowflakes falling in soft 4K — the most peaceful winter ambience."),
        "tags": ["falling snow","snowfall","winter","4k","ambient","relaxing","peaceful","snow sounds","meditation","sleep"],
        "src": hd("19887145", "24"),
    },
    {
        "key": "winter_2",
        "title": "Snowy Forest ❄️ | 4K Winter Forest | Snow & Nature Ambience | SERENE",
        "description": desc("Snowy Forest", "Winter", "winter",
            "A snow-covered forest in perfect winter stillness — pure silence in 4K."),
        "tags": ["snowy forest","winter forest","snow","4k","ambient","nature","winter","peaceful","relaxing","meditation"],
        "src": hd("19493013", "30"),
    },
    {
        "key": "winter_3",
        "title": "Winter Calm ❄️ | 4K Peaceful Snowscape | Mindfulness Background | SERENE",
        "description": desc("Winter Calm", "Winter", "mindfulness",
            "A perfectly calm winter landscape blanketed in fresh snow — 4K serenity."),
        "tags": ["winter calm","snowscape","peaceful","4k","ambient","mindfulness","meditation","relax","snow","background"],
        "src": hd("10697994", "30"),
    },
    {
        "key": "winter_4",
        "title": "Alpine Snow ❄️ | 4K Mountain Winter | Drone Snow Ambience | SERENE",
        "description": desc("Alpine Snow", "Winter", "alpine",
            "Sweeping aerial views of alpine peaks wrapped in snow — breathtaking 4K."),
        "tags": ["alpine snow","mountain","drone","winter","4k","ambient","aerial","snow","relaxing","nature"],
        "src": hd("19491958", "30"),
    },
    {
        "key": "winter_5",
        "title": "Cold Forest ❄️ | 4K Winter Woodland | Frost & Snow Ambience | SERENE",
        "description": desc("Cold Forest", "Winter", "frost",
            "A frost-covered forest on a silent winter morning — crisp 4K beauty."),
        "tags": ["cold forest","frost","winter woodland","4k","ambient","relaxing","snow","nature","peaceful","study"],
        "src": hd("19642768", "30"),
    },

    # ── STARS ────────────────────────────────────────────────────────────────
    {
        "key": "stars_1",
        "title": "Milky Way 🌌 | 4K Night Sky | Relaxing Space Ambience | SERENE",
        "description": desc("Milky Way", "Stars", "cosmic",
            "The full sweep of the Milky Way galaxy captured in breathtaking 4K."),
        "tags": ["milky way","night sky","galaxy","4k","space","ambient","stars","cosmic","relaxing","meditation","astrophotography"],
        "src": hd("29238178", "24"),
    },
    {
        "key": "stars_2",
        "title": "Star Field 🌌 | 4K Starry Night | Deep Space Background | SERENE",
        "description": desc("Star Field", "Stars", "deep space",
            "An infinite field of stars fills the 4K frame — pure cosmic wonder."),
        "tags": ["star field","starry night","space","4k","ambient","stars","deep space","relaxing","meditation","cosmic"],
        "src": hd("29357730", "24"),
    },
    {
        "key": "stars_3",
        "title": "Galaxy 🌌 | 4K Galaxy View | Space Meditation Ambience | SERENE",
        "description": desc("Galaxy", "Stars", "meditative",
            "A sweeping view of a galaxy arm — the universe in stunning 4K Ultra HD."),
        "tags": ["galaxy","cosmos","space","4k","ambient","meditation","stars","universe","relaxing","sleep"],
        "src": hd("9557868", "24"),
    },
    {
        "key": "stars_4",
        "title": "Night Sky 🌌 | 4K Clear Star Night | Peaceful Astronomy Ambience | SERENE",
        "description": desc("Night Sky", "Stars", "peaceful",
            "A crystal-clear night sky packed with stars — peaceful and humbling in 4K."),
        "tags": ["night sky","stars","astronomy","4k","ambient","peaceful","relaxing","meditation","cosmos","background"],
        "src": hd("32901084", "25", "3240", "2160"),
    },
    {
        "key": "stars_5",
        "title": "Star Timelapse 🌌 | 4K Astro Timelapse | Rotating Night Sky | SERENE",
        "description": desc("Astro Timelapse", "Stars", "timelapse",
            "The night sky rotating above the horizon in a stunning 4K astronomical timelapse."),
        "tags": ["star timelapse","astro timelapse","night sky","4k","ambient","timelapse","stars","space","cosmos","relaxing"],
        "src": hd("27775202", "25", "3240", "2160"),
    },

    # ── ABSTRACT ─────────────────────────────────────────────────────────────
    {
        "key": "abstract_1",
        "title": "Neon Flow ✨ | 4K Abstract Neon | Visual Meditation Loop | SERENE",
        "description": desc("Neon Flow", "Abstract", "visual",
            "Flowing neon light streams in vibrant 4K — hypnotic visual meditation."),
        "tags": ["neon flow","abstract","neon","4k","visual","ambient","hypnotic","satisfying","meditation","loop","psychedelic"],
        "src": hd("14203831", "60"),
    },
    {
        "key": "abstract_2",
        "title": "Smoke Art ✨ | 4K Abstract Smoke | Artistic Ambient Loop | SERENE",
        "description": desc("Smoke Art", "Abstract", "artistic",
            "Smoke curling into beautiful abstract forms — mesmerising art in 4K Ultra HD."),
        "tags": ["smoke art","abstract smoke","4k","artistic","ambient","satisfying","loop","visual art","relaxing","asmr"],
        "src": hd("10004412", "30", "4096", "2160"),
    },
    {
        "key": "abstract_3",
        "title": "Fluid Colors ✨ | 4K Fluid Art | Satisfying Color Flow | SERENE",
        "description": desc("Fluid Colors", "Abstract", "satisfying",
            "Swirling fluid paint in vivid colors — the most satisfying 4K loop."),
        "tags": ["fluid art","fluid colors","satisfying","4k","abstract","ambient","paint","color flow","relaxing","hypnotic"],
        "src": hd("7670835", "30"),
    },
    {
        "key": "abstract_4",
        "title": "Geometric Art ✨ | 4K 3D Geometry | Abstract Digital Background | SERENE",
        "description": desc("Geometric", "Abstract", "digital",
            "Precision geometric forms morphing in 4K — the intersection of art and math."),
        "tags": ["geometric art","3d geometry","abstract","4k","digital art","ambient","loop","visual","satisfying","modern"],
        "src": hd("16685801", "30"),
    },
    {
        "key": "abstract_5",
        "title": "Liquid Art ✨ | 4K Acrylic Pour | Satisfying Abstract Loop | SERENE",
        "description": desc("Liquid Art", "Abstract", "satisfying",
            "Acrylic paint pouring and spreading in breathtaking 4K macro detail."),
        "tags": ["liquid art","acrylic pour","satisfying","4k","abstract","ambient","paint","visual art","asmr","hypnotic"],
        "src": hd("7126521", "30", "4096", "2160"),
    },
    {
        "key": "abstract_6",
        "title": "Abstract Loop ✨ | 4K Motion Graphics | Visual Ambient Background | SERENE",
        "description": desc("Abstract Loop", "Abstract", "motion",
            "Dynamic abstract motion graphics looping seamlessly in crisp 4K."),
        "tags": ["abstract loop","motion graphics","4k","abstract","ambient","visual","loop","digital","satisfying","modern"],
        "src": hd("10916595", "30"),
    },
    {
        "key": "abstract_7",
        "title": "Neon Waves ✨ | 4K Neon Abstract | Cyber Ambience Background | SERENE",
        "description": desc("Neon Waves", "Abstract", "cyber",
            "Electric neon waves pulsing through 4K space — cyberpunk ambient background."),
        "tags": ["neon waves","cyber","neon abstract","4k","ambient","cyberpunk","loop","visual","futuristic","satisfying"],
        "src": hd("15439669", "30"),
    },
]


# ── YOUTUBE API ───────────────────────────────────────────────────────────────

def get_youtube():
    try:
        from googleapiclient.discovery import build
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.oauth2.credentials import Credentials
        import google.auth.transport.requests
    except ImportError:
        print("Install deps: pip install google-api-python-client google-auth-oauthlib")
        sys.exit(1)

    SCOPES = ['https://www.googleapis.com/auth/youtube']
    creds = None

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
        else:
            if not os.path.exists('client_secrets.json'):
                print("\n❌  client_secrets.json not found.")
                print("   1. Go to https://console.cloud.google.com")
                print("   2. Enable YouTube Data API v3")
                print("   3. Create OAuth 2.0 Desktop credentials")
                print("   4. Download as client_secrets.json into this folder")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as f:
            f.write(creds.to_json())

    return build('youtube', 'v3', credentials=creds)


def create_broadcast(yt, video):
    # Schedule 1 min from now so it's immediately startable
    start = (datetime.now(timezone.utc) + timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M:%SZ')

    broadcast = yt.liveBroadcasts().insert(
        part="snippet,status,contentDetails",
        body={
            "snippet": {
                "title": video["title"],
                "description": video["description"],
                "scheduledStartTime": start,
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
                "madeForKids": False,
            },
            "contentDetails": {
                "enableAutoStart": True,
                "enableAutoStop": False,
                "enableDvr": False,
                "recordFromStart": False,
            }
        }
    ).execute()

    stream = yt.liveStreams().insert(
        part="snippet,cdn",
        body={
            "snippet": {"title": video["title"]},
            "cdn": {
                "frameRate": "30fps",
                "resolution": "1080p",
                "ingestionType": "rtmp",
            }
        }
    ).execute()

    yt.liveBroadcasts().bind(
        part="id,contentDetails",
        id=broadcast["id"],
        streamId=stream["id"]
    ).execute()

    # Set tags (separate API call for video update)
    yt.videos().update(
        part="snippet",
        body={
            "id": broadcast["id"],
            "snippet": {
                "title": video["title"],
                "description": video["description"],
                "tags": video["tags"],
                "categoryId": "22",  # People & Blogs
                "defaultLanguage": "en",
            }
        }
    ).execute()

    rtmp = stream["cdn"]["ingestionInfo"]["ingestionAddress"]
    key  = stream["cdn"]["ingestionInfo"]["streamName"]
    return broadcast["id"], f"{rtmp}/{key}"


def ffmpeg_cmd(src_url, rtmp_endpoint):
    return (
        f'ffmpeg -stream_loop -1 -re \\\n'
        f'  -i "{src_url}" \\\n'
        f'  -vf "scale=1920:1080,setsar=1" \\\n'
        f'  -c:v libx264 -preset veryfast -b:v 4500k -maxrate 4500k -bufsize 9000k \\\n'
        f'  -g 60 -keyint_min 60 \\\n'
        f'  -c:a aac -b:a 128k -ar 44100 -ac 2 \\\n'
        f'  -f flv "{rtmp_endpoint}"'
    )


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print("\n🎬  SERENE — YouTube Stream Creator")
    print(f"    {len(VIDEOS)} videos to broadcast\n")

    yt = get_youtube()
    results = []

    for i, v in enumerate(VIDEOS, 1):
        print(f"[{i:02d}/{len(VIDEOS)}] Creating: {v['title'][:60]}...")
        try:
            broadcast_id, rtmp = create_broadcast(yt, v)
            cmd = ffmpeg_cmd(v["src"], rtmp)
            results.append({
                "key": v["key"],
                "title": v["title"],
                "broadcast_id": broadcast_id,
                "youtube_url": f"https://youtu.be/{broadcast_id}",
                "src": v["src"],
                "ffmpeg": cmd,
            })
            print(f"    ✓  https://youtu.be/{broadcast_id}")
        except Exception as e:
            print(f"    ✗  Error: {e}")

    # Save results
    with open('streams_output.json', 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Generate shell script to start all streams
    with open('start_all_streams.sh', 'w') as f:
        f.write("#!/bin/bash\n# Run each stream in background\n\n")
        for r in results:
            cmd_oneliner = r['ffmpeg'].replace('\n', ' ').replace('\\', '').replace('  ', ' ')
            f.write(f"# {r['title']}\n")
            f.write(f"nohup {cmd_oneliner} > logs/{r['key']}.log 2>&1 &\n\n")

    print(f"\n✅  Done! {len(results)}/{len(VIDEOS)} streams created.")
    print(f"   → streams_output.json  (broadcast IDs + FFmpeg commands)")
    print(f"   → start_all_streams.sh (run all streams at once)")
    print(f"\n   To start a single stream, copy the ffmpeg command from streams_output.json")
    print(f"   To start all:  bash start_all_streams.sh\n")


if __name__ == "__main__":
    main()
