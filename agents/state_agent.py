"""
agents/state_agent.py — Event deduplication for the watch daemon

Tracks which event hashes have already been processed so the watch
loop doesn't re-analyze the same headline every scan cycle.

State is stored in Firestore (collection: seen_events) so it persists
across process restarts and cloud redeploys — no local file needed.

Falls back to in-memory set if Firestore is unavailable (dev mode).
"""

import hashlib
import os
from datetime import datetime, timezone, timedelta
from typing import Optional


def _normalize(text: str) -> str:
    """Normalize event text for consistent hashing."""
    return " ".join(text.lower().strip().split())


def _hash(text: str) -> str:
    return hashlib.md5(_normalize(text).encode()).hexdigest()


class StateAgent:
    """
    Tracks seen events via Firestore. Prevents duplicate analysis.
    Falls back to in-memory cache if Firestore is not configured.
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._memory: set[str] = set()   # in-memory fallback
        self._use_firestore = bool(os.getenv("FIREBASE_CREDENTIALS_JSON"))

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[StateAgent] {msg}")

    def is_seen(self, event_text: str) -> bool:
        """Return True if this event has already been processed."""
        h = _hash(event_text)

        if self._use_firestore:
            try:
                from db.firestore import get_db
                db = get_db()
                doc = db.collection("seen_events").document(h).get()
                return doc.exists
            except Exception as e:
                self._log(f"Firestore check failed, using memory: {e}")

        return h in self._memory

    def mark_seen(self, event_text: str) -> None:
        """Mark an event as processed."""
        h = _hash(event_text)

        if self._use_firestore:
            try:
                from db.firestore import get_db
                db = get_db()
                db.collection("seen_events").document(h).set({
                    "event_text": event_text[:200],
                    "seen_at": datetime.now(timezone.utc),
                })
                self._log(f"Marked seen in Firestore: {h[:8]}...")
                return
            except Exception as e:
                self._log(f"Firestore write failed, using memory: {e}")

        self._memory.add(h)
        self._log(f"Marked seen in memory: {h[:8]}...")

    def prune_old(self, days: int = 7) -> int:
        """Remove events older than N days. Returns count pruned."""
        if not self._use_firestore:
            return 0
        try:
            from db.firestore import get_db
            db = get_db()
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            old = db.collection("seen_events").where("seen_at", "<", cutoff).stream()
            count = 0
            for doc in old:
                doc.reference.delete()
                count += 1
            if count:
                self._log(f"Pruned {count} old events")
            return count
        except Exception as e:
            self._log(f"Prune failed: {e}")
            return 0
