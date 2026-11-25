"""yt-audit: ONE fix, not a report. Order matters: no data -> same-shape titles -> uneven rhythm -> weak packaging."""
import statistics
from collections import Counter
from datetime import datetime
from .skills import title as titlelint


def _shape(t):
    w = t.split(); return (any(c.isdigit() for c in t), t.strip().endswith("?"), w[0].lower() if w else "")


def audit_channel(recs):
    working = []
    if len(recs) < 5: return {"fix": "Not enough data yet: publish at least 5 videos before judging the channel.", "working": working, "not_yet": ["everything"]}
    good = [r for r in recs if (r.get("avg_view_pct") or 0) >= 70]
    if good: working.append(f"{len(good)} video(s) hold 70%+ of viewers to the end")
    shape, n = Counter(_shape(r["title"]) for r in recs).most_common(1)[0]
    if n / len(recs) >= 0.7: return {"fix": f"Title shape is the same on {n} of {len(recs)} videos. Break the pattern: vary how titles open, with and without a number or question.", "working": working, "not_yet": []}
    days = sorted(datetime.fromisoformat(r["published_at"].replace("Z", "+00:00")) for r in recs if r.get("published_at"))
    gaps = [(b - a).total_seconds() / 86400 for a, b in zip(days, days[1:])]
    if gaps and max(gaps) > 7 and max(gaps) > 3 * max(statistics.median(gaps), 1): return {"fix": f"Consistency: there is a {max(gaps):.0f}-day hole in the upload rhythm. Fix the schedule before anything else.", "working": working, "not_yet": []}
    avg = statistics.mean(titlelint.check(r["title"])["score"] for r in recs)
    if avg < 60: return {"fix": f"Packaging: titles average {avg:.0f}/100 on the lint. Shorten them and front-load the subject.", "working": working, "not_yet": []}
    return {"fix": "No single dominant problem. Keep the rhythm and let analytics steer subgenre choice.", "working": working, "not_yet": []}
