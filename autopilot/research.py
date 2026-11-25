"""Topic research. yt-viral: rank by multiple over each channel's own median (never raw views). Novelty filter keeps the
channel from repeating itself (YouTube's 'generic or repetitive content' rule)."""
import json, os, re, subprocess, sys, tempfile
from datetime import timedelta

STOP = set("the a an of for to in on and or is are was were with this that it as at by from my your his her their".split())
SWIPE = os.path.join(os.path.dirname(__file__), "skills", "yt-viral", "swipe.py")


class ResearchError(Exception):
    pass


def _tokens(t): return {w for w in re.findall(r"[a-z0-9\u0900-\u097f']+", t.lower()) if w not in STOP}


def novelty(a, b):
    x, y = _tokens(a), _tokens(b)
    return 1.0 if not x or not y else round(1 - len(x & y) / len(x | y), 4)


def filter_novel(candidates, recent_titles, threshold=0.5):
    return [c for c in candidates if all(novelty(c["topic"], r) >= threshold for r in recent_titles)]


def swipe_rank(collected, min_multiple=1.5):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh: json.dump(collected, fh); path = fh.name
    try:
        r = subprocess.run([sys.executable, SWIPE, path, "--min", str(min_multiple), "--json"], capture_output=True, text=True)
        if r.returncode != 0: return []
        data = json.loads(r.stdout or "[]")
        return data.get("outliers", []) if isinstance(data, dict) else data
    except (ValueError, OSError): return []
    finally: os.unlink(path)


def trend_titles(yt, settings, now, max_queries=3):
    after = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"); seen, out = set(), []
    for q in settings["niche"]["seed_queries"][:max_queries]:
        for v in yt.search_recent(q, after, max_results=10):
            if v["id"] not in seen: seen.add(v["id"]); out.append({"id": v["id"], "title": v["title"], "channel": v.get("channel"), "channel_id": v.get("channel_id")})
    return out


def build_research_prompt(settings, trends, insights, recent_topics, variety):
    n = settings["niche"]
    tr = "\n".join(f"- {t['title']}" for t in trends[:25]) or "(no trend data available; use your own knowledge of what the audience likes)"
    best = ", ".join(f"{r['value']} ({r['mean_view_pct']}% avg viewed)" for r in (insights or {}).get("subgenre", [])[:3]) or "no analytics yet"
    return f"""[task:research]
Channel niche: {n['name']}. Audience: {n['audience']}. Today's chosen subgenre: {variety['subgenre']}; structure: {variety['structure']}.
Recent titles from similar videos (study the PATTERNS - themes, settings, emotional hooks - never copy a title or plot):
{tr}
What has retained best on this channel: {best}.
Already used on this channel (do not repeat or paraphrase; avoid reusing the central supernatural mechanism, setting and resolution even under a different title): {json.dumps(recent_topics[-30:])}
Propose 5 ORIGINAL story topics. Each must be an invented fiction premise, not a real event, person, brand or tragedy.
Return ONLY JSON: {{"candidates": [{{"topic": "short working title", "premise": "2 sentences", "angle": "what makes it fresh", "why_now": "why this fits the audience today"}}]}}"""


def pick_topic(llm, settings, recent_topics, trends, insights, variety, rng):
    prompt = build_research_prompt(settings, trends, insights, recent_topics, variety)
    for attempt in range(3):
        out = llm.generate_json(prompt)
        cands = out.get("candidates", []) if isinstance(out, dict) else out
        cands = [c for c in (cands or []) if isinstance(c, dict) and c.get("topic")]
        fresh = filter_novel(cands, recent_topics)
        if fresh: return rng.choice(fresh)
        prompt += "\nThe previous candidates were too similar to earlier topics. Invent completely different settings and mechanisms."
    raise ResearchError("every proposed topic repeats a recent one after three attempts")
