import logging
from typing import Optional

import requests

from . import config

logger = logging.getLogger(__name__)


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """Query SearXNG and return a list of {title, url, content} dicts."""
    try:
        resp = requests.get(
            f"{config.SEARXNG_URL}/search",
            params={"q": query, "format": "json", "categories": "general"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"Web search failed: {e}")
        return []

    results = []
    for item in (data.get("results") or [])[:max_results]:
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "content": item.get("content", ""),
        })
    return results


def format_web_context(results: list[dict]) -> Optional[str]:
    """Format web search results into a context string for the LLM."""
    if not results:
        return None
    parts = []
    for r in results:
        parts.append(f"[Web: {r['title']} | {r['url']}]\n{r['content']}")
    return "\n\n---\n\n".join(parts)
