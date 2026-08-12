import requests
from xml.etree import ElementTree as ET
from typing import Dict, List, Optional

# Fix 2a (2026-08-01): fed_stance must be a POLICY STANCE, never a scraped
# headline. The press-release RSS feed carries supervisory/regulatory
# releases alongside FOMC statements, so a headline can never be trusted as
# a stance (the 2026-07-20 / 2026-07-27 pollution incidents). When no
# reliable read is injected by the report writer, emit exactly:
STANCE_UNAVAILABLE = "Unknown. Stance source unavailable."

ALLOWED_STANCE_WORDS = {"hawkish", "dovish", "neutral", "hold", "easing", "tightening", "unknown"}


def _valid_stance(text: str) -> bool:
    lead = text.split(".", 1)[0].split(",", 1)[0].split(":", 1)[0].split(";", 1)[0].strip().lower()
    return lead in ALLOWED_STANCE_WORDS


def _fetch_rss_headlines(url: str, max_items: int = 3) -> List[str]:
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")
        headlines = []
        for item in items[:max_items]:
            title = item.find("title")
            if title is not None and title.text:
                headlines.append(title.text.strip())
        return headlines
    except Exception as exc:
        print(f"[fetch_context] RSS fetch failed for {url}: {exc}")
        return []


def fetch_macro_context(fed_stance_override: Optional[str] = None) -> Dict[str, str]:
    """Fetch macro headlines via web RSS. Falls back to placeholders.

    fed_stance: the Fed press-release RSS feed is NOT a stance source
    (Fix 2a). A stance is accepted only via fed_stance_override from the
    report writer (derived from the most recent FOMC statement / chair
    remarks), and only if it leads with a recognized stance word.
    Otherwise the exact STANCE_UNAVAILABLE string is emitted.
    """
    headlines = _fetch_rss_headlines(
        "https://feeds.finance.yahoo.com/rss/2.0/headlines?s=SPY", max_items=3
    )
    if not headlines:
        headlines = _fetch_rss_headlines(
            "https://news.google.com/rss/search?q=stock+market+fed+stance", max_items=3
        )

    if not headlines:
        headlines = [
            "Market consolidates amid mixed earnings signals.",
            "Investors watch inflation data for next Fed move.",
            "Sector rotation continues into defensive names."
        ]

    if fed_stance_override and _valid_stance(fed_stance_override):
        fed_stance = fed_stance_override
    else:
        if fed_stance_override:
            print(f"[fetch_context] fed_stance override failed stance-word validation: {fed_stance_override[:60]}")
        fed_stance = STANCE_UNAVAILABLE

    return {
        "fed_stance": fed_stance,
        "world_events": "; ".join(headlines) if headlines else "Stable global conditions."
    }
