import base64, tempfile, unittest, wave
from pathlib import Path
from autopilot import production
from autopilot.cinematic_media import GeminiMedia, MediaError, generate_visuals

class ProductionTests(unittest.TestCase):
    def test_caps_per_profile(self):
        items = [{"profile":"hindi_shorts","status":"awaiting_approval"}]*3
        self.assertFalse(production.should_generate(items,"hindi_shorts"))
        self.assertTrue(production.should_generate(items,"english_long"))
        self.assertTrue(production.should_generate([dict(items[0],demo=True)]*3,"hindi_shorts"))
    def test_memory_skips_demo(self):
        self.assertEqual(production.story_memory([{"topic":"demo","demo":True},{"topic":"original","premise":"p"}])[0]["topic"],"original")
    def test_chapters(self):
        self.assertEqual(production.chapters([20]*6),["00:00 The first clue","00:40 The mystery deepens","01:20 The revelation"])
    def test_visual_report(self):
        r=production.visual_report([{"kind":"ai_image"},{"kind":"illustration"}],["forest","forest"])
        self.assertEqual(r["repeated_queries"],1)
        self.assertEqual(r["sources"]["ai_image"],1)
    def test_speech_wav(self):
        class Response:
            status_code=200
            def json(self):
                return {"candidates":[{"content":{"parts":[{"inlineData":{"mimeType":"audio/L16;rate=24000","data":base64.b64encode(b"\x01\x00"*24000).decode()}}]}}]}
        class Session:
            def post(self,*args,**kwargs):
                self.payload=kwargs["json"]; return Response()
        session=Session()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"voice.wav"
            GeminiMedia("test-key",session).speech("test-model","Hindi")("नमस्ते",p)
            with wave.open(str(p),"rb") as w:
                self.assertEqual(w.getframerate(),24000)
                self.assertEqual(w.getnframes(),24000)
        self.assertEqual(session.payload["generationConfig"]["responseModalities"],["AUDIO"])
    def test_image_budget_and_reference(self):
        class Fake:
            def __init__(self): self.refs=[]
            def image(self,model,prompt,aspect,out,reference):
                self.refs.append(reference); Path(out).write_bytes(b"fake")
        m=Fake()
        with tempfile.TemporaryDirectory() as d:
            rows=generate_visuals(m,"model",{"logline":"story","scenes":[{}]*3},["a","b","c"],d,max_calls=2)
            self.assertEqual(len(m.refs),2)
            self.assertIsNone(m.refs[0])
            self.assertIsNotNone(m.refs[1])
            self.assertIsNone(rows[2]["path"])
