import os, tempfile, unittest
from autopilot import config, youtube
from tests.helpers import FakeResp, FakeSession

META = {"title": "T" * 120, "description": "d", "tags": ["a", "b"]}


def fresh(): return config.load_settings("/nonexistent")


class BodyTests(unittest.TestCase):
    def test_private_by_default_and_declares_not_for_kids(self):
        b = youtube.build_video_body(META, "private", None, fresh())
        self.assertEqual(b["status"]["privacyStatus"], "private"); self.assertFalse(b["status"]["selfDeclaredMadeForKids"])
        self.assertNotIn("publishAt", b["status"]); self.assertLessEqual(len(b["snippet"]["title"]), 100)
        self.assertEqual(b["snippet"]["categoryId"], "24")

    def test_publish_at_only_with_private(self):
        b = youtube.build_video_body(META, "private", "2026-11-25T18:00:00Z", fresh())
        self.assertEqual(b["status"]["publishAt"], "2026-11-25T18:00:00Z")
        with self.assertRaises(ValueError): youtube.build_video_body(META, "public", "2026-11-25T18:00:00Z", fresh())

    def test_synthetic_disclosure_flag_follows_setting(self):
        s = fresh(); s["publish"]["disclose_synthetic"] = True
        self.assertTrue(youtube.build_video_body(META, "private", None, s)["status"]["containsSyntheticMedia"])
        s["publish"]["disclose_synthetic"] = False
        self.assertNotIn("containsSyntheticMedia", youtube.build_video_body(META, "private", None, s)["status"])

    def test_video_id_from_url(self):
        for u in ["https://youtu.be/abcDEF12345", "https://www.youtube.com/watch?v=abcDEF12345&t=3", "https://youtube.com/shorts/abcDEF12345?feature=share", "abcDEF12345"]:
            self.assertEqual(youtube.video_id_from_url(u), "abcDEF12345")
        self.assertIsNone(youtube.video_id_from_url("https://example.com/x"))


def client(replies):
    s = FakeSession([FakeResp(200, {"access_token": "AT", "expires_in": 3600})] + replies)
    return youtube.YouTubeClient("cid", "csecret", "rtoken", session=s, clock=lambda: 1000.0), s


class ClientTests(unittest.TestCase):
    def test_token_refresh_and_cache(self):
        c, s = client([FakeResp(200, {"items": []}), FakeResp(200, {"items": []})])
        c.video_stats(["x"]); c.video_stats(["y"])
        token_calls = [x for x in s.calls if "oauth2.googleapis.com/token" in x["url"]]
        self.assertEqual(len(token_calls), 1)
        self.assertEqual(token_calls[0]["data"]["grant_type"], "refresh_token"); self.assertEqual(token_calls[0]["data"]["refresh_token"], "rtoken")
        self.assertEqual(s.calls[1]["headers"]["Authorization"], "Bearer AT")

    def test_search_recent_params(self):
        c, s = client([FakeResp(200, {"items": [{"id": {"videoId": "v1"}, "snippet": {"title": "T", "channelTitle": "C", "channelId": "UC1", "publishedAt": "2026-11-01T00:00:00Z"}}]})])
        out = c.search_recent("scary story", "2026-10-25T00:00:00Z", max_results=5)
        p = s.calls[1]["params"]
        self.assertEqual((p["type"], p["order"], p["videoDuration"], p["publishedAfter"]), ("video", "viewCount", "short", "2026-10-25T00:00:00Z"))
        self.assertEqual(out[0]["id"], "v1"); self.assertNotIn("key", p)

    def test_upload_resumable_flow(self):
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "v.mp4"); open(f, "wb").write(b"0" * 2048)
            c, s = client([FakeResp(200, {}, headers={"Location": "https://upload.example/session1"}), FakeResp(200, {"id": "NEWID"})])
            vid = c.upload(f, {"snippet": {"title": "t"}, "status": {"privacyStatus": "private"}})
            self.assertEqual(vid, "NEWID")
            init, put = s.calls[1], s.calls[2]
            self.assertIn("uploadType=resumable", init["url"]); self.assertEqual(init["headers"]["X-Upload-Content-Length"], "2048")
            self.assertEqual(put["method"], "PUT"); self.assertEqual(put["url"], "https://upload.example/session1")

    def test_upload_failure_raises_without_leaking_token(self):
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "v.mp4"); open(f, "wb").write(b"0")
            c, s = client([FakeResp(403, {"error": {"message": "quota"}}, text='{"error":"quota"}')])
            with self.assertRaises(youtube.YouTubeError) as cm: c.upload(f, {})
            self.assertNotIn("AT", str(cm.exception).replace("quota", ""))

    def test_update_status_and_thumbnail(self):
        with tempfile.TemporaryDirectory() as d:
            img = os.path.join(d, "t.jpg"); open(img, "wb").write(b"jpg")
            c, s = client([FakeResp(200, {}), FakeResp(200, {})])
            c.update_status("V1", {"privacyStatus": "private", "publishAt": "2026-11-25T18:00:00Z", "selfDeclaredMadeForKids": False})
            c.set_thumbnail("V1", img)
            self.assertEqual(s.calls[1]["method"], "PUT"); self.assertEqual(s.calls[1]["params"]["part"], "status")
            self.assertEqual(s.calls[1]["json"]["id"], "V1"); self.assertIn("thumbnails/set", s.calls[2]["url"])

    def test_video_stats_parse(self):
        c, s = client([FakeResp(200, {"items": [{"id": "V1", "statistics": {"viewCount": "120", "likeCount": "9", "commentCount": "2"}}]})])
        self.assertEqual(c.video_stats(["V1"]), {"V1": {"views": 120, "likes": 9, "comments": 2}})

    def test_analytics_and_retention_parse(self):
        rows = {"columnHeaders": [{"name": "views"}, {"name": "averageViewPercentage"}], "rows": [[100, 61.5]]}
        ret = {"columnHeaders": [{"name": "elapsedVideoTimeRatio"}, {"name": "audienceWatchRatio"}], "rows": [[0.01, 1.0], [0.5, 0.6]]}
        c, s = client([FakeResp(200, rows), FakeResp(200, ret)])
        self.assertEqual(c.analytics("V1", "2026-11-01", "2026-11-24"), {"views": 100, "averageViewPercentage": 61.5})
        self.assertEqual(c.retention("V1", "2026-11-01", "2026-11-24"), [(0.01, 1.0), (0.5, 0.6)])


if __name__ == "__main__":
    unittest.main()
