"""
agents/reasoning_agent.py — GeoRisk Oracle Core

Uses NVIDIA Nemotron via NIM (OpenAI-compatible endpoint) to perform
multi-step causal chain reasoning:
  Geopolitical event
    → Geographic scope & choke points
    → Supply chain disruptions
    → Sector / company exposure
    → Investor implications & hedge signals
    → Risk score + urgency level

Usage:
    from agents.reasoning_agent import ReasoningAgent
    agent = ReasoningAgent()
    result = agent.analyze("China restricts gallium exports")
    print(result.model_dump_json(indent=2))
"""

import json
import re
import sys
from typing import Optional

from openai import OpenAI
from pydantic import BaseModel, Field, field_validator

from config.settings import get_settings


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

class CausalStep(BaseModel):
    """One link in the causal chain."""
    step: str = Field(description="Short label for this reasoning step")
    entities: list[str] = Field(description="Countries, companies, commodities involved")
    impact: str = Field(description="Specific impact at this step")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this link (0–1)")


class RiskAssessment(BaseModel):
    """Full structured output from the reasoning agent."""
    event_summary: str = Field(description="One-sentence event summary")
    event_type: str = Field(description="conflict | sanction | natural_disaster | political_crisis | trade_dispute | other")
    causal_chain: list[CausalStep] = Field(description="Step-by-step causal reasoning chain")
    affected_regions: list[str] = Field(description="Countries / regions directly affected")
    affected_sectors: list[str] = Field(description="Industry sectors at risk")
    affected_companies: list[str] = Field(description="Specific companies or tickers at risk")
    affected_commodities: list[str] = Field(description="Commodities / raw materials disrupted")
    risk_score: int = Field(ge=0, le=100, description="Overall risk score 0–100")
    urgency: str = Field(description="LOW | MEDIUM | HIGH | CRITICAL")
    hedge_signals: list[str] = Field(description="Actionable early-warning / hedge flags for investors")
    time_horizon: str = Field(description="Expected impact horizon: immediate | weeks | months | quarters")
    reasoning: str = Field(description="Free-form analyst reasoning narrative")

    @field_validator("urgency")
    @classmethod
    def validate_urgency(cls, v: str) -> str:
        allowed = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"urgency must be one of {allowed}, got {v!r}")
        return v

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        allowed = {"conflict", "sanction", "natural_disaster", "political_crisis", "trade_dispute", "other"}
        v = v.lower()
        if v not in allowed:
            v = "other"
        return v


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are GeoRisk Oracle, an autonomous geopolitical risk analyst powered by NVIDIA Nemotron.
Your mission: trace causal chains from geopolitical events to supply chain disruptions and investor impact.

You MUST reason step-by-step through ALL of the following:

1. EVENT CLASSIFICATION
   - Type: conflict / sanction / natural_disaster / political_crisis / trade_dispute / other
   - Severity: who are the actors, what actions were taken

2. GEOGRAPHIC SCOPE
   - Affected countries and regions
   - Critical choke points (straits, ports, borders, air corridors)

3. SUPPLY CHAIN TRACE
   - Which commodities, raw materials, or components are disrupted
   - Which trade routes / logistics chains are affected
   - Lead-time and inventory buffer estimates

4. SECTOR EXPOSURE
   - Industries with immediate impact (< 2 weeks)
   - Industries with lagged impact (weeks to quarters)
   - Named companies or tickers most exposed

5. INVESTOR IMPLICATIONS
   - Equities: sectors / stocks to watch (long/short signals)
   - Fixed income: sovereign spread implications
   - FX: currency pairs at risk
   - Commodities: directional price pressure

6. RISK SCORE (0–100)
   - 0–29: Routine monitoring
   - 30–59: Elevated watch
   - 60–79: Active risk
   - 80–100: Crisis / immediate action

7. URGENCY: LOW | MEDIUM | HIGH | CRITICAL

8. HEDGE SIGNALS
   - Concrete actionable flags (e.g., "accumulate gold", "reduce TSM exposure", "hedge oil via XLE calls")

9. TIME HORIZON
   - immediate (< 1 week) | weeks (1–4 weeks) | months (1–3 months) | quarters (3–12 months)

Return ONLY a single valid JSON object matching this exact schema — no markdown, no prose before or after:

{
  "event_summary": "string",
  "event_type": "conflict|sanction|natural_disaster|political_crisis|trade_dispute|other",
  "causal_chain": [
    {
      "step": "string",
      "entities": ["string"],
      "impact": "string",
      "confidence": 0.0
    }
  ],
  "affected_regions": ["string"],
  "affected_sectors": ["string"],
  "affected_companies": ["string"],
  "affected_commodities": ["string"],
  "risk_score": 0,
  "urgency": "LOW|MEDIUM|HIGH|CRITICAL",
  "hedge_signals": ["string"],
  "time_horizon": "immediate|weeks|months|quarters",
  "reasoning": "string"
}
"""

USER_PROMPT_TEMPLATE = """\
Analyze this geopolitical event and produce a full risk assessment:

EVENT: {event_text}

Remember: return ONLY valid JSON, no other text.
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class ReasoningAgent:
    """
    Calls NVIDIA Nemotron via NIM to perform causal chain risk reasoning.
    """

    def __init__(self, verbose: bool = False):
        self.settings = get_settings()
        self.verbose = verbose

        if not self.settings.nim_api_key:
            print("[WARNING] NIM_API_KEY not set — API calls will fail.", file=sys.stderr)

        self.client = OpenAI(
            api_key=self.settings.nim_api_key,
            base_url=self.settings.nim_base_url,
        )

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[ReasoningAgent] {msg}", file=sys.stderr)

    def list_models(self) -> list[str]:
        """Return available model IDs from the NIM endpoint."""
        try:
            models = self.client.models.list()
            return [m.id for m in models.data]
        except Exception as e:
            self._log(f"Could not list models: {e}")
            return []

    def _extract_json(self, text: str) -> dict:
        """
        Robustly extract the first JSON object from a response string.
        Handles cases where the model wraps JSON in markdown fences.
        """
        # Strip markdown fences if present
        text = re.sub(r"```(?:json)?\s*", "", text).strip()

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Find the first {...} block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not extract valid JSON from response:\n{text[:500]}")

    def analyze(self, event_text: str) -> RiskAssessment:
        """
        Main entry point. Takes a plain-text event description,
        calls Nemotron, returns a validated RiskAssessment.

        Args:
            event_text: Natural language description of the geopolitical event

        Returns:
            RiskAssessment: Fully validated Pydantic model
        """
        self._log(f"Analyzing: {event_text[:80]}...")
        self._log(f"Model: {self.settings.nim_model}")

        user_prompt = USER_PROMPT_TEMPLATE.format(event_text=event_text)

        response = self.client.chat.completions.create(
            model=self.settings.nim_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=self.settings.max_tokens,
            temperature=self.settings.temperature,
        )

        raw_content = response.choices[0].message.content or ""
        self._log(f"Raw response length: {len(raw_content)} chars")

        parsed = self._extract_json(raw_content)
        assessment = RiskAssessment(**parsed)

        self._log(f"Risk score: {assessment.risk_score} | Urgency: {assessment.urgency}")
        return assessment

    def analyze_batch(self, events: list[str]) -> list[RiskAssessment]:
        """Analyze multiple events sequentially. Returns list in same order."""
        results = []
        for i, event in enumerate(events, 1):
            self._log(f"Processing event {i}/{len(events)}")
            try:
                result = self.analyze(event)
                results.append(result)
            except Exception as e:
                print(f"[ERROR] Event {i} failed: {e}", file=sys.stderr)
        return results
