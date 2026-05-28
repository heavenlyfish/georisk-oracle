# GeoRisk Oracle — CLAUDE.md

## Project Overview
Autonomous geopolitical risk agent for NVIDIA Build-a-Claw Hackathon.
Traces causal chains: geopolitical event → supply chain disruption → sector exposure → investor alert.
Powered by NVIDIA Nemotron via NIM API.

## Hackathon
- **Event**: NVIDIA Build-a-Claw Agent Challenge
- **Submitted**: 2026-05-28 ~11:45 AM GMT+8 ✅
- **Team**: 小魚兒 — 杜孟憲 (Marvin), 蕭清懿, 黃暐庭
- **Result**: Announced 2026-05-29

## Current Architecture (as submitted)
```
News/Event Input
    ↓
agents/screener_agent.py     # Llama 3.3 70B — fast triage
    ↓
agents/reasoning_agent.py    # Nemotron 49B — causal chain reasoning
    ↓
agents/guardrails_agent.py   # NeMo Guardrails (nemoguardrails 0.22.0) — policy check
    ↓
agents/synthesis_agent.py    # Nemotron 49B — investor memo
    ↓
agents/alert_agent.py        # Telegram push if score >= threshold

Orchestration:
agents/orchestrator.py       # Pipeline coordinator
agents/state_agent.py        # Deduplication via Firestore
agents/insight_agent.py      # Daily Nemotron pattern analysis + 2-week outlook
agents/data_agent.py         # NewsAPI fetcher + watchlist fallback

Web:
app.py                       # FastAPI + watch daemon (single process)
api/server.py                # REST API endpoints
templates/dashboard.html     # Bootstrap dark theme dashboard

Database:
db/firestore.py              # Firebase Firestore (cloud, 24/7)
```

## NIM Models Used
| Model | Role |
|---|---|
| `nvidia/llama-3.3-nemotron-super-49b-v1` | Causal reasoning + memo synthesis |
| `meta/llama-3.3-70b-instruct` | Fast event screener |

## Local Dev
```bash
cd /Users/marvint/Sites/GitHub/georisk-oracle
pip install -r requirements.txt

# Single pipeline run
python main.py --pipeline "Taiwan Strait tensions escalate" --verbose

# Full demo
python main.py --demo --full --verbose

# Start web dashboard + watch daemon
python app.py

# Watch daemon only
python app.py --watch-only --verbose
```

