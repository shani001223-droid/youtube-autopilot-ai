"""Pexels footage. Scenery only: the Pexels licence forbids showing identifiable people in a bad light, and horror does."""
import re
import time
from pathlib import Path
import requests

PEOPLE = {"person", "people", "man", "men", "woman", "women", "girl", "boy", "child", "children", "kid", "kids", "baby", "couple",
          "family", "crowd", "face", "faces", "portrait", "selfie", "model", "guy", "lady", "teen", "teenager", "silhouette",
          "worker", "workers", "student", "students", "friends", "dancer", "doctor", "nurse", "patient"}
FALLBACKS = ["foggy forest night", "dark empty hallway", "rain on window night", "abandoned house interior", "moonlit field mist", "old lantern flicker"]
API = "https://api.pexels.com/videos/search"


def is_people_free(video):
    slug = video.get("url", "").rstrip("/").split("/")[-1]
    return not (set(re.split(r"[-_]", slug.lower())) & PEOPLE)


def pick_file(video, min_height=1280):
    mp4 = [f for f in video.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width") and f.get("height")]
    portrait = [f for f in mp4 if f["height"] > f["width"] and f["height"] >= min_height]
    if portrait: return min(portrait, key=lambda f: abs(f["height"] - 1920))
    land = [f for f in mp4 if f["width"] >= f["height"] and f["height"] >= 1080]       # centre-cropped later
    if land: return min(land, key=lambda f: abs(f["height"] - 1080))
    smaller = [f for f in mp4 if f["height"] >= 720]
    return max(smaller, key=lambda f: f["height"]) if smaller else None


def attribution(video):
    u = video.get("user", {})
    return f"Video by {u.get('name', 'a Pexels contributor')} on Pexels ({u.get('url', 'https://www.pexels.com')})"


class PexelsClient:
    def __init__(self, api_key, session=None, timeout=30, sleep=time.sleep):
        self.key, self.sess, self.timeout = api_key.strip(), session or requests.Session(), timeout
        self.sleep = sleep

    def search_videos(self, query, orientation="portrait", per_page=15):
        for attempt in range(2):
            try:
                r = self.sess.get(API, headers={"Authorization": self.key}, params={"query": query, "orientation": orientation, "per_page": per_page, "size": "medium"}, timeout=self.timeout)
            except (requests.Timeout, requests.ConnectionError):
                if attempt: raise
                self.sleep(2); continue
            if r.status_code in (408, 500, 502, 503, 504) and attempt == 0:
                self.sleep(2); continue
            r.raise_for_status()
            return r.json().get("videos", [])

    def download(self, url, dest):
        r = self.sess.get(url, stream=True, timeout=self.timeout); r.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in r.iter_content(65536): fh.write(chunk)


def select_clips(pexels, queries, durations, workdir, used_ids=None, log=lambda *a: None):
    workdir = Path(workdir); workdir.mkdir(parents=True, exist_ok=True)
    used, out, down = set(used_ids or []), [], False
    for i, q in enumerate(queries):
        chosen = None
        if not down:
            for query in [q] + FALLBACKS[i % len(FALLBACKS):] + FALLBACKS[:i % len(FALLBACKS)]:
                try:
                    vids = pexels.search_videos(query)
                    if not vids and isinstance(pexels, PexelsClient):
                        vids = pexels.search_videos(query, orientation="landscape")
                except Exception as ex:
                    response = getattr(ex, "response", None)
                    status = getattr(response, "status_code", None)
                    log("warning", f"Pexels unavailable ({type(ex).__name__}, HTTP {status or 'unknown'}); trying alternate sources"); down = True; break
                for v in vids:
                    f = pick_file(v)
                    if v["id"] not in used and is_people_free(v) and f: chosen = (v, f); break
                if chosen: break
        if not chosen:
            out.append({"path": None, "video_id": None, "credit": None}); continue
        v, f = chosen; dest = workdir / f"clip_{i}.mp4"
        try:
            pexels.download(f["link"], dest)
            if not dest.is_file() or dest.stat().st_size == 0:
                raise ValueError("empty footage")
        except Exception as ex:
            dest.unlink(missing_ok=True)
            log("warning", f"Footage download failed ({type(ex).__name__}); using generated visual for scene {i + 1}")
            out.append({"path": None, "video_id": None, "credit": None})
            continue
        used.add(v["id"])
        out.append({"path": str(dest), "video_id": v["id"], "credit": attribution(v)})
    return out
