"""FFmpeg editing: per-scene segments (crop to 9:16, horror grade), concat, burn captions, duck music under voice,
normalise loudness, encode 1080x1920 H.264/AAC. If a clip is missing a generated dark-fog segment is used instead."""
import json, os, subprocess
from pathlib import Path

W, H, FPS = 1080, 1920, 30
GRADE = "eq=saturation=0.55:contrast=1.12:brightness=-0.06,vignette=PI/4,noise=alls=4:allf=t"


def probe(path, ffprobe="ffprobe"):
    r = subprocess.run([ffprobe, "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration", "-of", "json", str(path)],
                       capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError("ffprobe failed: " + r.stderr[-200:])
    d = json.loads(r.stdout); st = d.get("streams", []); v = next((s for s in st if s["codec_type"] == "video"), {})
    return {"width": v.get("width"), "height": v.get("height"), "duration": float(d["format"]["duration"]),
            "has_video": bool(v), "has_audio": any(s["codec_type"] == "audio" for s in st)}


def scene_durations(timeline, counts, tail=0.6):
    out, i = [], 0
    for n, c in enumerate(counts):
        start = timeline[i]["start"]; i += c
        end = timeline[i]["start"] if n < len(counts) - 1 else timeline[-1]["end"] + tail
        out.append(round(end - start, 3))
    return out


def segment_args(src, dur, out, w=W, h=H, fps=FPS, ffmpeg="ffmpeg"):
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps={fps},{GRADE}"
    return [ffmpeg, "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(src), "-t", f"{dur:.3f}", "-an", "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out)]


def still_segment_args(src, dur, out, w=W, h=H, fps=FPS, ffmpeg="ffmpeg", motion=0):
    frames = max(1, round(dur * fps))
    zoom = [f"1.02+0.13*on/{frames}", f"1.15-0.12*on/{frames}", f"1.08+0.07*on/{frames}"][motion % 3]
    x = ["iw/2-iw/zoom/2", "iw/2-iw/zoom/2", f"(iw-iw/zoom)*on/{frames}"][motion % 3]
    vf = (f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,crop={w*2}:{h*2},"
          f"zoompan=z='{zoom}':x='{x}':y='ih/2-ih/zoom/2':"
          f"d={frames}:s={w}x{h}:fps={fps},setsar=1,format=yuv420p")
    return [ffmpeg,"-y","-loglevel","error","-i",str(src),"-vf",vf,"-frames:v",str(frames),
            "-an","-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p",str(out)]


def fallback_segment_args(dur, out, seed=0, w=W, h=H, fps=FPS, ffmpeg="ffmpeg"):
    tint = ["16202b", "142420", "201a28", "1e1e1e"][seed % 4]
    return [ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=0x{tint}:s={w}x{h}:r={fps}:d={dur:.3f}",
            "-vf", "noise=alls=5:allf=t,vignette=PI/3,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", str(out)]


def _run(cmd, runner, cwd=None):
    r = runner(cmd, capture_output=True, text=True, cwd=cwd)
    if r.returncode != 0: raise RuntimeError("ffmpeg failed: " + (r.stderr or "")[-400:])


def render_video(spec, voice, music, ass, out, workdir, runner=subprocess.run, music_volume=0.14, font_dir="/usr/share/fonts", width=W, height=H):
    wd = Path(workdir); wd.mkdir(parents=True, exist_ok=True); segs = []
    for i, it in enumerate(spec):
        seg = wd / f"seg_{i:02d}.mp4"
        try:
            if not it.get("path"):
                raise RuntimeError("missing scene asset")
            is_still = Path(it["path"]).suffix.lower() in {".jpg", ".jpeg", ".png"}
            args = still_segment_args if is_still else segment_args
            _run(args(it["path"], it["duration"], seg, w=width, h=height, **({"motion": i} if is_still else {})), runner)
        except RuntimeError:
            from .illustration import draw_scene
            print(f"Warning: scene {i + 1} unavailable; rendering original illustration.", flush=True)
            still = wd / f"recovery_{i}.jpg"
            draw_scene(it.get("query", "foggy forest night"), still, i)
            _run(still_segment_args(still, it["duration"], seg, w=width, h=height, motion=i), runner)
        segs.append(seg)
    lst = wd / "concat.txt"; lst.write_text("".join(f"file '{p.resolve()}'\n" for p in segs))
    joined = wd / "joined.mp4"; _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)], runner)
    (wd / "subs.ass").write_bytes(Path(ass).read_bytes()); total = sum(i["duration"] for i in spec)
    audio = (f"[1:a]aresample=44100,apad,asplit=2[vo][vosc];[2:a]aresample=44100,volume={music_volume}[mus];"
             "[mus][vosc]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[duck];"
             "[vo][duck]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[aout]")
    graph = f"[0:v]ass=subs.ass:fontsdir={font_dir}[vout];{audio}"
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(joined.resolve()), "-i", str(Path(voice).resolve()), "-i", str(Path(music).resolve()),
          "-filter_complex", graph, "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-maxrate", "5M", "-bufsize", "10M",
          "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(Path(out).resolve())], runner, cwd=str(wd))
    return probe(out)
