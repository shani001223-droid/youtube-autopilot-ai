"""Keyless Wikimedia Commons media. Only unambiguous CC0/PD/CC BY assets are eligible.
Network failures fall through to original illustrated scenes, never blank screens."""
import html, re, io
from pathlib import Path
from urllib.parse import urlparse
import requests
from PIL import Image
from .footage import PEOPLE, FALLBACKS

API = "https://commons.wikimedia.org/w/api.php"
AGENT = "NightShiftDesk/1.1 (https://github.com/shani001223-droid/youtube-autopilot-ai)"
LIMIT = 40 * 1024 * 1024

def clean(value):
    return " ".join(html.unescape(re.sub(r"<[^>]*>", "", str(value or ""))).split())

def candidate(page):
    info = (page.get("imageinfo") or [{}])[0]
    md = info.get("extmetadata", {})
    get = lambda k: clean(md.get(k, {}).get("value", ""))
    license = get("LicenseShortName")
    if license.lower() not in {"cc0", "cc0 1.0", "public domain", "cc by 2.0", "cc by 2.5", "cc by 3.0", "cc by 4.0"}:
        return None
    if get("Restrictions") or get("NonFree") not in {"", "false", "0"}:
        return None
    title = page.get("title", "")
    if set(re.findall(r"[a-z]+", title.lower())) & PEOPLE:
        return None
    artist, license_url = get("Artist"), get("LicenseUrl")
    if license.lower().startswith("cc by ") and (not artist or not license_url):
        return None
    mime = info.get("mime", "")
    if mime not in {"video/webm", "video/ogg", "video/mp4", "image/jpeg", "image/png"}:
        return None
    video = mime.startswith("video/")
    if min(info.get("width", 0), info.get("height", 0)) < 480 or not 0 < info.get("size", 0) <= LIMIT:
        return None
    url = info.get("url", "")
    source = info.get("descriptionurl", "")
    if urlparse(url).scheme != "https" or urlparse(url).hostname != "upload.wikimedia.org":
        return None
    if urlparse(source).scheme != "https" or urlparse(source).hostname != "commons.wikimedia.org":
        return None
    credit = f"{title.removeprefix('File:')[:110]} — {(artist or 'public domain')[:100]}, {license}; {source} {license_url} (cropped, color graded" + ("" if video else ", animated") + ")"
    return {"id": page.get("pageid"), "url": url, "video": video, "credit": credit, "mime": mime}

class Commons:
    def __init__(self, session=None):
        self.sess = session or requests.Session()
        self.sess.headers.update({"User-Agent": AGENT})
        self.unavailable = False

    def find(self, query, media):
        if self.unavailable:
            return []
        q = " ".join(re.findall(r"[A-Za-z0-9]+", query)[:5])
        try:
            r = self.sess.get(API, params={"action":"query","format":"json","generator":"search",
                "gsrsearch":f"{q} filetype:{media}", "gsrnamespace":6, "gsrlimit":12,
                "prop":"imageinfo","iiprop":"url|size|mime|extmetadata",
                "iiextmetadatafilter":"Artist|LicenseShortName|LicenseUrl|Restrictions|NonFree"}, timeout=(8,20))
            r.raise_for_status()
            pages = r.json().get("query", {}).get("pages", {}).values()
            return [c for p in sorted(pages,key=lambda p:p.get("index",999)) if (c:=candidate(p))]
        except (requests.RequestException, ValueError, TypeError):
            self.unavailable = True
            return []

    def download(self, asset, directory, index):
        suffix = {"video/webm":".webm","video/ogg":".ogv","video/mp4":".mp4"}.get(asset["mime"],".jpg")
        path = Path(directory) / f"commons_{index}{suffix}"
        try:
            with self.sess.get(asset["url"],stream=True,timeout=(8,25)) as r:
                r.raise_for_status()
                total = 0
                with path.open("wb") as f:
                    for chunk in r.iter_content(65536):
                        total += len(chunk)
                        if total > LIMIT: raise ValueError("asset too large")
                        f.write(chunk)
            if not total: raise ValueError("empty media")
            if not asset["video"]:
                with Image.open(path) as im:
                    im.thumbnail((2000,2000))
                    data = io.BytesIO()
                    im.convert("RGB").save(data,"JPEG",quality=92)
                path.write_bytes(data.getvalue())
            return str(path)
        except (requests.RequestException, OSError, ValueError):
            path.unlink(missing_ok=True)
            return None

def fill_missing(clips, queries, workdir, log=lambda *a: None, client=None):
    from .illustration import draw_scene
    workdir = Path(workdir)
    workdir.mkdir(parents=True,exist_ok=True)
    client = client or Commons()
    used = set()
    for i,(clip,q) in enumerate(zip(clips,queries)):
        if clip.get("path"):
            clip.setdefault("kind","stock_video")
            continue
        # Keep request count bounded; prefer moving footage, then animate a relevant photograph.
        found = None
        for query, media in [(q,"video"),(q,"bitmap"),(FALLBACKS[i % len(FALLBACKS)],"video"),(FALLBACKS[i % len(FALLBACKS)],"bitmap")]:
            if found or client.unavailable: break
            for asset in client.find(query,media)[:4]:
                if asset["id"] in used: continue
                path = client.download(asset,workdir,i)
                if path:
                    found = {"path":path,"video_id":asset["id"],"credit":asset["credit"],
                        "kind":"commons_video" if asset["video"] else "commons_photo"}
                    used.add(asset["id"])
                    break
        if found:
            clip.update(found)
            log("info",f"Scene {i+1}: {found['kind']}")
        else:
            path = workdir / f"illustration_{i}.jpg"
            draw_scene(q,path,i)
            clip.update(path=str(path),kind="illustration",credit=None)
            log("warning",f"Scene {i+1}: original animated illustration (no stock available)")
    return clips
