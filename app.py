"""
app.py — GeoRisk Oracle main entry point

Starts two concurrent processes in one Python process:
  1. FastAPI web dashboard (port $PORT, default 8000)
  2. Background watch loop (scans news every WATCH_INTERVAL minutes)

Usage:
  python app.py                  # starts both web + watch loop
  python app.py --web-only       # dashboard only, no scanning
  python app.py --watch-only     # scanning only, no web server

Railway deployment: Procfile sets `web: python app.py`
"""

import argparse
import os
import sys
import time
import threading

# Set OPENAI_API_KEY from NIM_API_KEY at startup
# Required by nemoguardrails which looks for OPENAI_API_KEY internally
_nim_key = os.getenv("NIM_API_KEY", "")
if _nim_key and not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = _nim_key
if not os.getenv("OPENAI_API_BASE"):
    os.environ["OPENAI_API_BASE"] = os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
import logging
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("georisk")

WATCH_INTERVAL = int(os.getenv("WATCH_INTERVAL", "30"))  # minutes


# ── Watch Loop ────────────────────────────────────────────────────────────────

def run_one_cycle(verbose: bool = False) -> dict:
    """
    Run a single monitoring cycle:
      1. Fetch news headlines
      2. Filter already-seen events
      3. Run full pipeline on new events
      4. Save results to Firestore
      5. Return cycle stats
    """
    from agents.data_agent import DataAgent
    from agents.state_agent import StateAgent
    from agents.orchestrator import Orchestrator
    from db.firestore import save_event, save_scan, save_alert
    from config.settings import get_settings
    from api.server import monitor_state

    settings = get_settings()
    started_at = datetime.now(timezone.utc)

    log.info("=== Scan cycle starting ===")

    data_agent  = DataAgent()
    state_agent = StateAgent(verbose=verbose)
    orchestrator = Orchestrator(verbose=verbose)

    # Fetch events
    if settings.news_api_key:
        headlines = data_agent.fetch_news()
        source = "newsapi"
    else:
        headlines = data_agent.get_watchlist_events()[:5]
        source = "watchlist"

    log.info(f"Fetched {len(headlines)} headlines from {source}")

    # Filter seen
    new_events = [h for h in headlines if not state_agent.is_seen(h)]
    log.info(f"{len(new_events)} new (unseen) events to analyze")

    analyzed = 0
    alerts_sent = 0

    for event_text in new_events:
        try:
            result = orchestrator.run(event_text)
            state_agent.mark_seen(event_text)

            if result.skipped:
                log.info(f"Skipped: {result.skip_reason[:60]}")
                continue

            # Save to Firestore
            event_id = save_event(
                assessment=result.assessment,
                source=source,
                event_text=event_text,
                memo=result.memo or "",
            )
            analyzed += 1
            log.info(f"Saved event {event_id[:8]} | score={result.assessment.risk_score} | {result.assessment.urgency}")

            if result.alert_sent:
                save_alert(
                    event_id=event_id,
                    event_summary=result.assessment.event_summary,
                    risk_score=result.assessment.risk_score,
                    telegram_sent=True,
                )
                alerts_sent += 1

        except Exception as e:
            log.error(f"Pipeline error: {e}")

    # Prune old seen events weekly
    state_agent.prune_old(days=7)

    completed_at = datetime.now(timezone.utc)

    try:
        save_scan(
            started_at=started_at,
            completed_at=completed_at,
            events_fetched=len(headlines),
            events_new=len(new_events),
            events_analyzed=analyzed,
        )
    except Exception as e:
        log.warning(f"Could not save scan record: {e}")

    # Update shared state for dashboard
    next_scan = completed_at + timedelta(minutes=WATCH_INTERVAL)
    monitor_state.update({
        "running": True,
        "last_scan_at": completed_at.isoformat(),
        "next_scan_at": next_scan.isoformat(),
        "total_events_today": monitor_state.get("total_events_today", 0) + analyzed,
        "total_alerts_today": monitor_state.get("total_alerts_today", 0) + alerts_sent,
    })

    log.info(f"Cycle done: {analyzed} analyzed, {alerts_sent} alerts | next in {WATCH_INTERVAL}m")
    return {"analyzed": analyzed, "alerts_sent": alerts_sent}


def watch_loop(verbose: bool = False):
    """Infinite watch loop — runs run_one_cycle() every WATCH_INTERVAL minutes."""
    from api.server import monitor_state
    monitor_state["running"] = True
    monitor_state["started_at"] = datetime.now(timezone.utc).isoformat()
    monitor_state["interval_minutes"] = WATCH_INTERVAL

    log.info(f"Watch loop started — scanning every {WATCH_INTERVAL} minutes")

    # Generate initial insight if Firestore is available
    def _initial_insight():
        time.sleep(60)  # wait for first scan to complete
        try:
            from agents.insight_agent import InsightAgent
            InsightAgent(verbose=verbose).generate(since_days=7, period="weekly")
        except Exception as e:
            log.warning(f"Initial insight failed: {e}")

    threading.Thread(target=_initial_insight, daemon=True).start()

    # Daily insight regeneration
    last_insight_day = None

    while True:
        try:
            run_one_cycle(verbose=verbose)

            # Regenerate insight once per day
            today = datetime.now(timezone.utc).date()
            if last_insight_day != today:
                try:
                    from agents.insight_agent import InsightAgent
                    InsightAgent(verbose=verbose).generate(since_days=7, period="weekly")
                    last_insight_day = today
                    log.info("Daily insight regenerated")
                except Exception as e:
                    log.warning(f"Insight generation failed: {e}")

        except Exception as e:
            log.error(f"Cycle error: {e}")

        log.info(f"Sleeping {WATCH_INTERVAL} minutes until next scan...")
        time.sleep(WATCH_INTERVAL * 60)


# ── Web Server ────────────────────────────────────────────────────────────────

def start_web(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    from api.server import app
    log.info(f"Dashboard starting on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="GeoRisk Oracle — Web + Watch")
    parser.add_argument("--web-only", action="store_true", help="Run dashboard only")
    parser.add_argument("--watch-only", action="store_true", help="Run watch loop only")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    port = int(os.getenv("PORT", "8000"))

    log.info("=" * 50)
    log.info("GeoRisk Oracle starting")
    log.info(f"Watch interval: {WATCH_INTERVAL} minutes")
    log.info("=" * 50)

    if args.watch_only:
        watch_loop(verbose=args.verbose)
        return

    if args.web_only:
        start_web(port=port)
        return

    # Default: run both
    t = threading.Thread(target=watch_loop, args=(args.verbose,), daemon=True, name="WatchLoop")
    t.start()

    start_web(port=port)  # blocks main thread


if __name__ == "__main__":
    main()
