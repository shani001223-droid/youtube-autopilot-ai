"""Script stage. Rules come from the installed skills: yt-script (5 hooks, scored, keep the best; 150 wpm) and
yt-shorts (opens on a complete thought, has a turn, ends on a line, has a loop point; 20-55 s)."""
import json, os, re
from . import improve, tts
from .skills import hookscore

STRUCTURES = ["twist in the last line", "slow reveal through a letter", "countdown to something arriving", "found recording transcript",
              "two timelines that collide", "unreliable narrator", "a list of rules that gets darker", "one phone call, in real time"]
VISUAL_STYLES = ["fog and night forest", "abandoned interiors", "rain and streetlights", "old houses and stairwells", "fields at dusk", "sea mist and lighthouse"]
MUSIC_MOODS = ["dread", "uneasy", "hollow", "pulse"]
BANNED = [(re.compile(p, re.I), label) for p, label in [
    (r"\b(rape[sd]?|molest\w*|sexual assault)\b", "sexual violence"),
    (r"\b(suicide|kill (?:my|your|him|her)self|self[- ]harm)\b", "suicide / self-harm"),
    (r"\b(school shooting|mass shooting|holocaust|genocide|9/11)\b", "real tragedy"),
]]
CHILD = re.compile(r"\b(child|children|kid|kids|baby|infant|toddler)\b", re.I)
VIOLENT = re.compile(r"\b(cut|cuts|killed|kills|murder\w*|torture\w*|abus\w*|dismember\w*|mutilat\w*|stab\w*|strangl\w*)\b", re.I)


class ScriptError(Exception):
    pass


def words_for_seconds(seconds, wpm=150):
    return int(seconds * wpm / 60)


def choose_hook(hooks):
    rows = []
    for h in hooks:
        parts, verdict, name, hits = hookscore.score(h)
        rows.append({"hook": h, "verdict": verdict, "band": hookscore.band(verdict), "formula": name, "properties": parts})
    rows.sort(key=lambda r: -r["verdict"])
    return {"hook": rows[0]["hook"], "score": rows[0]["verdict"], "band": rows[0]["band"], "formula": rows[0]["formula"], "ranking": rows}


def pick_variety(settings, history, insights, rng):
    last = (history[-1].get("variety") or {}) if history else {}
    subs = [s for s in settings["niche"]["subgenres"] if s != last.get("subgenre")] or settings["niche"]["subgenres"]
    recent_structs = {(h.get("variety") or {}).get("structure") for h in history[-2:]}
    structs = [s for s in STRUCTURES if s not in recent_structs] or STRUCTURES
    return {"subgenre": improve.pick_subgenre(subs, insights, rng), "structure": rng.choice(structs),
            "visual_style": rng.choice(VISUAL_STYLES), "music_mood": rng.choice(MUSIC_MOODS)}


def normalize_script(raw):
    if isinstance(raw, list) and raw and isinstance(raw[0], dict): raw = raw[0]
    if not isinstance(raw, dict): raise ScriptError("model did not return a JSON object")
    clean = lambda x: str(x or "").strip()
    scenes = [{"narration": clean(s.get("narration")), "visual_query": clean(s.get("visual_query")), "mood": clean(s.get("mood")) or "dread"}
              for s in raw.get("scenes", []) if isinstance(s, dict)]
    lst = lambda k: [clean(x) for x in raw.get(k, []) if clean(x)]
    return {"logline": clean(raw.get("logline")), "title_ideas": lst("title_ideas"), "thumbnail_text": lst("thumbnail_text"), "hooks": lst("hooks"),
            "scenes": scenes, "closing_line": clean(raw.get("closing_line")), "loop_line": clean(raw.get("loop_line")), "tags": lst("tags"),
            "content_notes": raw.get("content_notes") if isinstance(raw.get("content_notes"), dict) else {}}


def _spoken_words(script):
    text = " ".join([script["hooks"][0] if script["hooks"] else ""] + [s["narration"] for s in script["scenes"]] + [script["closing_line"], script["loop_line"]])
    return len(text.split())


def validate_script(script, settings):
    e, c = [], settings["content"]
    long = c["mode"] == "long"
    if len(script["hooks"]) < 3: e.append("need at least 3 hooks")
    if len(script["title_ideas"]) < 3: e.append("need at least 3 title_ideas")
    if not script["thumbnail_text"]: e.append("need thumbnail_text")
    lo, hi = (12, 60) if long else (4, 10)
    if not lo <= len(script["scenes"]) <= hi: e.append(f"scenes must be {lo}-{hi}, got {len(script['scenes'])}")
    for i, s in enumerate(script["scenes"]):
        if not s["narration"]: e.append(f"scene {i}: missing narration")
        if not s["visual_query"]: e.append(f"scene {i}: missing visual_query")
    if not script["closing_line"] or not script["loop_line"]: e.append("need closing_line and loop_line")
    target = words_for_seconds(c["long_target_minutes"] * 60 if long else c["short_target_seconds"])
    n = _spoken_words(script)
    if not 0.65 * target <= n <= 1.4 * target: e.append(f"spoken words {n}; target about {target} (allowed {int(.65 * target)}-{int(1.4 * target)})")
    if script["hooks"] and len(script["hooks"][0].split()) > 30: e.append("first hook is too long to land in 10 seconds")
    text = " ".join(s["narration"] for s in script["scenes"]) + " " + script["closing_line"] + " " + script["loop_line"]
    for rx, label in BANNED:
        if rx.search(text): e.append(f"banned content: {label}")
    for sent in re.split(r"(?<=[.!?])\s+", text):
        if CHILD.search(sent) and VIOLENT.search(sent): e.append("banned content: violence involving a child"); break
    for t in settings["niche"]["banned_topics"]:
        if t.strip() and t.lower() in text.lower(): e.append(f"banned topic '{t}' appears in the story")
    return e


