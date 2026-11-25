import random
import unittest
from autopilot import config, research, render, scriptgen

class CinematicUpgradeTests(unittest.TestCase):
    def test_language_and_long_prompt(self):
        settings = config.load_settings("/nonexistent")
        variety = {"subgenre":"mystery","structure":"reveal","visual_style":"rain"}
        settings["niche"]["language"] = "hi"
        p = scriptgen.build_script_prompt(settings, {}, variety)
        self.assertIn("Hindi in Devanagari", p)
        self.assertIn("vertical short-form", p)
        settings["niche"]["language"] = "en"
        settings["content"]["mode"] = "long"
        p = scriptgen.build_script_prompt(settings, {}, variety)
        self.assertIn("1200 spoken words", p)
        self.assertIn("horizontal long-form", p)

    def test_repeat_hindi_title(self):
        self.assertEqual(research.novelty("पुराना दरवाजा", "पुराना दरवाजा"), 0)

    def test_retry_duplicate(self):
        class LLM:
            def __init__(self): self.calls = 0
            def generate_json(self, prompt):
                self.calls += 1
                return {"candidates":[{"topic":"Old radio" if self.calls == 1 else "Silent lighthouse"}]}
        llm = LLM()
        result = research.pick_topic(llm, config.load_settings("/nonexistent"), ["Old radio"], [], {}, {"subgenre":"mystery","structure":"reveal"}, random.Random(0))
        self.assertEqual(result["topic"], "Silent lighthouse")
        self.assertEqual(llm.calls, 2)

    def test_distinct_camera_motion(self):
        filters = []
        for i in range(3):
            args = render.still_segment_args("image.jpg", 2, "out.mp4", motion=i)
            filters.append(args[args.index("-vf")+1])
        self.assertEqual(len(set(filters)), 3)

if __name__ == "__main__":
    unittest.main()
