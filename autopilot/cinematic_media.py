"""Optional Gemini native media. Off by default; no paid feature enabled automatically."""
import base64, io, re, wave
from pathlib import Path
import requests
from PIL import Image, ImageStat
from .llm import BASE

class MediaError(RuntimeError): pass

class GeminiMedia:
    def __init__(self, key, session=None):
        self.key = key
        self.session = session or requests.Session()

    def request(self, model, parts, config, kind):
        if not self.key or not re.fullmatch(r"[a-zA-Z0-9._-]+", model):
            raise MediaError("Media provider not configured")
        try:
            response = self.session.post(f"{BASE}/models/{model}:generateContent",
                headers={"x-goog-api-key": self.key}, json={
                    "contents": [{"parts": parts}], "generationConfig": config}, timeout=(15, 120))
        except requests.RequestException:
            raise MediaError("Media provider connection failed") from None
        if response.status_code != 200:
            raise MediaError(f"Media provider HTTP {response.status_code}")
        for candidate in response.json().get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                data = part.get("inlineData") or {}
                mime = data.get("mimeType", "")
                if mime.startswith(kind + "/") and data.get("data"):
                    return mime, base64.b64decode(data["data"], validate=True)
        raise MediaError("No requested media in response")

    def speech(self, model, language, voice="Charon"):
        def synth(text, out):
            prompt = ("Read only the following narration verbatim in natural " + language +
                      ", intimate suspense, clear diction, restrained emotion, no added words:\n" + text)
            mime, audio = self.request(model, [{"text": prompt}], {"responseModalities": ["AUDIO"],
                "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}, "audio")
            if len(audio) < 4800 or len(audio) % 2:
                raise MediaError("Unusable narration audio")
            if audio[:4] == b"RIFF":
                with wave.open(io.BytesIO(audio), "rb") as w:
                    if w.getnchannels() != 1 or w.getsampwidth() != 2 or w.getframerate() != 24000:
                        raise MediaError("Unexpected speech WAV format")
                Path(out).write_bytes(audio)
            else:
                if not (mime.startswith("audio/L16") or mime.startswith("audio/pcm")):
                    raise MediaError("Unexpected speech media format")
                rate = re.search(r"rate=(\d+)", mime)
                if rate and int(rate.group(1)) != 24000:
                    raise MediaError("Unexpected speech sample rate")
                with wave.open(str(out), "wb") as w:
                    w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(audio)
        return synth

    def image(self, model, prompt, aspect, out, reference=None):
        parts = [{"text": prompt}]
        if reference:
            parts.append({"inlineData": {"mimeType": "image/jpeg",
                "data": base64.b64encode(Path(reference).read_bytes()).decode("ascii")}})
        _, data = self.request(model, parts, {"responseModalities": ["IMAGE"],
                      "imageConfig": {"aspectRatio": aspect}}, "image")
        with Image.open(io.BytesIO(data)) as source:
            im = source.convert("RGB")
            if min(im.size) < 480 or max(ImageStat.Stat(im).stddev) < 12:
                raise MediaError("Image is too small or visually blank")
            im.thumbnail((2048, 2048))
            im.save(out, "JPEG", quality=94)

def generate_visuals(media, model, script, queries, out, long=False, max_calls=8, log=lambda *a: None):
    """Generate one image per selected shot, reuse first as visual continuity reference.
    A strict call budget includes failed attempts; unused shots retain licensed fallback."""
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    result = [{"path": None, "video_id": None, "credit": None} for _ in queries]
    aspect = "16:9" if long else "9:16"
    ref = None
    calls = 0
    for i, query in enumerate(queries):
        if calls >= max_calls: break
        scene = script["scenes"][i]
        prompt = ("Generate one cinematic realistic fictional horror film still, no gore, no text, no logos. "
                  "Consistent production design and lighting across shots, dramatic depth, legible shadows. "
                  f"Story world: {script.get('continuity') or script['logline']}. "
                  f"Shot {i+1}: {scene.get('visual_prompt') or query}. "
                  "If a reference frame is attached, preserve its fictional character design, setting and color grade, not its composition.")
        dest = out / f"ai_{i:03d}.jpg"
        calls += 1
        try:
            media.image(model, prompt, aspect, dest, ref)
        except (MediaError, ValueError, OSError) as exc:
            log("warning", "AI image unavailable; continuing with licensed media")
            break
        result[i] = {"path": str(dest), "video_id": None, "credit": None, "kind": "ai_image"}
        if ref is None: ref = dest
    return result
