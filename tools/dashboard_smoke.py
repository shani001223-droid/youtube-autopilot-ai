"""Optional browser smoke test for the dashboard (needs: pip install playwright && playwright install chromium).
Mocks the GitHub API, loads the page at phone size, clicks through, and asserts on the requests it WOULD send.
Usage: python tools/dashboard_smoke.py [path/to/sample/video.mp4]"""
import base64, glob, json, os, sys
from playwright.sync_api import sync_playwright

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dashboard")
VIDEO = sys.argv[1] if len(sys.argv) > 1 else None
SHOTS = os.environ.get("SHOTS", "/tmp/shots"); os.makedirs(SHOTS, exist_ok=True)
b64 = lambda o: base64.b64encode(json.dumps(o).encode()).decode()
PV = "https://github.com/me/repo/releases/download/preview-a/video.mp4"
QUEUE = [
    {"id": "a", "status": "awaiting_approval", "title": "The radio that knew my name", "hook": "You will never trust a radio at 3 AM again.", "hook_score": 71, "created_at": "2026-11-25T01:00:00Z",
     "preview_url": PV, "thumb_url": "https://github.com/me/repo/releases/download/preview-a/thumb.jpg", "description": "Desc line", "tags": ["horror story"], "script": {"scenes": [{"narration": "It began."}]}, "demo": True},
    {"id": "b", "status": "approved_manual", "title": "Nine knocks from the cellar", "created_at": "2026-11-24T01:00:00Z", "preview_url": PV, "description": "D", "tags": ["x"], "hook": "Nine.", "hook_score": 60},
    {"id": "c", "status": "failed", "failed_stage": "script", "error": "GeminiError: all Gemini models failed: gemini-flash-lite-latest: daily quota used up", "created_at": "2026-11-23T01:00:00Z"},
    {"id": "d", "status": "awaiting_approval", "title": "<img src=x onerror=\"window.__pwned=1\">", "created_at": "2026-11-22T01:00:00Z", "preview_url": "javascript:window.__pwned=1"},
]
FILES = {
    "settings.json": {"publish": {"mode": "manual"}},
    "queue.json": QUEUE,
    "logs.json": [{"t": "2026-11-25T01:00:05Z", "level": "info", "stage": "script", "message": "6 scenes", "run": "r"}, {"t": "2026-11-25T01:00:09Z", "level": "error", "stage": "research", "message": "quota exhausted", "run": "r"}],
    "analytics.json": {"records": [{"title": "T1", "views": 120, "avg_view_pct": 71.4}]},
    "insights.json": {"subgenre": [{"value": "folk horror", "n": 3, "mean_view_pct": 75.0}]},
    "audit.json": {"fix": "Not enough data yet: publish at least 5 videos before judging the channel."},
    "replies.json": {"drafts": [{"id": "1", "reply": "Thanks for listening!"}]},
}
seen = []

