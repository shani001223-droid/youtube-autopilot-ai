import tempfile, unittest, subprocess
from pathlib import Path
from PIL import Image, ImageStat
from autopilot import commons_media as cm, illustration, render

def page(license="CC BY 4.0", mime="video/webm"):
    return {"pageid":1,"title":"File:Fog in forest.webm","imageinfo":[{"mime":mime,"width":1280,"height":720,
        "size":50000,"url":"https://upload.wikimedia.org/test.webm","descriptionurl":"https://commons.wikimedia.org/wiki/File:Test.webm",
        "extmetadata":{"LicenseShortName":{"value":license},"Artist":{"value":"<b>Test Author</b>"},
        "LicenseUrl":{"value":"https://creativecommons.org/licenses/by/4.0/"}}}]}

class VisualTests(unittest.TestCase):
    def test_license_gate(self):
        self.assertIn("Test Author",cm.candidate(page())["credit"])
        self.assertIsNone(cm.candidate(page("CC BY-SA 4.0")))
        self.assertIsNone(cm.candidate(page("unknown")))
        p=page();p["imageinfo"][0]["extmetadata"]["Restrictions"]={"value":"trademark"}
        self.assertIsNone(cm.candidate(p))
    def test_offline_fallback_not_blank(self):
        class Offline:
            unavailable=True
        with tempfile.TemporaryDirectory() as d:
            clips=cm.fill_missing([{"path":None,"credit":None}]*1,["foggy lighthouse"],d,client=Offline())
            self.assertEqual(clips[0]["kind"],"illustration")
            with Image.open(clips[0]["path"]) as im:
                self.assertGreater(max(ImageStat.Stat(im).stddev),15)
            p=Path(d)/"motion.mp4"
            subprocess.run(render.still_segment_args(clips[0]["path"],1,p,w=360,h=640,fps=15),check=True,capture_output=True)
            info=render.probe(p)
            self.assertTrue(info["has_video"])
            self.assertAlmostEqual(info["duration"],1,delta=.1)
    def test_prefer_stock_and_credit(self):
        class Online:
            unavailable=False
            def find(self,q,media): return [cm.candidate(page())] if media=="video" else []
            def download(self,a,d,i):
                p=Path(d)/"clip.webm";p.write_bytes(b"mock");return str(p)
        with tempfile.TemporaryDirectory() as d:
            clips=cm.fill_missing([{"path":None,"credit":None}],["foggy forest"],d,client=Online())
            self.assertEqual(clips[0]["kind"],"commons_video")
            self.assertIn("CC BY 4.0",clips[0]["credit"])
