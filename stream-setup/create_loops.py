#!/usr/bin/env python3
"""
SERENE — YouTube 10-Hour Loop Creator
======================================
For each ambient video:
  1. Downloads from Pexels (1080p)
  2. Creates a 10-hour seamless loop (no re-encoding — fast!)
  3. Uploads to YouTube with SEO title & description
  4. Deletes local files to save disk space
  5. Moves on to the next video

Run on Hetzner server:
  pip install google-api-python-client google-auth-oauthlib
  python3 create_loops.py

Requires: ffmpeg, ffprobe, client_secrets.json or token.json
"""

import json
import math
import os
import subprocess
import sys
import time

LOOP_DURATION_HOURS = 10
LOOP_SECONDS = LOOP_DURATION_HOURS * 3600

# ── VIDEO DATA ────────────────────────────────────────────────────────────────

BASE = "https://videos.pexels.com/video-files/"

def hd(vid_id, fps, w="1920", h="1080"):
    return f"{BASE}{vid_id}/{vid_id}-hd_{w}_{h}_{fps}fps.mp4"

def desc(scene, category, scene_desc):
    return f"""{scene} | {LOOP_DURATION_HOURS}-Hour Ambient Loop

{scene_desc}

Perfect for focus, deep work, studying, meditation, relaxation, and sleep. Plays for {LOOP_DURATION_HOURS} hours without interruption.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
♾ {LOOP_DURATION_HOURS} Hours · No Ads · 🎧 Best with headphones · Full HD 1080p
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌐 More scenes: https://www.calm-veritas.com

Video source: Pexels (pexels.com/license)

#{category.lower()} #ambient #relaxing #lofi #study #sleep #meditation #backgroundvideo #{LOOP_DURATION_HOURS}hours #serene"""

