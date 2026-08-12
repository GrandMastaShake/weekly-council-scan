"""
Wiki signals — lets the engines read the Living Wiki Grid.

The Saturday Research Crew maintains one wiki per sector in
GrandMastaShake/weekly-council-scan (wiki/*.md). This module distills each
wiki into two machine-usable signals:

1. Sector sentiment: positive/negative keyword balance per sector wiki,
   mapped onto the engine SECTOR_MAP sectors and clamped to a ±5 score
   adjustment.
2. Ticker mentions: how many wikis name a given ticker (cap +2 bonus).

Signals are small on purpose: the wikis nudge the engines toward what the
research crew actually wrote; they do not override price/value data.
If no wiki can be loaded, every adjustment is 0 -- but WikiSignals.fetch_ok
is then False, so engines can tell a fetch outage apart from genuine
zero-mentions and flag the run as data-degraded instead of silently
scoring zeros (Fix C-e). Backward compatible: additive attribute only.
"""

import os
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

from scan_pipeline.config.tickers import AVAILABLE_TICKERS
from scan_pipeline.utils.data_utils import get_sector

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/GrandMastaShake/weekly-council-scan/main/wiki"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
FETCH_TIMEOUT = 10

# Wiki page -> SECTOR_MAP sector it informs. Note: communication-services
# tickers live under "Technology" and materials tickers under "Energy" in
# the engine SECTOR_MAP, so those wikis feed those buckets.
WIKI_SECTOR_MAP: Dict[str, str] = {
    "tech": "Technology",
    "communication-services": "Technology",
    "energy": "Energy",
    "materials": "Energy",
    "healthcare": "Healthcare",
    "financials": "Financials",
    "consumer-discretionary": "Consumer",
    "consumer-staples": "Consumer",
    "industrials": "Industrials",
    "utilities": "Utilities",
    "real-estate": "Real Estate",
}

POSITIVE_KEYWORDS = [
    "bullish", "outperform", "upgrade", "upgraded", "breakout", "beat",
    "growth", "inflow", "inflows", "accumulate", "strength", "rally",
    "raised guidance", "above the 50", "momentum building", "support held",
]
NEGATIVE_KEYWORDS = [
    "bearish", "underperform", "downgrade", "downgraded", "breakdown",
    "miss", "missed", "headwind", "headwinds", "outflow", "outflows",
    "risk-off", "selloff", "sell-off", "below the 50", "cut guidance",
    "overbought", "weakness", "caution",
]

MAX_SECTOR_ADJUSTMENT = 5.0
MAX_MENTION_BONUS = 2.0

_PIPELINE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class WikiSignals:
    def __init__(self, sector_sentiment: Dict[str, float], mentions: Dict[str, int], loaded_files: List[str], watchlist: Optional[set] = None, fetch_ok: bool = True):
        self.sector_sentiment = sector_sentiment      # sector -> avg (pos - neg)
        self.mentions = mentions                      # ticker -> wiki mention count
        self.loaded_files = loaded_files              # wiki pages successfully read
        self.watchlist = watchlist or set()           # tickers in synthesis.md Monday Watchlist
        # Fix C-e: False when EVERY page fetch failed -- distinguishable
        # from a successful load that genuinely found zero mentions.
        self.fetch_ok = fetch_ok

    @property
    def loaded(self) -> bool:
        return len(self.loaded_files) > 0

    def sector_adjustment(self, sector: str) -> float:
        sentiment = self.sector_sentiment.get(sector)
        if sentiment is None:
            return 0.0
        adj = sentiment * 0.5
        return max(-MAX_SECTOR_ADJUSTMENT, min(MAX_SECTOR_ADJUSTMENT, adj))

    def mention_bonus(self, ticker: str) -> float:
        return min(MAX_MENTION_BONUS, float(self.mentions.get(ticker, 0)))


_CACHE: Optional[WikiSignals] = None


def get_signals(refresh: bool = False) -> WikiSignals:
    """Load (and cache for the process) the distilled wiki signals."""
    global _CACHE
    if _CACHE is None or refresh:
        _CACHE = _load()
    return _CACHE


def adjusted_score(ticker: str, base_score: float, signals: Optional[WikiSignals] = None) -> float:
    """Apply the wiki nudge to an engine's raw score for *ticker*."""
    s = signals or get_signals()
    return base_score + s.sector_adjustment(get_sector(ticker)) + s.mention_bonus(ticker)


# ---------------------------------------------------------------------------
# Loading internals
# ---------------------------------------------------------------------------

def _local_candidates(name: str) -> List[str]:
    return [
        os.path.join(_PIPELINE_ROOT, "wiki", f"{name}.md"),
        os.path.join(_PIPELINE_ROOT, "StockApp", "wiki", f"{name}.md"),
    ]


def _fetch_one(name: str) -> Optional[str]:
    """Fetch one wiki page: GitHub raw first, local copies as fallback."""
    url = f"{GITHUB_RAW_BASE}/{name}.md"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        pass
    for path in _local_candidates(name):
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception:
            continue
    return None


def _count_keywords(text: str, keywords: List[str]) -> int:
    lower = text.lower()
    return sum(lower.count(kw) for kw in keywords)


def _extract_watchlist(text: Optional[str]) -> set:
    """Tickers named in the synthesis.md Monday Watchlist section.

    Tie-break rule (a) — a ticker the Council's own synthesis explicitly
    watches beats an equally-scored name with no repo support.
    """
    if not text:
        return set()
    m = re.search(
        r"^#{1,4}\s*[^\n]*watchlist[^\n]*\n(.*?)(?=^#{1,4}\s|\Z)",
        text,
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    section = m.group(1) if m else ""
    found = set()
    for ticker in AVAILABLE_TICKERS:
        if len(ticker) < 3:
            continue
        if re.search(r"\b" + re.escape(ticker) + r"\b", section):
            found.add(ticker)
    return found


def _load() -> WikiSignals:
    names = list(WIKI_SECTOR_MAP.keys()) + ["synthesis"]
    texts: Dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = dict(zip(names, pool.map(_fetch_one, names)))
    for name, text in results.items():
        if text:
            texts[name] = text

    watchlist = _extract_watchlist(texts.get("synthesis"))
    sector_texts = {k: v for k, v in texts.items() if k != "synthesis"}

    # Sector sentiment = mean keyword balance across the sector's wiki pages
    buckets: Dict[str, List[int]] = {}
    for name, text in sector_texts.items():
        sector = WIKI_SECTOR_MAP[name]
        balance = _count_keywords(text, POSITIVE_KEYWORDS) - _count_keywords(text, NEGATIVE_KEYWORDS)
        buckets.setdefault(sector, []).append(balance)
    sector_sentiment = {sector: sum(vals) / len(vals) for sector, vals in buckets.items()}

    # Ticker mentions (case-sensitive; skip <3-char tickers to avoid prose
    # false positives like the letter "C" or "D" in grade tables)
    mentions: Dict[str, int] = {}
    combined = list(sector_texts.values())
    for ticker in AVAILABLE_TICKERS:
        if len(ticker) < 3:
            continue
        pattern = re.compile(r"\b" + re.escape(ticker) + r"\b")
        count = sum(1 for text in combined if pattern.search(text))
        if count:
            mentions[ticker] = count

    # Fix C-e: fetch_ok=False when no page could be loaded at all (network
    # outage + no local copies). Engines treat that as data-degraded rather
    # than reading the all-zero signals as genuine neutrality.
    return WikiSignals(
        sector_sentiment, mentions, sorted(texts.keys()), watchlist,
        fetch_ok=len(texts) > 0,
    )
