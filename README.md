# YouTube Autopilot AI V1

A phone-managed, GitHub-Actions-run pipeline that makes **one original horror/mystery Short per day**, shows it to you for
approval on a mobile dashboard, and keeps everything **private/manual until you approve a sample**. Zero cost, no PC, no server.

**Read `docs/STATUS.md` first**: it says exactly what has been tested and what has not.

## How a day works
1. 03:17 UTC: `generate.yml` runs. Research -> script (Gemini) -> voice (Piper) -> footage (Pexels) -> FFmpeg edit, animated captions,
   generated music, 1080x1920 -> thumbnail -> title/description/tags.
2. The video is attached to a GitHub Release; the dashboard shows it in the **Queue** tab.
3. You watch it on your phone and tap **Approve** or **Reject**.
4. Manual mode (default): download the MP4 + copy the text, upload in the YouTube app, tap **I posted it**.
   API mode: the pipeline uploads it **private**. Public scheduling stays locked until you mark a sample as good *and* flip the switch.
5. `analytics.yml` reads results, finds which subgenres retain best, and nudges the next videos toward them.

## Where each installed skill is used
| Skill | Used for | Code |
|---|---|---|
| yt-plan | weekly plan, honest about workload | `scheduler.weekly_plan` |
| yt-script | 5 hooks per script, scored; 150 wpm sizing | `scriptgen`, `skills/hookscore.py` |
| yt-shorts | Short rules in the prompt: 20-55 s, complete opening, a turn, a loop line (clip-extraction from long videos is **not built**) | `scriptgen.build_script_prompt` |
| yt-viral | rank trending videos by multiple of channel median | `research.swipe_rank`, `skills/yt-viral/swipe.py` |
| yt-package | title + thumbnail lint as a pair | `seo.choose_title`, `skills/title.py` |
| yt-seo | description first-two-lines, tags, query test | `seo.build_description`, `query_test` |
| yt-edit | dead-air QA on the narration | `qa.dead_air_report`, `skills/deadair.py` |
| yt-chapters | YouTube chapter-rule validator (chapter *generation* for long-form is **not wired**) | `seo.chapters_valid` |
| yt-retention | retention curve analysis | `analytics.retention_report`, `skills/retention.py` |
| yt-audit | one fix, not a report | `audit.audit_channel` |
| yt-comment | triage + reply *drafts* (never auto-posted) | `comments.py` |

Superpowers used: brainstorming (`docs/superpowers/specs`), writing-plans (`docs/superpowers/plans`), test-driven-development (tests written
and watched failing first), verification-before-completion (every claim in STATUS.md comes from a command that was run),
frontend-design (dashboard). **No independent code review was done.**

## Layout
`autopilot/` pipeline - `tests/` 122 Python + 10 JS tests - `dashboard/` phone UI (GitHub Pages) - `.github/workflows/` 5 workflows -
`data/` JSON state committed by the workflows - `docs/` setup, policies, status - `tools/` helpers and the browser smoke test.

## Secrets (GitHub Secrets only; never in chat, never in files)
`GEMINI_API_KEY`, `PEXELS_API_KEY` for generation. `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` for analytics and API mode (optional).
Run `python -m autopilot doctor` (or the demo) to see which are present. It prints names, never values.

Start with `docs/SETUP_ANDROID.md`.
