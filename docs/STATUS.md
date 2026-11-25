# Status: what is done, what was tested, what was not

Every number below came from a command run in the build sandbox on 24-25 Nov 2026
(Python 3.12, FFmpeg 6.1, Node 22, headless Chromium; **no internet**, so no live API was ever called).

## Test evidence
| Check | Result |
|---|---|
| Python unit/integration tests (`python -m unittest discover -s tests -t .`) | **122 passed**, 0 failed (4 of them render full 1080p videos, ~3 min total) |
| Dashboard helper tests (`node tests/dashboard_lib.test.js`) | **10 passed** |
| Dashboard in headless Chromium, 390 px phone viewport, mocked GitHub API (`python tools/dashboard_smoke.py`) | **passed**: renders, XSS payload inert, unsafe `javascript:` URL refused, Approve/posted/settings/demo send the exact expected requests, public-publishing button locked, no JS errors, no overflow at 360 px |
| 5 workflow files | **parse as valid YAML** only; never executed |
| End-to-end demo through the real CLI (`python -m autopilot generate --demo`) | **passed**: 1080x1920 H.264+AAC, ~37 s, 2.5 MB, captions, thumbnail, queue entry. ~60 s on 1 CPU |

## Completed and tested (against fakes / local FFmpeg)
Settings + validation, publish guard (manual / private / scheduled, both-flags rule, daily cap), scheduler (timezones), state store with secret-redacting log,
Gemini client (retry, model fallback, header-only key), script validation + repair loop + hook scoring, novelty filter, swipe ranking via the installed skill,
voice licence allow-list, sentence timeline, footage selection + people filter + attribution, FFmpeg music, animated ASS captions, segment/grade/mix/duck/loudnorm render,
bitrate cap, thumbnail, title/thumbnail lint, tags, description, chapter validator, YouTube REST client (token refresh, resumable upload, thumbnails, stats, analytics, retention, comments),
retention report, insights, audit, comment triage, sample-approval and public-switch gates, doctor.

## Written but NOT tested against the real service
- **Gemini**: prompts, JSON-mode behaviour, the default `-latest` model names, free-tier limits on your key.
- **Pexels**: real search results, how often the people filter rejects or lets through a clip, download of the chosen file.
- **Piper**: CLI flags (`--model --data-dir --download-dir --output_file`), first-use voice download, whether `en_US-john-medium` exists, voice quality.
- **YouTube**: OAuth refresh, resumable upload, `thumbnails.set` (may need a verified channel), Analytics/retention response shapes (built from the docs and mocked).
- **GitHub Actions**: all five workflows (release creation, `GITHUB_TOKEN` permissions, state commit/rebase races, cron, Pages deploy), and the bootstrap unpack.
- **Dashboard against the real GitHub API**: CORS and fine-grained-token behaviour, video playback of release assets on Android Chrome.
- **Runner time**: unknown; expect a few minutes.

## Not built (honest gaps)
- **Long-form videos.** The pipeline refuses `content.mode = long` and logs why. Needs minute-scale pacing, chapters generation and a different script prompt.
- **yt-shorts clip extraction** from long videos. Only the Short *rules* are used.
- **yt-chapters generation.** Only the rule validator exists.
- Posting comment replies (drafts only, by design). Word-level caption timing from audio (it is estimated per sentence).
- An independent code review. Content-quality evaluation: nobody has watched a real Gemini-written, Pexels-illustrated video yet.

## Known risks
1. **Monetisation.** An automated daily template-like horror channel is the pattern YouTube's 2026 guidance targets. See POLICIES.md.
2. **API audit.** Until it passes, API uploads are forced private, so manual mode is the real path.
3. **Public repo.** Scripts, queue and logs are public; secrets are not.
4. **Pexels people filter** is a heuristic on the URL slug.
5. **Dashboard token** lives in browser storage on your phone.

## Bugs found and fixed during the build (so you know the checks are real)
Wrong JSON key from the swipe skill; 127 MB demo video (27 Mbps grain) now capped at 5 Mbps; a commented-out thumbnail call (caught by running the tests,
now guarded by an output check); captions burned into thumbnails; clipped nav tab on narrow phones; queue ordering depended on array order; misleading "pull down to refresh" copy.
