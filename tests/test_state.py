import tempfile, unittest
from autopilot.state import Store


class StoreTests(unittest.TestCase):
    def test_add_update_persist(self):
        with tempfile.TemporaryDirectory() as d:
            s = Store(d); it = s.add_item({"status": "awaiting_approval", "title": "A"})
            self.assertTrue(it["id"])
            s.update(it["id"], status="approved")
            s2 = Store(d)
            self.assertEqual(s2.get(it["id"])["status"], "approved")
            self.assertEqual(len(s2.items("approved")), 1); self.assertEqual(s2.items("failed"), [])

    def test_log_ring_buffer_and_filter(self):
        with tempfile.TemporaryDirectory() as d:
            s = Store(d, log_cap=5)
            for i in range(9): s.log("error" if i % 2 else "info", "script", f"m{i}", run_id="r")
            logs = s.logs(limit=50)
            self.assertEqual(len(logs), 5); self.assertEqual(logs[-1]["message"], "m8")
            self.assertTrue(all(l["level"] == "error" for l in s.logs(level="error")))

    def test_unknown_id_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(KeyError): Store(d).update("nope", status="x")

    def test_log_never_stores_secrets(self):
        with tempfile.TemporaryDirectory() as d:
            s = Store(d); s.log("error", "yt", "token=ya29.A0SECRETVALUE failed key=AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ0123456")
            msg = s.logs()[-1]["message"]
            self.assertNotIn("SECRETVALUE", msg); self.assertNotIn("AIzaSy", msg)


if __name__ == "__main__":
    unittest.main()
