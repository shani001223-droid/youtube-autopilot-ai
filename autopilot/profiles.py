"""Preview-only profiles; never mutate legacy settings or share upload authorization."""
from .config import deep_merge

PROFILES = {
    "hindi_shorts": {
        "niche": {"name": "Original Hindi Horror & Mystery Stories", "language": "hi",
                  "audience": "Hindi-speaking horror fans", "seed_queries": ["हिंदी डरावनी कहानी", "hindi horror shorts", "भूत की कहानी"]},
        "content": {"mode": "shorts", "short_target_seconds": 45},
        "voice": {"model": "hi-preview-espeak"},
    },
    "english_long": {
        "niche": {"name": "Original English Cinematic Horror & Mystery Stories", "language": "en",
                  "seed_queries": ["original horror stories", "scary stories narration", "supernatural mystery story"]},
        "content": {"mode": "long", "long_target_minutes": 8},
        "voice": {"model": "en_US-john-medium"},
    },
}

def select_profile(settings, name):
    if name == "legacy":
        return settings
    result = deep_merge(settings, PROFILES[name])
    result = deep_merge(result, {"profile": name, "publish": {"mode": "manual"},
        "safety": {"sample_approved": False, "sample_item_id": None, "public_publishing_enabled": False}})
    return result
