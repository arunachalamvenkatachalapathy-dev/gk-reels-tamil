# GK Snippets Tamil

Separate repository scaffold for the Tamil GK short-video pipeline.

- YouTube channel: [GK Snippets Tamil](https://www.youtube.com/@GK_Snippets_Tamil)
- Verified YouTube channel ID: `UC5ZLfNHUI4z92IW69KVTGxg`
- Repository: private

## Publishing is paused

GitHub Actions must remain **disabled** in this repository's Settings until Arun verifies YouTube, Instagram and Facebook access and explicitly approves resuming. The included workflow is a manual no-op only. No scheduled triggers, content uploads, comments, or platform credentials are active. The pipeline fails closed unless explicitly enabled and refuses to proceed while the Tamil source-checked question bank is empty.

## Tamil content dependency

`data/questions_ta.json` and `data/reviewed_ta.json` are deliberately empty. The Hindi/English reference repositories are not Tamil sources. Do not relabel or machine-translate their material. Content can be added after Arun shares source PDFs or an editor supplies a Tamil bank with the same source-check and review gates used by the other GK repos. Each published item must have validated answer/explanation/source data before rendering is implemented.

## Required repository Actions secrets (not configured)

YouTube, after owner OAuth consent on the Tamil channel:

- `YT_CLIENT_ID`
- `YT_CLIENT_SECRET`
- `YT_REFRESH_TOKEN`
- `YT_CHANNEL_ID` = `UC5ZLfNHUI4z92IW69KVTGxg`

For later Meta verification:

- `IG_ACCESS_TOKEN`
- `IG_USER_ID`
- `FB_PAGE_ID`

Store values only under **Settings → Secrets and variables → Actions**. Never commit them, paste them into chat, or print them in logs. `scripts/upload_youtube.py` verifies the OAuth token's actual channel ID matches the configured Tamil ID before any video upload. It does not post comments.

## Local checks

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

This scaffold has no video renderer or ready Tamil question bank. Do not enable Actions or publish until the content, YouTube token, IG and FB integrations are all verified and Arun has received the status summary.
