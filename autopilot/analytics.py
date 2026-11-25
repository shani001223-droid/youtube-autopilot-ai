"""Pull results for published videos; retention curve -> installed yt-retention skill."""
import json, os, subprocess, sys, tempfile
from datetime import datetime, timedelta, timezone

RETENTION = os.path.join(os.path.dirname(__file__), "skills", "retention.py")


def retention_csv(points):
    return "\n".join(f"{round(x * 100, 1)},{round(y * 100, 1)}" for x, y in points)


def retention_report(points, duration):
    if len(points) < 8: return {"ok": False, "error": "need at least 8 retention points"}
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh: fh.write(retention_csv(points)); path = fh.name
    try:
        r = subprocess.run([sys.executable, RETENTION, path, "--duration", str(duration), "--json"], capture_output=True, text=True)
        if r.returncode != 0: return {"ok": False, "error": (r.stderr or r.stdout)[-200:]}
        d = json.loads(r.stdout); return {"ok": True, "raw": d, "hook_leak": d.get("hook_leak"), "cliffs": d.get("cliffs", [])[:3]}
    except (ValueError, OSError) as ex: return {"ok": False, "error": str(ex)}
    finally: os.unlink(path)


def collect(yt, items, today):
    pub = [i for i in items if i.get("video_id")]
    if not pub: return []
    stats = yt.video_stats([i["video_id"] for i in pub]); out = []
    for it in pub:
        s = stats.get(it["video_id"], {}); start = (it.get("published_at") or (datetime.fromisoformat(today) - timedelta(days=30)).isoformat())[:10]
        try: a = yt.analytics(it["video_id"], start, today)
        except Exception: a = {}
        out.append({"id": it["id"], "video_id": it["video_id"], "title": it.get("title"), "published_at": it.get("published_at"), "variety": it.get("variety", {}),
                    "views": s.get("views", a.get("views", 0)), "likes": s.get("likes", 0), "comments": s.get("comments", 0),
                    "avg_view_pct": a.get("averageViewPercentage"), "minutes_watched": a.get("estimatedMinutesWatched"),
                    "avg_view_seconds": a.get("averageViewDuration"), "collected_on": today})
    return out
