"""
agents/insight_agent.py — Nemotron pattern analysis + forward outlook

Reads recent events from Firestore and uses Nemotron to generate:
1. PATTERN ANALYSIS — what do this week's events have in common?
2. FORWARD OUTLOOK  — what might happen in the next 2 weeks?

Called by the watch loop once per day (or on-demand via API).
Results stored in Firestore (collection: insights) and shown on dashboard.
"""

import json
from openai import OpenAI
from config.settings import get_settings


INSIGHT_SYSTEM = """\
You are GeoRisk Oracle's strategic analyst powered by NVIDIA Nemotron.
You receive a batch of recent geopolitical risk events and produce two outputs:

1. PATTERN ANALYSIS
   - What themes, regions, or sectors are recurring?
   - Are risks escalating, de-escalating, or shifting?
   - Which supply chains are most stressed right now?

2. FORWARD OUTLOOK (next 2 weeks)
   - Based on these patterns, what events or escalations are likely next?
   - Which sectors/companies should investors watch most closely?
   - What early warning signals should we monitor?

Be specific, analytical, and concise. Max 400 words total.

Format exactly as:

## Pattern Analysis
[3-5 bullet points on common themes]

## Forward Outlook (Next 2 Weeks)
[3-5 bullet points on likely developments]

## Key Sectors to Watch
[comma-separated list]

## Recommended Monitoring Keywords
[comma-separated list of search terms to add to watchlist]
"""


class InsightAgent:
    """
    Generates periodic pattern analysis and forward outlook using Nemotron.
    Reads event history from Firestore, writes insight back.
    """

    def __init__(self, verbose: bool = False):
        self.settings = get_settings()
        self.verbose = verbose
        self.client = OpenAI(
            api_key=self.settings.nim_api_key,
            base_url=self.settings.nim_base_url,
        )

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[InsightAgent/Nemotron] {msg}")

    def _build_prompt(self, events: list[dict]) -> str:
        lines = []
        for i, e in enumerate(events, 1):
            lines.append(
                f"{i}. [{e.get('urgency','?')} | {e.get('risk_score','?')}/100] "
                f"{e.get('event_summary', e.get('event_text','')[:80])}\n"
                f"   Sectors: {', '.join(e.get('affected_sectors', []))}\n"
                f"   Hedge: {', '.join(e.get('hedge_signals', []))}"
            )
        events_text = "\n\n".join(lines)
        return f"Analyze these {len(events)} recent geopolitical events:\n\n{events_text}"

    def generate(self, since_days: int = 7, period: str = "weekly") -> str:
        """
        Fetch recent events from Firestore, run Nemotron analysis.
        Saves result to Firestore insights collection.
        Returns the generated insight text.
        """
        from db.firestore import get_events, save_insight

        self._log(f"Fetching events from last {since_days} days...")
        events = get_events(since_days=since_days, limit=30)

        if not events:
            self._log("No events found — skipping insight generation")
            return "No recent events to analyze."

        self._log(f"Analyzing {len(events)} events with Nemotron...")

        response = self.client.chat.completions.create(
            model=self.settings.nim_model,
            messages=[
                {"role": "system", "content": INSIGHT_SYSTEM},
                {"role": "user", "content": self._build_prompt(events)},
            ],
            max_tokens=800,
            temperature=0.4,
        )

        insight_text = response.choices[0].message.content or ""
        self._log(f"Insight generated ({len(insight_text)} chars)")

        save_insight(period=period, content=insight_text, events_analyzed=len(events))
        self._log("Saved to Firestore")

        return insight_text
