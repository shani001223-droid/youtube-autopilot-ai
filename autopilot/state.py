"""JSON state in data/: queue.json (videos) and logs.json (ring buffer). Atomic writes; secrets redacted from logs."""
import json, os, re, secrets, tempfile
from datetime import datetime, timezone

REDACT = [re.compile(p) for p in (r"AIza[0-9A-Za-z_\-]{20,}", r"ya29\.[0-9A-Za-z_\-]+", r"1//[0-9A-Za-z_\-]{20,}",
                                   r"Bearer\s+\S+", r"(?i)(token|key|secret|password|authorization)=\S+")]


def redact(text):
    for rx in REDACT:
        text = rx.sub(lambda m: (m.group(1) + "=[redacted]") if m.lastindex else "[redacted]", text)
    return text


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Store:
    def __init__(self, data_dir="data", log_cap=500):
        self.dir, self.log_cap = data_dir, log_cap
        os.makedirs(data_dir, exist_ok=True)
        self._queue = self._read("queue.json"); self._logs = self._read("logs.json")

    def _read(self, name):
        try:
            with open(os.path.join(self.dir, name), encoding="utf-8") as fh: return json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError): return []

    def _write(self, name, data):
        fd, tmp = tempfile.mkstemp(dir=self.dir, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh: json.dump(data, fh, indent=1, ensure_ascii=False)
        os.replace(tmp, os.path.join(self.dir, name))

    def add_item(self, item):
        item = dict(item); item.setdefault("id", datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(2))
        item.setdefault("created_at", now_iso()); self._queue.append(item); self._write("queue.json", self._queue); return item

    def get(self, item_id):
        for it in self._queue:
            if it["id"] == item_id: return it
        raise KeyError(item_id)

    def update(self, item_id, **fields):
        it = self.get(item_id); it.update(fields); self._write("queue.json", self._queue); return it

    def items(self, status=None):
        return [i for i in self._queue if status is None or i.get("status") == status]

    def log(self, level, stage, message, run_id=None):
        self._logs.append({"t": now_iso(), "level": level, "stage": stage, "message": redact(str(message))[:2000], "run": run_id})
        self._logs = self._logs[-self.log_cap:]; self._write("logs.json", self._logs)

    def logs(self, level=None, limit=100):
        return [l for l in self._logs if level is None or l["level"] == level][-limit:]


def _extra_read(self, name, default):
    try:
        with open(os.path.join(self.dir, name), encoding="utf-8") as fh: return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError): return default


def _extra_write(self, name, data):
    self._write(name, data)


Store.read_json, Store.write_json = _extra_read, _extra_write
