"""Orchestration. Every stage is logged; any failure becomes a 'failed' queue item with the stage name, never a crash."""
import random, subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import config, demo, footage, music, qa, render, research, safety, scriptgen, seo, subtitles, thumbnail, tts, youtube
from .state import redact
from .llm import GeminiUnavailable
from .reserve import reserve_story


class GateError(Exception):
    pass


@dataclass
class Deps:
    llm: Any
    pexels: Any
    yt: Any
    synth_fn: Callable
    rng: random.Random
    now: datetime
    runner: Callable = field(default=subprocess.run)


def demo_deps(seed=1, now=None):
    return Deps(llm=demo.DemoLLM(seed), pexels=None, yt=None, synth_fn=demo.demo_synth, rng=random.Random(seed), now=now or datetime.now(timezone.utc))


def _iso(dt): return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_generate(settings, store, deps, workdir, run_id=None, demo=False):
    run_id = run_id or deps.now.strftime("%Y%m%d%H%M%S")
    log = lambda level, stage, msg: store.log(level, stage, msg, run_id)
    if not settings["automation"]["enabled"]:
        log("info", "start", "automation is switched off; nothing generated"); return None
    long = settings["content"]["mode"] == "long"
    profile = settings.get("profile", "legacy")
    if long and profile != "english_long":
        log("error", "start", "long-form requires the english_long preview profile"); return None
    width, height = (1920, 1080) if long else (1080, 1920)
    item = store.add_item({"status": "generating", "mode": "long" if long else "short", "profile": profile, "language": settings["niche"]["language"], "run_id": run_id, "demo": bool(demo)}); iid = item["id"]; stage = "research"
    try:
        history = [i for i in store.items() if i["id"] != iid and i.get("variety")]
        recent = [i["topic"] for i in history if i.get("topic")]; insights = store.read_json("insights.json", {})
        variety = scriptgen.pick_variety(settings, history, insights, deps.rng); trends = []
        if deps.yt:
            try: trends = research.trend_titles(deps.yt, settings, deps.now)
            except Exception as ex: log("warning", "research", f"trend lookup failed, continuing without: {redact(str(ex))}")
        source = "demo" if demo else "gemini"
        try:
            topic = research.pick_topic(deps.llm, settings, recent, trends, insights, variety, deps.rng)
            log("info", "research", f"topic '{topic['topic']}' | {variety['subgenre']} | {variety['structure']} | {len(trends)} trend titles")
            stage = "script"
            script = scriptgen.generate_script(deps.llm, settings, topic, variety)
        except GeminiUnavailable as ex:
            if demo: raise
            log("warning", stage, f"Gemini unavailable: {redact(str(ex))}; trying original story reserve")
            stage = "script"
            topic, script = reserve_story(settings, recent, deps.rng)
            source = "original_reserve"
            log("info", "script", f"Using original reserve: {topic['topic']}")
        hook = scriptgen.choose_hook(script["hooks"])
        log("info", "script", f"{len(script['scenes'])} scenes; hook score {hook['score']} ({hook['band']}, {hook['formula']})")

        stage = "voice"; out = Path(workdir) / iid; out.mkdir(parents=True, exist_ok=True)
        sentences, counts, queries = scriptgen.script_to_sentences(script, hook["hook"])
        vo = tts.synthesize_all(sentences, out / "voice", deps.synth_fn); durations = render.scene_durations(vo["timeline"], counts)
        dead = qa.dead_air_report(vo["timeline"]); qa_ok = dead["ok"] and dead["gap_seconds"] <= 1.5
        log("info" if qa_ok else "warning", "voice", f"{len(sentences)} sentences, {vo['duration']:.1f}s narration, longest gap {dead['gap_seconds']:.2f}s")

        stage = "footage"
        clips = footage.select_clips(deps.pexels, queries, durations, out / "clips", log=lambda l, m: log(l, "footage", m)) if deps.pexels \
            else [{"path": None, "video_id": None, "credit": None} for _ in queries]
        if not demo:
            from .commons_media import fill_missing
            if not deps.pexels:
                log("warning", "footage", "PEXELS_API_KEY missing; using keyless licensed media search")
            clips = fill_missing(clips, queries, out / "clips", log=lambda l,m: log(l,"footage",m))
        got = sum(1 for c in clips if c.get("kind") in ("stock_video", "commons_video") or (c.get("path") and not c.get("kind")))
        photos = sum(1 for c in clips if c.get("kind") == "commons_photo")
        log("info", "footage", f"{got}/{len(clips)} moving stock clips; {photos} animated licensed photos; {len(clips)-got-photos} original illustrated scenes")

        stage = "render"; mus = out / "music.wav"; music.make_ambient(sum(durations) + 1, mus, variety["music_mood"], deps.rng.randint(0, 99), runner=deps.runner)
        ass = out / "captions.ass"
        caption_options = {"width": width, "height": height, "size": 54, "margin_v": 100} if long else {}
        if settings["niche"]["language"] == "hi": caption_options["font"] = "Noto Sans Devanagari"
        subtitles.write_ass(ass, subtitles.word_timings(vo["timeline"]), **caption_options); video = out / "video.mp4"
        info = render.render_video([{"path": c["path"], "duration": d, "query": q} for c, d, q in zip(clips, durations, queries)], vo["wav"], mus, ass, video, out / "work",
                                   runner=deps.runner, music_volume=settings["audio"]["music_volume"], **({"width": width, "height": height} if long else {}))
        log("info", "render", f"{info['width']}x{info['height']} {info['duration']:.1f}s audio={info['has_audio']}")
        target = settings["content"]["long_target_minutes"] * 60
        low, high = (target * 0.65, target * 1.4) if long else (20, 60)
        if not info.get("has_video") or not info.get("has_audio") or (info.get("width"), info.get("height")) != (width, height) or not low <= info.get("duration", 0) <= high:
            raise GateError("Rendered video failed resolution/audio/duration quality gate")

        stage = "thumbnail"; choice = seo.choose_title(script["title_ideas"], script["thumbnail_text"]); thumb = out / "thumb.jpg"; frame = out / "frame.jpg"
        thumbnail.extract_frame(out / "work" / "joined.mp4", min(1.0, info["duration"] / 2), frame, runner=deps.runner)   # caption-free source
        thumbnail.make_thumbnail(frame, choice["thumb_text"], thumb, **({"size": (1280, 720)} if long else {}))
        if not thumb.exists() or not video.exists(): raise RuntimeError("expected output file is missing after render/thumbnail")
        log("info", "thumbnail", f"title score {choice['score']}; thumbnail text '{choice['thumb_text']}'")

        stage = "seo"; credits = [c["credit"] for c in clips if c["credit"]]
        desc = seo.build_description(script, choice["title"], credits, settings); tags = seo.clean_tags(script["tags"] + [variety["subgenre"], "horror story" if long else "short story"])
        missing = seo.query_test(choice["title"], desc, [f"{variety['subgenre']} story", topic["topic"]])
        log("info", "seo", f"{len(tags)} tags; description {len(desc)} chars" + (f"; uncovered queries: {missing}" if missing else ""))

        return store.update(iid, status="awaiting_approval", topic=topic["topic"], premise=topic.get("premise"), variety=variety, title=choice["title"],
                            thumb_text=choice["thumb_text"], title_issues=choice["issues"], description=desc, tags=tags, hook=hook["hook"], hook_score=hook["score"],
                            hook_formula=hook["formula"], script={"scenes": script["scenes"], "closing_line": script["closing_line"], "loop_line": script["loop_line"]},
                            credits=credits, video_info=info, visual_sources=[c.get("kind", "stock_video" if c.get("path") else "illustration") for c in clips], qa={"ok": qa_ok, "gap_seconds": dead["gap_seconds"]}, files={"video": str(video), "thumb": str(thumb)},
                            preview_url=None, error=None, script_source=source)
    except Exception as ex:
        msg = redact(f"{type(ex).__name__}: {ex}"); log("error", stage, msg)
        return store.update(iid, status="failed", failed_stage=stage, error=msg)


