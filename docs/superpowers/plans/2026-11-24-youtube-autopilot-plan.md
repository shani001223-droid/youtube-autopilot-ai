# YouTube Autopilot AI V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (native, no subagent tool available). Steps use checkboxes.

**Goal:** A phone-managed, GitHub-Actions-run pipeline that produces one approved horror Short per day.
**Architecture:** `autopilot/` Python package (pure functions + injected clients), JSON state in `data/`, 5 workflows, static dashboard.
**Tech Stack:** Python 3.11+, requests, PyYAML, Pillow, FFmpeg, Piper, Gemini REST, Pexels REST, YouTube REST.
**Spec:** docs/superpowers/specs/2026-11-24-youtube-autopilot-design.md

## Global Constraints
- Zero cost, 100% cloud, Android-only. Secrets only via GitHub Secrets: GEMINI_API_KEY, PEXELS_API_KEY, YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
- Public publishing blocked unless `safety.sample_approved` AND `safety.public_publishing_enabled` AND `publish.mode == "api"`.
- Short target 20-55 s, 1080x1920, 30 fps, H.264 + AAC, loudness-normalised.

## Review Focus
- Gemini returns fenced / malformed JSON -> `extract_json` and a repair retry.
- Pexels returns no usable clip -> fallback generated clip, never a failed render.
- A voice with a non-commercial licence is configured -> hard error.
- Two uploads attempted the same day -> blocked by `can_upload_today`.
- Settings file edited by hand into an unsafe state -> `validate_settings` rejects it.

### Tasks (each: failing test -> implementation -> green -> commit)
1. `config.py`, `safety.py`, `scheduler.py` - settings, publish guard, slots, weekly plan (yt-plan).
2. `state.py` - queue/log store with ring buffer.
3. `llm.py` - Gemini REST client with model fallback and retry.
4. `scriptgen.py` - variety engine, prompt, validation, hook scoring (yt-script, yt-shorts rules).
5. `research.py` - novelty filter, trend titles, swipe ranking (yt-viral).
6. `tts.py` - voice allow-list, sentence timeline, Piper wrapper.
7. `footage.py` - Pexels search, people filter, file picking, attribution.
8. `music.py`, `subtitles.py` - FFmpeg ambient bed, animated ASS.
9. `render.py` - FFmpeg segments, grade, mix, ducking, 1080p encode, probe, QA (yt-edit deadair).
10. `thumbnail.py`, `seo.py` - thumbnail, title/thumb lint (yt-package), tags/description (yt-seo), chapters (yt-chapters).
11. `youtube.py`, `analytics.py`, `improve.py`, `audit.py`, `comments.py` - REST clients, retention (yt-retention), audit (yt-audit), comment triage (yt-comment).
12. `pipeline.py`, `cli.py` - orchestration, demo mode, doctor.
13. Workflows: ci, generate, publish, analytics, pages.
14. Dashboard (frontend-design skill).
15. Docs, ZIP, honest status matrix.
