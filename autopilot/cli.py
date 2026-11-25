"""python -m autopilot <command>. Secrets are read from environment variables only (GitHub Secrets in Actions)."""
import argparse, json, os, shutil, sys
import importlib.util
from datetime import date, datetime, timedelta, timezone

from . import analytics as an, audit, comments, config, improve, pipeline, scheduler, tts
from .state import Store

SECRETS = ["GEMINI_API_KEY", "PEXELS_API_KEY", "YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"]


def doctor(env, settings):
    return {"secrets": {k: bool(env.get(k)) for k in SECRETS}, "settings_errors": config.validate_settings(settings),
            "tools": {"ffmpeg": bool(shutil.which("ffmpeg")), "ffprobe": bool(shutil.which("ffprobe")), "piper": importlib.util.find_spec("piper") is not None},
            "publish_mode": settings["publish"]["mode"], "public_publishing": settings["safety"]["public_publishing_enabled"]}


def _yt(env):
    from .youtube import YouTubeClient
    return YouTubeClient(env["YT_CLIENT_ID"], env["YT_CLIENT_SECRET"], env["YT_REFRESH_TOKEN"]) if all(env.get(k) for k in SECRETS[2:]) else None


def _out(**kv):
    for k, v in kv.items():
        print(f"{k}={v}")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as fh: fh.write(f"{k}={v}\n")


def main(argv=None, env=None):
    env = os.environ if env is None else env
    ap = argparse.ArgumentParser(prog="autopilot"); ap.add_argument("--data", default="data"); sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate"); g.add_argument("--demo", action="store_true"); g.add_argument("--workdir", default="out"); g.add_argument("--profile", choices=["legacy", "hindi_shorts", "english_long"], default="legacy")
    p = sub.add_parser("publish"); p.add_argument("--id", required=True); p.add_argument("--action", required=True); p.add_argument("--video-url"); p.add_argument("--workdir", default="out")
    s = sub.add_parser("settings-action"); s.add_argument("--action", required=True, choices=["approve_sample", "enable_public", "disable_public"]); s.add_argument("--id")
    r = sub.add_parser("set-preview"); r.add_argument("--id", required=True); r.add_argument("--url", required=True); r.add_argument("--thumb-url")
    for name in ("analytics", "comments", "plan", "doctor", "validate-settings"): sub.add_parser(name)
    a = ap.parse_args(argv); sp = os.path.join(a.data, "settings.json"); settings = config.load_settings(sp); store = Store(a.data)

    if a.cmd == "generate":
        from .profiles import select_profile
        settings = select_profile(settings, a.profile)

    if a.cmd == "doctor": print(json.dumps(doctor(env, settings), indent=2)); return 0
    errs = config.validate_settings(settings)
    if a.cmd == "validate-settings" or errs:
        for e in errs: print("settings error:", e, file=sys.stderr)
        if a.cmd == "validate-settings": return 1 if errs else 0
        store.log("error", "settings", "; ".join(errs)); return 1
    now = datetime.now(timezone.utc)

    if a.cmd == "generate":
        if a.demo: deps = pipeline.demo_deps(seed=int(now.timestamp()) % 1000, now=now)
        else:
            import random; from .footage import PexelsClient; from .llm import GeminiClient
            from .reserve import UnavailableClient
            llm = GeminiClient(env["GEMINI_API_KEY"], settings["gemini"]["models"], temperature=settings["gemini"]["temperature"]) if env.get("GEMINI_API_KEY", "").strip() else UnavailableClient()
            v = settings["voice"]
            deps = pipeline.Deps(llm=llm,
                                 pexels=PexelsClient(env["PEXELS_API_KEY"]) if env.get("PEXELS_API_KEY") else None, yt=_yt(env),
                                 synth_fn=tts.hindi_preview_synth if v["model"] == "hi-preview-espeak" else tts.piper_synth(v["model"], "voices", allow_noncommercial=v["allow_noncommercial"], length_scale=v["length_scale"]),
                                 rng=random.Random(), now=now)
        item = pipeline.run_generate(settings, store, deps, a.workdir, demo=a.demo)
        if item is None: _out(ITEM_ID="", STATUS="skipped"); return 0
        _out(ITEM_ID=item["id"], STATUS=item["status"]); return 0 if item["status"] != "failed" else 1
    if a.cmd == "publish":
        item = pipeline.run_publish(settings, store, a.id, a.action, yt=_yt(env), workdir=a.workdir, video_url=a.video_url, now=now); _out(ITEM_ID=a.id, STATUS=item["status"]); return 0
    if a.cmd == "settings-action":
        try:
            new = pipeline.approve_sample(settings, store, a.id) if a.action == "approve_sample" else pipeline.set_public(settings, a.action == "enable_public")
        except pipeline.GateError as ex: print("blocked:", ex, file=sys.stderr); store.log("warning", "gate", str(ex)); return 1
        config.save_settings(new, sp); return 0
    if a.cmd == "set-preview": store.update(a.id, preview_url=a.url, thumb_url=a.thumb_url); return 0
    if a.cmd == "plan": store.write_json("plan.json", scheduler.weekly_plan(settings, date.today() - timedelta(days=date.today().weekday()))); return 0
    yt = _yt(env)
    if yt is None: print("YouTube secrets missing: " + ", ".join(SECRETS[2:]), file=sys.stderr); return 2
    if a.cmd == "analytics":
        today = now.strftime("%Y-%m-%d"); recs = an.collect(yt, store.items(), today); ret = {}
        for rec in recs[-3:]:
            try: ret[rec["video_id"]] = an.retention_report(yt.retention(rec["video_id"], (rec.get("published_at") or today)[:10], today), 45)
            except Exception as ex: ret[rec["video_id"]] = {"ok": False, "error": str(ex)[:200]}
        store.write_json("analytics.json", {"updated": now.isoformat(), "records": recs, "retention": ret})
        store.write_json("insights.json", improve.build_insights(recs)); store.write_json("audit.json", audit.audit_channel(recs)); return 0
    if a.cmd == "comments":
        from .llm import GeminiClient
        vids = [i for i in store.items() if i.get("video_id")][-3:]; cs = [c for v in vids for c in yt.recent_comments(v["video_id"], 30)]; piles = comments.triage(cs)
        todo = piles["questions"] + piles["corrections"] + piles["praise"]
        out = GeminiClient(env["GEMINI_API_KEY"], settings["gemini"]["models"]).generate_json(comments.draft_prompt(todo[:15], settings["niche"])) if todo and env.get("GEMINI_API_KEY") else {"replies": []}
        store.write_json("replies.json", {"updated": now.isoformat(), "piles": {k: len(v) for k, v in piles.items()}, "drafts": out.get("replies", []), "source": todo[:15]}); return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
