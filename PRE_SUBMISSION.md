# Pre-Submission Checklist
**Do all of these BEFORE submitting to the Airtable form.**

## 🔑 Regenerate All API Keys
These keys were used during development and must be rotated before going public:

- [ ] **NIM_API_KEY** — https://build.nvidia.com → regenerate
- [ ] **TELEGRAM_BOT_TOKEN** — contact @BotFather → /token
- [ ] **Firebase service account key** — Firebase Console → Project Settings → Service Accounts → delete old key → generate new
- [ ] **ANTHROPIC_API_KEY** — https://console.anthropic.com (if re-enabled)
- [ ] Update all new keys in `.env` AND in Railway env vars dashboard

## 📋 Final Code Checks
- [ ] Run `python main.py --demo --full` — confirm clean output end-to-end
- [ ] Run `python app.py --watch-only --verbose` — confirm Firestore writes events
- [ ] Open dashboard locally (`python app.py`) at http://localhost:8000 — confirm UI loads
- [ ] Confirm `.env` is NOT committed: `git status` should not show `.env`
- [ ] Confirm Firebase JSON is NOT committed: `git status` should not show `*.json`

## 🚀 Railway Deployment
- [ ] Deploy latest `main` branch to Railway
- [ ] Set all env vars in Railway dashboard (NIM_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, FIREBASE_CREDENTIALS_JSON, WATCH_INTERVAL)
- [ ] Confirm dashboard URL is live (e.g. https://georisk-oracle.railway.app)
- [ ] Confirm Telegram alert fires from Railway (not local machine)
- [ ] Confirm events appear in Firestore after first Railway scan cycle

## 🎬 Demo Video
- [ ] Record ~3.5 min video (see SUBMISSION.md for script)
- [ ] Upload to YouTube (unlisted) or Google Drive
- [ ] Copy video URL

## 📝 Airtable Submission Form
- [ ] Fill form at: https://airtable.com/appuGjP9jaVJtwxJt/pagqXe6ElIlXx6oa3/form
- [ ] GitHub repo URL: https://github.com/heavenlyfish/georisk-oracle
- [ ] Dashboard live URL: (Railway URL)
- [ ] Demo video URL: (YouTube/Drive link)
- [ ] Deadline: **2026-05-28 12:00 PM GMT+8**
