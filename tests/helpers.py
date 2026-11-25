"""Shared fakes. Real code is tested; only the network edge is faked."""
import json, math, struct, wave


class FakeResp:
    def __init__(self, status=200, body=None, headers=None, text=None, content=b""):
        self.status_code = status
        self._body = body if body is not None else {}
        self.headers = headers or {}
        self.text = text if text is not None else json.dumps(self._body)
        self.content = content

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size=65536):
        yield self.content


class FakeSession:
    """Records every call; replies from a queue (last reply repeats)."""
    def __init__(self, replies=None):
        self.replies = list(replies or [FakeResp()])
        self.calls = []

    def _next(self):
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]

    def request(self, method, url, **kw):
        self.calls.append({"method": method, "url": url, **kw})
        return self._next()

    def get(self, url, **kw): return self.request("GET", url, **kw)
    def post(self, url, **kw): return self.request("POST", url, **kw)
    def put(self, url, **kw): return self.request("PUT", url, **kw)


def sine_synth(text, out_path, sr=22050):
    """Stand-in for Piper: 0.35 s of tone per word. Real WAV, real duration."""
    n = max(1, len(text.split()))
    dur = 0.35 * n
    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        frames = b"".join(struct.pack("<h", int(6000 * math.sin(2 * math.pi * 180 * i / sr)))
                          for i in range(int(sr * dur)))
        w.writeframes(frames)


def good_script(words_per_scene=16, scenes=6):
    sc = []
    for i in range(scenes):
        body = " ".join(f"word{i}x{j}" for j in range(words_per_scene))
        sc.append({"narration": f"The door opened again. {body}.", "visual_query": f"foggy forest night {i}", "mood": "dread"})
    return {
        "logline": "A night watchman hears his own voice on the radio.",
        "title_ideas": [f"The 3 AM radio voice {i}" for i in range(6)],
        "thumbnail_text": ["HE KNEW", "TOO LATE", "WRONG VOICE"],
        "hooks": ["You will never trust a radio at 3 AM again after this night.",
                  "At 3 AM my radio said my name.", "It was my voice, and I was asleep.",
                  "Why did the radio know what I would do next?", "Nobody tells you the dial can listen back."],
        "scenes": sc,
        "closing_line": "The radio is still on.",
        "loop_line": "And that is why I never sleep at 3 AM.",
        "tags": ["horror story", "scary stories", "mystery", "creepypasta", "short horror"],
        "content_notes": {"fiction": True, "gore_level": "none"},
    }
