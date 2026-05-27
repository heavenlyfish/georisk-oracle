"""
agents/orchestrator.py — Multi-model pipeline coordinator

Runs the full GeoRisk Oracle pipeline:

  [Input Event]
       ↓
  [Llama 3.3 70B]   ← screener_agent: fast triage, entity extraction
       ↓ (if relevant)
  [Nemotron 49B]    ← reasoning_agent: deep causal chain reasoning
       ↓
  [NeMo Guardrails] ← guardrails_agent: policy-based output validation (NemoClaw ⭐)
       ↓ (if passed)
  [Nemotron 49B]    ← synthesis_agent: investor memo generation
       ↓
  [AlertAgent]      ← Telegram push if score >= threshold
"""

from dataclasses import dataclass, field
from typing import Optional

from agents.screener_agent import ScreenerAgent, ScreenerResult
from agents.reasoning_agent import ReasoningAgent, RiskAssessment
from agents.guardrails_agent import GuardrailsAgent, GuardrailsResult
from agents.synthesis_agent import SynthesisAgent
from agents.alert_agent import AlertAgent
from config.settings import get_settings


@dataclass
class PipelineResult:
    event_text: str
    screen: ScreenerResult
    assessment: Optional[RiskAssessment] = None
    guardrails: Optional[GuardrailsResult] = None
    memo: Optional[str] = None
    alert_sent: bool = False
    skipped: bool = False
    skip_reason: str = ""


class Orchestrator:
    """
    Coordinates Llama → Nemotron → NeMo Guardrails → Nemotron pipeline.
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.settings = get_settings()
        self.screener = ScreenerAgent(verbose=verbose)
        self.reasoner = ReasoningAgent(verbose=verbose)
        self.guardrails = GuardrailsAgent(verbose=verbose)
        self.synthesizer = SynthesisAgent(verbose=verbose)
        self.alerter = AlertAgent()

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[Orchestrator] {msg}")

    def run(self, event_text: str, skip_screen: bool = False) -> PipelineResult:
        """
        Run the full multi-model pipeline on a single event.

        Args:
            event_text: Natural language event description
            skip_screen: If True, bypass Llama screener

        Returns:
            PipelineResult with all intermediate outputs
        """
        self._log("=" * 60)
        self._log(f"Pipeline start: {event_text[:80]}")

        # ── Stage 1: Llama screener ──────────────────────────────────
        self._log("Stage 1 — Llama 3.3 70B: screening...")
        screen = self.screener.screen(event_text)

        if not skip_screen and not screen.relevant:
            self._log(f"FILTERED: {screen.reason}")
            return PipelineResult(
                event_text=event_text,
                screen=screen,
                skipped=True,
                skip_reason=screen.reason,
            )

        # ── Stage 2: Nemotron reasoning ──────────────────────────────
        self._log("Stage 2 — Nemotron: causal chain reasoning...")
        assessment = self.reasoner.analyze(event_text)

        # ── Stage 2.5: NeMo Guardrails policy check ──────────────────
        self._log("Stage 2.5 — NeMo Guardrails: policy validation...")
        guardrails_result = self.guardrails.validate(assessment)

        if not guardrails_result.passed:
            self._log(f"GUARDRAILS FAILED: {guardrails_result.violations}")
            return PipelineResult(
                event_text=event_text,
                screen=screen,
                assessment=assessment,
                guardrails=guardrails_result,
                skipped=True,
                skip_reason=f"Policy violation: {'; '.join(guardrails_result.violations)}",
            )

        # ── Stage 3: Nemotron synthesis ──────────────────────────────
        self._log("Stage 3 — Nemotron: synthesizing investor memo...")
        memo = self.synthesizer.synthesize(assessment, screen_reason=screen.reason)

        # ── Stage 4: Alert ───────────────────────────────────────────
        alert_sent = False
        if self.alerter.should_alert(assessment):
            self._log(f"Stage 4 — Alert: score {assessment.risk_score} >= {self.settings.risk_threshold}")
            alert_sent = self.alerter.process(assessment)
        else:
            self._log(f"Stage 4 — No alert: score {assessment.risk_score} < {self.settings.risk_threshold}")

        self._log("Pipeline complete.")
        return PipelineResult(
            event_text=event_text,
            screen=screen,
            assessment=assessment,
            guardrails=guardrails_result,
            memo=memo,
            alert_sent=alert_sent,
        )

    def run_batch(self, events: list[str], skip_screen: bool = False) -> list[PipelineResult]:
        """Run pipeline on multiple events."""
        results = []
        for i, event in enumerate(events, 1):
            self._log(f"Batch {i}/{len(events)}")
            try:
                result = self.run(event, skip_screen=skip_screen)
                results.append(result)
            except Exception as e:
                print(f"[Orchestrator] ERROR on event {i}: {e}")
        return results
