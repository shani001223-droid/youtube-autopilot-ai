import os, shutil, tempfile, unittest
from datetime import datetime, timezone
from autopilot import cli, config, pipeline
from autopilot.llm import GeminiError
from autopilot.state import Store
from tests.helpers import FakeResp, FakeSession

NOW = datetime(2026, 11, 24, 10, 0, tzinfo=timezone.utc)


def fresh(): return config.load_settings("/nonexistent")


class FakeYT:
    def __init__(self): self.uploads = []; self.thumbs = []; self.updates = []
    def upload(self, path, body): self.uploads.append((path, body)); return "VID12345678"
    def set_thumbnail(self, vid, path): self.thumbs.append((vid, path))
    def update_status(self, vid, status): self.updates.append((vid, status))


def generated(d, store):
    deps = pipeline.demo_deps(seed=1, now=NOW)
    return pipeline.run_generate(fresh(), store, deps, workdir=d, demo=True)


class GenerateTests(unittest.TestCase):
    def test_demo_pipeline_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(os.path.join(d, "data")); item = generated(os.path.join(d, "out"), store)
            self.assertEqual(item["status"], "awaiting_approval", item.get("error"))
            self.assertTrue(os.path.exists(item["files"]["video"])); self.assertTrue(os.path.exists(item["files"]["thumb"]))
            self.assertEqual((item["video_info"]["width"], item["video_info"]["height"]), (1080, 1920))
            self.assertTrue(20 <= item["video_info"]["duration"] <= 60, item["video_info"]["duration"])
            self.assertLessEqual(len(item["title"]), 60); self.assertLessEqual(len(item["tags"]), 15)
            self.assertTrue(item["description"]); self.assertIn("hook_score", item); self.assertTrue(item["qa"]["ok"])
            self.assertEqual(store.get(item["id"])["status"], "awaiting_approval")
            stages = {l["stage"] for l in store.logs(limit=500)}
            self.assertTrue({"research", "script", "voice", "footage", "render", "thumbnail", "seo"} <= stages)

    def test_failure_is_recorded_not_raised(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(os.path.join(d, "data")); deps = pipeline.demo_deps(seed=1, now=NOW)
            class Boom:
                def generate_json(self, *a, **k): raise GeminiError("quota exhausted")
            deps.llm = Boom()
            item = pipeline.run_generate(fresh(), store, deps, workdir=os.path.join(d, "out"), demo=True)
            self.assertEqual(item["status"], "failed"); self.assertEqual(item["failed_stage"], "research")
            self.assertTrue(any(l["level"] == "error" for l in store.logs()))

    def test_second_generation_is_not_a_duplicate_topic(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(os.path.join(d, "data"))
            a = pipeline.run_generate(fresh(), store, pipeline.demo_deps(seed=1, now=NOW), workdir=os.path.join(d, "o1"), demo=True)
            b = pipeline.run_generate(fresh(), store, pipeline.demo_deps(seed=2, now=NOW), workdir=os.path.join(d, "o2"), demo=True)
            self.assertNotEqual(a["topic"], b["topic"])

    def test_disabled_automation_does_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            s = fresh(); s["automation"]["enabled"] = False; store = Store(os.path.join(d, "data"))
            self.assertIsNone(pipeline.run_generate(s, store, pipeline.demo_deps(1, NOW), os.path.join(d, "o"), demo=True))
            self.assertEqual(store.items(), [])


_BASE = {}


def clone(dst):
    """Render ONE demo video for the whole module, then copy it per test (a full render takes ~20 s)."""
    if "dir" not in _BASE:
        d = tempfile.mkdtemp(); store = Store(os.path.join(d, "data")); item = generated(os.path.join(d, "out"), store); _BASE.update(dir=d, id=item["id"])
    shutil.copytree(os.path.join(_BASE["dir"], "data"), os.path.join(dst, "data")); shutil.copytree(os.path.join(_BASE["dir"], "out"), os.path.join(dst, "out"))
    store = Store(os.path.join(dst, "data")); return store, store.get(_BASE["id"]), os.path.join(dst, "out")


class PublishTests(unittest.TestCase):
    def setup(self, d, mode="manual", **safety_flags):
        store, item, out = clone(d)
        s = fresh(); s["publish"]["mode"] = mode; s["safety"].update(safety_flags)
        return store, s, item, out

    def test_manual_mode_makes_no_api_call(self):
        with tempfile.TemporaryDirectory() as d:
            store, s, item, out = self.setup(d); yt = FakeYT()
            r = pipeline.run_publish(s, store, item["id"], "approve", yt=yt, workdir=out, now=NOW)
            self.assertEqual(r["status"], "approved_manual"); self.assertEqual(yt.uploads, [])

    def test_api_upload_is_private_before_sample_approval(self):
        with tempfile.TemporaryDirectory() as d:
            store, s, item, out = self.setup(d, "api"); yt = FakeYT()
            r = pipeline.run_publish(s, store, item["id"], "approve", yt=yt, workdir=out, now=NOW)
            body = yt.uploads[0][1]
            self.assertEqual(body["status"]["privacyStatus"], "private"); self.assertNotIn("publishAt", body["status"])
            self.assertEqual((r["status"], r["video_id"]), ("uploaded_private", "VID12345678")); self.assertEqual(yt.thumbs[0][0], "VID12345678")

    def test_public_only_when_both_flags_set(self):
        with tempfile.TemporaryDirectory() as d:
            store, s, item, out = self.setup(d, "api", sample_approved=True, public_publishing_enabled=True); yt = FakeYT()
            r = pipeline.run_publish(s, store, item["id"], "approve", yt=yt, workdir=out, now=NOW)
            self.assertEqual(yt.uploads[0][1]["status"]["publishAt"], "2026-11-24T18:00:00Z"); self.assertEqual(r["status"], "scheduled")

    def test_daily_cap_blocks_second_upload(self):
        with tempfile.TemporaryDirectory() as d:
            store, s, item, out = self.setup(d, "api"); yt = FakeYT()
            second = store.add_item({k: v for k, v in item.items() if k != "id"}); shutil.copytree(os.path.join(out, item["id"]), os.path.join(out, second["id"]))
            pipeline.run_publish(s, store, item["id"], "approve", yt=yt, workdir=out, now=NOW)
            r = pipeline.run_publish(s, store, second["id"], "approve", yt=yt, workdir=out, now=NOW)
            self.assertEqual(len(yt.uploads), 1); self.assertEqual(r["status"], "awaiting_approval"); self.assertIn("cap", r["error"])

    def test_thumbnail_failure_is_not_fatal(self):
        with tempfile.TemporaryDirectory() as d:
            store, s, item, out = self.setup(d, "api")
            class YT(FakeYT):
                def set_thumbnail(self, *a): raise RuntimeError("channel not verified")
            r = pipeline.run_publish(s, store, item["id"], "approve", yt=YT(), workdir=out, now=NOW)
            self.assertEqual(r["status"], "uploaded_private"); self.assertTrue(any(l["level"] == "warning" for l in store.logs()))

    def test_reject(self):
        with tempfile.TemporaryDirectory() as d:
            store, s, item, out = self.setup(d)
            self.assertEqual(pipeline.run_publish(s, store, item["id"], "reject", workdir=out, now=NOW)["status"], "rejected")

    def test_posted_stores_video_id(self):
        with tempfile.TemporaryDirectory() as d:
            store, s, item, out = self.setup(d)
            pipeline.run_publish(s, store, item["id"], "approve", workdir=out, now=NOW)
            r = pipeline.run_publish(s, store, item["id"], "posted", workdir=out, video_url="https://youtube.com/shorts/abcDEF12345", now=NOW)
            self.assertEqual((r["status"], r["video_id"]), ("published", "abcDEF12345"))

    def test_unknown_action_and_bad_url(self):
        with tempfile.TemporaryDirectory() as d:
            store, s, item, out = self.setup(d)
            with self.assertRaises(ValueError): pipeline.run_publish(s, store, item["id"], "explode", workdir=out, now=NOW)
            with self.assertRaises(ValueError): pipeline.run_publish(s, store, item["id"], "posted", workdir=out, video_url="https://example.com/x", now=NOW)


class DoctorTests(unittest.TestCase):
    def test_reports_names_only(self):
        r = cli.doctor({"GEMINI_API_KEY": "sekrit-value-123"}, fresh())
        self.assertTrue(r["secrets"]["GEMINI_API_KEY"]); self.assertFalse(r["secrets"]["PEXELS_API_KEY"])
        self.assertNotIn("sekrit-value-123", str(r)); self.assertEqual(r["settings_errors"], [])
        self.assertIn("ffmpeg", r["tools"])


if __name__ == "__main__":
    unittest.main()


class GateTests(unittest.TestCase):
    """The owner's rule: public publishing stays off until a successful sample is approved."""
    def make(self, d, status):
        store = Store(os.path.join(d, "data")); it = store.add_item({"status": status, "title": "T"}); return store, it

    def test_sample_cannot_be_approved_before_any_video_was_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            store, it = self.make(d, "awaiting_approval")
            with self.assertRaises(pipeline.GateError): pipeline.approve_sample(fresh(), store, it["id"])

    def test_sample_approval_after_accepted_video(self):
        with tempfile.TemporaryDirectory() as d:
            store, it = self.make(d, "approved_manual")
            s = pipeline.approve_sample(fresh(), store, it["id"])
            self.assertTrue(s["safety"]["sample_approved"]); self.assertFalse(s["safety"]["public_publishing_enabled"])

    def test_cannot_enable_public_without_sample_or_api_mode(self):
        s = fresh()
        with self.assertRaises(pipeline.GateError): pipeline.set_public(s, True)
        s["safety"]["sample_approved"] = True
        with self.assertRaises(pipeline.GateError): pipeline.set_public(s, True)       # still manual mode
        s["publish"]["mode"] = "api"
        self.assertTrue(pipeline.set_public(s, True)["safety"]["public_publishing_enabled"])

    def test_disable_is_always_allowed(self):
        s = fresh(); s["safety"]["public_publishing_enabled"] = True
        self.assertFalse(pipeline.set_public(s, False)["safety"]["public_publishing_enabled"])
