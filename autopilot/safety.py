"""The publish guard. The dashboard greys things out, but THIS is the enforcement."""
from datetime import timezone
from zoneinfo import ZoneInfo
from . import scheduler


class PublishBlocked(Exception):
    pass


def _public_allowed(s):
    return s["publish"]["mode"] == "api" and s["safety"]["sample_approved"] and s["safety"]["public_publishing_enabled"]


def assert_public_allowed(s):
    if not _public_allowed(s):
        raise PublishBlocked("public publishing needs publish.mode='api', an approved sample AND the public-publishing switch")


def publish_plan(settings, now, taken_slots):
    if settings["publish"]["mode"] == "manual":
        return {"mode": "manual", "privacy": "private", "publish_at": None, "will_be_public": False,
                "reason": "manual mode: nothing is sent to YouTube; upload by hand from the YouTube app"}
    if not _public_allowed(settings):
        return {"mode": "api", "privacy": "private", "publish_at": None, "will_be_public": False,
                "reason": "uploaded as PRIVATE: sample not approved or public publishing switch is off"}
    slot = scheduler.next_slot(now, settings["schedule"]["publish_time"], settings["schedule"]["timezone"], taken_slots)
    return {"mode": "api", "privacy": "private", "publish_at": slot.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "will_be_public": True, "reason": "scheduled: YouTube makes it public at publish_at"}


def can_upload_today(settings, items, now):
    z = ZoneInfo(settings["schedule"]["timezone"]); today = now.astimezone(z).date()
    n = sum(1 for it in items if it.get("uploaded_at") and scheduler.parse_iso(it["uploaded_at"]).astimezone(z).date() == today)
    return n < settings["safety"]["max_uploads_per_day"]
