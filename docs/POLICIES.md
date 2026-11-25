# Verified policies, licences and limits (checked 24-25 Nov 2026)

Things change. Re-check anything that matters to you. "Verified" means I read it in a source this session; "not re-verified" means I am relying on prior knowledge.

## YouTube
- **Unverified API projects force uploads private.** Verified, YouTube `videos.insert` docs: videos uploaded through that endpoint from API projects created after 28 Jul 2020 that have not passed an API compliance audit are restricted to private. This is why `publish.mode` defaults to `manual`.
  https://developers.google.com/youtube/v3/docs/videos/insert - audit form: https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits
- **Quota.** The newest docs version I retrieved lists small per-day call allowances for `search.list` and `videos.insert` plus a 10,000-unit pool for other calls. Older versions priced an upload at 1,600 units. One upload per day is far inside either. Read your own quota page in Google Cloud Console.
  https://developers.google.com/youtube/v3/determine_quota_cost
- **Writable fields I rely on** (verified in the `videos` resource docs): `status.selfDeclaredMadeForKids`, `status.publishAt` (requires `privacyStatus=private`), `status.containsSyntheticMedia`.
- **"Generic / repetitive / off-putting" content.** As reported by TechCrunch (20 Jul 2026) and Tubefilter (13 Jul 2026): YouTube tightened monetisation rules for mass-produced, template-based and AI-slop content. I read press summaries, not the primary policy text. **A fully automated daily horror channel is exactly the pattern at risk.** Mitigations built in: variety engine, novelty filter, human approval, original scripts, no gore. They reduce, not remove, the risk.
- AI disclosure help page: https://support.google.com/youtube/answer/14328491

## Google OAuth
- **Refresh tokens expire after 7 days while the consent screen is in "Testing".** Verified via Google API forum threads (secondary source). Publish the app ("In production") *before* creating your token. A personal unverified app shows a warning screen you can click through.
- The OAuth Playground's *default* credentials reportedly revoke tokens after 24 h; use *your own* client ID/secret there.

## Gemini API (free tier)
- Limits are per model and per project, differ between models, and change without notice. Verified: docs page https://ai.google.dev/gemini-api/docs/rate-limits and a measurements post show per-minute and per-day ceilings that can be as low as tens of requests a day for some models. This project needs about 3-6 calls per video. If a model's daily quota is exhausted the client falls through to the next configured model.
- Model names are configuration (`gemini.models`). The `-latest` aliases are my assumption; confirm them in AI Studio.
- Not re-verified: Google's free-tier terms say unpaid-tier content may be used to improve its products. Do not send anything private.

## Pexels
- API default **200 requests/hour, 20,000/month** (verified, Pexels API docs). Typical use here: under 15 requests a day.
- Licence (verified, Pexels help centre): free to use, no attribution required; do not show **identifiable people in a bad light**; do not sell unaltered copies. **Horror is that risk**, so `footage.is_people_free` rejects clips whose URL names people, and queries are scenery/objects only. The slug filter is a heuristic, not a guarantee. Review the preview.
- Credit lines are added to every description anyway.

## Piper TTS
- `piper-tts` (OHF-Voice/piper1-gpl) is **GPL-3.0**. It runs as a tool inside the workflow; this project does not redistribute it.
- **Voice licences differ per voice.** Per third-party catalogue notes: `ryan`, `hfc_female`, `hfc_male` are CC BY-NC-SA (non-commercial); `lessac`, `amy`, `alan` have unclear or research-only terms. `tts.NONCOMMERCIAL` refuses these. The default `en_US-john-medium` is listed as public domain by a third party, **I did not read its model card. Check it** before monetising.

## GitHub
- Verified (docs): Actions is free for **public** repositories on standard runners; private repos on the Free plan get **2,000 minutes/month** and 500 MB artifact storage. A daily run here takes roughly 2-6 minutes.
- Not re-verified: Pages from a private repo needs a paid plan, which is why the repo is public. **Public means your scripts, queue and logs are readable by anyone.** Secrets stay private.
- Not re-verified: scheduled workflows in public repos are disabled after 60 days without repository activity. The daily state commits should count as activity; if the schedule ever stops, run any workflow once by hand.
- `GITHUB_TOKEN` cannot create or modify files under `.github/workflows`; that is why the bootstrap step needs a token with *Workflows* permission.
