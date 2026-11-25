"""Credential-free fakes so the WHOLE pipeline (script -> voice -> render -> thumbnail) can run as a smoke test.
Demo output is deliberately plain: sine-tone 'voice', generated fog visuals. It proves the plumbing, not the quality."""
import math, re, struct, wave

TOPICS = ["The radio that knew my name", "Nine knocks from the cellar", "The tenant above apartment four", "Letters from the drowned lighthouse",
          "The well that answers back", "A stranger on the night bus", "The last train to Harrow Mill", "What the scarecrow counted",
          "The empty chair at dinner", "A lullaby in the walls", "The map of rooms that moved", "Mirror in the attic stairwell"]
SENT = ["The house had been quiet for years before the sound began.", "Every night it came a little closer to the door.",
        "I told myself it was only the wind in the old pipes.", "Then it said my name in a voice I almost knew.",
        "The lights flickered and the air went cold as a cellar.", "I counted the steps and there were more than before.",
        "Nobody else in the street had heard anything at all.", "By morning the door stood open and the floor was wet."]


def demo_synth(text, out_path, sr=22050):
    n = max(1, len(text.split())); dur = 0.35 * n
    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", int(5000 * math.sin(2 * math.pi * 170 * i / sr) * (0.6 + 0.4 * math.sin(2 * math.pi * 3 * i / sr))))
                               for i in range(int(sr * dur))))


class DemoLLM:
    def __init__(self, seed=1): self.seed = seed

    def generate_json(self, prompt, system=None):
        if "[task:research]" in prompt:
            return {"candidates": [{"topic": TOPICS[(self.seed * 3 + i) % len(TOPICS)], "premise": "An invented demo premise.", "angle": "demo", "why_now": "demo"} for i in range(5)]}
        if "[task:replies]" in prompt: return {"replies": []}
        m = re.search(r"TOPIC: (.*?) \| PREMISE", prompt); topic = m.group(1) if m else "A demo story"
        scenes = [{"narration": SENT[(self.seed + i) % 8], "visual_query": ["foggy forest night", "dark hallway", "rain window", "old house", "moonlit field", "lantern"][i % 6], "mood": "dread"} for i in range(6)]
        return {"logline": f"{topic}: a short original horror story.", "title_ideas": [topic, f"3 AM: {topic.lower()}", f"Nobody believed me: {topic.lower()}", f"{topic} (true to life, but fiction)",
                f"Why I stopped answering: {topic.lower()}", f"The night of {topic.lower()}"],
                "thumbnail_text": ["HE KNEW", "TOO LATE", "DON'T LOOK"],
                "hooks": [f"You will never look at {topic.lower()} the same way after tonight.", "At three in the morning something knocked back.", "It knew my name before I ever said it.",
                          "Why did nobody else hear what I heard that night?", "Nobody warns you the dark can listen."],
                "scenes": scenes, "closing_line": "The door is still open.", "loop_line": "And that is why you will never look at it the same way.",
                "tags": ["horror story", "scary stories", "short horror", "mystery", "creepy", "fiction", "night"], "content_notes": {"fiction": True, "gore_level": "none"}}
