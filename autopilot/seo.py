"""Packaging + search text. yt-package: the title/thumbnail PAIR is linted (no repeated words, <=60 chars, <=3 thumb words).
yt-seo: tags are the weakest signal; title and first two description lines carry the query."""
import re
from .skills import title as titlelint

GENERIC = {"story", "stories", "video", "videos", "short", "shorts"}
STOP = titlelint.STOP | {"s", "at", "by", "from"}


def choose_title(titles, thumb_texts):
    pool = [t for t in titles if 0 < len(t) <= 60] or sorted(titles, key=len)[:1]
    thumbs = [" ".join(x.split()[:3]) for x in thumb_texts if x.strip()] or [""]
    best = None
    for t in pool:
        for th in thumbs:
            r = titlelint.check(t, th or None); key = (r["score"], -len(t))
            if best is None or key > best[0]: best = (key, t, th, r)
    _, t, th, r = best
    return {"title": t[:100], "thumb_text": th, "score": r["score"], "issues": r["issues"]}


def clean_tags(tags, max_tags=15, budget=450):
    out, seen, used = [], set(), 0
    for t in tags:
        t = t.replace("#", "").strip()
        if not t or len(t) > 30 or t.lower() in seen: continue
        if len(out) >= max_tags or used + len(t) + 1 > budget: break
        seen.add(t.lower()); out.append(t); used += len(t) + 1
    return out


def _words(text): return {w for w in re.findall(r"[a-z0-9']+", text.lower()) if w not in STOP and w not in GENERIC}


def query_test(title, description, queries):
    have = _words(title + " " + " ".join(description.splitlines()[:2]))
    return [q for q in queries if not _words(q) <= have]


def build_description(script, title, credits, settings, chapters=None):
    n = settings["niche"]
    lines = [script["logline"].strip(), f"A new original {n['name'].lower()} - subscribe so you never miss the next one.", ""]
    if chapters: lines += chapters + [""]
    lines += ["This is a work of fiction. The story and narration are AI-assisted; every name and event is invented.", ""]
    if credits: lines += ["Footage:"] + sorted(set(credits)) + [""]
    lines += ["Music: generated for this channel.", "", "#horrorstories #shorts #mystery"]
    return re.sub(r"[<>]", "", "\n".join(lines))[:4900]


def _secs(ts):
    p = [int(x) for x in ts.split(":")]
    return p[0] * 60 + p[1] if len(p) == 2 else p[0] * 3600 + p[1] * 60 + p[2]


def chapters_valid(lines):
    """YouTube's chapter rules: first at 00:00, at least three, each at least 10 seconds long."""
    try: stamps = [_secs(l.split()[0]) for l in lines]
    except (ValueError, IndexError): return False
    return len(stamps) >= 3 and stamps[0] == 0 and all(b - a >= 10 for a, b in zip(stamps, stamps[1:]))