VIDEOS = [
    # ── OCEAN ─────────────────────────────────────────────────────────────────
    {
        "key": "ocean_1",
        "title": f"Deep Ocean Waves 🌊 | {LOOP_DURATION_HOURS}-Hour Ambient | Relaxing Sea Sounds | 4K Loop",
        "description": desc("Deep Ocean Waves", "Ocean",
            "Endless deep ocean waves rolling to shore — immersive sea ambience for relaxation and focus."),
        "tags": ["ocean waves","10 hours","ambient","relaxing","sea sounds","study","sleep","meditation","lofi","4k","wave sounds","ocean ambience"],
        "src": hd("16727103", "60"),
    },
    {
        "key": "ocean_2",
        "title": f"Aerial Beach 🌊 | {LOOP_DURATION_HOURS}-Hour 4K Drone Ocean | Peaceful Ambience Loop",
        "description": desc("Aerial Beach", "Ocean",
            "Stunning aerial drone footage over a pristine beach and crystal-clear water — peaceful and serene."),
        "tags": ["aerial beach","drone","ocean","10 hours","ambient","relaxing","beach","coastal","peaceful","4k"],
        "src": hd("29052984", "30"),
    },
    {
        "key": "ocean_3",
        "title": f"Breaking Surf 🌊 | {LOOP_DURATION_HOURS}-Hour Ocean Waves | Study & Relax Loop",
        "description": desc("Breaking Surf", "Ocean",
            "Powerful waves breaking on the shore — energising ocean ambience for deep focus and study."),
        "tags": ["breaking waves","surf","ocean","10 hours","ambient","study","relax","wave sounds","beach","focus"],
        "src": hd("6624689", "25"),
    },
    {
        "key": "ocean_4",
        "title": f"Open Sea 🌊 | {LOOP_DURATION_HOURS}-Hour Endless Ocean | Calm Ambient Loop",
        "description": desc("Open Sea", "Ocean",
            "The vast open sea stretching endlessly to the horizon — pure calm and clarity."),
        "tags": ["open sea","ocean","horizon","10 hours","ambient","relaxing","calm","meditation","peaceful","4k"],
        "src": hd("3446616", "25"),
    },
    {
        "key": "ocean_5",
        "title": f"Tropical Shore 🌊 | {LOOP_DURATION_HOURS}-Hour Paradise Beach | Ambient Loop",
        "description": desc("Tropical Shore", "Ocean",
            "Crystal-clear tropical waters on a white sand beach — pure paradise ambience."),
        "tags": ["tropical beach","paradise","crystal water","10 hours","ambient","relaxing","beach","tropical","calm","4k"],
        "src": hd("33840319", "30"),
    },
    {
        "key": "ocean_6",
        "title": f"Wave Close-Up 🌊 | {LOOP_DURATION_HOURS}-Hour Satisfying Water Loop | Ocean Ambience",
        "description": desc("Wave Close-up", "Ocean",
            "A mesmerising close-up of ocean waves — water texture in hypnotic looping detail."),
        "tags": ["wave closeup","macro water","ocean","10 hours","satisfying","ambient","relaxing","asmr","meditative","loop"],
        "src": hd("32760161", "30"),
    },

    # ── FIRE ──────────────────────────────────────────────────────────────────
    {
        "key": "fire_1",
        "title": f"Winter Fireplace 🔥 | {LOOP_DURATION_HOURS}-Hour Cozy Fire | Crackling Ambience Loop",
        "description": desc("Winter Fireplace", "Fire",
            "A warm crackling fireplace on a snowy evening — the ultimate cozy winter ambience."),
        "tags": ["fireplace","crackling fire","cozy","winter","10 hours","ambient","relaxing","fire sounds","asmr","sleep","hygge"],
        "src": hd("35481118", "30"),
    },
    {
        "key": "fire_2",
        "title": f"Indoor Fireplace 🔥 | {LOOP_DURATION_HOURS}-Hour Warm Fire | Study & Sleep Loop",
        "description": desc("Indoor Fire", "Fire",
            "A beautifully lit indoor fireplace casting warm amber light — perfect for study and sleep."),
        "tags": ["indoor fireplace","warm fire","10 hours","ambient","study","relax","fire","cozy room","lofi","sleep"],
        "src": hd("6984877", "24"),
    },
    {
        "key": "fire_3",
        "title": f"Open Flame 🔥 | {LOOP_DURATION_HOURS}-Hour Bonfire Ambience | Outdoor Fire Loop",
        "description": desc("Open Flame", "Fire",
            "A raw open flame burning brightly — elemental fire ambience for relaxation and meditation."),
        "tags": ["open flame","bonfire","fire","10 hours","ambient","outdoor","camping","nature","relaxing","meditation"],
        "src": hd("11353677", "30"),
    },
    {
        "key": "fire_4",
        "title": f"Bonfire Night 🔥 | {LOOP_DURATION_HOURS}-Hour Campfire | Night Outdoor Ambience Loop",
        "description": desc("Bonfire Night", "Fire",
            "A roaring bonfire under the night sky — warmth and crackling stars all night long."),
        "tags": ["bonfire night","campfire","night fire","10 hours","ambient","outdoor","camping","relaxing","sleep"],
        "src": hd("17062878", "24"),
    },
    {
        "key": "fire_5",
        "title": f"Glowing Embers 🔥 | {LOOP_DURATION_HOURS}-Hour Fire Embers | Deep Relaxation Loop",
        "description": desc("Glowing Embers", "Fire",
            "Slowly glowing and fading embers — hypnotic fire ambience for deep relaxation and sleep."),
        "tags": ["fire embers","glowing","10 hours","ambient","meditative","relaxing","hypnotic","asmr","sleep"],
        "src": hd("31055868", "25"),
    },

    # ── RAIN ──────────────────────────────────────────────────────────────────
    {
        "key": "rain_1",
        "title": f"Rain on Window 🌧 | {LOOP_DURATION_HOURS}-Hour Rainy Day | Study & Focus Ambience",
        "description": desc("Rainy Window", "Rain",
            "Raindrops streaking down a window — the classic study and deep focus background."),
        "tags": ["rain on window","rainy day","10 hours","study","focus","ambient","rain sounds","asmr","relaxing","cozy"],
        "src": hd("15454042", "25"),
    },
    {
        "key": "rain_2",
        "title": f"Autumn Rain 🌧 | {LOOP_DURATION_HOURS}-Hour Fall Rainfall | Cozy Ambience Loop",
        "description": desc("Autumn Rain", "Rain",
            "Soft autumn rain falling on golden leaves — the coziest seasonal ambience."),
        "tags": ["autumn rain","fall rain","10 hours","ambient","cozy","rainy day","seasonal","study","lofi"],
        "src": hd("5197762", "25"),
    },
    {
        "key": "rain_3",
        "title": f"City Rain 🌧 | {LOOP_DURATION_HOURS}-Hour Urban Rainfall | Night City Ambience Loop",
        "description": desc("City Rain", "Rain",
            "Rain falling on city streets at night — moody urban ambience for work and relaxation."),
        "tags": ["city rain","urban rain","night city","10 hours","ambient","moody","street","relaxing","lofi","study"],
        "src": hd("28628298", "25"),
    },
    {
        "key": "rain_4",
        "title": f"Heavy Rain 🌧 | {LOOP_DURATION_HOURS}-Hour Downpour | Deep Focus Ambience Loop",
        "description": desc("Heavy Rain", "Rain",
            "A powerful rainstorm — immersive and deeply relaxing for focus and sleep."),
        "tags": ["heavy rain","downpour","10 hours","ambient","deep focus","study","rainstorm","sleep sounds","asmr","meditation"],
        "src": hd("13619802", "60"),
    },
    {
        "key": "rain_5",
        "title": f"Rain on Glass 🌧 | {LOOP_DURATION_HOURS}-Hour Water Drops | Satisfying Rain Loop",
        "description": desc("Rain on Glass", "Rain",
            "Raindrops on glass in hypnotic macro detail — endlessly satisfying and calming."),
        "tags": ["rain on glass","water drops","macro rain","10 hours","satisfying","ambient","asmr","relaxing","meditative"],
        "src": hd("6520303", "30"),
    },

    # ── FOREST ────────────────────────────────────────────────────────────────
    {
        "key": "forest_1",
        "title": f"Forest Light 🌿 | {LOOP_DURATION_HOURS}-Hour Sunlit Forest | Nature Ambience Loop",
        "description": desc("Forest Light", "Forest",
            "Dappled sunlight filtering through a lush forest canopy — pure nature therapy."),
        "tags": ["forest light","sunlit forest","nature","10 hours","ambient","relaxing","trees","woodland","meditation"],
        "src": hd("35982732", "25"),
    },
    {
        "key": "forest_2",
        "title": f"Deep Forest 🌿 | {LOOP_DURATION_HOURS}-Hour Dense Woodland | Nature Meditation Loop",
        "description": desc("Deep Forest", "Forest",
            "A deep ancient forest with dense canopy and peaceful silence — nature at its most serene."),
        "tags": ["deep forest","woodland","nature","10 hours","ambient","meditation","trees","green","relax","peaceful"],
        "src": hd("13234202", "24"),
    },
    {
        "key": "forest_3",
        "title": f"Forest Path 🌿 | {LOOP_DURATION_HOURS}-Hour Nature Trail | Peaceful Walk Ambience",
        "description": desc("Forest Path", "Forest",
            "A winding forest path leading into the trees — a peaceful walk through nature."),
        "tags": ["forest path","nature trail","walking","10 hours","ambient","peaceful","nature","trees","relaxing"],
        "src": hd("14050551", "24"),
    },
    {
        "key": "forest_4",
        "title": f"Woodland 🌿 | {LOOP_DURATION_HOURS}-Hour Forest Ambience | Calm Nature Background Loop",
        "description": desc("Woodland", "Forest",
            "A serene woodland scene — gently swaying branches and filtered light for hours."),
        "tags": ["woodland","forest","nature","10 hours","ambient","calm","trees","relaxing","background","green"],
        "src": hd("2711092", "24"),
    },
    {
        "key": "forest_5",
        "title": f"Forest Mist 🌿 | {LOOP_DURATION_HOURS}-Hour Misty Forest | Atmospheric Loop",
        "description": desc("Forest Mist", "Forest",
            "Morning mist rolling through an ancient forest — ethereal, calming, and otherworldly."),
        "tags": ["forest mist","misty forest","fog","10 hours","ambient","atmospheric","nature","meditation","ethereal"],
        "src": hd("13210975", "24"),
    },

    # ── WINTER ────────────────────────────────────────────────────────────────
    {
        "key": "winter_1",
        "title": f"Falling Snow ❄️ | {LOOP_DURATION_HOURS}-Hour Snowfall | Winter Relaxation Loop",
        "description": desc("Falling Snow", "Winter",
            "Gentle snowflakes falling in soft silence — the most peaceful winter ambience."),
        "tags": ["falling snow","snowfall","winter","10 hours","ambient","relaxing","peaceful","snow","meditation","sleep"],
        "src": hd("19887145", "24"),
    },
    {
        "key": "winter_2",
        "title": f"Snowy Forest ❄️ | {LOOP_DURATION_HOURS}-Hour Winter Forest | Snow & Nature Loop",
        "description": desc("Snowy Forest", "Winter",
            "A snow-covered forest in perfect winter stillness — pure silence and serenity."),
        "tags": ["snowy forest","winter forest","snow","10 hours","ambient","nature","peaceful","relaxing","meditation"],
        "src": hd("19493013", "30"),
    },
    {
        "key": "winter_3",
        "title": f"Winter Calm ❄️ | {LOOP_DURATION_HOURS}-Hour Peaceful Snowscape | Mindfulness Loop",
        "description": desc("Winter Calm", "Winter",
            "A perfectly calm winter landscape blanketed in fresh snow — serenity in stillness."),
        "tags": ["winter calm","snowscape","peaceful","10 hours","ambient","mindfulness","meditation","relax","snow"],
        "src": hd("10697994", "30"),
    },
    {
        "key": "winter_4",
        "title": f"Alpine Snow ❄️ | {LOOP_DURATION_HOURS}-Hour Mountain Winter | Drone Snow Loop",
        "description": desc("Alpine Snow", "Winter",
            "Sweeping aerial views of alpine peaks wrapped in snow — breathtaking winter grandeur."),
        "tags": ["alpine snow","mountain","drone","winter","10 hours","ambient","aerial","snow","relaxing","nature"],
        "src": hd("19491958", "30"),
    },
    {
        "key": "winter_5",
        "title": f"Cold Forest ❄️ | {LOOP_DURATION_HOURS}-Hour Winter Woodland | Frost Ambience Loop",
        "description": desc("Cold Forest", "Winter",
            "A frost-covered forest on a silent winter morning — crisp, beautiful, and still."),
        "tags": ["cold forest","frost","winter woodland","10 hours","ambient","relaxing","snow","nature","peaceful"],
        "src": hd("19642768", "30"),
    },

    # ── STARS ─────────────────────────────────────────────────────────────────
    {
        "key": "stars_1",
        "title": f"Milky Way 🌌 | {LOOP_DURATION_HOURS}-Hour Night Sky | Space Ambience Loop",
        "description": desc("Milky Way", "Stars",
            "The full sweep of the Milky Way galaxy — cosmic wonder for relaxation and sleep."),
        "tags": ["milky way","night sky","galaxy","10 hours","space","ambient","stars","cosmic","relaxing","meditation"],
        "src": hd("29238178", "24"),
    },
    {
        "key": "stars_2",
        "title": f"Star Field 🌌 | {LOOP_DURATION_HOURS}-Hour Starry Night | Deep Space Loop",
        "description": desc("Star Field", "Stars",
            "An infinite field of stars fills the frame — pure cosmic wonder for sleep and meditation."),
        "tags": ["star field","starry night","space","10 hours","ambient","stars","deep space","relaxing","meditation"],
        "src": hd("29357730", "24"),
    },
    {
        "key": "stars_3",
        "title": f"Galaxy 🌌 | {LOOP_DURATION_HOURS}-Hour Galaxy View | Space Meditation Loop",
        "description": desc("Galaxy", "Stars",
            "A sweeping view of a galaxy — the entire universe visible for meditation and sleep."),
        "tags": ["galaxy","cosmos","space","10 hours","ambient","meditation","stars","universe","relaxing","sleep"],
        "src": hd("9557868", "24"),
    },
    {
        "key": "stars_4",
        "title": f"Night Sky 🌌 | {LOOP_DURATION_HOURS}-Hour Clear Stars | Astronomy Ambience Loop",
        "description": desc("Night Sky", "Stars",
            "A crystal-clear night sky packed with stars — peaceful, humbling, and beautiful."),
        "tags": ["night sky","stars","astronomy","10 hours","ambient","peaceful","relaxing","meditation","cosmos"],
        "src": hd("32901084", "25", "3240", "2160"),
    },
    {
        "key": "stars_5",
        "title": f"Star Timelapse 🌌 | {LOOP_DURATION_HOURS}-Hour Astro Timelapse | Rotating Sky Loop",
        "description": desc("Astro Timelapse", "Stars",
            "The night sky rotating above the horizon — a stunning astronomical timelapse for sleep."),
        "tags": ["star timelapse","astro","night sky","10 hours","ambient","timelapse","stars","space","cosmos","relaxing"],
        "src": hd("27775202", "25", "3240", "2160"),
    },

    # ── ABSTRACT ──────────────────────────────────────────────────────────────
    {
        "key": "abstract_1",
        "title": f"Neon Flow ✨ | {LOOP_DURATION_HOURS}-Hour Abstract Neon | Visual Meditation Loop",
        "description": desc("Neon Flow", "Abstract",
            "Flowing neon light streams — hypnotic visual meditation for focus and creativity."),
        "tags": ["neon flow","abstract","neon","10 hours","visual","ambient","hypnotic","satisfying","meditation","loop"],
        "src": hd("14203831", "60"),
    },
    {
        "key": "abstract_2",
        "title": f"Smoke Art ✨ | {LOOP_DURATION_HOURS}-Hour Abstract Smoke | Artistic Ambient Loop",
        "description": desc("Smoke Art", "Abstract",
            "Smoke curling into beautiful abstract forms — mesmerising art in motion."),
        "tags": ["smoke art","abstract smoke","10 hours","artistic","ambient","satisfying","loop","visual art","relaxing"],
        "src": hd("10004412", "30", "4096", "2160"),
    },
    {
        "key": "abstract_3",
        "title": f"Fluid Colors ✨ | {LOOP_DURATION_HOURS}-Hour Fluid Art | Satisfying Color Loop",
        "description": desc("Fluid Colors", "Abstract",
            "Swirling fluid paint in vivid colors — the most satisfying and hypnotic loop."),
        "tags": ["fluid art","fluid colors","satisfying","10 hours","abstract","ambient","paint","color flow","relaxing"],
        "src": hd("7670835", "30"),
    },
    {
        "key": "abstract_4",
        "title": f"Geometric Art ✨ | {LOOP_DURATION_HOURS}-Hour 3D Geometry | Abstract Digital Loop",
        "description": desc("Geometric", "Abstract",
            "Precision geometric forms morphing in digital space — the intersection of art and mathematics."),
        "tags": ["geometric art","3d geometry","abstract","10 hours","digital art","ambient","loop","visual","satisfying"],
        "src": hd("16685801", "30"),
    },
    {
        "key": "abstract_5",
        "title": f"Liquid Art ✨ | {LOOP_DURATION_HOURS}-Hour Acrylic Pour | Satisfying Abstract Loop",
        "description": desc("Liquid Art", "Abstract",
            "Acrylic paint pouring and spreading in breathtaking macro detail — pure satisfaction."),
        "tags": ["liquid art","acrylic pour","satisfying","10 hours","abstract","ambient","paint","visual art","asmr"],
        "src": hd("7126521", "30", "4096", "2160"),
    },
    {
        "key": "abstract_6",
        "title": f"Abstract Loop ✨ | {LOOP_DURATION_HOURS}-Hour Motion Graphics | Visual Ambient Background",
        "description": desc("Abstract Loop", "Abstract",
            "Dynamic abstract motion graphics looping seamlessly — modern visual ambience."),
        "tags": ["abstract loop","motion graphics","10 hours","abstract","ambient","visual","loop","digital","satisfying"],
        "src": hd("10916595", "30"),
    },
    {
        "key": "abstract_7",
        "title": f"Neon Waves ✨ | {LOOP_DURATION_HOURS}-Hour Neon Abstract | Cyber Ambience Loop",
        "description": desc("Neon Waves", "Abstract",
            "Electric neon waves pulsing through space — cyberpunk ambient background for focus."),
        "tags": ["neon waves","cyber","neon abstract","10 hours","ambient","cyberpunk","loop","visual","futuristic"],
        "src": hd("15439669", "30"),
    },
]


