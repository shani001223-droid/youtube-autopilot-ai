"""Voice: licence allow-list, sentence timeline, Piper wrapper. Piper itself is GPL-3 (runtime only, not redistributed)."""
import re, subprocess, sys, wave
from pathlib import Path

# Voices whose licence does not clearly allow monetised use (verified against third-party catalogue notes, Nov 2026).
NONCOMMERCIAL = {
    "en_US-ryan": "CC BY-NC-SA (non-commercial)",
    "en_US-hfc_female": "CC BY-NC-SA (non-commercial)",
    "en_US-hfc_male": "CC BY-NC-SA (non-commercial)",
    "zh_CN-xiao_ya": "CC BY-NC-SA (non-commercial)",
    "en_US-lessac": "dataset reported as research-only / licence unclear",
    "en_US-amy": "licence only says 'see dataset URL'",
    "en_GB-alan": "licence only says 'see dataset URL'",
}


class VoiceLicenseError(Exception):
    pass


def check_voice(model, allow_noncommercial=False):
    for prefix, why in NONCOMMERCIAL.items():
        if model.startswith(prefix) and not allow_noncommercial:
            raise VoiceLicenseError(f"{model}: {why}. Pick another voice or set voice.allow_noncommercial (non-monetised channels only)")


def split_sentences(text):
    parts = re.split(r'(?<=[.!?])\s+(?=["\u201c\'(]?[A-Z])', text.strip())
    return [p.strip() for p in parts if p.strip()]


def wav_duration(path):
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def build_timeline(sentences, durations, gap=0.35):
    t, out = 0.0, []
    for s, d in zip(sentences, durations):
        out.append({"text": s, "start": round(t, 3), "end": round(t + d, 3)}); t = t + d + gap
    return out


def synthesize_all(sentences, out_dir, synth_fn, gap=0.35):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    paths, durations = [], []
    for i, s in enumerate(sentences):
        p = out_dir / f"sent_{i:03d}.wav"; synth_fn(s, p); paths.append(p); durations.append(wav_duration(p))
    timeline = build_timeline(sentences, durations, gap)
    out = out_dir / "narration.wav"
    with wave.open(str(paths[0]), "rb") as first: params = first.getparams()
    silence = b"\x00" * (int(params.framerate * gap) * params.sampwidth * params.nchannels)
    with wave.open(str(out), "wb") as w:
        w.setparams(params)
        for i, p in enumerate(paths):
            with wave.open(str(p), "rb") as r:
                if (r.getframerate(), r.getnchannels(), r.getsampwidth()) != (params.framerate, params.nchannels, params.sampwidth):
                    raise RuntimeError("TTS output format changed between sentences")
                w.writeframes(r.readframes(r.getnframes()))
            if i < len(paths) - 1: w.writeframes(silence)
    return {"wav": str(out), "timeline": timeline, "duration": wav_duration(out)}


def piper_synth(voice, data_dir="voices", runner=subprocess.run, allow_noncommercial=False, length_scale=1.0):
    """UNTESTED against a live Piper install (needs network to fetch the voice on first use)."""
    check_voice(voice, allow_noncommercial)

    def synth(text, out_path):
        cmd = [sys.executable, "-m", "piper", "--model", voice, "--data-dir", str(data_dir), "--download-dir", str(data_dir),
               "--output_file", str(out_path)]
        if length_scale != 1.0: cmd += ["--length-scale", str(length_scale)]
        r = runner(cmd, input=text, text=True, capture_output=True)
        if r.returncode != 0: raise RuntimeError(f"piper failed: {(r.stderr or '')[-300:]}")
    return synth
