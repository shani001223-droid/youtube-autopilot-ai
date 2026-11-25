"""Cloud production scheduling, review caps, and quality checks."""
from collections import Counter

PREVIEW_CAPS = {"hindi_shorts": 3, "english_long": 1}
PENDING = {"awaiting_approval", "approved_manual"}

def should_generate(items, profile):
    cap = PREVIEW_CAPS.get(profile)
    if cap is None:
        return True
    return sum(i.get("profile") == profile and not i.get("demo") and
               i.get("status") in PENDING for i in items) < cap

def story_memory(items, limit=40):
    return [{"topic": i.get("topic", ""), "premise": i.get("premise", ""),
             "closing": (i.get("script") or {}).get("closing_line", "")}
            for i in items if i.get("topic") and not i.get("demo")][-limit:]

def visual_report(clips, queries):
    kinds = Counter(c.get("kind", "stock_video" if c.get("path") else "illustration") for c in clips)
    repeated = len(queries) - len(set(q.strip().casefold() for q in queries))
    return {"sources": dict(kinds), "repeated_queries": repeated,
            "scene_count": len(queries), "requires_visual_review": True}

def chapters(durations):
    total = sum(durations)
    if total < 45 or len(durations) < 3:
        return []
    points = [0, int(sum(durations[:len(durations)//3])), int(sum(durations[:2*len(durations)//3]))]
    if any(b-a < 10 for a,b in zip(points, points[1:])) or total-points[-1] < 10:
        return []
    def stamp(t): return f"{t//60:02d}:{t%60:02d}"
    return [f"{stamp(t)} {label}" for t,label in zip(points, ["The first clue", "The mystery deepens", "The revelation"])]
