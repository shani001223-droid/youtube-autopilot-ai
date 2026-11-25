"""Finite original story reserve for English horror shorts; never uses demo scripts."""
from .llm import GeminiUnavailable
from .research import filter_novel
from .scriptgen import normalize_script, validate_script

class UnavailableClient:
    def generate_json(self, *args, **kwargs):
        raise GeminiUnavailable("GEMINI_API_KEY missing")

STORIES = [
    ("The Clock in the Locked Station", "An abandoned station clock counts backward toward an impossible arrival.",
     ["The station clock ran backward, even though its power cable lay severed.",
      "At first I thought the hands were loose. Then the old departure board clicked to life.",
      "Every destination was blank except my street. The arrival time was three minutes ago.",
      "I hurried home and found a paper ticket beneath the door, still warm from a machine.",
      "The ticket showed my address and tomorrow's date. Outside, a bell rang where no railway had ever been."],
     ["abandoned railway station", "old station clock", "empty railway platform", "paper ticket door", "foggy street night"],
     "The next train is already here.", "Check the time before you leave."),
    ("The Lighthouse Without a Coast", "A light appears in a field where no lighthouse exists.",
     ["A white beam swept across the wheat every night, always at exactly the same moment.",
      "There was no tower nearby, only a rusted gate and a road that ended at the field.",
      "I followed the light and discovered a brass compass hanging from a wooden post.",
      "The needle pointed straight down. From below the soil came the soft rhythm of distant waves.",
      "The beam stopped over my house. Saltwater began gathering inside the windows, though the glass was dry."],
     ["wheat field dusk", "rusted gate", "old brass compass", "sea waves night", "dark house window"],
     "Something is guiding the sea inland.", "Watch where the light points next."),
    ("The Archive of Unwritten Letters", "A clerk receives letters describing events that haven't happened.",
     ["A sealed envelope arrived at the archive with a postmark dated next Thursday.",
      "Inside was a description of a lamp falling from my desk. I laughed and pushed the lamp farther back.",
      "It fell anyway, without anyone touching it. A second envelope appeared inside the locked drawer.",
      "This time the letter described a window opening during a storm. I checked every latch.",
      "When the wind rose, the glass stayed shut. But the letter itself began flapping like a curtain."],
     ["old archive room", "sealed envelope", "desk lamp", "locked wooden drawer", "rain on window"],
     "The last envelope has my handwriting.", "Read the date before opening yours."),
    ("The Lake That Reflected Tomorrow", "A still lake reflects a day that has not arrived.",
     ["The lake reflected a red autumn forest, even though every tree around it was green.",
      "I put a stone on the bank. In the reflection, the stone was already lying beneath the water.",
      "The following morning I returned. The leaves had changed, but only along the water's edge.",
      "A wooden bench stood on the far shore. Its reflection was empty except for a small lantern.",
      "I backed away as the reflected lantern brightened. Behind me, the real path vanished into mist."],
     ["still forest lake", "autumn trees reflection", "stone shoreline", "empty wooden bench", "lantern fog"],
     "The lake is waiting for another morning.", "Look twice before trusting a reflection."),
]

def reserve_story(settings, recent, rng):
    if settings.get("profile") in ("hindi_shorts", "english_long"):
        from .reserve_profiles import reserve_profile
        return reserve_profile(settings, recent, rng)
    niche = settings["niche"]
    if niche.get("language") != "en" or settings["content"]["mode"] != "shorts" or "horror" not in niche.get("name", "").lower():
        raise GeminiUnavailable("original reserve is only configured for English horror shorts")
    options = []
    for title, premise, narration, queries, closing, loop in STORIES:
        topic = {"topic": title, "premise": premise, "angle": "original reserve", "why_now": "provider outage; no live trend claim"}
        if not filter_novel([topic], recent): continue
        raw = {"logline": premise, "title_ideas": [title, title + " | A Mystery", "The Strange Truth: " + title],
               "thumbnail_text": ["NOT POSSIBLE", "LOOK AGAIN", "NO WAY"],
               "hooks": [premise, "What would you do if the ordinary world suddenly stopped obeying its own rules?",
                         "I thought I understood what I was seeing. Then everything changed."],
               "scenes": [{"narration": n, "visual_query": q, "mood": "dread"} for n, q in zip(narration, queries)],
               "closing_line": closing, "loop_line": loop,
               "tags": ["original horror", "short mystery", "creepy fiction", "scary story"],
               "content_notes": {"fiction": True, "gore_level": "none"}}
        script = normalize_script(raw)
        if any(t.strip() and t.lower() in (title + " " + premise + " " + " ".join(raw["hooks"])).lower() for t in niche["banned_topics"]): continue
        if not validate_script(script, settings): options.append((topic, script))
    if not options: raise GeminiUnavailable("original story reserve exhausted or unsuitable for current settings; retry when Gemini recovers")
    return rng.choice(options)
