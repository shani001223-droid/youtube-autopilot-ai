/* Pure helpers for the dashboard (no DOM). Tested with: node tests/dashboard_lib.test.js */
(function (g) {
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const isSafeUrl = u => typeof u === "string" && /^https:\/\/(github\.com|objects\.githubusercontent\.com|youtu\.be|www\.youtube\.com|youtube\.com)\//.test(u);
  const toB64 = s => { const b = new TextEncoder().encode(s); let x = ""; b.forEach(c => x += String.fromCharCode(c)); return btoa(x); };
  const fromB64 = s => { const x = atob(s.replace(/\s/g, "")); return new TextDecoder().decode(Uint8Array.from(x, c => c.charCodeAt(0))); };
  const deepMerge = (a, b) => {
    const o = JSON.parse(JSON.stringify(a || {}));
    for (const [k, v] of Object.entries(b || {})) o[k] = (v && typeof v === "object" && !Array.isArray(v) && typeof o[k] === "object" && !Array.isArray(o[k])) ? deepMerge(o[k], v) : JSON.parse(JSON.stringify(v));
    return o;
  };
  const LABELS = { generating: "Making it", awaiting_approval: "Needs your review", approved_manual: "Approved: post it yourself", uploaded_private: "Uploaded (private)",
    scheduled: "Scheduled", published: "Published", rejected: "Rejected", failed: "Failed" };
  const statusLabel = s => LABELS[s] || "Unknown";
  function validateSettings(s) {
    const e = [], c = s.content, sch = s.schedule, saf = s.safety;
    if (!(c.short_target_seconds >= 20 && c.short_target_seconds <= 55)) e.push("content.short_target_seconds must be 20-55");
    if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(sch.publish_time)) e.push("schedule.publish_time must be HH:MM");
    if (saf.public_publishing_enabled && !saf.sample_approved) e.push("public publishing requires an approved sample");
    if (saf.public_publishing_enabled && s.publish.mode !== "api") e.push("public publishing requires publish.mode 'api'");
    if (!s.niche.subgenres.length) e.push("niche.subgenres must not be empty");
    return e;
  }
  function weekPlan(s, from) {
    const days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"], d0 = new Date(Date.UTC(from.getUTCFullYear(), from.getUTCMonth(), from.getUTCDate()));
    d0.setUTCDate(d0.getUTCDate() - ((d0.getUTCDay() + 6) % 7)); const rows = [], longs = s.content.long_days.slice(0, s.content.long_per_week);
    for (let i = 0; i < 7; i++) {
      const d = new Date(d0); d.setUTCDate(d0.getUTCDate() + i); const wd = days[i], date = d.toISOString().slice(0, 10);
      for (let k = 0; k < s.content.shorts_per_day; k++) rows.push({ date, weekday: wd, format: "short", time: s.schedule.publish_time });
      if (longs.includes(wd)) rows.push({ date, weekday: wd, format: "long", time: s.schedule.publish_time });
    }
    return rows;
  }
  function ago(iso, now) {
    const m = Math.max(0, Math.round(((now || new Date()) - new Date(iso)) / 60000));
    return m < 1 ? "just now" : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.floor(m / 60)} h ago` : `${Math.floor(m / 1440)} d ago`;
  }
  const api = { esc, isSafeUrl, toB64, fromB64, deepMerge, statusLabel, validateSettings, weekPlan, ago };
  g.Lib = api; if (typeof module !== "undefined") module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
