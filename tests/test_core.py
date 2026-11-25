import json, os, tempfile, unittest
from datetime import date, datetime, timezone
from autopilot import config, safety, scheduler


def fresh():
    return config.load_settings("/nonexistent/settings.json")


class ConfigTests(unittest.TestCase):
    def test_defaults_are_safe(self):
        s = fresh()
        self.assertFalse(s["safety"]["public_publishing_enabled"])
        self.assertFalse(s["safety"]["sample_approved"])
        self.assertEqual(s["publish"]["mode"], "manual")
        self.assertEqual(config.validate_settings(s), [])

    def test_partial_file_is_merged_with_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.json")
            json.dump({"niche": {"name": "Cozy Mysteries"}}, open(p, "w"))
            s = config.load_settings(p)
        self.assertEqual(s["niche"]["name"], "Cozy Mysteries")
        self.assertIn("subgenres", s["niche"])
        self.assertEqual(s["content"]["shorts_per_day"], 1)

    def test_save_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.json")
            s = fresh(); s["niche"]["name"] = "X"
            config.save_settings(s, p)
            self.assertEqual(config.load_settings(p)["niche"]["name"], "X")

    def test_public_without_sample_is_rejected(self):
        s = fresh(); s["safety"]["public_publishing_enabled"] = True
        self.assertTrue(any("sample" in e for e in config.validate_settings(s)))

    def test_public_needs_api_mode(self):
        s = fresh(); s["safety"].update(public_publishing_enabled=True, sample_approved=True)
        self.assertTrue(any("api" in e for e in config.validate_settings(s)))

    def test_noncommercial_voice_rejected(self):
        s = fresh(); s["voice"]["model"] = "en_US-ryan-high"
        self.assertTrue(any("voice" in e for e in config.validate_settings(s)))

    def test_bad_time_timezone_and_length(self):
        s = fresh(); s["schedule"]["publish_time"] = "25:99"; s["schedule"]["timezone"] = "Mars/Base"
        s["content"]["short_target_seconds"] = 5
        errs = " ".join(config.validate_settings(s))
        self.assertIn("publish_time", errs); self.assertIn("timezone", errs); self.assertIn("short_target_seconds", errs)


class SafetyTests(unittest.TestCase):
    now = datetime(2026, 11, 24, 10, 0, tzinfo=timezone.utc)

    def test_manual_mode_never_uploads(self):
        p = safety.publish_plan(fresh(), self.now, [])
        self.assertEqual(p["mode"], "manual"); self.assertIsNone(p["publish_at"])

    def test_api_stays_private_without_sample(self):
        s = fresh(); s["publish"]["mode"] = "api"
        p = safety.publish_plan(s, self.now, [])
        self.assertEqual((p["mode"], p["privacy"], p["publish_at"], p["will_be_public"]), ("api", "private", None, False))

    def test_both_flags_required_for_public(self):
        s = fresh(); s["publish"]["mode"] = "api"; s["safety"]["sample_approved"] = True
        self.assertFalse(safety.publish_plan(s, self.now, [])["will_be_public"])
        with self.assertRaises(safety.PublishBlocked):
            safety.assert_public_allowed(s)

    def test_public_is_scheduled_in_future(self):
        s = fresh(); s["publish"]["mode"] = "api"
        s["safety"].update(sample_approved=True, public_publishing_enabled=True)
        p = safety.publish_plan(s, self.now, [])
        self.assertTrue(p["will_be_public"]); self.assertEqual(p["privacy"], "private")
        self.assertEqual(p["publish_at"], "2026-11-24T18:00:00Z")
        safety.assert_public_allowed(s)

    def test_daily_cap(self):
        s = fresh()
        items = [{"uploaded_at": "2026-11-24T01:00:00Z"}]
        self.assertFalse(safety.can_upload_today(s, items, self.now))
        self.assertTrue(safety.can_upload_today(s, [{"uploaded_at": "2026-11-23T01:00:00Z"}], self.now))


class SchedulerTests(unittest.TestCase):
    def test_today_if_ahead(self):
        n = datetime(2026, 11, 24, 10, 0, tzinfo=timezone.utc)
        self.assertEqual(scheduler.next_slot(n, "18:00", "UTC", []).isoformat(), "2026-11-24T18:00:00+00:00")

    def test_tomorrow_if_passed_or_inside_lead(self):
        late = datetime(2026, 11, 24, 20, 0, tzinfo=timezone.utc)
        self.assertEqual(scheduler.next_slot(late, "18:00", "UTC", []).day, 25)
        close = datetime(2026, 11, 24, 17, 50, tzinfo=timezone.utc)
        self.assertEqual(scheduler.next_slot(close, "18:00", "UTC", [], min_lead_minutes=30).day, 25)

    def test_taken_slot_skipped(self):
        n = datetime(2026, 11, 24, 10, 0, tzinfo=timezone.utc)
        self.assertEqual(scheduler.next_slot(n, "18:00", "UTC", ["2026-11-24T18:00:00Z"]).day, 25)

    def test_timezone_conversion(self):
        n = datetime(2026, 11, 24, 10, 0, tzinfo=timezone.utc)
        self.assertEqual(scheduler.next_slot(n, "18:00", "America/New_York", []).hour, 23)

    def test_weekly_plan_daily_shorts_two_longs(self):
        s = fresh(); s["content"]["long_per_week"] = 2
        rows = scheduler.weekly_plan(s, date(2026, 11, 23))
        self.assertEqual(sum(r["format"] == "short" for r in rows), 7)
        self.assertEqual(sorted(r["weekday"] for r in rows if r["format"] == "long"), ["sat", "tue"])


if __name__ == "__main__":
    unittest.main()
