"""
agents/synthesis_agent.py — Investor memo synthesis via Nemotron (NIM)

Final stage of the multi-model pipeline.
Takes Nemotron's RiskAssessment and synthesizes it into a polished,
investor-grade memo with macro context and actionable items.

Uses the same NIM endpoint as the reasoning agent — no extra API needed.
"""

import re
from openai import OpenAI
from agents.reasoning_agent import RiskAssessment
from config.settings import get_settings


SYNTHESIS_SYSTEM = """\
You are a senior geopolitical risk analyst at a global macro hedge fund.
You receive structured risk assessments from an AI reasoning engine and
synthesize them into concise, actionable investor memos.

Your memo must:
1. VALIDATE the causal logic — does it hold? Note any gaps.
2. ADD macro context — how does this fit current market environment?
3. PRIORITIZE the top 3 most actionable investor implications
4. Give a CONVICTION LEVEL: Low / Medium / High
5. Suggest SPECIFIC instruments (ETFs, options, FX pairs) where relevant
6. Keep it under 300 words — sharp, not verbose

Use this exact format:

## GeoRisk Intel Memo
**Event**: [one line]
**Conviction**: [Low/Medium/High] | **Urgency**: [urgency] | **Score**: [score]/100

### Key Risk
[2-3 sentences on the core risk]

### Top 3 Investor Actions
1. [action + instrument]
2. [action + instrument]
3. [action + instrument]

### Macro Context
[1-2 sentences connecting to current market backdrop]

### Analyst Note
[Any caveats, data gaps, or confidence qualifiers]
"""


class SynthesisAgent:
    """
    Synthesizes a RiskAssessment into an investor memo using Nemotron via NIM.
    All-NVIDIA pipeline — no external API dependencies.
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
            print(f"[SynthesisAgent/Nemotron] {msg}")

    def _build_user_prompt(self, assessment: RiskAssessment, screen_reason: str = "") -> str:
        chain_text = "\n".join(
            f"  {i+1}. {s.step}: {s.impact} "
            f"(entities: {', '.join(s.entities)}, conf: {s.confidence:.0%})"
            for i, s in enumerate(assessment.causal_chain)
        )
        return f"""\
Risk Assessment to synthesize into an investor memo:

Event: {assessment.event_summary}
Type: {assessment.event_type}
Risk Score: {assessment.risk_score}/100
Urgency: {assessment.urgency}
Time Horizon: {assessment.time_horizon}

Causal Chain:
{chain_text}

Affected Regions: {', '.join(assessment.affected_regions)}
Affected Sectors: {', '.join(assessment.affected_sectors)}
Affected Companies: {', '.join(assessment.affected_companies)}
Affected Commodities: {', '.join(assessment.affected_commodities)}

Hedge Signals: {', '.join(assessment.hedge_signals)}
Reasoning: {assessment.reasoning}
{f"Screener Note: {screen_reason}" if screen_reason else ""}

Write the investor memo now.
"""

    def synthesize(self, assessment: RiskAssessment, screen_reason: str = "") -> str:
        """
        Generate an investor memo from a RiskAssessment.

        Returns:
            Formatted markdown memo string
        """
        self._log(f"Synthesizing: {assessment.event_summary[:60]}...")
        self._log(f"Model: {self.settings.nim_model}")

        response = self.client.chat.completions.create(
            model=self.settings.nim_model,
            messages=[
                {"role": "system", "content": SYNTHESIS_SYSTEM},
                {"role": "user", "content": self._build_user_prompt(assessment, screen_reason)},
            ],
            max_tokens=1024,
            temperature=0.3,
        )

        memo = response.choices[0].message.content or ""
        self._log(f"Memo generated ({len(memo)} chars)")
        return memo