# ── HELPERS ───────────────────────────────────────────────────────────────────

def run(cmd, desc=""):
    print(f"  ▶ {desc or cmd[:80]}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ Error: {result.stderr[:200]}")
        return False
    return True

def get_duration(path):
    result = subprocess.run(
        f'ffprobe -v error -show_entries format=duration -of csv=p=0 "{path}"',
        shell=True, capture_output=True, text=True
    )
    try:
        return float(result.stdout.strip())
    except Exception:
        return 30.0  # fallback

def make_loop(src_url, output_path, key):
    tmp = f"/tmp/{key}_src.mp4"

    # 1. Download original
    print(f"  ↓ Downloading...")
    ok = run(f'ffmpeg -y -i "{src_url}" -c copy "{tmp}" 2>/dev/null || '
             f'ffmpeg -y -user_agent "Mozilla/5.0" -i "{src_url}" -c copy "{tmp}"',
             "Download video")
    if not ok or not os.path.exists(tmp):
        return False

    # 2. Get duration, calculate repeats
    dur = get_duration(tmp)
    repeats = math.ceil(LOOP_SECONDS / dur) + 1
    print(f"  ↻ Duration: {dur:.1f}s → need {repeats}× repeat for {LOOP_DURATION_HOURS}h")

    # 3. Build concat list
    concat_file = f"/tmp/{key}_concat.txt"
    with open(concat_file, "w") as f:
        for _ in range(repeats):
            f.write(f"file '{tmp}'\n")

    # 4. Concat without re-encoding (fast!), trim to exact duration
    print(f"  ⟳ Building {LOOP_DURATION_HOURS}-hour loop (no re-encoding)...")
    ok = run(
        f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" '
        f'-t {LOOP_SECONDS} -c copy "{output_path}"',
        f"Create {LOOP_DURATION_HOURS}h loop"
    )

    # Cleanup temp files
    os.remove(tmp)
    os.remove(concat_file)
    return ok and os.path.exists(output_path)


