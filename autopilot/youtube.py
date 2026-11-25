"""YouTube Data + Analytics over plain REST (requests only). The refresh token comes from the YT_* GitHub Secrets.
Uploads from an UNAUDITED API project are forced private by YouTube - the pipeline's 'manual' mode exists for that."""
import os, re, time
import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/youtube/v3"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3"
ANALYTICS = "https://youtubeanalytics.googleapis.com/v2/reports"


class YouTubeError(Exception):
    pass


def build_video_body(meta, privacy, publish_at, settings):
    if publish_at and privacy != "private": raise ValueError("publishAt only works with privacyStatus='private'")
    body = {"snippet": {"title": meta["title"][:100], "description": meta["description"][:5000], "tags": meta.get("tags", []),
                        "categoryId": settings["publish"]["category_id"]},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": bool(settings["publish"]["made_for_kids"])}}
    if publish_at: body["status"]["publishAt"] = publish_at
    if settings["publish"]["disclose_synthetic"]: body["status"]["containsSyntheticMedia"] = True
    return body


def video_id_from_url(s):
    s = s.strip()
    for rx in (r"youtu\.be/([\w-]{11})", r"[?&]v=([\w-]{11})", r"/shorts/([\w-]{11})", r"^([\w-]{11})$"):
        m = re.search(rx, s)
        if m: return m.group(1)
    return None


class YouTubeClient:
    def __init__(self, client_id, client_secret, refresh_token, session=None, clock=time.time):
        self.cid, self.secret, self.refresh, self.sess, self.clock = client_id, client_secret, refresh_token, session or requests.Session(), clock
        self._tok, self._exp = None, 0

    def access_token(self):
        if self._tok and self.clock() < self._exp - 60: return self._tok
        r = self.sess.post(TOKEN_URL, data={"client_id": self.cid, "client_secret": self.secret, "refresh_token": self.refresh, "grant_type": "refresh_token"}, timeout=30)
        if r.status_code != 200:
            raise YouTubeError(f"token refresh failed (HTTP {r.status_code}). Refresh tokens expire after 7 days while the OAuth app is in 'Testing': publish the app, then create a new token.")
        d = r.json(); self._tok, self._exp = d["access_token"], self.clock() + int(d.get("expires_in", 3600)); return self._tok

    def _req(self, method, url, headers=None, **kw):
        h = {"Authorization": f"Bearer {self.access_token()}"}; h.update(headers or {})
        return self.sess.request(method, url, headers=h, timeout=kw.pop("timeout", 60), **kw)

    def _ok(self, r, what):
        if r.status_code >= 400: raise YouTubeError(f"{what} failed: HTTP {r.status_code}: {r.text[:200]}")
        return r

    def channel_ids(self):
        r = self._ok(self._req("GET", f"{API}/channels", params={"part": "id", "mine": "true"}), "channel identity")
        return {i["id"] for i in r.json().get("items", [])}

    def search_recent(self, query, published_after, max_results=10, language="en", duration="short"):
        r = self._ok(self._req("GET", f"{API}/search", params={"part": "snippet", "type": "video", "order": "viewCount", "videoDuration": duration,
                     "publishedAfter": published_after, "q": query, "maxResults": max_results, "relevanceLanguage": language}), "search")
        return [{"id": i["id"]["videoId"], "title": i["snippet"]["title"], "channel": i["snippet"]["channelTitle"], "channel_id": i["snippet"]["channelId"],
                 "published": i["snippet"]["publishedAt"]} for i in r.json().get("items", [])]

    def upload(self, path, body):
        size = os.path.getsize(path)
        r = self._ok(self._req("POST", f"{UPLOAD}/videos?uploadType=resumable&part=snippet,status", json=body,
                     headers={"Content-Type": "application/json; charset=UTF-8", "X-Upload-Content-Length": str(size), "X-Upload-Content-Type": "video/mp4"}), "upload init")
        url = r.headers.get("Location")
        if not url: raise YouTubeError("upload init returned no session URL")
        with open(path, "rb") as fh:
            r = self.sess.put(url, data=fh, headers={"Content-Length": str(size), "Content-Type": "video/mp4"}, timeout=600)
        self._ok(r, "upload"); return r.json()["id"]

    def set_thumbnail(self, video_id, path):
        with open(path, "rb") as fh: data = fh.read()
        self._ok(self._req("POST", f"{UPLOAD}/thumbnails/set", params={"videoId": video_id}, data=data, headers={"Content-Type": "image/jpeg"}), "thumbnail")

    def update_status(self, video_id, status):
        self._ok(self._req("PUT", f"{API}/videos", params={"part": "status"}, json={"id": video_id, "status": status}), "status update")

    def video_stats(self, ids):
        r = self._ok(self._req("GET", f"{API}/videos", params={"part": "statistics", "id": ",".join(ids)}), "stats")
        return {i["id"]: {"views": int(i["statistics"].get("viewCount", 0)), "likes": int(i["statistics"].get("likeCount", 0)),
                          "comments": int(i["statistics"].get("commentCount", 0))} for i in r.json().get("items", [])}

    def _report(self, video_id, start, end, metrics, dimensions=None):
        p = {"ids": "channel==MINE", "startDate": start, "endDate": end, "metrics": metrics, "filters": f"video=={video_id}"}
        if dimensions: p["dimensions"] = dimensions
        return self._ok(self._req("GET", ANALYTICS, params=p), "analytics").json()

    def analytics(self, video_id, start, end):
        d = self._report(video_id, start, end, "views,averageViewPercentage,estimatedMinutesWatched,averageViewDuration,subscribersGained")
        return dict(zip([h["name"] for h in d.get("columnHeaders", [])], d["rows"][0])) if d.get("rows") else {}

    def retention(self, video_id, start, end):
        d = self._report(video_id, start, end, "audienceWatchRatio", "elapsedVideoTimeRatio")
        return [tuple(r) for r in d.get("rows", [])]

    def recent_comments(self, video_id, max_results=50):
        r = self._ok(self._req("GET", f"{API}/commentThreads", params={"part": "snippet", "videoId": video_id, "maxResults": max_results, "order": "time"}), "comments")
        return [{"id": i["id"], "text": i["snippet"]["topLevelComment"]["snippet"]["textDisplay"]} for i in r.json().get("items", [])]
