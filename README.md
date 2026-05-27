# GeoRisk Oracle

**Autonomous geopolitical risk agent powered by NVIDIA NIM.**  
Traces causal chains from geopolitical events → supply chain disruptions → investor alerts.

Built for the NVIDIA Agent Hackathon.

---

## How It Works

```
Geopolitical Event (text input or news headline)
        │
        ▼
┌─────────────────────────────┐
│  Stage 1 — Llama 3.3 70B   │  Fast triage: is this a real geo-risk event?
│  (NVIDIA NIM)               │  Extracts key entities, estimates severity
└────────────┬────────────────┘
             │ relevant ✅
             ▼
┌─────────────────────────────┐
│  Stage 2 — Nemotron         │  Deep causal chain reasoning:
│  (NVIDIA NIM)               │  Event → Supply Chain → Sectors → Investors
│                             │  Outputs: risk score (0–100), urgency, hedge signals
└────────────┬────────────────┘
             ▼
┌─────────────────────────────┐
│  Stage 3 — Nemotron         │  Synthesizes structured data into a
│  (NVIDIA NIM)               │  polished investor memo with macro context
└────────────┬────────────────┘
             ▼
     Telegram Alert (if score ≥ threshold)
```

All three stages run on **NVIDIA NIM** — no external AI dependencies.

---

## Demo

```bash
# Full 3-model pipeline
python main.py --pipeline "China restricts gallium and germanium exports targeting semiconductor supply chains"

# Built-in demo event
python main.py --demo --full

# Nemotron reasoning only
python main.py --event "Red Sea Houthi attacks disrupt 15% of global shipping"

# Auto-scan watchlist via NewsAPI
python main.py --scan --full
```

### Sample Output

```
Stage 1 — Llama 3.3 70B: Triage
✅ Relevant: True  |  Confidence: 90%  |  Severity: CRITICAL
Entities: China, US, gallium, germanium, antimony, semiconductors

Stage 2 — Nemotron: Causal Chain Reasoning
🟠 Urgency: HIGH  |  Risk Score: 82/100  |  Horizon: weeks

  Causal Chain:
  1. Export Restrictions Imposed → Immediate disruption to global semiconductor supply chain (90%)
  2. Supply Chain Disruption     → Increased production costs and delays (80%)
  3. Industry Impact             → Lagging effects on tech, automotive, aerospace (70%)

  Sectors:    Technology, Automotive, Aerospace
  Companies:  TSM, INTC, NVDA, TM, BA
  Hedge:      Short TSM | Accumulate Rare Earth ETFs | Hedge tech with QID

Stage 3 — Nemotron: Investor Memo
  Conviction: High | Score: 82/100
  Top Actions:
  1. Short TSM — direct supply chain exposure
  2. Accumulate REEM (Rare Earth ETF) — hedge critical material tensions
  3. Buy QID puts — protect against tech sector volatility
```

---

## Setup

```bash
git clone https://github.com/heavenlyfish/georisk-oracle
cd georisk-oracle
pip install -r requirements.txt
cp .env.example .env
# Add your NIM_API_KEY to .env
```

Get your NVIDIA NIM API key: https://build.nvidia.com

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `NIM_API_KEY` | ✅ | NVIDIA NIM API key |
| `NIM_BASE_URL` | — | Default: `https://integrate.api.nvidia.com/v1` |
| `NIM_MODEL` | — | Nemotron model (default: `nvidia/llama-3.3-nemotron-super-49b-v1`) |
| `LLAMA_MODEL` | — | Screener model (default: `meta/llama-3.3-70b-instruct`) |
| `RISK_THRESHOLD` | — | Alert threshold 0–100 (default: `60`) |
| `NEWS_API_KEY` | — | NewsAPI key for `--scan` mode |
| `TELEGRAM_BOT_TOKEN` | — | Telegram bot for alerts |
| `TELEGRAM_CHAT_ID` | — | Telegram chat target |

---

## Project Structure

```
georisk-oracle/
├── main.py                    # CLI entry point
├── agents/
│   ├── screener_agent.py      # Stage 1: Llama 3.3 70B fast triage
│   ├── reasoning_agent.py     # Stage 2: Nemotron causal chain reasoning
│   ├── synthesis_agent.py     # Stage 3: Nemotron investor memo
│   ├── orchestrator.py        # Multi-model pipeline coordinator
│   ├── data_agent.py          # NewsAPI fetcher
│   └── alert_agent.py         # Telegram alert formatter
├── config/
│   └── settings.py            # Pydantic settings
└── data/
    └── watchlist.json         # Monitored hotspots, sectors, companies
```

---

## Watchlist

**Hotspots**: Taiwan Strait · Ukraine · Red Sea · South China Sea · Persian Gulf · Strait of Hormuz  
**Sectors**: Semiconductors · Energy · Agriculture · Rare Earth · Shipping · Defense  
**Companies**: TSMC · ASML · NVIDIA · Intel · Samsung · Maersk · MP Materials  
**Commodities**: Oil · LNG · Wheat · Lithium · Gallium · Germanium · NAND Flash

---

## Models Used

| Model | Provider | Role |
|---|---|---|
| `meta/llama-3.3-70b-instruct` | NVIDIA NIM | Fast event triage |
| `nvidia/llama-3.3-nemotron-super-49b-v1` | NVIDIA NIM | Causal reasoning + synthesis |

---

## License

MIT
