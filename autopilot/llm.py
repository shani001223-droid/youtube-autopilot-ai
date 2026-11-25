"""Gemini REST client (free tier). Key goes in a header, never in a URL. Falls back across models; retries politely."""
import json, time
import requests

BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiError(Exception):
    pass

class GeminiUnavailable(GeminiError):
    pass


def extract_json(text):
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t[3:]
        t = t.rsplit("```", 1)[0]
    try: return json.loads(t)
    except ValueError: pass
    dec = json.JSONDecoder()
    for i, ch in enumerate(t):
        if ch in "{[":
            try: return dec.raw_decode(t[i:])[0]
            except ValueError: continue
    raise ValueError("no JSON found in model output")


class GeminiClient:
    def __init__(self, api_key, models, session=None, sleep=time.sleep, max_retries=3, temperature=1.0, timeout=180):
        self.key, self.models, self.sess = api_key.strip(), list(dict.fromkeys(models)), session or requests.Session()
        self.daily_exhausted = set()
        self.sleep, self.max_retries, self.temperature, self.timeout = sleep, max_retries, temperature, timeout

    def generate_text(self, prompt, system=None, json_mode=False):
        payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": {"temperature": self.temperature}}
        if system: payload["systemInstruction"] = {"parts": [{"text": system}]}
        if json_mode: payload["generationConfig"]["responseMimeType"] = "application/json"
        errors = []
        for model in self.models:
            if model in self.daily_exhausted:
                errors.append(f"{model}: HTTP 429 daily quota used up (cached for this run)")
                continue
            for attempt in range(self.max_retries):
                last_attempt = attempt + 1 >= self.max_retries
                try:
                    r = self.sess.post(
                        f"{BASE}/models/{model}:generateContent",
                        headers={"x-goog-api-key": self.key, "Content-Type": "application/json"},
                        json=payload, timeout=(15, self.timeout))
                except (requests.Timeout, requests.ConnectionError) as ex:
                    reason = f"{type(ex).__name__} (read timeout {self.timeout}s)"
                    if last_attempt:
                        errors.append(f"{model}: {reason}; retries exhausted")
                        break
                    self.sleep(min(30, 5 * 2 ** attempt))
                    continue
                code = r.status_code
                if code == 200:
                    try:
                        body = r.json()
                    except ValueError:
                        errors.append(f"{model}: invalid response JSON"); break
                    if not isinstance(body, dict):
                        errors.append(f"{model}: unexpected response shape"); break
                    if body.get("promptFeedback", {}).get("blockReason"):
                        raise GeminiError(f"prompt blocked: {body['promptFeedback']['blockReason']}")
                    parts = (body.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
                    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
                    if text.strip():
                        if json_mode:
                            try: extract_json(text)
                            except ValueError:
                                errors.append(f"{model}: invalid generated JSON"); break
                        return text
                    errors.append(f"{model}: empty response"); break
                if code == 404:
                    errors.append(f"{model}: HTTP 404 model not found"); break
                if code == 429:
                    raw = r.text.lower()
                    if "perday" in raw or "per day" in raw:
                        self.daily_exhausted.add(model)
                        errors.append(f"{model}: HTTP 429 daily quota used up"); break
                    reason = "HTTP 429 rate limit or quota"
                    delay = min(60, 15 * 2 ** attempt)
                    try:
                        delay = max(delay, min(90, float(r.headers.get("Retry-After", 0))))
                    except (ValueError, TypeError):
                        pass
                elif code >= 500 or code == 408:
                    reason = f"HTTP {code} temporary server error"
                    delay = min(30, 5 * 2 ** attempt)
                else:
                    raise GeminiError(f"{model}: HTTP {code} from Gemini (check GEMINI_API_KEY and project access)")
                if last_attempt:
                    errors.append(f"{model}: {reason}; retries exhausted")
                    break
                self.sleep(delay)
        raise GeminiUnavailable("all Gemini models failed: " + "; ".join(errors))

    def generate_json(self, prompt, system=None):
        try: return extract_json(self.generate_text(prompt, system, json_mode=True))
        except ValueError as ex: raise GeminiError(f"model returned invalid JSON: {ex}")