## Cloud Deployment
- **Platform**: Railway (https://railway.app)
- **Project**: magnificent-reverence
- **Live URL**: https://web-production-96213.up.railway.app
- **Procfile**: `web: python app.py`
- **Env vars**: set via Railway CLI (`railway variables`)

## Environment Variables
| Key | Description |
|---|---|
| `NIM_API_KEY` | NVIDIA NIM API key (required) |
| `NIM_BASE_URL` | `https://integrate.api.nvidia.com/v1` |
| `NIM_MODEL` | `nvidia/llama-3.3-nemotron-super-49b-v1` |
| `LLAMA_MODEL` | `meta/llama-3.3-70b-instruct` |
| `OPENAI_API_KEY` | Same as NIM_API_KEY (required by nemoguardrails) |
| `OPENAI_API_BASE` | Same as NIM_BASE_URL |
| `FIREBASE_CREDENTIALS_JSON` | Full Firebase service account JSON (single line) |
| `TELEGRAM_BOT_TOKEN` | Bot token for alerts |
| `TELEGRAM_CHAT_ID` | Target chat ID |
| `RISK_THRESHOLD` | Min score 0–100 to trigger alert (default: 60) |
| `WATCH_INTERVAL` | Minutes between scan cycles (default: 30) |
| `NEWS_API_KEY` | NewsAPI.org key (optional — enables live news) |

## ⚠️ What's NOT Done Yet (Weekend TODO)

### Priority 1 — OpenClaw Integration (the real Build-a-Claw goal)
The hackathon's core concept is:
```
NemoClaw (security sandbox)
    └── OpenClaw (autonomous agent + Nemotron)
            ├── tool: scan_news()
            ├── tool: analyze_event()
            ├── tool: send_alert()
            └── tool: update_dashboard()
```
Currently our pipeline is a hardcoded watch loop. The proper version has OpenClaw autonomously deciding when to scan, what to analyze, and what action to take — with NemoClaw sandboxing it.

**How to do it:**
1. Get Oracle Cloud VM running (kept failing with capacity error in Tokyo AD-1)
2. OR use GitHub Codespaces (free, browser-based, fastest option)
3. Install NemoClaw: `curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash`
4. Register GeoRisk pipeline as OpenClaw tools
5. Let OpenClaw orchestrate instead of our hardcoded loop

### Priority 2 — Oracle Cloud VM (still pending)
- Account created, VCN + subnet configured (georisk-vcn / georisk-subnet / Tokyo)
- Instance creation saved as stack: `georisk-openclaw-stack`
- Kept failing: "Out of capacity for VM.Standard.A1.Flex in AD-1"
- **Fix**: Go to Oracle Cloud → Resource Manager → Stacks → georisk-openclaw-stack → Apply (keep retrying until capacity available)
- Shape: VM.Standard.A1.Flex, 4 OCPU, 24GB RAM, Oracle Linux 9

### Priority 3 — OpenClaw + Multi-Source Intelligence (see ROADMAP.md locally)
- Full product vision documented in local ROADMAP.md (gitignored, not on GitHub)
- Core idea: importance = cross-source confirmation × supply chain hierarchy level
- Reference cases: Ukraine/Russia → energy → fertilizer; Iran/US → Qatar → urea/氮肥

### Priority 4 — NewsAPI Key ✅ DONE
- Free key obtained from newsapi.org
- Added to `.env` and Railway via CLI
- Live news scanning now active

### Priority 5 — Dashboard showing real data
- Railway env vars now confirmed set via CLI (all 10 vars)
- Dashboard live at https://web-production-96213.up.railway.app
- First real scan cycle should run within 30 min of deploy

## Known Issues & Fix History

### 2026-05-27/28 — NVIDIA Build-a-Claw Hackathon Session

**Issue 1: Wrong NIM model (404 error)**
- Symptom: `nvidia/llama-3.1-nemotron-70b-instruct` returned 404
- Root cause: Model exists in catalog but not accessible on this account tier
- Fix: Switched to `nvidia/llama-3.3-nemotron-super-49b-v1` ✅

**Issue 2: NeMo Guardrails not actually using the library**
- Symptom: `guardrails_agent.py` was a pure Python validator, not using `nemoguardrails`
- Fix: Rewrote to use `RailsConfig` + `LLMRails` from `nemoguardrails 0.22.0`
- Config at `guardrails/config.yml`, Colang flows at `guardrails/colang/main.co`

**Issue 3: NeMo Guardrails output rail crashing pipeline**
- Symptom: `generate_user_intent` internal error when checking output rail
- Fix: Simplified output check to direct phrase detection, kept input rail via NeMo

**Issue 4: Starlette 1.x TemplateResponse API change**
- Symptom: `TypeError: unhashable type: 'dict'` on dashboard load
- Fix: Changed to `templates.TemplateResponse(request=request, name="dashboard.html")`

**Issue 5: Railway env vars not set (all MISSING)**
- Symptom: All env vars showed MISSING in Railway logs despite UI edits
- Root cause: Railway UI variable saves were not persisting (unknown UI bug)
- Fix: Used Railway CLI (`railway variables set ...`) to set all vars programmatically ✅

**Issue 6: SSH keys accidentally committed**
- Symptom: `ssh-key-2026-05-27.key` files committed to git
- Fix: `git rm --cached`, added `*.key` to `.gitignore`, force pushed ✅

**Issue 7: Firebase credentials corrupted in .env**
- Symptom: Private key had literal newlines after `tr -d '\n'` + sed substitution
- Fix: Used Python `json.load()` + `json.dumps(separators=(',',':'))` for clean single-line output ✅

**Issue 8: Oracle Cloud capacity exhausted (unresolved)**
- Symptom: "Out of capacity for VM.Standard.A1.Flex in AD-1" on every attempt
- Tokyo region only has AD-1 — no alternatives
- Status: Stack saved as `georisk-openclaw-stack`, retry on weekend

**Issue 9: Railway env vars silently not saving via UI**
- Symptom: All vars showed MISSING even after repeated UI saves
- Root cause: Railway UI had a silent save bug
- Fix: Installed Railway CLI → `railway link` → `railway variables set ...` for all 10 vars ✅

## Post-Submission Features Added (2026-05-28)

**Feature 1: Supply chain breakdown by category**
- `SupplyChainImpact` Pydantic model added to `reasoning_agent.py`
- Nemotron now outputs per-category breakdown: Rare Earth, Advanced Node Semi,
  Mature Node Semi, Memory, Energy, Agricultural, Shipping, Defense, Automotive, Pharma
- Dashboard shows colored severity pills per event (hover for detail)
- Firestore saves `supply_chain_breakdown` field per event

**Feature 2: Risk score legend on dashboard**
- Bottom of dashboard explains: 0–29 routine / 30–59 elevated / 60–79 active / 80–100 crisis
- Includes Nemotron disclaimer

**Feature 3: Pre-commit security hook**
- `scripts/pre-commit-hook.sh` — scans staged files for API keys, private keys, tokens
- `scripts/install-hooks.sh` — one-command install for teammates
- Blocks: nvapi- keys, sk-ant- keys, private key blocks, Firebase credentials, Telegram tokens
- Install after cloning: `bash scripts/install-hooks.sh`

**Feature 4: SSH key moved to ~/.ssh/**
- `ssh-key-2026-05-27.key` → `~/.ssh/georisk-oracle.key` (chmod 600)
- Use: `ssh -i ~/.ssh/georisk-oracle.key opc@<oracle-instance-ip>`

**Feature 5: Personal notes gitignored**
- `ROADMAP.md`, `NOTES.md`, `TODO.md` added to `.gitignore`
- Stay local, never pushed to GitHub
