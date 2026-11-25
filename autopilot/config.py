"""Settings: one JSON file (data/settings.json) edited from the phone dashboard. Defaults are the safe state."""
import copy, json, os, re, tempfile

DEFAULTS = {
    "version": 1,
    "automation": {"enabled": True},
    "niche": {
        "name": "Original English Horror & Mystery Stories",
        "channel_name": "",
        "language": "en",
        "audience": "adults 18-45 who like short scary stories",
        "tone": "slow-burn dread, concrete sensory detail, a quiet twist, no gore",
        "subgenres": ["supernatural", "haunted places", "folk horror", "psychological", "urban mystery",
                      "cosmic unease", "found-document mystery", "small-town secrets"],
        "banned_topics": [],
        "seed_queries": ["scary story", "horror story short", "creepy mystery story"],
    },
    "content": {"mode": "shorts", "shorts_per_day": 1, "short_target_seconds": 45,
                "long_per_week": 0, "long_days": ["tue", "sat"], "long_target_minutes": 8},
    "voice": {"model": "en_US-john-medium", "allow_noncommercial": False, "length_scale": 1.0},
    "visual": {"avoid_people": True, "grade": "horror"},
    "audio": {"music_volume": 0.14},
    "schedule": {"timezone": "UTC", "publish_time": "18:00"},
    "approval": {"required": True},
    "safety": {"sample_approved": False, "public_publishing_enabled": False, "max_uploads_per_day": 1},
    "publish": {"mode": "manual", "category_id": "24", "made_for_kids": False, "disclose_synthetic": True},
    "gemini": {"models": ["gemini-flash-lite-latest", "gemini-flash-latest"], "temperature": 1.0},
}


def deep_merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_settings(path="data/settings.json"):
    try:
        with open(path, encoding="utf-8") as fh:
            return deep_merge(DEFAULTS, json.load(fh))
    except (FileNotFoundError, NotADirectoryError):
        return copy.deepcopy(DEFAULTS)


def save_settings(settings, path="data/settings.json"):
    d = os.path.dirname(os.path.abspath(path)); os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(settings, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def validate_settings(s):
    from zoneinfo import ZoneInfo
    from . import tts
    e = []
    c, sch, saf, pub = s["content"], s["schedule"], s["safety"], s["publish"]
    if c["mode"] not in ("shorts", "long"): e.append("content.mode must be 'shorts' or 'long'")
    if not isinstance(c["shorts_per_day"], int) or not 0 <= c["shorts_per_day"] <= 3: e.append("content.shorts_per_day must be 0-3")
    if not 20 <= c["short_target_seconds"] <= 55: e.append("content.short_target_seconds must be 20-55 (yt-shorts rule)")
    if not 0 <= c["long_per_week"] <= 7: e.append("content.long_per_week must be 0-7")
    if pub["mode"] not in ("manual", "api"): e.append("publish.mode must be 'manual' or 'api'")
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", str(sch["publish_time"])): e.append("schedule.publish_time must be HH:MM")
    try: ZoneInfo(sch["timezone"])
    except Exception: e.append(f"schedule.timezone '{sch['timezone']}' is not a valid IANA timezone")
    if saf["public_publishing_enabled"]:
        if not saf["sample_approved"]: e.append("safety.public_publishing_enabled requires an approved sample (safety.sample_approved)")
        if pub["mode"] != "api": e.append("public publishing requires publish.mode = 'api'")
    try: tts.check_voice(s["voice"]["model"], s["voice"]["allow_noncommercial"])
    except tts.VoiceLicenseError as ex: e.append(f"voice: {ex}")
    if not s["niche"]["subgenres"]: e.append("niche.subgenres must not be empty")
    return e
