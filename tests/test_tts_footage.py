import os, tempfile, unittest
from autopilot import tts, footage
from tests.helpers import FakeResp, FakeSession, sine_synth


class VoiceTests(unittest.TestCase):
    def test_blocks_noncommercial_and_unclear_voices(self):
        for v in ["en_US-ryan-high", "en_US-hfc_female-medium", "en_US-lessac-medium", "en_US-amy-medium", "en_GB-alan-low"]:
            with self.assertRaises(tts.VoiceLicenseError): tts.check_voice(v)

    def test_allows_listed_and_override(self):
        tts.check_voice("en_US-john-medium")
        tts.check_voice("en_US-ryan-high", allow_noncommercial=True)

    def test_split_sentences(self):
        self.assertEqual(tts.split_sentences('It was dark. "Who is there?" he asked! Nobody answered.'),
                         ["It was dark.", '"Who is there?" he asked!', "Nobody answered."])
        self.assertEqual(tts.split_sentences("  "), [])

    def test_build_timeline(self):
        t = tts.build_timeline(["a", "b"], [1.0, 2.0], gap=0.5)
        self.assertEqual(t, [{"text": "a", "start": 0.0, "end": 1.0}, {"text": "b", "start": 1.5, "end": 3.5}])

    def test_synthesize_all_matches_real_wav_duration(self):
        with tempfile.TemporaryDirectory() as d:
            r = tts.synthesize_all(["One two three.", "Four five."], d, sine_synth, gap=0.3)
            self.assertTrue(os.path.exists(r["wav"]))
            self.assertAlmostEqual(r["duration"], tts.wav_duration(r["wav"]), delta=0.05)
            self.assertAlmostEqual(r["timeline"][1]["start"], 3 * 0.35 + 0.3, delta=0.05)

    def test_piper_wrapper_builds_command_and_checks_voice(self):
        calls = []
        class R: returncode = 0; stderr = ""
        def runner(cmd, **kw): calls.append((cmd, kw)); return R()
        synth = tts.piper_synth("en_US-john-medium", data_dir="voices", runner=runner)
        synth("Hello there.", "/tmp/x.wav")
        cmd, kw = calls[0]
        self.assertIn("en_US-john-medium", cmd); self.assertIn("/tmp/x.wav", cmd); self.assertEqual(kw["input"], "Hello there.")
        with self.assertRaises(tts.VoiceLicenseError): tts.piper_synth("en_US-ryan-high", runner=runner)


def vid(slug, files, vid_id=1):
    return {"id": vid_id, "url": f"https://www.pexels.com/video/{slug}-{vid_id}/", "duration": 12,
            "user": {"name": "Jane Doe", "url": "https://www.pexels.com/@jane"}, "video_files": files}


def f(w, h, ft="video/mp4", link="http://x/v.mp4"): return {"width": w, "height": h, "file_type": ft, "link": link, "quality": "hd"}


class FootageTests(unittest.TestCase):
    def test_people_filter(self):
        self.assertFalse(footage.is_people_free(vid("woman-walking-in-forest", [])))
        self.assertFalse(footage.is_people_free(vid("silhouette-of-a-man-at-night", [])))
        self.assertTrue(footage.is_people_free(vid("foggy-forest-at-night", [])))

    def test_pick_file_prefers_portrait_mp4_near_1920(self):
        v = vid("x", [f(1080, 1920), f(720, 1280), f(1920, 1080), f(1080, 1920, "video/webm"), f(2160, 3840)])
        self.assertEqual((footage.pick_file(v)["width"], footage.pick_file(v)["height"]), (1080, 1920))

    def test_pick_file_none_when_too_small(self):
        self.assertIsNone(footage.pick_file(vid("x", [f(360, 640)])))

    def test_attribution(self):
        a = footage.attribution(vid("foggy-forest", []))
        self.assertIn("Jane Doe", a); self.assertIn("Pexels", a)

    def test_search_sends_auth_header_and_params(self):
        s = FakeSession([FakeResp(200, {"videos": [vid("a", [f(1080, 1920)])]})])
        out = footage.PexelsClient("PXKEY", session=s).search_videos("fog", per_page=5)
        self.assertEqual(len(out), 1); c = s.calls[0]
        self.assertEqual(c["headers"]["Authorization"], "PXKEY"); self.assertEqual(c["params"]["orientation"], "portrait")
        self.assertEqual(c["params"]["per_page"], 5)

    def test_select_clips_fallbacks_and_no_repeats(self):
        class P:
            def __init__(self): self.q = []
            def search_videos(self, q, **kw):
                self.q.append(q)
                if "empty" in q: return []
                return [vid("people-talking", [f(1080, 1920)], 9), vid("dark-hallway", [f(1080, 1920)], 1), vid("old-house", [f(1080, 1920)], 2), vid("moonlit-field", [f(1080, 1920)], 3)]
            def download(self, url, dest): open(dest, "wb").write(b"x")
        with tempfile.TemporaryDirectory() as d:
            clips = footage.select_clips(P(), ["empty zzz", "hallway", "hallway"], [4.0, 4.0, 4.0], d)
            ids = [c["video_id"] for c in clips]
            self.assertEqual(len(clips), 3); self.assertNotIn(9, ids); self.assertEqual(len(set(ids)), 3)
            self.assertTrue(all(os.path.exists(c["path"]) for c in clips))

    def test_select_clips_returns_none_paths_when_pexels_is_down(self):
        class P:
            def search_videos(self, q, **kw): raise RuntimeError("down")
        with tempfile.TemporaryDirectory() as d:
            clips = footage.select_clips(P(), ["a", "b"], [3.0, 3.0], d)
            self.assertEqual([c["path"] for c in clips], [None, None])


if __name__ == "__main__":
    unittest.main()
