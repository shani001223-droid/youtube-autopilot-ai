import unittest
from autopilot import config, profiles, render, tts, seo

class ChannelProfileTests(unittest.TestCase):
    def test_profiles_do_not_mutate_existing_settings(self):
        original = config.load_settings("/nonexistent")
        original["publish"]["mode"] = "api"
        original["safety"]["public_publishing_enabled"] = True
        for name, language, mode in [("hindi_shorts","hi","shorts"),("english_long","en","long")]:
            s = profiles.select_profile(original, name)
            self.assertEqual(s["niche"]["language"], language)
            self.assertEqual(s["content"]["mode"], mode)
            self.assertEqual(s["publish"]["mode"], "manual")
            self.assertFalse(s["safety"]["public_publishing_enabled"])
            self.assertFalse(s["safety"]["sample_approved"])
            self.assertEqual(config.validate_settings(s), [])
        self.assertTrue(original["safety"]["public_publishing_enabled"])

    def test_hindi_sentence_split(self):
        self.assertEqual(tts.split_sentences("दरवाजा खुला। कोई अंदर था।"), ["दरवाजा खुला।", "कोई अंदर था।"])

    def test_horizontal_media_args(self):
        args = render.still_segment_args("image.jpg", 2, "out.mp4", w=1920, h=1080)
        self.assertIn("s=1920x1080", args[args.index("-vf")+1])

    def test_long_metadata_has_no_shorts_tag(self):
        s = profiles.select_profile(config.load_settings("/nonexistent"), "english_long")
        self.assertNotIn("#shorts", seo.build_description({"logline":"Fiction."}, "Title", [], s))
