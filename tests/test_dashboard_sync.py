import json, os, unittest
from autopilot import config

ROOT = os.path.dirname(os.path.dirname(__file__))


class DashboardSyncTests(unittest.TestCase):
    def test_dashboard_defaults_match_python_defaults(self):
        with open(os.path.join(ROOT, "dashboard", "defaults.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), config.DEFAULTS, "run: python tools/export_defaults.py")

    def test_dashboard_never_uses_unsafe_html_sinks(self):
        for f in ("index.html", "lib.js"):
            src = open(os.path.join(ROOT, "dashboard", f), encoding="utf-8").read()
            self.assertNotIn("eval(", src); self.assertNotIn("document.write", src)
