import asyncio
import json
import os
import random
import subprocess
import textwrap
from pathlib import Path

import edge_tts
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
VOICE = os.getenv("TTS_VOICE", "hi-IN-MadhurNeural")
FONT_PATH = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"
BOLD_FONT_PATH = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"

def ask_gemini():
    key = os.environ["GEMINI_API_KEY"]
    genai.configure(api_key=key)
    model = genai.GenerativeModel(MODEL)
    prompt = """
Create ONE highly engaging, accurate, original Hindi fact for a 35-45 second YouTube Short designed to earn attention and hold viewers until the final reveal.
Return ONLY valid JSON with keys: title, narration, screens, description, sources.
Rules:
- Use natural, conversational Indian Hindi in Devanagari. It must sound like a curious Indian storyteller speaking to a friend, never formal textbook Hindi.
- narration: 85-105 Hindi words. Start immediately with a startling question, vivid claim, or curiosity gap in the first sentence. Do NOT greet viewers or introduce the channel.
- Build one clear curiosity loop: tease the surprising answer early, reveal useful clues progressively, then deliver the strongest verified payoff near the end.
- Write for speech, not reading: use short natural sentences, commas and question marks where a real Indian narrator would pause; spell out numbers in Hindi words; avoid awkward English acronyms, tongue-twisting compounds, and overly Sanskritized vocabulary. Use varied sentence lengths and conversational transitions. No filler, repetition, fake suspense, or exaggerated claims.
- End with a natural one-line question that invites comments; avoid begging for likes/subscriptions.
- screens: exactly 5 concise Hindi Devanagari lines, each max 8 words. Scene 1 must be a scroll-stopping hook; scenes 2-4 escalate the explanation; scene 5 delivers the payoff. Each line must match the narration at that moment.
- title: concise curiosity-driven Hindi title, truthful and not clickbait.
- description: concise Hindi summary and source references.
- sources: 2 or 3 real, directly relevant URLs from credible institutions, universities, government bodies, museums, or peer-reviewed publishers. Never fabricate URLs or claim a source verifies something it does not. If uncertain about a URL, return fewer sources rather than inventing one.
- Prefer unusual but well-established science, nature, history, space, or everyday-life facts. Avoid medical, political, financial, dangerous, disputed, or breaking-news claims.
- Avoid repeating common generic facts.
"""
    response = model.generate_content(
        prompt,
        generation_config={"temperature": 0.65, "response_mime_type": "application/json"},
    )
    data = json.loads(response.text)
    required = ["title", "narration", "screens", "description", "sources"]
    if any(k not in data for k in required) or len(data["screens"]) != 5:
        raise ValueError("Gemini response is missing required fields.")
    if not data["sources"]:
        raise ValueError("No source references returned; refusing to publish an unsourced fact.")
    return data

def font(size, bold=False):
    path = BOLD_FONT_PATH if bold and os.path.exists(BOLD_FONT_PATH) else FONT_PATH
    if not os.path.exists(path):
        raise FileNotFoundError("Devanagari font missing. Install fonts-noto-core in the runner.")
    return ImageFont.truetype(path, size=size)