# ── YOUTUBE ───────────────────────────────────────────────────────────────────

def get_youtube():
    try:
        from googleapiclient.discovery import build
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.oauth2.credentials import Credentials
        import google.auth.transport.requests
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        print("Run: pip install google-api-python-client google-auth-oauthlib")
        sys.exit(1)

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
              "https://www.googleapis.com/auth/youtube"]
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
        else:
            if not os.path.exists("client_secrets.json"):
                print("\n❌  client_secrets.json not found. See SETUP.txt\n")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())

    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=creds)


def upload_video(yt, video, file_path):
    from googleapiclient.http import MediaFileUpload

    file_size_gb = os.path.getsize(file_path) / 1e9
    print(f"  ↑ Uploading {file_size_gb:.1f}GB to YouTube...")

    body = {
        "snippet": {
            "title": video["title"],
            "description": video["description"],
            "tags": video["tags"],
            "categoryId": "22",
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            "madeForKids": False,
        }
    }

    media = MediaFileUpload(file_path, chunksize=10*1024*1024, resumable=True)
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    last_pct = -1
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            if pct != last_pct:
                print(f"  ↑ {pct}%", end="\r")
                last_pct = pct

    vid_id = response.get("id")
    print(f"  ✓ Uploaded: https://youtu.be/{vid_id}   ")
    return vid_id


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n🎬  SERENE — {LOOP_DURATION_HOURS}-Hour Loop Creator")
    print(f"    {len(VIDEOS)} videos · {LOOP_DURATION_HOURS}h each\n")

    yt = get_youtube()
    results = []
    os.makedirs("completed", exist_ok=True)

    # Skip already completed videos
    done = set()
    if os.path.exists("completed/done.json"):
        with open("completed/done.json") as f:
            done = set(json.load(f))

    for i, v in enumerate(VIDEOS, 1):
        if v["key"] in done:
            print(f"[{i:02d}/{len(VIDEOS)}] ✓ Already done: {v['key']}")
            continue

        print(f"\n[{i:02d}/{len(VIDEOS)}] {v['title'][:65]}...")

        output = f"/tmp/{v['key']}_10h.mp4"

        # Create loop
        ok = make_loop(v["src"], output, v["key"])
        if not ok:
            print(f"  ✗ Skipping — could not create loop")
            continue

        # Upload
        try:
            vid_id = upload_video(yt, v, output)
            results.append({"key": v["key"], "title": v["title"],
                            "youtube_url": f"https://youtu.be/{vid_id}"})
            done.add(v["key"])
            with open("completed/done.json", "w") as f:
                json.dump(list(done), f)
        except Exception as e:
            print(f"  ✗ Upload failed: {e}")
        finally:
            if os.path.exists(output):
                os.remove(output)
                print(f"  🗑  Local file deleted")

        # Small pause between uploads
        time.sleep(3)

    # Save final results
    with open("completed/youtube_links.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✅  Done! {len(results)} videos uploaded.")
    print(f"   → completed/youtube_links.json\n")


if __name__ == "__main__":
    main()