def main():
    video = open(VIDEO, "rb").read() if VIDEO else b""
    with sync_playwright() as p:
        br = p.chromium.launch(); ctx = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        page = ctx.new_page(); errors = []; page.on("pageerror", lambda e: errors.append(str(e))); page.on("dialog", lambda d: d.accept("https://youtu.be/abcDEF12345"))
        ctx.add_init_script("localStorage.setItem('ap_repo','me/repo'); localStorage.setItem('ap_token','tok')")

        def handle(route):
            req = route.request; u = req.url
            if u.startswith("http://dash.test/"):
                name = u.split("http://dash.test/")[1].split("?")[0] or "index.html"; path = os.path.join(ROOT, name)
                ctype = {"html": "text/html", "js": "text/javascript", "json": "application/json", "svg": "image/svg+xml", "webmanifest": "application/manifest+json"}.get(name.rsplit(".", 1)[-1], "text/plain")
                return route.fulfill(status=200, body=open(path, "rb").read(), content_type=ctype)
            if u.startswith("https://api.github.com/repos/me/repo/contents/data/"):
                name = u.split("/data/")[1].split("?")[0]
                if req.method == "PUT":
                    seen.append(("PUT", name, json.loads(req.post_data))); return route.fulfill(status=200, body=json.dumps({"content": {"sha": "newsha"}}), content_type="application/json")
                return route.fulfill(status=200, body=json.dumps({"content": b64(FILES[name]), "sha": "sha-" + name}), content_type="application/json") if name in FILES else route.fulfill(status=404, body="{}")
            if "/dispatches" in u:
                seen.append(("DISPATCH", u.split("/workflows/")[1].split("/")[0], json.loads(req.post_data)["inputs"])); return route.fulfill(status=204, body="")
            if "/actions/runs" in u:
                return route.fulfill(status=200, content_type="application/json", body=json.dumps({"workflow_runs": [{"name": "Generate video", "status": "completed", "conclusion": "success", "created_at": "2026-11-25T03:17:00Z", "html_url": "https://github.com/me/repo/actions/runs/1"}]}))
            if u.endswith("/video.mp4"): return route.fulfill(status=200, body=video, content_type="video/mp4")
            return route.fulfill(status=404, body="")
        page.route("**/*", handle); page.goto("http://dash.test/index.html"); page.wait_for_selector("article.card"); page.wait_for_timeout(300)

        n = page.locator("article.card").count(); assert n == 4, f"expected 4 cards, got {n}"
        assert page.evaluate("window.__pwned") is None, "XSS: script ran from repo data"
        assert page.locator("video").count() == 2, "unsafe preview URL must not become a <video>"
        page.screenshot(path=f"{SHOTS}/queue.png")
        page.locator("article.card").first.locator("button[data-a=approve]").click(); page.wait_for_timeout(200)
        assert ("DISPATCH", "publish.yml", {"item_id": "a", "action": "approve", "video_url": ""}) in seen, seen
        page.locator("article.card:has-text('Nine knocks')").locator("button[data-a=posted]").click(); page.wait_for_timeout(200)
        assert ("DISPATCH", "publish.yml", {"item_id": "b", "action": "posted", "video_url": "https://youtu.be/abcDEF12345"}) in seen, seen
        assert page.locator("text=Stopped at script").count() == 1

        page.click("nav [data-t=make]"); page.wait_for_selector("#pub"); assert page.locator("#pub").is_disabled(), "public publishing must be locked without an approved sample"
        page.screenshot(path=f"{SHOTS}/make.png")
        page.click("#auto"); page.wait_for_timeout(300)
        put = [s for s in seen if s[0] == "PUT" and s[1] == "settings.json"][-1]; saved = json.loads(base64.b64decode(put[2]["content"]))
        assert saved["automation"]["enabled"] is False and put[2]["sha"] == "sha-settings.json", put
        page.click("#demo"); page.wait_for_timeout(200); assert ("DISPATCH", "generate.yml", {"demo": "true"}) in seen

        page.click("nav [data-t=niche]"); page.wait_for_selector("#nt"); page.fill("#nt", "quiet dread, no gore"); page.click("#save"); page.wait_for_timeout(300)
        saved = json.loads(base64.b64decode([s for s in seen if s[0] == "PUT"][-1][2]["content"]))
        assert saved["niche"]["tone"] == "quiet dread, no gore" and saved["content"]["short_target_seconds"] == 45 and saved["automation"]["enabled"] is False, saved
        page.screenshot(path=f"{SHOTS}/niche.png")
        page.click("nav [data-t=plan]"); page.wait_for_selector("#pt"); page.screenshot(path=f"{SHOTS}/plan.png")
        page.click("nav [data-t=stats]"); page.wait_for_selector("text=One thing to fix"); page.screenshot(path=f"{SHOTS}/stats.png")
        page.click("nav [data-t=logs]"); page.wait_for_selector(".log"); page.click("[data-f=error]"); assert page.locator(".log").count() == 1
        page.screenshot(path=f"{SHOTS}/logs.png"); assert not errors, errors
        br.close()
    print("dashboard smoke test passed:", len(seen), "mocked GitHub calls checked; screenshots in", SHOTS)

main()
