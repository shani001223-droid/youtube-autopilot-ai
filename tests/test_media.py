import os, subprocess, tempfile, unittest
from autopilot import music, subtitles, render, thumbnail, qa, tts
from tests.helpers import sine_synth


def lavfi_clip(path, seconds=3, size="640x360", color="testsrc"):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"{color}=size={size}:rate=25:duration={seconds}",
                    "-pix_fmt", "yuv420p", str(path)], check=True)


class MusicTests(unittest.TestCase):
    def test_ambient_has_requested_duration(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "m.wav"); music.make_ambient(6, out, mood="dread", seed=3)
            self.assertAlmostEqual(render.probe(out)["duration"], 6.0, delta=0.3)

    def test_moods_and_seeds_differ_in_command(self):
        a = music.ambient_args(5, "o.wav", "dread", 1); b = music.ambient_args(5, "o.wav", "uneasy", 2)
        self.assertNotEqual(a, b)


class SubtitleTests(unittest.TestCase):
    tl = [{"text": "It was dark.", "start": 0.0, "end": 1.2}, {"text": "Nobody answered the door.", "start": 1.5, "end": 3.5}]

    def test_time_format(self):
        self.assertEqual(subtitles.fmt_ass_time(3661.5), "1:01:01.50"); self.assertEqual(subtitles.fmt_ass_time(0), "0:00:00.00")

    def test_word_timings_monotonic_and_within_sentence(self):
        w = subtitles.word_timings(self.tl)
        self.assertEqual(len(w), 3 + 4)
        self.assertTrue(all(a["end"] <= b["start"] + 1e-6 for a, b in zip(w, w[1:])))
        self.assertAlmostEqual(w[2]["end"], 1.2, places=2); self.assertAlmostEqual(w[3]["start"], 1.5, places=2)

    def test_chunks_respect_limits(self):
        w = subtitles.word_timings(self.tl)
        for ch in subtitles.chunk_words(w, max_words=3, max_chars=14): self.assertLessEqual(len(ch), 3)
        self.assertEqual(sum(len(c) for c in subtitles.chunk_words(w)), len(w))

    def test_ass_has_one_event_per_word_and_escapes(self):
        tl = [{"text": "Say {hello} now.", "start": 0, "end": 1.5}]
        ass = subtitles.build_ass(subtitles.word_timings(tl))
        self.assertEqual(ass.count("Dialogue:"), 3); self.assertIn("PlayResX: 1080", ass); self.assertIn("PlayResY: 1920", ass)
        self.assertNotIn("{hello}", ass)


class QATests(unittest.TestCase):
    def test_srt(self):
        s = qa.srt_from_timeline([{"text": "Hi.", "start": 0.0, "end": 1.0}])
        self.assertIn("00:00:00,000 --> 00:00:01,000", s); self.assertTrue(s.startswith("1\n"))

    def test_dead_air_report_runs_installed_skill(self):
        tl = [{"text": "One.", "start": 0.0, "end": 1.0}, {"text": "Two.", "start": 6.0, "end": 7.0}]
        r = qa.dead_air_report(tl)
        self.assertTrue(r["ok"]); self.assertGreaterEqual(r["gap_seconds"], 4.9)


class RenderTests(unittest.TestCase):
    def test_scene_durations_align_with_narration(self):
        tl = [{"start": 0, "end": 1}, {"start": 1.3, "end": 2.3}, {"start": 2.6, "end": 4.0}]
        self.assertEqual(render.scene_durations(tl, [2, 1], tail=0.5), [2.6, 1.9])
        self.assertAlmostEqual(sum(render.scene_durations(tl, [1, 1, 1], tail=0.5)), 4.5, places=2)

    def test_end_to_end_render_with_synthetic_inputs(self):
        with tempfile.TemporaryDirectory() as d:
            clip = os.path.join(d, "c.mp4"); lavfi_clip(clip, 2)           # shorter than the scene -> must loop
            r = tts.synthesize_all(["One two three four.", "Five six seven eight nine."], d, sine_synth, gap=0.3)
            durs = render.scene_durations(r["timeline"], [1, 1], tail=0.5)
            mus = os.path.join(d, "m.wav"); music.make_ambient(sum(durs) + 1, mus, "dread", 1)
            ass = os.path.join(d, "s.ass"); subtitles.write_ass(ass, subtitles.word_timings(r["timeline"]))
            out = os.path.join(d, "final.mp4")
            info = render.render_video([{"path": clip, "duration": durs[0]}, {"path": None, "duration": durs[1]}],
                                       r["wav"], mus, ass, out, d)
            self.assertEqual((info["width"], info["height"]), (1080, 1920))
            self.assertTrue(info["has_audio"]); self.assertTrue(info["has_video"])
            self.assertAlmostEqual(info["duration"], sum(durs), delta=0.6)
            self.assertGreater(os.path.getsize(out), 20000)
            # regression: grain made the first demo 27 Mbps / 127 MB. A Short must stay phone-friendly (< 8 Mbps).
            self.assertLess(os.path.getsize(out) * 8 / info["duration"], 8_000_000, "video bitrate too high")

    def test_thumbnail_from_frame(self):
        with tempfile.TemporaryDirectory() as d:
            clip = os.path.join(d, "c.mp4"); lavfi_clip(clip, 2, "1080x1920")
            fr = os.path.join(d, "f.jpg"); thumbnail.extract_frame(clip, 1.0, fr)
            out = os.path.join(d, "t.jpg"); thumbnail.make_thumbnail(fr, "HE KNEW TOO LATE NOW", out, size=(1080, 1920))
            from PIL import Image
            self.assertEqual(Image.open(out).size, (1080, 1920))


if __name__ == "__main__":
    unittest.main()
