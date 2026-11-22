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
VOICE = os.getenv("TTS_VOICE", "hi-IN-SwaraNeural")
FONT_PATH = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"
BOLD_FONT_PATH = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"

def ask_gemini():
    key = os.environ["GEMINI_API_KEY"]
    genai.configure(api_key=key)
    model = genai.GenerativeModel(MODEL)
    prompt = """
Create ONE original, accurate, surprising Hindi fact for a 35-45 second YouTube Short.
Return ONLY valid JSON with keys: title, narration, screens, description, sources.
Rules:
- Hindi in Devanagari; natural conversational Hindi, not Bengali.
- narration: about 75-100 Hindi words, engaging hook, explain one fact clearly, finish with a short CTA.
- screens: exactly 5 short on-screen Hindi lines, each max 9 words, first is a hook.
- title: concise Hindi title, no misleading claim.
- description: Hindi description, mention that viewers should verify factual details from listed sources.
- sources: 2 or 3 credible URLs from institutions, universities, government, museums, or peer-reviewed publishers. Never invent a URL; if unsure, use only sources you know are real and relevant.
- Avoid medical, political, financial, dangerous, or breaking-news claims.
- Do not repeat common generic facts if possible.
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
    d.ellipse((720, 180, 1220, 680), fill=(255,255,255,18))
    d.ellipse((-220, 1280, 360, 1860), fill=(255,255,255,15))
    d.rounded_rectangle((76, 120, 1004, 1800), radius=54,
                        fill=(4, 8, 20, 78), outline=(255,255,255,48), width=3)
    d.text((130, 220), "HINDI FACTS", font=font(42, True), fill=(255, 211, 100, 255))
    d.rounded_rectangle((130, 330, 950, 340), radius=5, fill=(255,211,100,220))
    fnt = font(78 if len(text) < 55 else 68, True)
    lines = draw_wrapped(d, text, fnt, 790)
    line_h = 118 if fnt.size >= 78 else 104
    total_h = len(lines) * line_h
    y = max(540, (h - total_h) // 2)
    for line in lines:
        bbox = d.textbbox((0,0), line, font=fnt, stroke_width=1)
        x = (w - (bbox[2]-bbox[0])) // 2
        d.text((x, y), line, font=fnt, fill=(255,255,255,255),
               stroke_width=2, stroke_fill=(0,0,0,80))
        y += line_h
    d.text((130, 1660), f"FACT {index+1}/5  •  रोज़ कुछ नया सीखें",
           font=font(36), fill=(222,232,245,235))
    path = OUT / f"card_{index+1}.png"
    img.save(path)
    return path

async def make_voice(text, path):
    communicate = edge_tts.Communicate(text, VOICE, rate="+2%", volume="+0%")
    await communicate.save(str(path))

def render_video(data):
    cards = [make_card(line, i) for i, line in enumerate(data["screens"])]
    audio = OUT / "narration.mp3"
    asyncio.run(make_voice(data["narration"], audio))
    # Each card is shown for 8 seconds; audio is trimmed to the narration length.
    concat = OUT / "cards.txt"
    with concat.open("w", encoding="utf-8") as f:
        for p in cards:
            f.write(f"file '{p.as_posix()}'\n")
            f.write("duration 8\n")
        f.write(f"file '{cards[-1].as_posix()}'\n")
    video = OUT / "hindi_fact_short.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-i", str(audio), "-vf", "fps=30,scale=1080:1920,format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
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

def main():
    data = ask_gemini()
    (OUT / "metadata.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    video = render_video(data)
    if os.getenv("NO_UPLOAD", "false").lower() == "true":
        print("VIDEO_READY_NO_UPLOAD=" + str(video))
        return
    upload_video(video, data)

if __name__ == "__main__":
    main()