def draw_wrapped(draw, text, fnt, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if draw.textbbox((0, 0), test, font=fnt)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

def draw_scene_art(draw, index, text):
    """Draw a distinct layered 2D vector illustration for each fact scene."""
    import math

    t = text.lower()
    cx, cy = 540, 1190
    # Shared atmospheric details
    for j in range(18):
        sx = 120 + ((j * 173 + index * 91) % 840)
        sy = 850 + ((j * 97 + index * 43) % 570)
        r = 3 + (j % 3) * 2
        draw.ellipse((sx-r, sy-r, sx+r, sy+r), fill=(255,255,255,110))

    space_words = ("अंतरिक्ष", "ग्रह", "सूर्य", "चंद्र", "तारा", "नासा", "ब्रह्मांड", "पृथ्वी", "space", "planet")
    ocean_words = ("समुद्र", "पानी", "महासागर", "मछली", "व्हेल", "पानी", "जल", "ocean", "sea", "fish")
    nature_words = ("पेड़", "जंगल", "पौधा", "पत्ता", "फूल", "प्रकृति", "वन", "tree", "forest", "plant")
    animal_words = ("जानवर", "हाथी", "शेर", "पक्षी", "कुत्ता", "बिल्ली", "चींटी", "साँप", "animal", "bird")
    tech_words = ("कंप्यूटर", "मोबाइल", "इंटरनेट", "रोबोट", "चिप", "तकनीक", "बिजली", "computer", "technology")

    if any(k in t for k in space_words):
        # Planet, orbital rings and a distant moon.
        draw.ellipse((310, 960, 770, 1420), fill=(70,125,190,255), outline=(205,230,255,255), width=8)
        draw.arc((205, 1030, 875, 1360), 185, 350, fill=(255,211,100,255), width=24)
        draw.arc((205, 1030, 875, 1360), 5, 170, fill=(255,211,100,255), width=24)
        draw.ellipse((690, 900, 825, 1035), fill=(225,220,205,255), outline=(255,255,255,220), width=5)
        for x,y,r in [(430,1080,45),(610,1220,70),(380,1300,30)]:
            draw.ellipse((x-r,y-r,x+r,y+r), fill=(90,165,115,220))
    elif any(k in t for k in ocean_words):
        draw.rectangle((120, 1120, 960, 1510), fill=(20,105,160,255))
        for y in (1160,1240,1320,1400):
            draw.arc((130,y-35,960,y+45), 185, 355, fill=(125,220,235,255), width=12)
        # Fish silhouette
        draw.ellipse((360,1030,680,1170), fill=(255,170,75,255))
        draw.polygon([(650,1100),(770,1010),(770,1190)], fill=(255,170,75,255))
        draw.ellipse((420,1065,440,1085), fill=(20,35,55,255))
        draw.ellipse((180,1280,260,1360), fill=(100,205,190,255))
    elif any(k in t for k in nature_words):
        draw.polygon([(100,1320),(330,990),(560,1320)], fill=(75,145,105,255))
        draw.polygon([(420,1350),(700,950),(1010,1350)], fill=(45,115,85,255))
        for x,y,r in [(260,1190,100),(700,1120,125),(850,1240,95)]:
            draw.rectangle((x-18,y,x+18,1480), fill=(120,78,48,255))
            draw.ellipse((x-r,y-r,x+r,y+r), fill=(75,175,105,255), outline=(180,235,165,255), width=5)
        draw.ellipse((760,870,900,1010), fill=(255,210,100,255))
    elif any(k in t for k in animal_words):
        # Friendly stylized animal portrait.
        draw.ellipse((300,960,780,1440), fill=(190,145,100,255), outline=(255,225,185,255), width=8)
        draw.ellipse((250,930,430,1190), fill=(170,120,80,255))
        draw.ellipse((650,930,830,1190), fill=(170,120,80,255))
        draw.ellipse((405,1110,455,1160), fill=(25,30,40,255))
        draw.ellipse((625,1110,675,1160), fill=(25,30,40,255))
        draw.ellipse((485,1220,595,1300), fill=(65,45,40,255))
        draw.arc((445,1210,635,1370), 5, 175, fill=(65,45,40,255), width=10)
    elif any(k in t for k in tech_words):
        draw.rounded_rectangle((300,930,780,1390), radius=55, fill=(45,65,95,255), outline=(180,220,255,255), width=10)
        draw.rounded_rectangle((350,990,730,1300), radius=25, fill=(35,155,175,255))
        for j in range(5):
            x = 405 + j*65
            draw.line((x,1060,x,1220-(j%2)*70), fill=(220,255,220,255), width=13)
        draw.rounded_rectangle((455,1400,625,1450), radius=20, fill=(180,200,220,255))
    else:
        # Science / discovery scene: open book, glowing discovery bulb and rays.
        draw.rounded_rectangle((220,1190,535,1430), radius=24, fill=(235,225,195,255), outline=(255,255,255,255), width=7)
        draw.rounded_rectangle((545,1190,860,1430), radius=24, fill=(245,235,210,255), outline=(255,255,255,255), width=7)
        draw.line((540,1200,540,1425), fill=(95,75,60,255), width=8)
        draw.ellipse((410,900,670,1160), fill=(255,211,100,255), outline=(255,245,190,255), width=8)
        draw.rounded_rectangle((485,1125,595,1195), radius=18, fill=(220,165,65,255))
        for angle in range(0,360,45):
            a = math.radians(angle)
            x1,y1 = 540+155*math.cos(a),1030+155*math.sin(a)
            x2,y2 = 540+205*math.cos(a),1030+205*math.sin(a)
            draw.line((x1,y1,x2,y2), fill=(255,220,120,255), width=9)

def make_card(text, index):
    w, h = 1080, 1920
    palettes = [
        ((12, 20, 48), (26, 91, 120)),
        ((38, 19, 62), (106, 47, 94)),
        ((8, 55, 66), (24, 112, 100)),
        ((54, 31, 12), (130, 77, 30)),
        ((25, 32, 55), (65, 82, 130)),
    ]
    top, bottom = palettes[index % len(palettes)]
    img = Image.new("RGB", (w, h))
    pix = img.load()
    for y in range(h):
        t = y / (h - 1)
        c = tuple(int(top[i] * (1-t) + bottom[i] * t) for i in range(3))
        for x in range(w):
            pix[x, y] = c
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse((720, 100, 1220, 600), fill=(255,255,255,18))
    d.ellipse((-220, 1280, 360, 1860), fill=(255,255,255,15))
    d.rounded_rectangle((60, 90, 1020, 1820), radius=58,
                        fill=(4, 8, 20, 55), outline=(255,255,255,55), width=3)
    d.text((125, 170), "HINDI FACTS", font=font(42, True), fill=(255, 211, 100, 255))
    d.rounded_rectangle((125, 265, 955, 276), radius=5, fill=(255,211,100,220))
    fnt = font(70 if len(text) < 55 else 62, True)
    lines = draw_wrapped(d, text, fnt, 820)
    line_h = 96
    total_h = len(lines) * line_h
    y = 390 + max(0, (390-total_h)//2)
    for line in lines[:4]:
        bbox = d.textbbox((0, 0), line, font=fnt, stroke_width=1)
        x = (w - (bbox[2]-bbox[0])) // 2
        d.text((x, y), line, font=fnt, fill=(255,255,255,255),
               stroke_width=2, stroke_fill=(0,0,0,100))
        y += line_h
    # A different illustrated subject is drawn for each scene's topic.
    draw_scene_art(d, index, text)
    d.text((125, 1690), f"FACT {index+1}/5  •  रोज़ कुछ नया सीखें",
           font=font(36), fill=(222,232,245,235))
    path = OUT / f"card_{index+1}.png"
    img.save(path)
    return path

def make_cta_card():
    """Create a dedicated end slate so the subscribe/comment CTA is visible."""
    img = Image.new("RGB", (1080, 1920), (13, 25, 55))
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse((690, 180, 1250, 740), fill=(255, 190, 70, 28))
    d.ellipse((-240, 1250, 420, 1910), fill=(70, 190, 210, 24))
    d.rounded_rectangle((65, 100, 1015, 1815), radius=64,
                        fill=(4, 10, 28, 90), outline=(255, 255, 255, 65), width=4)
    d.text((130, 270), "HINDI FACTS FACTORY", font=font(48, True),
           fill=(255, 211, 100, 255))
    d.text((540, 660), "ऐसे ही मज़ेदार", font=font(76, True),
           fill=(255, 255, 255, 255), anchor="mm")
    d.text((540, 770), "FACTS के लिए", font=font(82, True),
           fill=(255, 255, 255, 255), anchor="mm")
    d.rounded_rectangle((205, 900, 875, 1085), radius=85,
                        fill=(205, 35, 55, 255), outline=(255, 255, 255, 230), width=5)
    d.text((540, 992), "SUBSCRIBE", font=font(76, True),
           fill=(255, 255, 255, 255), anchor="mm")
    d.text((540, 1235), "और कमेंट में बताओ:", font=font(54, True),
           fill=(255, 220, 130, 255), anchor="mm")
    d.text((540, 1340), "अगला FACT किस पर हो?", font=font(52, True),
           fill=(255, 255, 255, 255), anchor="mm")
    path = OUT / "cta_end_card.png"
    img.save(path)
    return path

async def make_voice(text, path):
    # Slightly slower, neutral pitch and no exaggerated processing for clearer conversational Hindi.
    communicate = edge_tts.Communicate(text, VOICE, rate="-4%", volume="+0%", pitch="+0Hz")
    await communicate.save(str(path))

def render_video(data):
    cards = [make_card(line, i) for i, line in enumerate(data["screens"])]
    audio = OUT / "narration.mp3"
    cta_text = (
        "और ऐसे ही मज़ेदार फैक्ट्स के लिए चैनल को सब्सक्राइब करें। "
        "कमेंट में बताइए, अगला फैक्ट किस विषय पर होना चाहिए?"
    )
    full_narration = data["narration"].strip() + " " + cta_text
    asyncio.run(make_voice(full_narration, audio))

    # Turn each illustrated 2D scene card into a moving 9-second shot.
    # Slow camera pushes and alternating pans create motion instead of a static slideshow.
    clips = []
    for i, card in enumerate(cards):
        clip = OUT / f"scene_{i+1}.mp4"
        direction = i % 4
        if direction == 0:
            x_expr, y_expr = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
        elif direction == 1:
            x_expr, y_expr = "iw/2-(iw/zoom/2)+12", "ih/2-(ih/zoom/2)"
        elif direction == 2:
            x_expr, y_expr = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)+12"
        else:
            x_expr, y_expr = "iw/2-(iw/zoom/2)-12", "ih/2-(ih/zoom/2)"
        vf = (
            "zoompan=z='min(zoom+0.00045,1.10)'"
            f":x='{x_expr}':y='{y_expr}':d=270:s=1080x1920:fps=30,"
            "format=yuv420p"
        )
        subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-i", str(card),
            "-vf", vf, "-t", "9", "-r", "30",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            str(clip)
        ], check=True)
        clips.append(clip)

    # A short dedicated end slate reinforces the spoken subscribe/comment CTA.
    cta_card = make_cta_card()
    cta_clip = OUT / "cta_scene.mp4"
    cta_vf = (
        "zoompan=z='min(zoom+0.0007,1.08)'"
        ":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        ":d=120:s=1080x1920:fps=30,format=yuv420p"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(cta_card),
        "-vf", cta_vf, "-t", "4", "-r", "30",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        str(cta_clip)
    ], check=True)
    clips.append(cta_clip)

    concat = OUT / "scenes.txt"
    with concat.open("w", encoding="utf-8") as f:
        for clip in clips:
            f.write(f"file '{clip.as_posix()}'\n")

    video = OUT / "hindi_fact_short.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-i", str(audio), "-vf", "fps=30,scale=1080:1920,format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
        str(video)
    ], check=True)
    return video


