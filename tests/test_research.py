import random, unittest
from datetime import datetime, timezone
from autopilot import config, research


class FakeYT:
    def search_recent(self, query, published_after, max_results=10):
        return [{"id": "a", "title": "Scary lighthouse story", "channel": "C1", "channel_id": "UC1"},
                {"id": "b", "title": "Haunted radio at 3 AM", "channel": "C2", "channel_id": "UC2"}]


class FakeLLM:
    def __init__(self, out): self.out = out
    def generate_json(self, prompt, system=None): return self.out


class ResearchTests(unittest.TestCase):
    def test_novelty(self):
        self.assertEqual(research.novelty("haunted radio", "haunted radio"), 0.0)
        self.assertGreater(research.novelty("haunted radio at night", "lighthouse keeper letters"), 0.8)

    def test_filter_novel_drops_near_duplicates(self):
        c = [{"topic": "The haunted radio at 3 AM"}, {"topic": "Letters from a drowned lighthouse keeper"}]
        out = research.filter_novel(c, ["Haunted radio at 3 AM"], threshold=0.5)
        self.assertEqual([x["topic"] for x in out], ["Letters from a drowned lighthouse keeper"])

    def test_swipe_rank_runs_the_installed_skill(self):
        vids = [{"channel": "A", "title": f"v{i}", "views": 1000 + i, "url": "u", "duration": 40} for i in range(5)]
        vids.append({"channel": "A", "title": "Why you should never answer this call", "views": 90000, "url": "u2", "duration": 40})
        ranked = research.swipe_rank(vids, min_multiple=2.0)
        self.assertTrue(ranked); self.assertIn("never answer", ranked[0]["title"])

    def test_swipe_rank_empty_when_not_enough_data(self):
        self.assertEqual(research.swipe_rank([{"channel": "A", "title": "x", "views": 5, "url": "u", "duration": 1}]), [])

    def test_trend_titles(self):
        s = config.load_settings("/nonexistent")
        t = research.trend_titles(FakeYT(), s, datetime(2026, 11, 24, tzinfo=timezone.utc), max_queries=2)
        self.assertEqual(sorted(x["title"] for x in t), ["Haunted radio at 3 AM", "Scary lighthouse story"])  # de-duplicated across queries

    def test_pick_topic_skips_recent(self):
        s = config.load_settings("/nonexistent")
        out = {"candidates": [{"topic": "Haunted radio at 3 AM", "premise": "p", "angle": "a"},
                              {"topic": "The well that answers back", "premise": "p2", "angle": "a2"}]}
        topic = research.pick_topic(FakeLLM(out), s, ["Haunted radio at 3 AM"], [], {}, {"subgenre": "folk horror", "structure": "twist"}, random.Random(1))
        self.assertEqual(topic["topic"], "The well that answers back")

    def test_pick_topic_all_duplicates_raises(self):
        s = config.load_settings("/nonexistent")
        out = {"candidates": [{"topic": "Haunted radio at 3 AM", "premise": "p", "angle": "a"}]}
        with self.assertRaises(research.ResearchError):
            research.pick_topic(FakeLLM(out), s, ["Haunted radio at 3 AM"], [], {}, {"subgenre": "x", "structure": "y"}, random.Random(1))


if __name__ == "__main__":
    unittest.main()
