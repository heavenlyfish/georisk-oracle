# GeoRisk Oracle — Hackathon Submission Checklist
**Event**: NVIDIA Build-a-Claw Agent Challenge  
**Deadline**: 2026-05-28 12:00 PM GMT+8  
**Submit at**: https://airtable.com/appuGjP9jaVJtwxJt/pagqXe6ElIlXx6oa3/form

---

## What Judges Need to See

### 1. GitHub Repository ✅
**URL**: https://github.com/heavenlyfish/georisk-oracle

Must contain:
- [x] Working code that runs end-to-end
- [x] README with architecture, setup, demo instructions
- [x] `requirements.txt` — reproducible install
- [x] `.env.example` — no secrets committed
- [ ] `SUBMISSION.md` — this file (commit after completing checklist)

---

### 2. Demo Video (~3.5 min)
**Status**: ⏳ To record

Record in this order:

| Segment | Duration | What to Show |
|---|---|---|
| Intro | 20–30s | Face cam — your name, the problem you solve |
| Elevator pitch | 30–40s | Architecture diagram + 2-sentence product pitch |
| **Live demo** | 45–60s | Terminal fullscreen: `python main.py --pipeline "..."` with `--verbose` |
| Tech breakdown | 60–90s | Architecture diagram — 3 NIM models, guardrails layer, Telegram alert |
| "So what?" | 20–30s | Face cam — real-world value, who uses this |

**Demo command to run on camera**:
```bash
python main.py --pipeline "China restricts gallium and germanium exports targeting semiconductor supply chains" --verbose
```

What judges will see:
- Stage 1 — Llama 3.3 70B screens event (< 1 sec)
- Stage 2 — Nemotron traces causal chain, scores risk 82/100 HIGH
- Stage 2.5 — NeMo Guardrails validates output (policy check ✅)
- Stage 3 — Nemotron synthesizes investor memo
- Telegram alert fires live on screen

**Upload to**: YouTube (unlisted) or Google Drive

---

### 3. Submission Form Fields
Fill these out at the Airtable link above:

| Field | Your Answer |
|---|---|
| Project name | GeoRisk Oracle |
| Team name | (your team name) |
| Team members | (names) |
| GitHub repo URL | https://github.com/heavenlyfish/georisk-oracle |
| Demo video URL | (YouTube/Drive link — record this) |
| Problem statement | Investors lack real-time tools to translate geopolitical events into supply chain impact and actionable hedge signals. |
| Solution summary | Autonomous 3-model NIM pipeline: Llama screens → Nemotron reasons → Nemotron synthesizes → Telegram alert fires. Secured with NeMo Guardrails policy layer. |
| Models used | nvidia/llama-3.3-nemotron-super-49b-v1, meta/llama-3.3-70b-instruct |
| Framework | Custom orchestrator + NeMo Guardrails (NemoClaw bonus) |
| Bonus (NemoClaw) | Yes — policy-based guardrails on all Nemotron outputs |

---

### 4. Architecture Diagram
**Status**: ⏳ To create (for video + README)

```
┌─────────────────────────────────────────────────────────────┐
│                     GeoRisk Oracle                          │
│              Autonomous Geopolitical Risk Agent             │
└─────────────────────┬───────────────────────────────────────┘
                      │ Event (text / news headline)
                      ▼
          ┌───────────────────────┐
          │  Llama 3.3 70B / NIM  │  Fast triage — relevant? severity?
          └──────────┬────────────┘
                     │ relevant ✅
                     ▼
          ┌───────────────────────┐
          │  Nemotron 49B / NIM   │  Causal chain: Event → Supply Chain
          │  Reasoning Agent      │  → Sectors → Risk Score → Hedge Signals
          └──────────┬────────────┘
                     │
                     ▼
          ┌───────────────────────┐
          │  NeMo Guardrails      │  Policy check: hallucination filter,
          │  (NemoClaw bonus ⭐)  │  score validation, topic guardrail
          └──────────┬────────────┘
                     │ validated ✅
                     ▼
          ┌───────────────────────┐
          │  Nemotron 49B / NIM   │  Investor memo: conviction, top 3
          │  Synthesis Agent      │  actions, macro context
          └──────────┬────────────┘
                     │
                     ▼
          ┌───────────────────────┐
          │  Telegram Alert       │  Live push if score ≥ threshold
          └───────────────────────┘
```

---

## Pre-Submission Checklist

- [ ] Run `python main.py --demo --full` — confirm clean output
- [ ] Record demo video (3.5 min)
- [ ] Upload video to YouTube/Drive, copy link
- [ ] Fill in Airtable submission form
- [ ] Commit this file + final code changes
- [ ] Push to GitHub

---

## Key Talking Points for Video

1. **All-NVIDIA stack** — Llama + Nemotron + NeMo Guardrails, zero external AI APIs
2. **Structured reasoning** — Pydantic schema forces Nemotron to output verifiable JSON, not prose
3. **Guardrails layer** — NeMo policy rules prevent hallucinated tickers and dangerous advice
4. **Real output** — Telegram alert fires during the demo, live on camera
5. **Extensible** — swap watchlist, threshold, and models via `.env` — no code changes
