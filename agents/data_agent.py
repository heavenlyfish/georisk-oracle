"""
agents/data_agent.py — GeoRisk Oracle event ingestion

Fetches geopolitical news headlines from NewsAPI.org and
filters them against the watchlist. Falls back to manual
event injection when no API key is configured.
"""

import json
from pathlib import Path
from typing import Optional

import requests

from config.settings import get_settings

WATCHLIST_PATH = Path(__file__).parent.parent / "data" / "watchlist.json"
NEWSAPI_URL = "https://newsapi.org/v2/everything"


def load_watchlist() -> dict:
    with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class DataAgent:
    """
    Fetches geopolitical event headlines for analysis.
    """

    def __init__(self):
        self.settings = get_settings()
        self.watchlist = load_watchlist()

    def _build_query(self) -> str:
        """Build NewsAPI query from watchlist keywords."""
        keywords = self.watchlist.get("news_keywords", [])
        # NewsAPI allows OR queries with spaces; use top 5 to stay concise
        top = keywords[:8]
        return " OR ".join(f'"{kw}"' for kw in top)

    def fetch_news(self, query: Optional[str] = None, max_articles: Optional[int] = None) -> list[str]:
        """
        Fetch recent headlines from NewsAPI matching watchlist keywords.

        Args:
            query: Custom query string. Defaults to watchlist-generated query.
            max_articles: Max results to return.

        Returns:
            List of headline strings (title + description).
        """
        if not self.settings.news_api_key:
            print("[DataAgent] NEWS_API_KEY not set — returning empty list.")
            return []

        q = query or self._build_query()
        n = max_articles or self.settings.news_max_articles

        params = {
            "q": q,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": n,
            "apiKey": self.settings.news_api_key,
        }

        try:
            resp = requests.get(NEWSAPI_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            articles = data.get("articles", [])
            headlines = []
            for a in articles:
                title = a.get("title") or ""
                desc = a.get("description") or ""
                combined = f"{title}. {desc}".strip(". ")
                if combined:
                    headlines.append(combined)
            return headlines
        except requests.RequestException as e:
            print(f"[DataAgent] NewsAPI request failed: {e}")
            return []

    def get_watchlist_events(self) -> list[str]:
        """
        Build synthetic event descriptions from watchlist hotspots for testing
        when no news API is available.
        """
        hotspots = self.watchlist.get("hotspots", [])
        events = []
        for hs in hotspots:
            events.append(f"Geopolitical tensions escalate in {hs}, raising concerns for regional stability and supply chain continuity.")
        return events
