import unittest
from autopilot.llm import GeminiClient, GeminiError, extract_json
from tests.helpers import FakeResp, FakeSession


def ok(text):
    return FakeResp(200, {"candidates": [{"content": {"parts": [{"text": text}]}}]})


class ExtractJsonTests(unittest.TestCase):
    def test_fenced(self): self.assertEqual(extract_json('```json\n{"a": 1}\n```'), {"a": 1})
    def test_prose_around(self): self.assertEqual(extract_json('Sure! {"a": [1,2]} hope it helps'), {"a": [1, 2]})
    def test_array(self): self.assertEqual(extract_json("[1, 2]"), [1, 2])
    def test_garbage(self):
        with self.assertRaises(ValueError): extract_json("no json here")


class GeminiClientTests(unittest.TestCase):
    def make(self, replies, models=("m1", "m2")):
        self.sleeps = []
        sess = FakeSession(replies)
        return GeminiClient("KEY123", list(models), session=sess, sleep=self.sleeps.append), sess

    def test_text_and_key_in_header_not_url(self):
        c, s = self.make([ok("hello")])
        self.assertEqual(c.generate_text("hi"), "hello")
        call = s.calls[0]
        self.assertNotIn("KEY123", call["url"]); self.assertEqual(call["headers"]["x-goog-api-key"], "KEY123")

    def test_json_mode_sets_mime(self):
        c, s = self.make([ok('{"x": 1}')])
        self.assertEqual(c.generate_json("p"), {"x": 1})
        self.assertEqual(s.calls[0]["json"]["generationConfig"]["responseMimeType"], "application/json")

    def test_per_day_quota_falls_to_next_model(self):
        c, s = self.make([FakeResp(429, {"error": {"message": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}}), ok("from m2")])
        self.assertEqual(c.generate_text("x"), "from m2")
        self.assertIn("m1", s.calls[0]["url"]); self.assertIn("m2", s.calls[1]["url"]); self.assertEqual(self.sleeps, [])

    def test_per_minute_429_retries_with_sleep(self):
        c, s = self.make([FakeResp(429, {"error": {"message": "per minute"}}), ok("later")])
        self.assertEqual(c.generate_text("x"), "later"); self.assertEqual(len(self.sleeps), 1)

    def test_404_falls_back(self):
        c, s = self.make([FakeResp(404, {"error": {"message": "not found"}}), ok("ok")])
        self.assertEqual(c.generate_text("x"), "ok")

    def test_all_models_fail(self):
        c, s = self.make([FakeResp(500, {"error": {"message": "boom"}})])
        with self.assertRaises(GeminiError): c.generate_text("x")

    def test_blocked_prompt_raises(self):
        c, s = self.make([FakeResp(200, {"promptFeedback": {"blockReason": "SAFETY"}})], models=("m1",))
        with self.assertRaises(GeminiError): c.generate_text("x")


if __name__ == "__main__":
    unittest.main()
