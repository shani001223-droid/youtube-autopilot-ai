"""Publish slots (timezone-aware) and the weekly plan (yt-plan: say what the week costs, keep rest days honest)."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def parse_iso(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(UTC)


def next_slot(now, publish_time, tz, taken, min_lead_minutes=30):
    z = ZoneInfo(tz); h, m = (int(x) for x in publish_time.split(":"))
    taken_set = {parse_iso(t).replace(second=0, microsecond=0) for t in taken}
    day = now.astimezone(z).date()
    for _ in range(400):
        cand = datetime(day.year, day.month, day.day, h, m, tzinfo=z).astimezone(UTC)
        if cand >= now + timedelta(minutes=min_lead_minutes) and cand not in taken_set:
            return cand
        day += timedelta(days=1)
    raise RuntimeError("no free publish slot in the next 400 days")


def weekly_plan(settings, start):
    c, t = settings["content"], settings["schedule"]["publish_time"]
    long_days = c["long_days"][: c["long_per_week"]]
    rows = []
    for i in range(7):
        d = start + timedelta(days=i); wd = WEEKDAYS[d.weekday()]
        for _ in range(c["shorts_per_day"]):
            rows.append({"date": d.isoformat(), "weekday": wd, "format": "short", "time": t, "status": "planned"})
        if wd in long_days:
            rows.append({"date": d.isoformat(), "weekday": wd, "format": "long", "time": t, "status": "planned"})
    return rows
