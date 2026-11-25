import random, unittest
from autopilot import config, scriptgen
from tests.helpers import good_script


def fresh(): return config.load_settings("/nonexistent")


class FakeLLM:
    def __init__(self, outputs): self.outputs = list(outputs); self.prompts = []
    def generate_json(self, prompt, system=None):
        self.prompts.append(prompt); return self.outputs.pop(0)


class ScriptTests(unittest.TestCase):
    def test_words_for_seconds_uses_150_wpm(self):
        self.assertEqual(scriptgen.words_for_seconds(60), 150); self.assertEqual(scriptgen.words_for_seconds(45), 112)

    def test_choose_hook_ranks_with_hookscore(self):
        r = scriptgen.choose_hook(["Hello guys welcome to my channel today", "You will lose everything in 3 seconds if you open that door tonight?"])
        self.assertTrue(r["hook"].startswith("You will lose")); self.assertGreater(r["ranking"][0]["verdict"], r["ranking"][1]["verdict"])
        self.assertIn("formula", r)

    def test_validate_ok(self):
        s = fresh(); s["content"]["short_target_seconds"] = 45
        self.assertEqual(scriptgen.validate_script(good_script(), s), [])

    def test_validate_flags_problems(self):
        s = fresh(); sc = good_script()
        sc["scenes"][0]["visual_query"] = ""
        sc["hooks"] = sc["hooks"][:1]
        sc["scenes"][1]["narration"] += " He cut the child apart"
        errs = " ".join(scriptgen.validate_script(sc, s))
        self.assertIn("visual_query", errs); self.assertIn("hooks", errs); self.assertIn("banned", errs)

    def test_validate_word_budget(self):
        s = fresh(); short = good_script(words_per_scene=2, scenes=4)
        self.assertTrue(any("words" in e for e in scriptgen.validate_script(short, s)))

    def test_banned_topics_from_niche_are_enforced(self):
        s = fresh(); s["niche"]["banned_topics"] = ["zombie"]; sc = good_script(); sc["scenes"][2]["narration"] += " a zombie appeared"
        self.assertTrue(any("zombie" in e for e in scriptgen.validate_script(sc, s)))

    def test_variety_avoids_last_subgenre(self):
        s = fresh(); hist = [{"variety": {"subgenre": s["niche"]["subgenres"][0], "structure": "x"}}]
        for seed in range(20):
            v = scriptgen.pick_variety(s, hist, {}, random.Random(seed))
            self.assertNotEqual(v["subgenre"], s["niche"]["subgenres"][0])
            self.assertTrue({"subgenre", "structure", "visual_style", "music_mood"} <= set(v))

    def test_sentences_and_counts(self):
        sc = good_script(scenes=3); h = "Why did the radio know?"
        sentences, counts, queries = scriptgen.script_to_sentences(sc, h)
        self.assertEqual(sentences[0], h); self.assertEqual(len(counts), 3); self.assertEqual(sum(counts), len(sentences))
        self.assertEqual(len(queries), 3); self.assertIn("The radio is still on.", sentences[-2])
        self.assertEqual(sentences[-1], sc["loop_line"])

    def test_generate_script_repairs_once(self):
        s = fresh(); bad = good_script(words_per_scene=1, scenes=4); llm = FakeLLM([bad, good_script()])
        out = scriptgen.generate_script(llm, s, {"topic": "radio", "premise": "p"}, {"subgenre": "supernatural", "structure": "twist", "visual_style": "fog", "music_mood": "dread"})
        self.assertEqual(len(llm.prompts), 2); self.assertIn("words", llm.prompts[1]); self.assertEqual(scriptgen.validate_script(out, s), [])

    def test_generate_script_gives_up_with_error(self):
        s = fresh(); llm = FakeLLM([good_script(words_per_scene=1, scenes=4)] * 3)
        with self.assertRaises(scriptgen.ScriptError):
            scriptgen.generate_script(llm, s, {"topic": "t", "premise": "p"}, {"subgenre": "a", "structure": "b", "visual_style": "c", "music_mood": "dread"})


if __name__ == "__main__":
    unittest.main()