def render_3d_video(data):
    """Render genuine animated 3D scenes with Blender, then sync them to narration."""
    scene_json = OUT / "short_metadata.json"
    script = ROOT / "render_3d.py"
    if not script.exists():
        raise FileNotFoundError("render_3d.py is missing.")
    subprocess.run([
        "blender", "--background", "--python", str(script), "--",
        str(scene_json), str(OUT)
    ], check=True, timeout=2100)
    audio = OUT / "narration.mp3"
    cta_text = (
        "और ऐसे ही मज़ेदार फैक्ट्स के लिए चैनल को सब्सक्राइब करें। "
        "कमेंट में बताइए, अगला फैक्ट किस विषय पर होना चाहिए?"
    )
    full_narration = data["narration"].strip() + " " + cta_text
    asyncio.run(make_voice(full_narration, audio))
    visual = OUT / "three_d_visuals.mp4"
    video = OUT / "hindi_fact_short.mp4"
    # Repeat the animated scene reel only as needed to cover the full narration.
    subprocess.run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(visual), "-i", str(audio),
        "-map", "0:v:0", "-map", "1:a:0", "-vf",
        "scale=1080:1920:flags=lanczos,fps=30,format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
        str(video)
    ], check=True)
    return video


def upload_video(path, data):
    client_id = os.environ["YOUTUBE_CLIENT_ID"]
    client_secret = os.environ["YOUTUBE_CLIENT_SECRET"]
    refresh_token = os.environ["YOUTUBE_REFRESH_TOKEN"]
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    youtube = build("youtube", "v3", credentials=creds)
    sources = "\n".join(f"- {u}" for u in data["sources"])
    description = (data["description"] + "\n\nस्रोत / Sources:\n" + sources)[:4900]
    privacy = os.getenv("YOUTUBE_PRIVACY_STATUS", "unlisted")
    body = {
        "snippet": {
            "title": data["title"][:100],
            "description": description,
            "categoryId": "27",
            "tags": ["Hindi Facts", "Amazing Facts", "Shorts", "ज्ञान", "रोचक तथ्य"],
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(str(path), mimetype="video/mp4", resumable=True),
    )
    response = request.execute()
    print("UPLOAD_SUCCESS video_id=" + response["id"])
    print("PRIVACY_STATUS=" + privacy)
    return response["id"]



def ask_gemini_long():
    """Generate a separate, researched-feeling long-form Hindi explainer."""
    key = os.environ["GEMINI_API_KEY"]
    genai.configure(api_key=key)
    model = genai.GenerativeModel(MODEL)
    prompt = """
Create ONE original, accurate long-form Hindi YouTube explainer designed for an approximately 8-minute video.
Return ONLY valid JSON with keys: title, narration, description, sources, scenes.
Rules:
- Topic must be different from the daily Short whenever possible; choose an engaging science, nature, space, history, or everyday-life mystery.
- narration must be 850-950 words in natural conversational Indian Hindi (Devanagari), suitable for a native Indian male narrator.
- Open with a powerful 10-second hook and a clear question; do not greet viewers or introduce the channel.
- Build a coherent story with a clear beginning, progressive explanations, concrete examples, surprising but verified details, and a satisfying conclusion.
- Write for spoken delivery, not an essay: use clear everyday Indian Hindi, short-to-medium sentences, natural punctuation and breathing pauses; spell out numbers where practical; avoid awkward English acronyms, tongue-twisting compounds and overly Sanskritized words. Explain technical ideas simply. No padding, repeated points, fake suspense, fabricated facts, or exaggerated claims.
- Include natural transitions between sections. Keep spoken sentences comfortable for voice narration.
- End with a short question for comments, followed by this CTA in Hindi: "ऐसे ही दिलचस्प वीडियो के लिए चैनल को सब्सक्राइब करें।"
- scenes: exactly 8 concise visual scene descriptions in Hindi, each corresponding to a different part of the narration. These are visual direction labels, NOT subtitles or captions.
- title: truthful, curiosity-driven Hindi title, max 100 characters.
- description: concise Hindi summary.
- sources: 2-4 real, directly relevant URLs from credible institutions, universities, government bodies, museums, or peer-reviewed publishers. Never invent URLs. Return fewer if uncertain.
- Avoid medical, political, financial, dangerous, disputed, or breaking-news claims.
"""
    response = model.generate_content(
        prompt,
        generation_config={"temperature": 0.55, "response_mime_type": "application/json"},
    )
    data = json.loads(response.text)
    if not all(k in data for k in ["title", "narration", "description", "sources", "scenes"]):
        raise ValueError("Long-video response is missing required fields.")
    if len(data["scenes"]) != 8 or len(data["narration"].split()) < 700:
        raise ValueError("Long-video script is too short or has an invalid scene count.")
    if not data["sources"]:
        raise ValueError("No source references returned for long video.")
    return data


def make_long_card(scene_text, index, title):
    """Create a clean 16:9 illustrated scene card; deliberately no subtitles."""
    w, h = 1920, 1080
    palettes = [
        ((8, 18, 45), (22, 83, 115)), ((35, 18, 58), (100, 45, 92)),
        ((8, 48, 58), (20, 105, 95)), ((50, 28, 12), (120, 70, 28)),
        ((20, 30, 55), (62, 78, 125)), ((18, 48, 65), (35, 105, 125)),
        ((48, 22, 42), (110, 55, 82)), ((12, 38, 48), (55, 105, 90)),
    ]
    top, bottom = palettes[index % len(palettes)]
    img = Image.new("RGB", (w, h))
    pix = img.load()
    for y in range(h):
        t = y / (h - 1)
        c = tuple(int(top[i] * (1-t) + bottom[i] * t) for i in range(3))
        for x in range(w):
            pix[x, y] = c
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle((55, 55, 1865, 1025), radius=48,
                        fill=(3, 8, 20, 55), outline=(255,255,255,45), width=3)
    d.text((115, 105), "HINDI FACTS FACTORY", font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34),
           fill=(255, 211, 100, 255))
    # Large topic illustration made from simple layered vector shapes.
    cx, cy = 1420, 570
    for j in range(12):
        x = 1130 + ((j * 137 + index * 71) % 600)
        y = 300 + ((j * 89 + index * 43) % 470)
        r = 8 + (j % 4) * 7
        d.ellipse((x-r,y-r,x+r,y+r), fill=(255,255,255,90))
    d.ellipse((cx-205,cy-205,cx+205,cy+205), fill=(255,190,80,210), outline=(255,245,200,255), width=8)
    d.arc((cx-300,cy-110,cx+300,cy+110), 190, 350, fill=(180,230,255,255), width=18)
    d.arc((cx-300,cy-110,cx+300,cy+110), 10, 170, fill=(180,230,255,255), width=18)
    title_font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf", 54)
    scene_font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf", 66)
    title_lines = draw_wrapped(d, title, title_font, 850)
    y = 260
    for line in title_lines[:3]:
        d.text((115,y), line, font=title_font, fill=(255,211,100,255))
        y += 78
    scene_lines = draw_wrapped(d, scene_text, scene_font, 850)
    y += 75
    for line in scene_lines[:3]:
        d.text((115,y), line, font=scene_font, fill=(255,255,255,255),
               stroke_width=2, stroke_fill=(0,0,0,100))
        y += 88
    path = OUT / f"long_card_{index+1}.png"
    img.save(path)
    return path


