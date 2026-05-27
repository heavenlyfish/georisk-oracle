"""
agents/screener_agent.py — Fast triage via Llama 3.3 70B (NIM)

First stage of the multi-model pipeline.
Quickly determines if an event is geo-risk relevant and extracts
key entities — before handing off to the heavier Nemotron reasoning.

Fast, cheap, binary: RELEVANT / IRRELEVANT + brief entity extraction.
"""

import json
import re
from pydantic import BaseModel, Field
from openai import OpenAI

from config.settings import get_settings


SCREENER_SYSTEM = """\
You are a fast geopolitical risk screener. Your job is to quickly determine
whether an event is relevant to geopolitical risk and global supply chains.

Respond ONLY with valid JSON — no prose, no markdown:

{
  "relevant": true or false,
  "confidence": 0.0 to 1.0,
  "reason": "one sentence why",
  "key_entities": ["list", "of", "countries", "companies", "commodities"],
  "estimated_severity": "LOW | MEDIUM | HIGH | CRITICAL"
}

Mark relevant=true if the event involves ANY of:
- Military conflict, sanctions, trade restrictions
- Supply chain disruption (commodities, shipping, semiconductors)
- Political instability affecting trade
- Energy, food, or technology security
"""

SCREENER_USER = "Screen this event: {event_text}"


class ScreenerResult(BaseModel):
    relevant: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    key_entities: list[str]
    estimated_severity: str


class ScreenerAgent:
    """
    Fast triage using Llama 3.3 70B via NIM.
    Runs before Nemotron to filter irrelevant events cheaply.
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
            print(f"[ScreenerAgent/Llama] {msg}")

    def _extract_json(self, text: str) -> dict:
        text = re.sub(r"```(?:json)?\s*", "", text).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ValueError(f"Could not parse JSON: {text[:300]}")

    def screen(self, event_text: str) -> ScreenerResult:
        """
        Screen an event. Returns ScreenerResult with relevant=True/False.
        Fast — Llama 3.3 70B, max 256 tokens.
        """
        self._log(f"Screening: {event_text[:80]}...")
        self._log(f"Model: {self.settings.llama_model}")

        response = self.client.chat.completions.create(
            model=self.settings.llama_model,
            messages=[
                {"role": "system", "content": SCREENER_SYSTEM},
                {"role": "user", "content": SCREENER_USER.format(event_text=event_text)},
            ],
            max_tokens=256,
            temperature=0.1,
        )

        raw = response.choices[0].message.content or ""
        self._log(f"Result: {raw[:200]}")

        parsed = self._extract_json(raw)
        result = ScreenerResult(**parsed)
        self._log(f"Relevant: {result.relevant} | Severity: {result.estimated_severity} | Conf: {result.confidence:.0%}")
        return result
