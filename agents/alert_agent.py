"""
agents/alert_agent.py — GeoRisk Oracle alert formatter

Formats RiskAssessment into Telegram messages and sends them.
Only fires when risk_score >= settings.risk_threshold.
"""

import requests
from datetime import datetime

from agents.reasoning_agent import RiskAssessment
from config.settings import get_settings


URGENCY_EMOJI = {
    "LOW": "🟢",
    "MEDIUM": "🟡",
    "HIGH": "🟠",
    "CRITICAL": "🔴",
}


def format_alert(assessment: RiskAssessment) -> str:
    """Format a RiskAssessment into a Telegram-ready message."""
    urgency_icon = URGENCY_EMOJI.get(assessment.urgency, "⚪")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Causal chain summary (max 4 steps for readability)
    chain_lines = []
    for step in assessment.causal_chain[:4]:
        entities = ", ".join(step.entities[:3])
        chain_lines.append(f"  → {step.step}: {step.impact} [{entities}]")
    chain_text = "\n".join(chain_lines) if chain_lines else "  (no chain)"

    # Hedge signals
    hedge_text = "\n".join(f"  • {h}" for h in assessment.hedge_signals[:5]) or "  (none)"

    # Affected
    sectors = ", ".join(assessment.affected_sectors[:4]) or "—"
    companies = ", ".join(assessment.affected_companies[:5]) or "—"

    msg = (
        f"🌐 GeoRisk Oracle Alert\n"
        f"{urgency_icon} {assessment.urgency}  |  Score: {assessment.risk_score}/100\n"
        f"🕐 {ts}\n"
        f"\n"
        f"📌 {assessment.event_summary}\n"
        f"\n"
        f"⛓ Causal Chain:\n{chain_text}\n"
        f"\n"
        f"🏭 Sectors at risk: {sectors}\n"
        f"🏢 Companies: {companies}\n"
        f"⏱ Horizon: {assessment.time_horizon}\n"
        f"\n"
        f"📊 Hedge Signals:\n{hedge_text}\n"
        f"\n"
        f"─────────────\n"
        f"📦 georisk-oracle"
    )
    return msg


class AlertAgent:
    """
    Sends risk alerts via Telegram when risk_score crosses the threshold.
    """

    def __init__(self):
        self.settings = get_settings()

    def should_alert(self, assessment: RiskAssessment) -> bool:
        return assessment.risk_score >= self.settings.risk_threshold

    def send_telegram(self, text: str) -> bool:
        """Send a message via Telegram Bot API. Returns True on success."""
        token = self.settings.telegram_bot_token
        chat_id = self.settings.telegram_chat_id

        if not token or not chat_id:
            print("[AlertAgent] Telegram not configured — skipping send.")
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"[AlertAgent] Telegram send failed: {e}")
            return False

    def process(self, assessment: RiskAssessment) -> bool:
        """
        Format and send alert if score meets threshold.
        Returns True if alert was sent.
        """
        msg = format_alert(assessment)

        if self.should_alert(assessment):
            print(f"[AlertAgent] Score {assessment.risk_score} >= threshold {self.settings.risk_threshold} — sending alert.")
            return self.send_telegram(msg)
        else:
            print(f"[AlertAgent] Score {assessment.risk_score} < threshold {self.settings.risk_threshold} — no alert.")
            return False
