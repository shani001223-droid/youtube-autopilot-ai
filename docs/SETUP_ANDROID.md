# Setup: Android only, no terminal, no cost

Everything below happens in Chrome (and the GitHub / YouTube apps) on your phone. **Type keys and tokens only into the GitHub or Google
pages named here. Never paste them into chat, the dashboard's text fields other than the one marked, or any file.**
Nothing in this guide has been run against live GitHub or Google (see STATUS.md); expect small differences in menu names.

## 1. Accounts (all free)
- GitHub account. Google account. 
- **Gemini key:** aistudio.google.com/apikey -> Create API key. Keep that page open or copy it straight into step 4.
- **Pexels key:** pexels.com/api -> request a key.

## 2. Create the repository
1. GitHub -> New repository. Name e.g. `youtube-autopilot-ai`. **Public** (needed for free Actions minutes and free Pages). Tick "Add a README".
2. Settings -> Actions -> General -> allow actions; under "Workflow permissions" choose **Read and write permissions**.

## 3. Install the project (the bootstrap)
Android cannot upload folders, so a tiny workflow unpacks the ZIP for you.
1. Create a **fine-grained token**: github.com/settings/personal-access-tokens/new -> Repository access: *Only select repositories* -> your repo.
   Permissions: **Actions: Read and write, Contents: Read and write, Workflows: Read and write.** Generate, copy it.
2. Repo -> Settings -> Secrets and variables -> Actions -> New repository secret: name `BOOTSTRAP_TOKEN`, paste the token.
3. Repo -> Add file -> **Create new file**. Name: `.github/workflows/unpack.yml`. Paste the contents of `bootstrap/unpack.yml` (shown below). Commit.
4. Repo -> Add file -> **Upload files** -> pick `youtube-autopilot-ai.zip` from your phone. Commit. (Only one .zip may be in the repo root.)
5. Actions tab -> **Unpack project** -> Run workflow. When green, the repo contains the whole project.
6. If it fails with "refusing to allow ... to create or update workflow", the token is missing the *Workflows* permission.
7. Afterwards: delete the `BOOTSTRAP_TOKEN` secret, and edit the token to remove *Workflows* if you reuse it for the dashboard (step 6).

```yaml
name: Unpack project
on: workflow_dispatch
permissions:
  contents: write
jobs:
  unpack:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.BOOTSTRAP_TOKEN }}
      - name: Unpack the ZIP you uploaded
        run: |
          set -e
          Z=$(ls *.zip | head -n 1)
          mkdir _unz && unzip -q "$Z" -d _unz
          cp -a _unz/*/. .
          rm -rf _unz "$Z"
          git config user.name "autopilot-bot"
          git config user.email "autopilot-bot@users.noreply.github.com"
          git add -A
          git commit -m "Install YouTube Autopilot AI"
          git push
```

## 4. Add secrets
Settings -> Secrets and variables -> Actions -> New repository secret:
`GEMINI_API_KEY` and `PEXELS_API_KEY`. (YouTube secrets come in step 8 and are optional at first.)

## 5. Turn on the dashboard
Settings -> Pages -> Source: **GitHub Actions**. Then Actions -> **Deploy dashboard** -> Run workflow.
Open `https://YOUR-USERNAME.github.io/youtube-autopilot-ai/` in Chrome -> menu -> *Add to Home screen*.

## 6. Connect the dashboard
Create a second fine-grained token (same page as above) for this repo only: **Actions: Read and write, Contents: Read and write**.
Paste it into the dashboard's connect screen. It is stored in this browser only. "Disconnect" in the Make tab erases it.

## 7. Test with no keys, then with keys
1. Make tab -> **Run demo (no keys)**. Wait 3-6 minutes, tap Refresh. A tone-voice test video with plain visuals appears in Queue.
   This proves the plumbing (FFmpeg, captions, thumbnail, release, dashboard), not the quality.
2. Make tab -> **Make a video now**. This uses Gemini + Piper + Pexels and is the first real test. The first run downloads the voice.
3. Watch it in Queue. **Approve** (manual mode) -> Download MP4, copy the text, upload in the YouTube app, tap **I posted it** and paste the link.
   In the YouTube app set the "Altered content" disclosure to Yes (AI voice).

## 8. Optional: connect YouTube (analytics now, API upload later)
1. console.cloud.google.com -> new project (free). APIs & Services -> enable **YouTube Data API v3** and **YouTube Analytics API**.
2. OAuth consent screen -> External -> add yourself as a test user -> then **Publish app (In production)**. Do this BEFORE step 4, or the token dies in 7 days.
3. Credentials -> Create credentials -> OAuth client ID -> **Web application** -> Authorized redirect URI `https://developers.google.com/oauthplayground`.
   Copy the client ID and secret straight into GitHub secrets `YT_CLIENT_ID` and `YT_CLIENT_SECRET`.
4. Open developers.google.com/oauthplayground -> gear icon -> tick *Use your own OAuth credentials* -> enter them there.
   Scopes: `https://www.googleapis.com/auth/youtube`, `https://www.googleapis.com/auth/youtube.upload`, `https://www.googleapis.com/auth/yt-analytics.readonly`.
   Authorize (click through "Google hasn't verified this app" -> Advanced) -> Exchange authorization code for tokens.
5. Copy the **refresh token** into GitHub secret `YT_REFRESH_TOKEN`. Do not paste it anywhere else.
6. Actions -> **Analytics and learning** -> Run workflow.

## 9. Going public (only after you are happy)
1. Post a few videos by hand. When one is a good sample: Queue -> **This sample is good**.
2. Public scheduling also needs `publish.mode = api`, which only works after YouTube approves your API project's audit (see POLICIES.md). Until then keep `manual`.
3. Make tab -> Public publishing -> **Turn on**. The pipeline enforces this itself; the dashboard is not the guard.

## If something breaks
Logs tab shows the stage that failed. Actions tab -> the red run -> the failing step. "token refresh failed" = redo step 8 (7-day rule).
"daily quota used up" = Gemini free-tier limit; wait a day or add a second model name under Niche -> settings.