def run_publish(settings, store, item_id, action, yt=None, workdir="out", video_url=None, now=None):
    now = now or datetime.now(timezone.utc); item = store.get(item_id); log = lambda l, m: store.log(l, "publish", m, item_id)
    if action == "reject":
        log("info", "rejected"); return store.update(item_id, status="rejected", preview_url=None, thumb_url=None)
    if action == "posted":
        vid = youtube.video_id_from_url(video_url or "")
        if not vid: raise ValueError("that does not look like a YouTube video link")
        log("info", f"marked as posted: {vid}"); return store.update(item_id, status="published", video_id=vid, url=f"https://youtu.be/{vid}", published_at=_iso(now))
    if action != "approve": raise ValueError(f"unknown action '{action}'")
    if item.get("status") != "awaiting_approval":
        if item.get("status") in ("approved_manual", "uploaded_private", "scheduled", "published"):
            return item
        raise GateError("only a generated video awaiting review can be approved")
    taken = [i["publish_at"] for i in store.items() if i.get("publish_at")]; plan = safety.publish_plan(settings, now, taken)
    if item.get("profile", "legacy") != "legacy":
        plan = {"mode": "manual", "reason": "Separate channel OAuth not verified; preview profile is manual-only."}
    if plan["mode"] == "manual":
        log("info", plan["reason"]); return store.update(item_id, status="approved_manual", plan=plan, error=None)
    if not safety.can_upload_today(settings, store.items(), now):
        msg = f"daily upload cap reached (max {settings['safety']['max_uploads_per_day']} per day)"; log("warning", msg); return store.update(item_id, error=msg)
    if yt is None: raise RuntimeError("YouTube credentials are not configured (YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN)")
    video = Path(workdir) / item_id / "video.mp4"
    if not video.exists(): raise FileNotFoundError(f"{video} missing; download the preview asset first")
    body = youtube.build_video_body(item, plan["privacy"], plan["publish_at"], settings); vid = yt.upload(str(video), body)
    thumb = Path(workdir) / item_id / "thumb.jpg"
    try: yt.set_thumbnail(vid, str(thumb))
    except Exception as ex: log("warning", f"thumbnail not set (custom thumbnails may need a verified channel): {redact(str(ex))}")
    status = "scheduled" if plan["will_be_public"] else "uploaded_private"; log("info", f"{status}: {vid} ({plan['reason']})")
    return store.update(item_id, status=status, video_id=vid, url=f"https://youtu.be/{vid}", uploaded_at=_iso(now), publish_at=plan["publish_at"],
                        published_at=plan["publish_at"], plan=plan, error=None)


def approve_sample(settings, store, item_id):
    if store.get(item_id).get("status") not in ("approved_manual", "uploaded_private", "scheduled", "published"):
        raise GateError("approve a video (and review it on YouTube) before marking it as the sample")
    s = config.deep_merge(settings, {"safety": {"sample_approved": True, "sample_item_id": item_id}}); store.log("info", "gate", f"sample approved: {item_id}"); return s


def set_public(settings, enabled):
    if enabled:
        if not settings["safety"]["sample_approved"]: raise GateError("approve a sample first")
        if settings["publish"]["mode"] != "api": raise GateError("public scheduling needs publish.mode = 'api' (YouTube API audit passed)")
    return config.deep_merge(settings, {"safety": {"public_publishing_enabled": bool(enabled)}})
