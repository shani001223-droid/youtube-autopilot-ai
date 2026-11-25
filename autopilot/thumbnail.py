"""Thumbnail from a real video frame + at most three words (yt-package rule: three words max at feed size)."""
import os, subprocess
from PIL import Image, ImageDraw, ImageFont

FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
         "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", "/Library/Fonts/Arial Bold.ttf"]


def find_font(size):
    for p in FONTS:
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def extract_frame(video, at, out, runner=subprocess.run):
    r = runner(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(at), "-i", str(video), "-frames:v", "1", "-q:v", "2", str(out)], capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out): raise RuntimeError("frame extraction failed: " + (r.stderr or "")[-200:])


def _fit(draw, words, width, start):
    for size in range(start, 40, -6):
        f = find_font(size); lines, cur = [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if draw.textlength(t, font=f) <= width or not cur: cur = t
            else: lines.append(cur); cur = w
        lines.append(cur)
        if len(lines) <= 3 and all(draw.textlength(l, font=f) <= width for l in lines): return f, lines
    return f, lines


def make_thumbnail(frame, text, out, size=(1080, 1920)):
    W, H = size; img = Image.open(frame).convert("RGB"); r = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * r) + 1, int(img.height * r) + 1)); l, t = (img.width - W) // 2, (img.height - H) // 2
    img = img.crop((l, t, l + W, t + H)); shade = Image.new("L", (1, H))
    for y in range(H): shade.putpixel((0, y), int(170 * (y / H) ** 1.5))
    img = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img, shade.resize((W, H)))
    d = ImageDraw.Draw(img); words = text.upper().split()[:3]
    f, lines = _fit(d, words, int(W * 0.86), int(W * 0.16)); lh = int(f.size * 1.15); y = int(H * 0.62) if H > W else int(H * 0.55)
    for line in lines:
        x = (W - d.textlength(line, font=f)) / 2
        d.text((x, y), line, font=f, fill=(240, 240, 240), stroke_width=max(4, f.size // 14), stroke_fill=(0, 0, 0)); y += lh
    img.save(out, "JPEG", quality=90)
