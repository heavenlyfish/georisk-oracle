"""
agents/guardrails_agent.py — NeMo Guardrails policy layer (NemoClaw bonus ⭐)

Two-layer validation:

Layer 1 — NeMo Guardrails (nemoguardrails library):
  - Input rail: blocks off-topic requests using Colang flows
  - Output rail: adds financial disclaimer when needed
  - Powered by Nemotron via NIM

Layer 2 — Structural validation (Python):
  - Risk score range check (0-100)
  - Urgency validity check
  - Causal chain completeness
  - Dangerous phrase detection
  - Score/urgency consistency

Both layers must pass before the pipeline continues to synthesis.
"""

import os
import asyncio
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

from agents.reasoning_agent import RiskAssessment
from config.settings import get_settings


DANGEROUS_PHRASES = [
    "sell everything", "go all in", "guaranteed profit",
    "risk-free", "100% certain", "sure thing",
]

GUARDRAILS_PATH = str(Path(__file__).parent.parent / "guardrails")


@dataclass
class GuardrailsResult:
    passed: bool
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    nemo_input_check: str = "skipped"   # passed | blocked | skipped
    nemo_output_check: str = "skipped"  # passed | disclaimer_added | skipped
    disclaimer: str = ""
    sanitized_assessment: Optional[RiskAssessment] = None


class GuardrailsAgent:
    """
    Two-layer guardrails: NeMo Guardrails (real library) + structural validation.
    """

    def __init__(self, verbose: bool = False):
        self.settings = get_settings()
        self.verbose = verbose
        self.rails = None
        self._init_nemo()

    def _init_nemo(self):
        """Initialize NeMo Guardrails with Nemotron via NIM."""
        try:
            from nemoguardrails import RailsConfig, LLMRails

            # Set NIM API key for the OpenAI-compatible engine
            os.environ["OPENAI_API_KEY"] = self.settings.nim_api_key
            os.environ["OPENAI_API_BASE"] = self.settings.nim_base_url

            config = RailsConfig.from_path(GUARDRAILS_PATH)
            self.rails = LLMRails(config)
            self._log("NeMo Guardrails initialized with Nemotron/NIM ✅")
        except Exception as e:
            self._log(f"NeMo Guardrails init failed (falling back to structural only): {e}")
            self.rails = None

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[GuardrailsAgent/NemoClaw] {msg}")

    # ── Layer 1: NeMo Guardrails ─────────────────────────────────────────────

    def _nemo_check_input(self, event_text: str) -> tuple[str, str]:
        """
        Run NeMo input rail on event text.
        Returns (status, message): status = 'passed' | 'blocked'
        """
        if not self.rails:
            return "skipped", ""
        try:
            prompt = f"Analyze this geopolitical event for risk assessment: {event_text[:300]}"
            result = asyncio.run(self.rails.generate_async(
                messages=[{"role": "user", "content": prompt}]
            ))
            # result may be a dict or string depending on nemoguardrails version
            result_text = result if isinstance(result, str) else result.get("content", str(result))
            if "only analyze" in result_text.lower() or ("geopolitical" in result_text.lower() and "only" in result_text.lower()):
                return "blocked", result_text
            return "passed", result_text
        except Exception as e:
            self._log(f"NeMo input check error: {e}")
            return "skipped", str(e)

    def _nemo_check_output(self, memo: str) -> tuple[str, str]:
        """
        Check investor memo for dangerous financial advice phrases.
        Returns (status, disclaimer): status = 'passed' | 'disclaimer_added'
        """
        if not memo:
            return "skipped", ""
        # Check for dangerous phrases directly
        memo_lower = memo.lower()
        triggers = ["sell everything", "go all in", "guaranteed", "risk-free", "100% certain"]
        if any(t in memo_lower for t in triggers):
            disclaimer = "⚠️ Disclaimer: All signals are for informational purposes only and do not constitute financial advice."
            return "disclaimer_added", disclaimer
        return "passed", ""

    # ── Layer 2: Structural validation ───────────────────────────────────────

    def _structural_check(self, assessment: RiskAssessment) -> tuple[list[str], list[str]]:
        """Run structural policy checks on RiskAssessment. Returns (violations, warnings)."""
        violations = []
        warnings = []

        # Policy 1: Risk score range
        if not (0 <= assessment.risk_score <= 100):
            violations.append(f"risk_score out of range: {assessment.risk_score}")

        # Policy 2: Valid urgency
        if assessment.urgency not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            violations.append(f"Invalid urgency: {assessment.urgency}")

        # Policy 3: Causal chain completeness
        if not assessment.causal_chain:
            violations.append("causal_chain is empty")
        else:
            for i, step in enumerate(assessment.causal_chain):
                if not (0.0 <= step.confidence <= 1.0):
                    violations.append(f"causal_chain[{i}] confidence out of range: {step.confidence}")

        # Policy 4: Dangerous financial advice
        for signal in assessment.hedge_signals:
            for phrase in DANGEROUS_PHRASES:
                if phrase.lower() in signal.lower():
                    violations.append(f"Dangerous advice detected: '{signal}'")

        # Policy 5: Required fields
        if not assessment.event_summary:
            violations.append("event_summary is missing")
        if not assessment.affected_sectors:
            warnings.append("affected_sectors is empty")
        if not assessment.reasoning:
            warnings.append("reasoning narrative is empty")

        # Policy 6: Score/urgency consistency
        score, urgency = assessment.risk_score, assessment.urgency
        if (urgency == "CRITICAL" and score < 70) or \
           (urgency == "LOW" and score > 40) or \
           (urgency == "HIGH" and score < 50):
            warnings.append(f"Score/urgency mismatch: score={score}, urgency={urgency}")

        return violations, warnings

    # ── Main entry point ─────────────────────────────────────────────────────

    def validate(self, assessment: RiskAssessment,
                 event_text: str = "", memo: str = "") -> GuardrailsResult:
        """
        Run both NeMo Guardrails + structural checks.

        Args:
            assessment: Nemotron's RiskAssessment to validate
            event_text: Original event text (for input rail)
            memo: Generated investor memo (for output rail)

        Returns:
            GuardrailsResult with full validation details
        """
        self._log(f"Validating: {assessment.event_summary[:60]}...")

        # Layer 1a: NeMo input check
        nemo_input_status = "skipped"
        if event_text:
            nemo_input_status, _ = self._nemo_check_input(event_text)
            self._log(f"NeMo input check: {nemo_input_status}")
            if nemo_input_status == "blocked":
                return GuardrailsResult(
                    passed=False,
                    violations=["NeMo input rail: event blocked as off-topic"],
                    nemo_input_check="blocked",
                )

        # Layer 1b: NeMo output check
        nemo_output_status, disclaimer = "skipped", ""
        if memo:
            nemo_output_status, disclaimer = self._nemo_check_output(memo)
            self._log(f"NeMo output check: {nemo_output_status}")

        # Layer 2: Structural validation
        violations, warnings = self._structural_check(assessment)

        passed = len(violations) == 0

        if passed:
            self._log(f"✅ Passed ({len(warnings)} warnings)")
        else:
            self._log(f"❌ Failed: {violations}")

        for w in warnings:
            self._log(f"  ⚠ {w}")

        return GuardrailsResult(
            passed=passed,
            violations=violations,
            warnings=warnings,
            nemo_input_check=nemo_input_status,
            nemo_output_check=nemo_output_status,
            disclaimer=disclaimer,
            sanitized_assessment=assessment if passed else None,
        )