async def make_long_voice(text, path):
    # Match the Short: relaxed pace and unchanged natural pitch.
    communicate = edge_tts.Communicate(text, VOICE, rate="-4%", volume="+0%", pitch="+0Hz")
    await communicate.save(str(path))


def render_long_video(data):
    audio = OUT / "long_narration.mp3"
    asyncio.run(make_long_voice(data["narration"].strip(), audio))
    probe = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(audio)
    ], check=True, capture_output=True, text=True)
    audio_duration = float(probe.stdout.strip())
    # Aim for roughly eight minutes; retain the complete narration rather than cutting words.
    per_scene = audio_duration / len(data["scenes"])
    clips = []
    for i, scene in enumerate(data["scenes"]):
        card = make_long_card(scene, i, data["title"])
        clip = OUT / f"long_scene_{i+1}.mp4"
        frames = max(1, int(per_scene * 30))
        vf = (
            "zoompan=z='min(zoom+0.00012,1.06)'"
            ":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s=1920x1080:fps=30,format=yuv420p"
        )
        subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-i", str(card),
            "-vf", vf, "-frames:v", str(frames), "-r", "30",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
            str(clip)
        ], check=True)
        clips.append(clip)
    concat = OUT / "long_scenes.txt"
    with concat.open("w", encoding="utf-8") as f:
        for clip in clips:
            f.write(f"file '{clip.as_posix()}'\n")
    video = OUT / "hindi_facts_long.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-i", str(audio), "-vf", "fps=30,scale=1920:1080,format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
        str(video)
    ], check=True)
    return video, audio_duration


