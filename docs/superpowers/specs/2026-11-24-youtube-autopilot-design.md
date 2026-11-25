# YouTube Autopilot AI V1 - Design

Written with the brainstorming skill. The owner opted out of clarifying questions ("START BUILDING NOW"),
so every "My call" below is a proposal the owner can change, not something they agreed to.

## Intent and why
One person, one Android phone, no budget. A channel of original English horror and mystery stories that
produces one vertical Short per day with a human approval step, so that the owner supervises instead of producing.

## Goals
- Daily Short (20-55 s, 1080x1920) generated entirely in GitHub Actions: topic, script, voice, footage, edit, subtitles, music, thumbnail, SEO.
- Phone-only control: a dashboard served from GitHub Pages; credentials only in GitHub Secrets.
- Public publishing impossible until the owner approves a sample and flips a second switch.
- Long-form (2 per week) switchable on after the Shorts flow is proven.
- Niche, voice, length, schedule and safety are data (`data/settings.json`), not code.

## Non-goals
- No paid service, no server, no PC. No scraping. No cloning of real people's voices or faces.
- No auto-reply to comments (drafts only). No monetization promises.

## Anti-goals (failure even if it "works")
- A channel of near-identical template videos (YouTube's July 2026 "generic or repetitive content" guidance).
- A secret or token ever appearing in chat, in the repo, or in a log.
- A video going public the owner has not seen.

## Constraints (verified, see docs/POLICIES.md)
- Unverified YouTube API projects: uploads are locked private until an audit. => `publish.mode = manual` is the default.
- OAuth consent screen in Testing: refresh tokens die after 7 days. => set to In production before creating the token.
- Free Actions minutes need a public repo (private: 2,000 min/month). Pages for free also needs a public repo.
- Piper voices differ in licence; several popular ones are non-commercial. => voice allow-list enforced in code.
- Pexels forbids showing identifiable people in a bad light. => horror footage is scenery/objects only, enforced by a filter.

## Approaches considered
1. **Everything in GitHub (chosen).** State as JSON committed by workflows; dashboard is static and talks to the GitHub API.
   Trade-off: repo is public; the phone holds a fine-grained token. No extra service.
2. Supabase for state and a hosted dashboard. Trade-off: one more account and free-tier pausing; more secrets.
3. Telegram/chat bot for approval. Trade-off: no preview/settings UI, still needs a host.

## My calls (not agreed, change freely)
- Piper voice default `en_US-john-medium` (listed public domain by a third party; verify its model card).
- Gemini model names are config; defaults are the `-latest` aliases.
- Music is synthesized by FFmpeg (no third-party licence at all).
- Preview video is a GitHub Release asset (public URL, unguessable-by-obscurity only).
- Variety engine (subgenre x structure x visual style, biased by analytics) to fight the "repetitive" policy.
- Stdlib `unittest` so tests run with zero installs.
