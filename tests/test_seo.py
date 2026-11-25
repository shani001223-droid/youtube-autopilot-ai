import unittest
from autopilot import config, seo
from tests.helpers import good_script


class SeoTests(unittest.TestCase):
    def test_choose_title_avoids_thumb_duplicate_and_length(self):
        r = seo.choose_title(["The Radio That Knew My Name And Everything About My Whole Life Story Today Now",
                              "The 3 AM radio voice", "3 AM: the radio said my name"], ["WRONG VOICE", "HE KNEW"])
        self.assertLessEqual(len(r["title"]), 60); self.assertIn(r["thumb_text"], ["WRONG VOICE", "HE KNEW"])
        self.assertLessEqual(len(r["thumb_text"].split()), 3)

    def test_clean_tags(self):
        t = seo.clean_tags(["#Horror", "horror", " Scary Stories ", "x" * 80] + [f"tag{i}" for i in range(40)])
        self.assertEqual(t[0], "Horror"); self.assertLessEqual(len(t), 15); self.assertLessEqual(sum(len(x) + 1 for x in t), 450)
        self.assertEqual(len({x.lower() for x in t}), len(t)); self.assertTrue(all(len(x) <= 30 for x in t))

    def test_description(self):
        s = config.load_settings("/nonexistent"); sc = good_script()
        d = seo.build_description(sc, "The 3 AM radio voice", ["Video by Jane on Pexels (https://pexels.com/@jane)"], s)
        first_two = "\n".join(d.splitlines()[:2]).lower()
        self.assertIn("radio", first_two); self.assertIn("Pexels", d); self.assertIn("fiction", d.lower()); self.assertLess(len(d), 5000)
        self.assertNotIn("<", d); self.assertNotIn(">", d)

    def test_query_test_reports_uncovered_queries(self):
        miss = seo.query_test("The 3 AM radio voice", "A night watchman hears his own voice on the radio.\nMore.",
                              ["radio voice story", "lighthouse mystery"])
        self.assertEqual(miss, ["lighthouse mystery"])

    def test_chapters_validator_follows_youtube_rules(self):
        ok = ["00:00 Intro", "00:20 Middle", "01:00 End"]
        self.assertTrue(seo.chapters_valid(ok))
        self.assertFalse(seo.chapters_valid(["00:05 Intro", "00:20 Middle", "01:00 End"]))   # must start at 00:00
        self.assertFalse(seo.chapters_valid(["00:00 Intro", "00:20 Middle"]))                 # at least three
        self.assertFalse(seo.chapters_valid(["00:00 A", "00:05 B", "01:00 C"]))               # each >= 10 s


if __name__ == "__main__":
    unittest.main()
