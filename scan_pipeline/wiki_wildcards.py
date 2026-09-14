"""The wiki wildcard lane: let the sector wikis put a name on the board.

The problem this solves
-----------------------
Every Saturday the sector wikis publish a SMALL/MID-CAP WATCH table: three to
five sub-$5B names per sector, each with a live-verified market cap, a price, a
sourced catalyst and a Council read. The Captains asked for that coverage
precisely because the briefs tracked mega-caps only.

None of it could ever reach a pick. The engines iterate a fixed universe, and
``wiki_signals.adjusted_score`` is called *inside* that loop -- so a wiki
mention can nudge the score of a name already being scored, but can never
introduce one. Measured 2026-09-13, **0 of 21** SMID names across the semis,
tech, financials and healthcare wikis were in STOCK_UNIVERSE. Reading the
committed panel (``panel_source``) fixes the curated watchlist but not this:
the panel carried only SOUN of those 21, because the SMID set is chosen weekly
by the wikis and the feed universe is static.

So the section was doing real work -- verifying caps, sourcing catalysts -- and
feeding nothing.

What this does
--------------
Parses the SMALL/MID-CAP WATCH tables and returns the names as scan candidates.
The wikis already did the verification work; this reads their own published
numbers rather than re-deriving them. Column ORDER varies between wikis
(healthcare carries a 52W Range column semis does not), so the header row is
parsed for the Ticker and Market Cap positions instead of assuming indices.

Admission rules, all of which must hold:
  * the ticker is 1-5 uppercase letters (a real symbol, not prose)
  * a market cap parses out of its own row
  * that cap is under MAX_CAP_USD_B -- the wikis' own sub-$5B rule, re-checked
    here so a graduated name (ACMR crossed $5.01B on 2026-09-12) drops out
    without anyone editing a list
  * the name is not already in the base universe (no duplicates)
  * at most MAX_WILDCARDS survive, smallest-cap first, so a malformed or
    hostile wiki cannot blow up the fetch

Nothing here invents a number. A row whose cap will not parse is skipped, not
guessed.

Enabling
--------
Off by default. Set ``COUNCIL_WIKI_WILDCARDS=1`` to turn it on.
"""
from __future__ import annotations

import os
import re
from typing import Dict, List, Optional

MAX_CAP_USD_B = 5.0
MAX_WILDCARDS = 60
# Admission is capped PER SOURCE WIKI, not globally. A single global
# smallest-cap-first ranking quietly hands every slot to whichever sector
# happens to publish the tiniest names -- at 25 global slots the energy and
# tech micro-caps crowded out every semiconductor name, including AOSL at
# $0.78B. Per-wiki caps keep the lane sector-balanced.
MAX_PER_WIKI = 6

# wiki_signals.WIKI_SECTOR_MAP covers the 11 GICS sector pages and does NOT
# include semiconductors -- so that page has never been loaded by wiki_signals
# at all, and its sector sentiment and ticker mentions have never reached a
# score. That is a separate pre-existing defect; it is named here rather than
# silently repaired, because changing what the main engines read is a bigger
# change than adding a page to this lane.
EXTRA_PAGES = ("semiconductors",)

_HEADING = re.compile(r"^#{1,4}\s*SMALL\s*/?\s*MID[\s-]*CAP\s+WATCH\s*$",
                      re.IGNORECASE | re.MULTILINE)
_TICKER = re.compile(r"^[A-Z]{1,5}$")
# "~$0.78B", "**$3.90B**", "$60M", "$1,234M"
_CAP = re.compile(r"\$\s*([\d,]+(?:\.\d+)?)\s*([BbMm])")

_CACHE: Optional[Dict[str, dict]] = None


def enabled() -> bool:
    return os.environ.get("COUNCIL_WIKI_WILDCARDS", "").strip().lower() in ("1", "true", "yes", "on")


def _cell(row: str) -> List[str]:
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    return [re.sub(r"[*`]", "", c).strip() for c in cells]


