# Dual-channel cloud manager — deployment and verification

This project runs on GitHub Actions, not a continuously running Render server. It can run scheduled jobs while the phone is off. Schedules are best-effort and subject to provider quotas.

## Production profiles

- hindi_shorts: 45 seconds, Hindi/Devanagari, 1080x1920, daily 08:17 and 17:43 Pakistan time.
- english_long: 8 minute target, English, 1920x1080, Tuesday and Saturday 13:27 Pakistan time.
- legacy: existing English Short generator remains available on manual dispatch.
- Review queue caps: 3 Hindi previews, 1 English long preview. New profiles cannot automatically upload to YouTube until separate channel authorization and publishing safeguards are completed.

## Sample verification

Open Actions > Generate video. Run workflow on main with profile hindi_shorts or english_long, demo unchecked, and wait for the actual job conclusion. The latest workflow upgrade also attempts both profiles on a push. Check the logs and release assets, then review the entire video on a phone: understandable speech, accurate subtitles, original fiction, matching shots, credible continuity, audio balance and duration. The Hindi offline eSpeak voice is a test fallback, not final quality. Do not mark a sample verified merely because its MP4 exists. Demo mode is for legacy plumbing tests only.

The existing repository is public: GitHub Release previews and committed queue/story/analytics metadata are publicly accessible. Avoid uploading confidential material. For private previews, change the repository/storage design before production.

## Optional media

Repository Settings > Secrets and variables > Actions > Variables:

- GEMINI_TTS_MODEL: optional model available to the existing Gemini key (verify free-tier availability/billing in AI Studio first; e.g. gemini-2.5-flash-preview-tts if still available). Uses one voice provider per video, not mixed voices.
- GEMINI_IMAGE_MODEL: optional model available to the Gemini key.
- ALLOW_PAID_IMAGE_API: defaults off. Set true only after explicit cost approval.
- AI_IMAGE_MAX_CALLS: defaults 0, maximum 8 per video including failures.

No model or paid service is automatically activated by these changes. If the optional image provider is unavailable, licensed stock / original illustrated scenes are used. This is not the same as text-to-video animation, and character consistency is a best-effort reference rather than a guaranteed identity lock.

## Claude manager

Use an authorized GitHub connector in Claude (or Claude's custom remote MCP support, if your plan and authentication method support it). GitHub's official MCP server documentation: https://github.com/github/github-mcp-server. Remote endpoint: https://api.githubcopilot.com/mcp/. Claude custom connector documentation: https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp. Compatibility and authorization must be checked in the user's account. If the connector cannot trigger workflows, use the Actions UI; do not create a public unauthenticated proxy.

Manager instructions:

> Manage only shani001223-droid/youtube-autopilot-ai. Read data/queue.json, data/logs.json, workflow results and this file. Distinguish code committed, CI passed, actual video rendered, and human-reviewed. Recommend new original fictional premises; avoid reproducing viral plots. Use generate.yml with profile hindi_shorts or english_long and demo=false only when the queue has capacity. Review existing failures before retrying. Respect API budgets. Never enable public uploads, change secrets, or change paid billing without the owner explicitly authorizing the relevant action. Report real job links and completed sample URLs; never invent metrics or promise virality.

Claude can direct the workflow once connected; GitHub Actions runs the scheduled production independently. This does not grant Claude persistent unattended sessions or constitute a verified Claude account connection.

## YouTube account authorization

Use separate OAuth credentials and actual UC channel IDs. GitHub Actions Secrets: YT_HINDI_CLIENT_ID, YT_HINDI_CLIENT_SECRET, YT_HINDI_REFRESH_TOKEN; YT_ENGLISH_CLIENT_ID, YT_ENGLISH_CLIENT_SECRET, YT_ENGLISH_REFRESH_TOKEN. Repository Variables: YT_HINDI_CHANNEL_ID and YT_ENGLISH_CHANNEL_ID. Never paste refresh tokens into a conversation or commit them.

Daily analytics is wired to check the authenticated channel identity and write separate insights. No automatic upload is enabled for these new profiles. Public auto-publishing additionally needs YouTube project audit where applicable, separate per-channel approval and an actual upload test.

## Current verification boundary

Source updates and regression tests have been committed. The actual Actions run conclusion and new sample videos were not verified by the editing connector. Do not claim that the system is production-ready until the live tests pass and samples are reviewed.
