"""QA on the narration with the installed yt-edit skill (deadair.py): a long silence inside a Short kills retention."""
import json, os, re, subprocess, sys, tempfile

DEADAIR = os.path.join(os.path.dirname(__file__), "skills", "deadair.py")


def _srt_time(t):
    ms = int(round(t * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def srt_from_timeline(tl):
    return "\n".join(f"{i}\n{_srt_time(s['start'])} --> {_srt_time(s['end'])}\n{s['text']}\n" for i, s in enumerate(tl, 1))


def dead_air_report(timeline, floor=None):
    with tempfile.NamedTemporaryFile("w", suffix=".srt", delete=False) as fh: fh.write(srt_from_timeline(timeline)); path = fh.name
    try:
        r = subprocess.run([sys.executable, DEADAIR, path, "--json"], capture_output=True, text=True)
        if r.returncode != 0: return {"ok": False, "error": (r.stderr or r.stdout)[-200:], "gap_seconds": 0.0, "cuts": []}
        d = json.loads(r.stdout); gaps = [float(m.group(1)) for c in d.get("cuts", []) for m in [re.search(r"([\d.]+)s gap", c.get("why", ""))] if m]
        return {"ok": True, "gap_seconds": max(gaps, default=0.0), "cuts": d.get("cuts", []), "removed": d.get("removed", 0.0)}
    except (ValueError, OSError) as ex: return {"ok": False, "error": str(ex), "gap_seconds": 0.0, "cuts": []}
    finally: os.unlink(path)
