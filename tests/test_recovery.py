import random, tempfile, unittest
from autopilot import config, pipeline, reserve, scriptgen
from autopilot.llm import GeminiClient, GeminiError, GeminiUnavailable
from autopilot.footage import PexelsClient
from autopilot.state import Store
from tests.helpers import FakeResp, FakeSession

def ok(text):
    return FakeResp(200, {"candidates":[{"content":{"parts":[{"text":text}]}}]})

class RecoveryTests(unittest.TestCase):
    def test_daily_quota_cached(self):
        s=FakeSession([FakeResp(429, {"error":{"message":"per day"}}), ok('{"ok":true}')])
        c=GeminiClient("secret", ["a","b"], session=s, sleep=lambda n:None)
        c.generate_json("x"); c.generate_json("y")
        self.assertEqual(len(s.calls),3)
        self.assertIn("/b:",s.calls[-1]["url"])
    def test_invalid_json_fallback(self):
        c=GeminiClient("secret",["a","b"],session=FakeSession([ok("bad"),ok('{"ok":true}')]))
        self.assertEqual(c.generate_json("x"),{"ok":True})
    def test_outage(self):
        c=GeminiClient("secret",["a"],session=FakeSession([FakeResp(503)]),sleep=lambda n:None)
        with self.assertRaises(GeminiUnavailable): c.generate_json("x")
    def test_safety_block_not_outage(self):
        c=GeminiClient("secret",["a"],session=FakeSession([FakeResp(200,{"promptFeedback":{"blockReason":"SAFETY"}})]))
        with self.assertRaises(GeminiError) as ctx: c.generate_json("x")
        self.assertNotIsInstance(ctx.exception,GeminiUnavailable)
    def test_reserve_unique_and_valid(self):
        s=config.load_settings("/nonexistent"); recent=[]
        for _ in reserve.STORIES:
            topic,script=reserve.reserve_story(s,recent,random.Random(1))
            self.assertFalse(scriptgen.validate_script(script,s))
            self.assertNotIn(topic["topic"],recent)
            recent.append(topic["topic"])
        with self.assertRaises(GeminiUnavailable): reserve.reserve_story(s,recent,random.Random(1))
    def test_wrong_language(self):
        s=config.load_settings("/nonexistent"); s["niche"]["language"]="ur"
        with self.assertRaises(GeminiUnavailable): reserve.reserve_story(s,[],random.Random(1))
    def test_pexels_retry(self):
        sleeps=[]; s=FakeSession([FakeResp(503),FakeResp(200,{"videos":[{"id":1}]})])
        self.assertEqual(PexelsClient(" key ",session=s,sleep=sleeps.append).search_videos("fog"),[{"id":1}])
        self.assertEqual(sleeps,[2])
        self.assertEqual(s.calls[-1]["headers"]["Authorization"],"key")
    def test_reject_clears_preview(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(d); item=store.add_item({"status":"awaiting_approval","preview_url":"old","thumb_url":"old"})
            result=pipeline.run_publish(config.load_settings("/nonexistent"),store,item["id"],"reject")
            self.assertIsNone(result["preview_url"]); self.assertIsNone(result["thumb_url"])
    def test_repeat_approval(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(d); item=store.add_item({"status":"approved_manual"})
            result=pipeline.run_publish(config.load_settings("/nonexistent"),store,item["id"],"approve")
            self.assertEqual(result["status"],"approved_manual")
