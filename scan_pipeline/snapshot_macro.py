# snapshot_macro.py -- non-equity instrument snapshot for the weekly scan.
#
# Exposes fetch_special_instruments(friday_date) returning the rates / vol /
# commodities / fx blocks of data/weekly/<date>.json (DATA_FEED.md section 1),
# plus a mandatory "missing" list. Closes only; volume is kept when the feed
# reports a real one and normalized to None otherwise (never invented).
#
# Fetch discipline follows truth_layer/sweep/scripts/arena_ingest.py fetch_bar:
# explicit start/end window around the Friday, select that date's bar. No
# period='1d' blind fetches. If the Friday was a holiday, the last trading
# day <= Friday is used and a "note" field records the substitution.
#
# ---------------------------------------------------------------------------
# INSTRUMENT RESEARCH LOG (live-verified, probes run against yfinance 1.5.2)
# ---------------------------------------------------------------------------
# VIX   -> ^VIX      2026-08-07 close 14.90, volume 0. Index: volume
#                    normalized to None. Plausible range (5-80) confirmed.
# US10Y -> ^TNX      2026-08-07 close 4.66. DOCUMENTED DIVISOR = 1.0.
#                    Older lore says ^TNX quotes yield x10 (44.66 = 4.466%);
#                    that is NOT what Yahoo serves now. Live evidence:
#                    2026-08-07 = 4.66, 2025-08-08 = 4.285, 2024-08-09 = 3.942
#                    -- plain yield across the whole 104-week backfill window.
#                    Defensive guard kept: raw > 20 would indicate the legacy
#                    x10 feed and is divided by 10 (documented in code).
# US2Y  -> 2YY=F     DECISION: CME 2-Year Yield Futures. Returns an actual
#                    2Y yield quote, not a price: 2026-08-07 = 4.17,
#                    2025-08-08 = 3.70, 2024-08-09 = 3.983 (covers the full
#                    104-week backfill). Front-month yield futures track the
#                    cash 2Y within a few bp; this is the most honest 2Y
#                    yield source Yahoo offers. Candidates rejected:
#                      ^IRX  2026-08-07 = 3.71 -- 13-week T-bill, a DIFFERENT
#                            instrument; refused to relabel it as US2Y.
#                      ZT=F  2026-08-07 = 102.9766 -- 2Y note futures PRICE,
#                            not a yield; conversion would be invented data.
#                    2YY=F volume is ~0 (settlement-style quotes) -> None.
# DXY   -> DX-Y.NYB  2026-08-07 close 99.60, volume 0 -> None.
# WTI   -> CL=F      2026-08-07 close 78.18, volume 241222 (real, kept).
# GOLD  -> GC=F      2026-08-07 close 4340.70, volume real, kept.
# SILVER-> SI=F      2026-08-07 close 63.332, volume real, kept.
#
# Sanity notes from the smoke run (2026-08-07): GOLD 4340.70 and SILVER
# 63.33 sit above the briefing ranges (3000-3500 / 30-45); both are genuine
# live closes (2025-08-08: GC=F 3439.10, SI=F 38.42 -- a sustained rally,
# not a fetch artifact). All other instruments landed inside their ranges.

import datetime as dt

try:
    import yfinance as yf
except ImportError as exc:
    raise ImportError("snapshot_macro requires yfinance") from exc

# ---------------------------------------------------------------------------
# Provider map: instrument -> yahoo symbol -> normalization. One place to
# touch on a provider swap.
# ---------------------------------------------------------------------------
INSTRUMENTS = {
    "rates": {
        "US10Y": {"symbol": "^TNX",  "divisor": 1.0, "kind": "yield"},
        "US2Y":  {"symbol": "2YY=F", "divisor": 1.0, "kind": "yield"},
    },
    "vol": {
        "VIX": {"symbol": "^VIX", "divisor": 1.0, "kind": "index"},
    },
    "commodities": {
        "WTI":    {"symbol": "CL=F", "divisor": 1.0, "kind": "future"},
        "GOLD":   {"symbol": "GC=F", "divisor": 1.0, "kind": "future"},
        "SILVER": {"symbol": "SI=F", "divisor": 1.0, "kind": "future"},
    },
    "fx": {
        "DXY": {"symbol": "DX-Y.NYB", "divisor": 1.0, "kind": "index"},
    },
}

# If a "yield" feed ever returns a raw value above this, assume the legacy
# x10 scaling (e.g. 44.66 for 4.466%) and divide by 10. See research log.
LEGACY_X10_GUARD = 20.0


def _fetch_one(ticker, cfg, friday):
    """Fetch one instrument's Friday bar. Returns (entry_dict, error_str)."""
    symbol = cfg["symbol"]
    start = (friday - dt.timedelta(days=5)).isoformat()
    end = (friday + dt.timedelta(days=2)).isoformat()
    try:
        hist = yf.Ticker(symbol).history(start=start, end=end)
    except Exception as exc:  # network/parse failure: never kill the batch
        return None, "%s: %s" % (type(exc).__name__, str(exc)[:160])
    if hist is None or hist.empty:
        return None, "no data returned for window %s..%s" % (start, end)

    # Select the exact Friday bar; else last trading day <= Friday.
    picked = None
    for idx, row in hist.iterrows():
        d = idx.date()
        if d <= friday:
            picked = (d, row)
        if d == friday:
            break
    if picked is None:
        return None, "no bar on or before %s in window" % friday.isoformat()

    d, row = picked
    close = float(row["Close"]) / cfg["divisor"]
    if cfg["kind"] == "yield" and close > LEGACY_X10_GUARD:
        close = close / 10.0  # legacy x10 feed guard, see research log
    vol = row.get("Volume")
    volume = None
    try:
        if vol is not None and vol == vol and int(vol) > 0:  # NaN/0 -> None
            volume = int(vol)
    except (TypeError, ValueError):
        volume = None

    entry = {"close": round(close, 4), "volume": volume}
    if d != friday:
        entry["note"] = ("Friday %s not a trading day; used last trading "
                         "day %s" % (friday.isoformat(), d.isoformat()))
    return entry, None


def fetch_special_instruments(friday_date: str) -> dict:
    """Fetch rates/vol/commodities/fx closes for a given Friday (YYYY-MM-DD).

    Returns {"rates": {...}, "vol": {...}, "commodities": {...}, "fx": {...},
    "missing": [{"ticker": ..., "reason": ...}]}. Each instrument entry is
    {"close": float, "volume": int|None} plus an optional "note" when a
    holiday forced a fallback to the prior trading day. Failures land in
    "missing", never silently.
    """
    friday = dt.date.fromisoformat(friday_date)
    out = {block: {} for block in INSTRUMENTS}
    out["missing"] = []
    for block, instruments in INSTRUMENTS.items():
        for ticker, cfg in instruments.items():
            entry, err = _fetch_one(ticker, cfg, friday)
            if err is not None:
                out["missing"].append({"ticker": ticker, "reason": err})
            else:
                out[block][ticker] = entry
    return out
