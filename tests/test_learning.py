import random, unittest
from autopilot import analytics, improve, audit, comments


def rec(i, sub, pct, views=100, title=None, day=None):
    return {"id": f"i{i}", "video_id": f"v{i}", "title": title or f"Story number {i}", "views": views, "avg_view_pct": pct,
            "published_at": day or f"2026-11-{10 + i:02d}T18:00:00Z", "variety": {"subgenre": sub, "structure": "twist"}}


class AnalyticsTests(unittest.TestCase):
    def test_retention_csv_percent_axis(self):
        self.assertEqual(analytics.retention_csv([(0.01, 1.0), (0.5, 0.6)]).splitlines(), ["1.0,100.0", "50.0,60.0"])

    def test_retention_report_runs_installed_skill(self):
        pts = [(i / 20, max(0.2, 1 - 0.04 * i)) for i in range(1, 21)]
        r = analytics.retention_report(pts, duration=45)
        self.assertTrue(r["ok"]); self.assertIn("raw", r)

    def test_retention_report_needs_data(self):
        self.assertFalse(analytics.retention_report([(0.1, 1.0)], duration=45)["ok"])

    def test_collect_merges_stats(self):
        class YT:
            def video_stats(self, ids): return {"v1": {"views": 50, "likes": 5, "comments": 1}}
            def analytics(self, vid, s, e): return {"views": 50, "averageViewPercentage": 72.0, "estimatedMinutesWatched": 10}
        items = [{"id": "i1", "video_id": "v1", "title": "T", "variety": {"subgenre": "a"}, "published_at": "2026-11-20T18:00:00Z"},
                 {"id": "i2", "title": "no video yet"}]
        out = analytics.collect(YT(), items, "2026-11-24")
        self.assertEqual(len(out), 1); self.assertEqual((out[0]["views"], out[0]["avg_view_pct"]), (50, 72.0))

    def test_collect_survives_analytics_failure(self):
        class YT:
            def video_stats(self, ids): return {"v1": {"views": 7, "likes": 0, "comments": 0}}
            def analytics(self, *a): raise RuntimeError("scope missing")
        out = analytics.collect(YT(), [{"id": "i1", "video_id": "v1", "title": "T"}], "2026-11-24")
        self.assertEqual(out[0]["views"], 7); self.assertIsNone(out[0]["avg_view_pct"])


class ImproveTests(unittest.TestCase):
    def recs(self):
        return [rec(1, "folk horror", 80), rec(2, "folk horror", 70), rec(3, "folk horror", 75),
                rec(4, "haunted places", 40), rec(5, "haunted places", 50), rec(6, "haunted places", 45)]

    def test_rank_traits(self):
        r = improve.rank_traits(self.recs(), "subgenre", min_samples=3)
        self.assertEqual(r[0]["value"], "folk horror"); self.assertAlmostEqual(r[0]["mean_view_pct"], 75.0)

    def test_min_samples_prevents_noise(self):
        self.assertEqual(improve.rank_traits(self.recs()[:2], "subgenre", min_samples=3), [])

    def test_pick_subgenre_exploits_then_explores(self):
        ins = improve.build_insights(self.recs())
        subs = ["folk horror", "haunted places", "supernatural"]
        self.assertEqual(improve.pick_subgenre(subs, ins, random.Random(1), epsilon=0.0), "folk horror")
        seen = {improve.pick_subgenre(subs, ins, random.Random(s), epsilon=1.0) for s in range(30)}
        self.assertEqual(seen, set(subs))

    def test_pick_subgenre_without_data_is_uniform_choice(self):
        self.assertIn(improve.pick_subgenre(["a", "b"], {}, random.Random(2)), ["a", "b"])


class AuditTests(unittest.TestCase):
    def test_one_fix_for_samey_titles(self):
        recs = [rec(i, "a", 50, title=f"Why you should never open door {i}?") for i in range(1, 7)]
        r = audit.audit_channel(recs)
        self.assertIn("shape", r["fix"].lower()); self.assertIsInstance(r["fix"], str); self.assertTrue(r["working"] is not None)

    def test_rhythm_problem(self):
        days = ["2026-11-01", "2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-12-20"]
        titles = ["I heard it twice", "Letters from the well", "3 rooms nobody enters", "The tenant upstairs", "What the tide returned", "Nine knocks at dawn"]
        recs = [rec(i, "a", 50, title=t, day=f"{d}T18:00:00Z") for i, (t, d) in enumerate(zip(titles, days))]
        self.assertIn("consisten", audit.audit_channel(recs)["fix"].lower())

    def test_not_enough_data(self):
        self.assertIn("not enough", audit.audit_channel([rec(1, "a", 50)])["fix"].lower())


class CommentTests(unittest.TestCase):
    def test_triage_piles(self):
        cs = [{"id": "1", "text": "What is the name of the song at the end?"}, {"id": "2", "text": "Actually it's pronounced lie-bury, not library"},
              {"id": "3", "text": "This scared me so much, loved the twist about the radio"}, {"id": "4", "text": "ur channel sucks lol"},
              {"id": "5", "text": "first"}]
        t = comments.triage(cs)
        self.assertEqual([c["id"] for c in t["questions"]], ["1"]); self.assertEqual([c["id"] for c in t["corrections"]], ["2"])
        self.assertEqual([c["id"] for c in t["praise"]], ["3"]); self.assertEqual([c["id"] for c in t["bait"]], ["4"])

    def test_prompt_carries_yt_comment_rules(self):
        p = comments.draft_prompt([{"id": "1", "text": "Where is this set?"}], {"name": "Night Shift Tales"})
        self.assertIn("30 words", p); self.assertIn("Never promise", p)


if __name__ == "__main__":
    unittest.main()
