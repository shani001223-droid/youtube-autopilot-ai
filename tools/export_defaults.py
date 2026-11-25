"""Regenerate dashboard/defaults.json from autopilot.config.DEFAULTS (a test fails if they drift)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from autopilot import config
with open(os.path.join(os.path.dirname(__file__), "..", "dashboard", "defaults.json"), "w", encoding="utf-8") as fh:
    json.dump(config.DEFAULTS, fh, indent=2, ensure_ascii=False)
print("dashboard/defaults.json written")
