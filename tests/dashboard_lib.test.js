// Run: node tests/dashboard_lib.test.js   (pure helpers only; the UI itself is untested in a browser)
const assert = require("assert");
const L = require("../dashboard/lib.js");
let n = 0; const t = (name, fn) => { fn(); n++; console.log("ok -", name); };

t("esc neutralises markup", () => assert.strictEqual(L.esc('<img src=x onerror="a()">&'), "&lt;img src=x onerror=&quot;a()&quot;&gt;&amp;"));
t("isSafeUrl only allows github https", () => {
  assert(L.isSafeUrl("https://github.com/o/r/releases/download/t/video.mp4"));
  assert(!L.isSafeUrl("javascript:alert(1)")); assert(!L.isSafeUrl("http://github.com/x")); assert(!L.isSafeUrl("https://evil.example/x"));
});
t("base64 utf-8 roundtrip", () => { const s = "Zażółć 😈 ghost"; assert.strictEqual(L.fromB64(L.toB64(s)), s); });
t("deepMerge keeps untouched keys and replaces arrays", () => {
  const m = L.deepMerge({ a: { x: 1, y: [1, 2] }, b: 1 }, { a: { y: [3] } }); assert.deepStrictEqual(m, { a: { x: 1, y: [3] }, b: 1 });
});
t("validate rejects unsafe public flag", () => {
  const s = L.deepMerge(require("../dashboard/defaults.json"), { safety: { public_publishing_enabled: true } });
  assert(L.validateSettings(s).some(e => /sample/.test(e)));
});
t("validate accepts defaults", () => assert.deepStrictEqual(L.validateSettings(require("../dashboard/defaults.json")), []));
t("validate catches bad time and length", () => {
  const s = L.deepMerge(require("../dashboard/defaults.json"), { schedule: { publish_time: "99:99" }, content: { short_target_seconds: 5 } });
  const e = L.validateSettings(s).join(" "); assert(/publish_time/.test(e)); assert(/short_target_seconds/.test(e));
});
t("weekPlan: 7 shorts and two longs, starts Monday", () => {
  const s = L.deepMerge(require("../dashboard/defaults.json"), { content: { long_per_week: 2 } });
  const p = L.weekPlan(s, new Date(Date.UTC(2026, 10, 25)));      // a Wednesday
  assert.strictEqual(p.filter(r => r.format === "short").length, 7); assert.strictEqual(p.filter(r => r.format === "long").length, 2);
  assert.strictEqual(p[0].weekday, "mon"); assert.strictEqual(p[0].date, "2026-11-23");
});
t("statusLabel knows every pipeline status", () => ["generating", "awaiting_approval", "approved_manual", "uploaded_private", "scheduled", "published", "rejected", "failed"].forEach(s => assert(L.statusLabel(s) && L.statusLabel(s) !== s)));
t("ago formats", () => assert.strictEqual(L.ago("2026-11-25T10:00:00Z", new Date("2026-11-25T12:30:00Z")), "2 h ago"));
console.log(`${n} dashboard helper tests passed`);
