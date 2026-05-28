"""
db/firestore.py — Firebase Firestore client + CRUD helpers

Collections:
  events   — every analyzed geopolitical event
  scans    — each monitoring cycle (when, how many events)
  alerts   — Telegram notifications sent
  insights — Nemotron pattern + forward outlook synthesis

Credentials: set FIREBASE_CREDENTIALS_JSON env var with the full
service account JSON content (paste the entire JSON as one line).
"""

import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore

_db = None


def get_db():
    """Return initialized Firestore client (singleton)."""
    global _db
    if _db is not None:
        return _db

    if not firebase_admin._apps:
        cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
        if not cred_json:
            raise RuntimeError(
                "FIREBASE_CREDENTIALS_JSON env var not set. "
                "Paste your Firebase service account JSON as a single-line string."
            )
        cred_dict = json.loads(cred_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)

    _db = firestore.client()
    return _db


# ── Events ───────────────────────────────────────────────────────────────────

def save_event(assessment, source: str, event_text: str, memo: str = "") -> str:
    """Save a RiskAssessment to Firestore. Returns document ID."""
    db = get_db()
    doc = {
        "event_text": event_text,
        "event_summary": assessment.event_summary,
        "event_type": assessment.event_type,
        "source": source,
        "risk_score": assessment.risk_score,
        "urgency": assessment.urgency,
        "time_horizon": assessment.time_horizon,
        "affected_regions": assessment.affected_regions,
        "affected_sectors": assessment.affected_sectors,
        "affected_companies": assessment.affected_companies,
        "affected_commodities": assessment.affected_commodities,
        "hedge_signals": assessment.hedge_signals,
        "reasoning": assessment.reasoning,
        "memo": memo,
        "causal_chain": [s.model_dump() for s in assessment.causal_chain],
        "supply_chain_breakdown": [s.model_dump() for s in assessment.supply_chain_breakdown],
        "scanned_at": datetime.now(timezone.utc),
    }
    ref = db.collection("events").add(doc)
    return ref[1].id


def get_events(since_days: int = 1, limit: int = 50) -> list[dict]:
    """Fetch recent events ordered by time."""
    db = get_db()
    since = datetime.now(timezone.utc) - timedelta(days=since_days)
    docs = (
        db.collection("events")
        .where("scanned_at", ">=", since)
        .order_by("scanned_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [{"id": d.id, **d.to_dict()} for d in docs]


def get_event_count(since_days: int = 1) -> int:
    db = get_db()
    since = datetime.now(timezone.utc) - timedelta(days=since_days)
    docs = db.collection("events").where("scanned_at", ">=", since).stream()
    return sum(1 for _ in docs)


# ── Scans ────────────────────────────────────────────────────────────────────

def save_scan(started_at: datetime, completed_at: datetime,
              events_fetched: int, events_new: int, events_analyzed: int) -> str:
    db = get_db()
    doc = {
        "started_at": started_at,
        "completed_at": completed_at,
        "events_fetched": events_fetched,
        "events_new": events_new,
        "events_analyzed": events_analyzed,
    }
    ref = db.collection("scans").add(doc)
    return ref[1].id


def get_last_scan() -> Optional[dict]:
    db = get_db()
    docs = (
        db.collection("scans")
        .order_by("completed_at", direction=firestore.Query.DESCENDING)
        .limit(1)
        .stream()
    )
    for d in docs:
        return {"id": d.id, **d.to_dict()}
    return None


def get_scans(since_days: int = 1) -> list[dict]:
    db = get_db()
    since = datetime.now(timezone.utc) - timedelta(days=since_days)
    docs = (
        db.collection("scans")
        .where("completed_at", ">=", since)
        .order_by("completed_at", direction=firestore.Query.DESCENDING)
        .stream()
    )
    return [{"id": d.id, **d.to_dict()} for d in docs]


# ── Alerts ───────────────────────────────────────────────────────────────────

def save_alert(event_id: str, event_summary: str,
               risk_score: int, telegram_sent: bool) -> str:
    db = get_db()
    doc = {
        "event_id": event_id,
        "event_summary": event_summary,
        "risk_score": risk_score,
        "telegram_sent": telegram_sent,
        "sent_at": datetime.now(timezone.utc),
    }
    ref = db.collection("alerts").add(doc)
    return ref[1].id


def get_alerts(since_days: int = 7) -> list[dict]:
    db = get_db()
    since = datetime.now(timezone.utc) - timedelta(days=since_days)
    docs = (
        db.collection("alerts")
        .where("sent_at", ">=", since)
        .order_by("sent_at", direction=firestore.Query.DESCENDING)
        .stream()
    )
    return [{"id": d.id, **d.to_dict()} for d in docs]


# ── Insights ─────────────────────────────────────────────────────────────────

def save_insight(period: str, content: str, events_analyzed: int) -> str:
    db = get_db()
    doc = {
        "period": period,
        "content": content,
        "events_analyzed": events_analyzed,
        "generated_at": datetime.now(timezone.utc),
    }
    ref = db.collection("insights").add(doc)
    return ref[1].id


def get_latest_insight(period: str = "weekly") -> Optional[dict]:
    db = get_db()
    docs = (
        db.collection("insights")
        .where("period", "==", period)
        .order_by("generated_at", direction=firestore.Query.DESCENDING)
        .limit(1)
        .stream()
    )
    for d in docs:
        return {"id": d.id, **d.to_dict()}
    return None