def _parse_cap_usd_b(text: str) -> Optional[float]:
    m = _CAP.search(text or "")
    if not m:
        return None
    value = float(m.group(1).replace(",", ""))
    return value / 1000.0 if m.group(2).upper() == "M" else value


def _section(text: str) -> str:
    m = _HEADING.search(text or "")
    if not m:
        return ""
    rest = text[m.end():]
    nxt = re.search(r"^#{1,4}\s", rest, re.MULTILINE)
    return rest[: nxt.start()] if nxt else rest


def parse_wiki(text: str, source: str = "") -> Dict[str, dict]:
    """Wildcards published by one wiki page."""
    out: Dict[str, dict] = {}
    section = _section(text)
    if not section:
        return out

    rows = [ln for ln in section.split("\n") if ln.strip().startswith("|")]
    if len(rows) < 2:
        return out

    header = [h.lower() for h in _cell(rows[0])]
    try:
        i_ticker = next(i for i, h in enumerate(header) if "ticker" in h)
    except StopIteration:
        return out
    i_cap = next((i for i, h in enumerate(header) if "market cap" in h or h == "cap"), None)
    if i_cap is None:
        return out

    for row in rows[1:]:
        cells = _cell(row)
        if len(cells) <= max(i_ticker, i_cap):
            continue
        ticker = cells[i_ticker]
        if not _TICKER.match(ticker):
            continue                      # separator rows and prose fall out here
        cap = _parse_cap_usd_b(cells[i_cap])
        if cap is None or cap >= MAX_CAP_USD_B:
            continue                      # unparseable, or graduated out
        out[ticker] = {"market_cap_usd_b": cap, "source": source}
    return out


def collect(texts: Dict[str, str]) -> Dict[str, dict]:
    """Merge wildcards across wiki pages; the smallest reported cap wins."""
    merged: Dict[str, dict] = {}
    for name, text in (texts or {}).items():
        for ticker, rec in parse_wiki(text, source=name).items():
            prev = merged.get(ticker)
            if prev is None or rec["market_cap_usd_b"] < prev["market_cap_usd_b"]:
                merged[ticker] = rec
    return merged


def wildcards(base_universe=(), refresh: bool = False) -> Dict[str, dict]:
    """Admitted wildcard candidates, keyed by ticker.

    Wiki text is loaded through ``wiki_signals`` so this shares its GitHub-raw
    fetch with local-copy fallback rather than opening a second path.
    """
    global _CACHE
    if _CACHE is not None and not refresh:
        found = _CACHE
    else:
        try:
            from scan_pipeline.utils import wiki_signals as ws
            from concurrent.futures import ThreadPoolExecutor
            names = list(ws.WIKI_SECTOR_MAP.keys()) + [
                p for p in EXTRA_PAGES if p not in ws.WIKI_SECTOR_MAP
            ]
            with ThreadPoolExecutor(max_workers=6) as pool:
                texts = dict(zip(names, pool.map(ws._fetch_one, names)))
            found = collect({k: v for k, v in texts.items() if v})
        except Exception as exc:                      # never block a scan
            print("[wildcards] wiki load failed (non-fatal): %s" % exc)
            found = {}
        _CACHE = found

    base = set(base_universe or ())
    admitted = [(t, r) for t, r in found.items() if t not in base]

    # Per-wiki cap first (sector balance), then a global ceiling as a
    # blast-radius guard against a malformed or hostile page.
    per_wiki: Dict[str, int] = {}
    kept: List[tuple] = []
    for ticker, rec in sorted(admitted, key=lambda kv: kv[1]["market_cap_usd_b"]):
        src = rec.get("source", "")
        if per_wiki.get(src, 0) >= MAX_PER_WIKI:
            continue
        per_wiki[src] = per_wiki.get(src, 0) + 1
        kept.append((ticker, rec))
        if len(kept) >= MAX_WILDCARDS:
            break
    return dict(kept)


def tickers(base_universe=()) -> List[str]:
    return sorted(wildcards(base_universe))