def script_to_sentences(script, hook):
    sentences, counts, queries = [], [], []
    last = len(script["scenes"]) - 1
    for i, sc in enumerate(script["scenes"]):
        text = sc["narration"]
        if i == 0: text = hook.strip() + " " + text
        if i == last: text = text + " " + script["closing_line"] + " " + script["loop_line"]
        parts = tts.split_sentences(text); sentences += parts; counts.append(len(parts)); queries.append(sc["visual_query"])
    return sentences, counts, queries


def build_script_prompt(settings, topic, variety):
    n, c = settings["niche"], settings["content"]
    with open(os.path.join(os.path.dirname(__file__), "skills", "hooks.json"), encoding="utf-8") as fh:
        formulas = ", ".join(f["name"] for f in json.load(fh)["hooks"][:21])
    long = c["mode"] == "long"
    seconds = c["long_target_minutes"] * 60 if long else c["short_target_seconds"]
    target = words_for_seconds(seconds)
    language = "natural spoken Hindi in Devanagari" if n.get("language") == "hi" else "natural spoken English"
    format_name = "horizontal long-form" if long else "vertical short-form"
    scene_count = "24-40" if long else "5-8"
    pacing = "Build three escalating acts, with a new clue or reversal every 30-45 seconds; resolve the central mystery." if long else "Open immediately, escalate every scene, and land a surprising but earned final twist."
    return f"""[task:script]
You write original {n['name']} for a {format_name} video channel. Audience: {n['audience']}. Tone: {n['tone']}.
TOPIC: {topic.get('topic')} | PREMISE: {topic.get('premise')} | ANGLE: {topic.get('angle')}
SUBGENRE: {variety['subgenre']} | STRUCTURE: {variety['structure']} | VISUAL STYLE: {variety['visual_style']}
LENGTH: about {target} spoken words in total ({seconds} seconds at 150 words per minute), {scene_count} scenes.
LANGUAGE: {language} for all spoken lines, titles and thumbnail text; keep visual_query in English for media search.
PACING: {pacing}

RULES (non-negotiable):
- Invent a distinct protagonist, setting, central mystery, clue progression and resolution; avoid familiar stock twists unless transformed into a genuinely different mechanism.
- 100% original fiction. No real people, real crimes, real tragedies, brands or copyrighted characters. No gore, no sexual content, nothing involving harm to children, no suicide or self-harm.
- Open on a complete thought (a viewer who has seen nothing else must understand line one). Include one turn that complicates the opening. End on a line, not a trail-off.
- Write 5 DIFFERENT hooks (each 9-24 words, speak to 'you' or raise a question the viewer cannot close). Formulas to draw on: {formulas}.
- For Shorts, loop_line must set up the first hook. For long-form, loop_line is a short final unsettling callback rather than a forced loop. closing_line is one short sentence.
- visual_query for each scene: 2-6 concrete English words describing the exact key SCENERY or OBJECT in the narration. Prefer specific, visually distinct shots (cracked station clock, rain-soaked ticket window, rusted railway signal). Maintain location, weather and time-of-day continuity. Alternate establishing shots, detail shots and reveal shots; never people, faces, bodies or hands. Do not reuse identical queries.
- Keep every sentence speakable aloud. No stage directions, no emoji, no hashtags in narration.
- title_ideas: 6 titles under 60 characters, front-load the subject, include a number or a name when natural. thumbnail_text: 3 options of at most 3 words that do NOT repeat the title's words.
- tags: 10 short search phrases people actually type.

Return ONLY this JSON:
{{"logline": "...", "title_ideas": ["..."], "thumbnail_text": ["..."], "hooks": ["..."],
 "scenes": [{{"narration": "...", "visual_query": "...", "mood": "dread"}}],
 "closing_line": "...", "loop_line": "...", "tags": ["..."], "content_notes": {{"fiction": true, "gore_level": "none"}}}}"""


def generate_script(llm, settings, topic, variety):
    base = build_script_prompt(settings, topic, variety); prompt, errs = base, []
    for _ in range(3):
        script = normalize_script(llm.generate_json(prompt))
        errs = validate_script(script, settings)
        if not errs: return script
        prompt = base + "\n\nYour previous attempt had these problems. Fix ALL of them and return the complete JSON again:\n- " + "\n- ".join(errs)
    raise ScriptError("script failed validation after 3 attempts: " + "; ".join(errs))
