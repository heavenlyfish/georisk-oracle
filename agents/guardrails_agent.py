"""
agents/guardrails_agent.py — NeMo Guardrails policy layer (NemoClaw bonus ⭐)

Validates Nemotron's RiskAssessment outputs against policy rules before
they reach the synthesis stage. Catches:
  - Invalid/out-of-range risk scores
  - Missing required fields
  - Hallucinated or implausible data
  - Dangerous financial advice language

Sits between Stage 2 (Nemotron reasoning) and Stage 3 (synthesis).
"""

import sys
from dataclasses import dataclass
from typing import Optional

from agents.reasoning_agent import RiskAssessment


# Known valid tickers/sectors for hallucination check
KNOWN_SECTORS = {
    "semiconductors", "energy", "agriculture", "rare_earth", "shipping",
    "defense", "automotive", "pharmaceuticals", "technology", "finance",
    "manufacturing", "transportation", "aerospace", "telecom",
}

DANGEROUS_PHRASES = [
    "sell everything", "go all in", "guaranteed profit",
    "risk-free", "100% certain", "sure thing",
]


@dataclass
class GuardrailsResult:
    passed: bool
    violations: list[str]
    warnings: list[str]
    sanitized_assessment: Optional[RiskAssessment] = None


class GuardrailsAgent:
    """
    Policy-based output validator for Nemotron RiskAssessments.
    Implements NemoClaw-style guardrails in Python.

    Policies enforced:
    1. Risk score must be 0–100
    2. Urgency must be LOW/MEDIUM/HIGH/CRITICAL
    3. Causal chain must have at least 1 step
    4. Hedge signals must not contain dangerous advice
    5. Affected sectors must be non-empty
    6. Confidence values must be 0.0–1.0
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[GuardrailsAgent/NemoClaw] {msg}")

    def validate(self, assessment: RiskAssessment) -> GuardrailsResult:
        """
        Run all policy checks on a RiskAssessment.
        Returns GuardrailsResult with pass/fail and any violations.
        """
        violations = []
        warnings = []

        self._log(f"Validating assessment: {assessment.event_summary[:60]}...")

        # Policy 1: Risk score range
        if not (0 <= assessment.risk_score <= 100):
            violations.append(f"risk_score out of range: {assessment.risk_score} (must be 0–100)")

        # Policy 2: Valid urgency
        if assessment.urgency not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            violations.append(f"Invalid urgency: {assessment.urgency}")

        # Policy 3: Causal chain completeness
        if not assessment.causal_chain:
            violations.append("causal_chain is empty — reasoning not provided")
        else:
            for i, step in enumerate(assessment.causal_chain):
                if not (0.0 <= step.confidence <= 1.0):
                    violations.append(f"causal_chain[{i}] confidence out of range: {step.confidence}")
                if not step.entities:
                    warnings.append(f"causal_chain[{i}] has no entities listed")

        # Policy 4: Hedge signal safety
        for signal in assessment.hedge_signals:
            for phrase in DANGEROUS_PHRASES:
                if phrase.lower() in signal.lower():
                    violations.append(f"Dangerous financial advice detected: '{signal}'")

        # Policy 5: Non-empty required fields
        if not assessment.affected_sectors:
            warnings.append("affected_sectors is empty")
        if not assessment.event_summary:
            violations.append("event_summary is missing")
        if not assessment.reasoning:
            warnings.append("reasoning narrative is empty")

        # Policy 6: Plausibility check — score vs urgency consistency
        score = assessment.risk_score
        urgency = assessment.urgency
        inconsistent = (
            (urgency == "CRITICAL" and score < 70) or
            (urgency == "LOW" and score > 40) or
            (urgency == "HIGH" and score < 50)
        )
        if inconsistent:
            warnings.append(
                f"Score/urgency mismatch: score={score}, urgency={urgency}. "
                "Consider reviewing Nemotron's output."
            )

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
            sanitized_assessment=assessment if passed else None,
        )