def upload_long_video(path, data):
    client_id = os.environ["YOUTUBE_CLIENT_ID"]
    client_secret = os.environ["YOUTUBE_CLIENT_SECRET"]
    refresh_token = os.environ["YOUTUBE_REFRESH_TOKEN"]
    creds = Credentials(
        token=None, refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id, client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    youtube = build("youtube", "v3", credentials=creds)
    sources = "\n".join(f"- {u}" for u in data["sources"])
    description = (data["description"] + "\n\nस्रोत / Sources:\n" + sources)[:4900]
    body = {
        "snippet": {
            "title": data["title"][:100],
            "description": description,
            "categoryId": "27",
            "tags": ["Hindi Facts", "Amazing Facts", "Science", "Knowledge"],
        },
        "status": {"privacyStatus": os.getenv("YOUTUBE_PRIVACY_STATUS", "unlisted"),
                   "selfDeclaredMadeForKids": False},
    }
    request = youtube.videos().insert(
        part="snippet,status", body=body,
        media_body=MediaFileUpload(str(path), mimetype="video/mp4", resumable=True),
    )
    response = request.execute()
    print("LONG_UPLOAD_SUCCESS video_id=" + response["id"])
    return response["id"]


def main():
    # Create both formats daily; the long-form script is generated separately.
    short_data = ask_gemini()
    (OUT / "short_metadata.json").write_text(json.dumps(short_data, ensure_ascii=False, indent=2), encoding="utf-8")
    short_video = render_3d_video(short_data)
    long_data = ask_gemini_long()
    (OUT / "long_metadata.json").write_text(json.dumps(long_data, ensure_ascii=False, indent=2), encoding="utf-8")
    long_video, long_seconds = render_long_video(long_data)
    print(f"LONG_VIDEO_DURATION_SECONDS={long_seconds:.1f}")
    if os.getenv("NO_UPLOAD", "false").lower() == "true":
        print("SHORT_READY_NO_UPLOAD=" + str(short_video))
        print("LONG_READY_NO_UPLOAD=" + str(long_video))
        return
    upload_video(short_video, short_data)
    upload_long_video(long_video, long_data)

if __name__ == "__main__":
    main()
