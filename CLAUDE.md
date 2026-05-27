# GeoRisk Oracle — CLAUDE.md

## Project Overview
Autonomous geopolitical risk agent for NVIDIA Agent Hackathon.
Traces causal chains: geopolitical event → supply chain disruption → sector exposure → investor alert.
Powered by NVIDIA Nemotron via NIM API.

## Hackathon
- **Event**: NVIDIA Agent Hackathon
- **Deadline**: 2026-05-28 12:00 PM GMT+8
- **Track**: Autonomous Agents / Financial Intelligence

## Architecture
```
main.py                      # CLI entry: --event "..." or --scan
config/settings.py           # Pydantic settings from .env
data/watchlist.json          # Hotspots, sectors, companies to monitor
agents/
  reasoning_agent.py         # Core: Nemotron NIM causal chain reasoning
  data_agent.py              # NewsAPI fetcher + manual event injection
  alert_agent.py             # Telegram alert formatter
```

## NIM API
- **Base URL**: https://integrate.api.nvidia.com/v1
- **Model (default)**: nvidia/llama-3.1-nemotron-70b-instruct
- **Alt models**: nvidia/llama-3.3-nemotron-super-49b-v1, nvidia/nemotron-4-340b-instruct
- Uses OpenAI-compatible SDK (`openai` package)
- Model overridable via `NIM_MODEL` env var

## Local Dev
```bash
# Setup
cp .env.example .env
# Fill in NIM_API_KEY

pip install -r requirements.txt

# Single event analysis
python main.py --event "Taiwan Strait tensions escalate"

# Auto-scan via NewsAPI
python main.py --scan

# Test reasoning agent directly
python -c "
from agents.reasoning_agent import ReasoningAgent
a = ReasoningAgent()
r = a.analyze('China restricts gallium exports')
print(r.model_dump_json(indent=2))
"
```

## Environment Variables
| Key | Description |
|-----|-------------|
| `NIM_API_KEY` | NVIDIA NIM API key (required) |
| `NIM_BASE_URL` | NIM endpoint (default: integrate.api.nvidia.com/v1) |
| `NIM_MODEL` | Nemotron model ID |
| `NEWS_API_KEY` | NewsAPI.org key (optional, enables --scan) |
| `TELEGRAM_BOT_TOKEN` | Bot token for alerts |
| `TELEGRAM_CHAT_ID` | Target chat ID |
| `RISK_THRESHOLD` | Min score (0–100) to trigger alert (default: 60) |

## Known Issues & Fix History
<!-- append session summaries here -->
