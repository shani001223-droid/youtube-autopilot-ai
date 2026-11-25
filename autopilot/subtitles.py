"""Animated word-by-word captions (ASS). Word timing is estimated inside each sentence by character weight,
because Piper gives sentence-level audio only."""


def fmt_ass_time(t):
    cs = int(round(max(0.0, t) * 100)); h, cs = divmod(cs, 360000); m, cs = divmod(cs, 6000); s, c = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def word_timings(timeline):
    out = []
    for seg in timeline:
        words = seg["text"].split()
        if not words: continue
        weights = [len(w) + 1 for w in words]; total = float(sum(weights)); t = seg["start"]; span = seg["end"] - seg["start"]
        for i, (w, wt) in enumerate(zip(words, weights)):
            end = seg["end"] if i == len(words) - 1 else t + span * wt / total
            out.append({"word": w, "start": round(t, 3), "end": round(end, 3)}); t = end
    return out


def chunk_words(words, max_words=3, max_chars=22):
    chunks, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or sum(len(x["word"]) + 1 for x in cur) + len(w["word"]) > max_chars):
            chunks.append(cur); cur = []
        cur.append(w)
        if w["word"][-1:] in ".!?": chunks.append(cur); cur = []
    if cur: chunks.append(cur)
    return chunks


def _clean(w): return w.replace("{", "(").replace("}", ")").replace("\\", "").upper()


def build_ass(words, width=1080, height=1920, font="DejaVu Sans", size=82, margin_v=430):
    head = (f"[Script Info]\nScriptType: v4.00+\nPlayResX: {width}\nPlayResY: {height}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, "
            "StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Default,{font},{size},&H00F2F2F2,&H00F2F2F2,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,7,2,2,60,60,{margin_v},1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    lines = []
    for chunk in chunk_words(words):
        for k, w in enumerate(chunk):
            end = chunk[k + 1]["start"] if k + 1 < len(chunk) else w["end"]
            parts = []
            for j, x in enumerate(chunk):
                txt = _clean(x["word"])
                parts.append(("{\\1c&H3AA6E0&\\fscx88\\fscy88\\t(0,90,\\fscx112\\fscy112)}" + txt + "{\\r}") if j == k else txt)
            lines.append(f"Dialogue: 0,{fmt_ass_time(w['start'])},{fmt_ass_time(max(end, w['start'] + 0.05))},Default,,0,0,0,,{' '.join(parts)}")
    return head + "\n".join(lines) + "\n"


def write_ass(path, words, **kw):
    with open(path, "w", encoding="utf-8") as fh: fh.write(build_ass(words, **kw))
