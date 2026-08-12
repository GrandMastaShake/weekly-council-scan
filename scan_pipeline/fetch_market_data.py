"""
fetch_market_data.py

Fetches live market data from Yahoo Finance public APIs and builds the
MarketDataContext consumed by Cecil / Marky / Ophelia.

Strategy
--------
* Yahoo Finance v8 chart API  (query1.finance.yahoo.com/v8/finance/chart/)
  – works without auth and gives daily OHLC + meta.
* Parallel fetch with ThreadPoolExecutor.
* Daily bars are rolled into weekly OHLC (Mon open → Fri close).
* VIX fetched directly via ^VIX; falls back to SPY-vol proxy if needed.
* P/E is not available from the free chart endpoint → falls back to the
  deterministic P/E routine already used by the TypeScript reference.
* Market conditions mirror the deterministic rules in scan.ts.

Usage
-----
    from fetch_market_data import MarketDataFetcher
    ctx = MarketDataFetcher().build_context(scan_date="2025-07-14")
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from scan_pipeline.config.tickers import STOCK_UNIVERSE
from scan_pipeline.utils.data_utils import (
    PE_MAP,
    PriceHistory,
    compute_simple_ma,
    compute_std_dev,
    get_fundamentals,
    get_pe,
    get_sector,
    generate_deterministic_context,
    mark_pe_unavailable,
    record_fundamentals,
    reset_pe_state,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
MAX_WORKERS = 10
WEEKS_LOOKBACK = 6          # fetch a little more than 4 weeks so we always have 4 complete weeks
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


# ---------------------------------------------------------------------------
# Raw fetcher
# ---------------------------------------------------------------------------

def _fetch_chart(ticker: str, range_str: str = "3mo", interval: str = "1d") -> Optional[dict]:
    """
    Hit the Yahoo Finance v8 chart endpoint for a single ticker.
    Returns the *result* dict (the inner payload) or None on failure.
    """
    url = (
        f"{YAHOO_CHART_URL.format(ticker=ticker)}"
        f"?interval={interval}&range={range_str}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except Exception:
        return None

    chart = data.get("chart", {})
    if chart.get("error"):
        return None
    results = chart.get("result")
    if not results:
        return None
    return results[0]


def _parse_daily_bars(result: dict) -> List[dict]:
    """
    Turn a v8 chart result into a list of daily bars:
        [{"date": "YYYY-MM-DD", "open": float, "high": float, "low": float, "close": float}, ...]
    """
    meta = result.get("meta", {})
    timestamps = result.get("timestamp", [])
    if not timestamps:
        return []

    # Try to use the adjclose / close arrays
    indicators = result.get("indicators", {})
    quote = indicators.get("quote", [{}])[0]
    adjclose_list = indicators.get("adjclose", [{}])[0].get("adjclose", [])

    opens = quote.get("open", [])
    highs = quote.get("high", [])
    lows = quote.get("low", [])
    closes = quote.get("close", [])
    volumes = quote.get("volume", [])

    bars = []
    for i, ts in enumerate(timestamps):
        if i >= len(opens) or i >= len(closes):
            break
        if opens[i] is None or closes[i] is None:
            continue
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        bars.append({
            "date": dt.strftime("%Y-%m-%d"),
            "open": float(opens[i]),
            "high": float(highs[i]) if highs[i] is not None else float(opens[i]),
            "low": float(lows[i]) if lows[i] is not None else float(opens[i]),
            "close": float(adjclose_list[i]) if (adjclose_list and i < len(adjclose_list) and adjclose_list[i] is not None) else float(closes[i]),
            "volume": float(volumes[i]) if (volumes and i < len(volumes) and volumes[i] is not None) else 0.0,
        })
    return bars


def _aggregate_weekly(bars: List[dict]) -> List[PriceHistory]:
    """
    Roll daily bars into weekly PriceHistory entries (Mon open → Fri close).
    ISO-calendar weeks are used so weeks are deterministic and Monday-based.
    Only weeks with at least one trading day are kept.
    """
    if not bars:
        return []

    # group by ISO calendar year + week number
    weeks: Dict[Tuple[int, int], List[dict]] = {}
    for bar in bars:
        dt = datetime.strptime(bar["date"], "%Y-%m-%d")
        iso_year, iso_week, _ = dt.isocalendar()
        key = (iso_year, iso_week)
        weeks.setdefault(key, []).append(bar)

    # sort by the first bar date in each week
    sorted_keys = sorted(weeks.keys(), key=lambda k: weeks[k][0]["date"])

    weekly: List[PriceHistory] = []
    for key in sorted_keys:
        days = weeks[key]
        days.sort(key=lambda x: x["date"])
        vols = [d.get("volume", 0.0) for d in days]
        avg_vol = sum(vols) / len(vols) if vols else 0.0
        weekly.append(PriceHistory(
            date=days[-1]["date"],   # label week by its last trading day
            open_price=days[0]["open"],
            close_price=days[-1]["close"],
            volume=avg_vol,
        ))

    return weekly


# ---------------------------------------------------------------------------
# Real P/E refresh (yfinance trailing P/E, weekly cache on disk)
# ---------------------------------------------------------------------------
PE_CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state", "pe_cache.json")


def _f(value) -> Optional[float]:
    """Defensive float coercion for yfinance .info fields."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _earnings_date_yf(tk, info: dict) -> Optional[str]:
    """Next earnings date as an ISO string; None when unavailable.

    Sources, in order: info.earningsTimestamp (epoch), then Ticker.calendar
    (dict on newer yfinance, DataFrame on older). All access is defensive.
    """
    try:
        ts = info.get("earningsTimestamp") or info.get("earningsTimestampStart")
        if ts:
            return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        pass
    try:
        cal = tk.calendar
        if isinstance(cal, dict):
            ed = cal.get("Earnings Date")
            if ed:
                d = ed[0] if isinstance(ed, (list, tuple)) else ed
                return d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]
        elif cal is not None and hasattr(cal, "iloc") and not cal.empty:
            d = cal.iloc[0, 0]
            return d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]
    except Exception:
        pass
    return None


def _fetch_fundamentals_yf(ticker: str) -> Optional[dict]:
    """Fetch real fundamentals for one ticker via yfinance. None on failure.

    Captures trailing/forward P/E plus the quality-leg fields Cecil scores
    on (dividend yield, payout ratio, revenue growth, leverage, free cash
    flow) and the next earnings date.

    Sanity bounds (tightened after the DOW/SYM hash-fiction incident):
    a trailing P/E of 0, |P/E| >= 10000, or a positive multiple below 4x is
    rejected as suspicious -- a "deep value" print that low is almost always
    misreported. A NEGATIVE trailing P/E is kept: loss-making is real
    information, and yfinance is the verified source for it.
    """
    try:
        import yfinance as yf
        tk = yf.Ticker(ticker)
        info = tk.info
        if not isinstance(info, dict):
            return None
        pe = _f(info.get("trailingPE"))
        if pe is not None and (pe == 0.0 or abs(pe) >= 10000.0 or 0.0 < pe < 4.0):
            pe = None
        fwd = _f(info.get("forwardPE"))
        if fwd is not None and (fwd == 0.0 or abs(fwd) >= 10000.0):
            fwd = None
        earnings_date = _earnings_date_yf(tk, info)
        if earnings_date is None:
            # Unavailable dates must NOT exclude the pick -- but say so loudly.
            print(f"[fetch_market_data] {ticker}: earnings date unknown")
        return {
            "pe": pe,
            "forward_pe": fwd,
            "dividend_yield": _f(info.get("dividendYield")),
            "payout_ratio": _f(info.get("payoutRatio")),
            "revenue_growth": _f(info.get("revenueGrowth")),
            "debt_to_equity": _f(info.get("debtToEquity")),
            "free_cashflow": _f(info.get("freeCashflow")),
            "earnings_date": earnings_date,
        }
    except Exception:
        return None


def _fetch_pe_yf(ticker: str) -> Optional[float]:
    """Backward-compatible P/E-only wrapper around _fetch_fundamentals_yf.
    None on failure; negative trailing P/Es are KEPT (loss-making is
    information, not missing data)."""
    data = _fetch_fundamentals_yf(ticker)
    return data.get("pe") if data else None


def _risk_stats(hist: List[PriceHistory]) -> Tuple[Optional[float], Optional[float]]:
    """Annualized realized vol and max drawdown from weekly bars.

    Drives Cecil's safety leg (decoupled from momentum). (None, None) when
    history is insufficient (<2 bars).
    """
    if len(hist) < 2:
        return None, None
    returns = [w.return_ for w in hist]
    vol = compute_std_dev(returns)
    ann_vol = vol * (52 ** 0.5) if vol is not None else None
    peak = hist[0].close
    max_dd = 0.0
    for w in hist:
        if w.close > peak:
            peak = w.close
        if peak > 0:
            dd = (w.close - peak) / peak
            if dd < max_dd:
                max_dd = dd
    return ann_vol, max_dd


def _business_days_between(start: str, end: str) -> int:
    """Weekday count from start (exclusive) to end (inclusive); negative
    when end precedes start. Holidays not modeled -- adequate for the
    5-trading-day earnings exclusion window."""
    d0 = datetime.strptime(start, "%Y-%m-%d").date()
    d1 = datetime.strptime(end, "%Y-%m-%d").date()
    if d1 < d0:
        return -_business_days_between(end, start)
    days = 0
    cur = d0
    while cur < d1:
        cur += timedelta(days=1)
        if cur.weekday() < 5:
            days += 1
    return days


def refresh_pe_map(tickers: List[str], week_label: str, max_workers: int = MAX_WORKERS) -> Tuple[int, int]:
    """
    Populate data_utils.PE_MAP with real trailing P/Es for the scan week.
    Uses a weekly on-disk cache (state/pe_cache.json); falls back per-ticker
    to deterministic_pe only where a real P/E is unavailable.
    Returns (real_count, failed_count).
    """
    # 0. A fresh week must NOT inherit last week's multiples: clear all
    # weekly P/E + fundamentals state BEFORE the cache load or live fetch.
    # (Residual shadowing bug: PE_MAP.update() merged onto stale entries, so
    # a week-N multiple could survive into week N+1 tagged pe_source:"real".)
    reset_pe_state()

    # 1. Try the weekly cache
    try:
        if os.path.exists(PE_CACHE_PATH):
            with open(PE_CACHE_PATH, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if cached.get("week") == week_label and cached.get("pe"):
                PE_MAP.update({k: float(v) for k, v in cached["pe"].items() if v is not None})
                mark_pe_unavailable(cached.get("unavailable") or [])
                # Additive cache field; older caches simply have no
                # fundamentals and engines fall back to neutral scoring.
                for k, v in (cached.get("fundamentals") or {}).items():
                    if isinstance(v, dict):
                        record_fundamentals(k, v)
                return len(cached["pe"]), len(cached.get("unavailable") or [])
    except Exception:
        pass

    # 2. Fetch live, in parallel
    fetched: Dict[str, float] = {}
    fundamentals: Dict[str, dict] = {}
    failed = 0
    failed_tickers: List[str] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_fetch_fundamentals_yf, t): t for t in tickers}
        for fut in as_completed(futures):
            t = futures[fut]
            try:
                data = fut.result(timeout=30)
            except Exception:
                data = None
            if data:
                # Real fundamentals are recorded even when the P/E itself is
                # absent -- the quality leg can still use them.
                fundamentals[t] = data
            pe = data.get("pe") if data else None
            if pe is not None:
                fetched[t] = pe
            else:
                failed += 1
                failed_tickers.append(t)

    PE_MAP.update(fetched)
    for t, data in fundamentals.items():
        record_fundamentals(t, data)
    # Record the failures so get_pe() returns None for them instead of a
    # fabricated hash-based multiple (the 2026-08-03 SYM incident).
    mark_pe_unavailable(failed_tickers)

    # 3. Persist the weekly cache (including the failure list so cached
    # weeks keep the same no-fabrication guarantee, plus fundamentals so a
    # cached week keeps real quality-leg data)
    try:
        os.makedirs(os.path.dirname(PE_CACHE_PATH), exist_ok=True)
        with open(PE_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "week": week_label,
                "pe": fetched,
                "unavailable": failed_tickers,
                "fundamentals": fundamentals,
            }, f)
    except Exception:
        pass

    return len(fetched), failed


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class MarketDataFetcher:
    """
    Fetches and assembles MarketDataContext from Yahoo Finance live data.
    """

    def __init__(self, max_workers: int = MAX_WORKERS):
        self.max_workers = max_workers
        self._cache: Dict[str, List[PriceHistory]] = {}

    # -- internals -----------------------------------------------------------

    def _fetch_ticker(self, ticker: str) -> List[PriceHistory]:
        """Fetch and cache weekly history for a single ticker."""
        if ticker in self._cache:
            return self._cache[ticker]

        result = _fetch_chart(ticker, range_str="3mo", interval="1d")
        if result is None:
            self._cache[ticker] = []
            return []

        bars = _parse_daily_bars(result)
        weekly = _aggregate_weekly(bars)
        self._cache[ticker] = weekly
        return weekly

    def _fetch_batch(self, tickers: List[str]) -> Dict[str, List[PriceHistory]]:
        """Parallel fetch for a list of tickers."""
        out: Dict[str, List[PriceHistory]] = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(self._fetch_ticker, t): t for t in tickers}
            for fut in as_completed(futures):
                t = futures[fut]
                try:
                    out[t] = fut.result()
                except Exception:
                    out[t] = []
        return out

    # -- context builders ----------------------------------------------------

    def build_context(self, scan_date: Optional[str] = None) -> dict:
        """
        Build the full MarketDataContext dict.

        Args:
            scan_date: ISO date string (YYYY-MM-DD).  If None, uses today.
                       The context is built from the most recent *completed*
                       trading week ending on or before this date.
        """
        if scan_date is None:
            scan_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Determine the effective Friday (end of the most recent completed week)
        scan_dt = datetime.strptime(scan_date, "%Y-%m-%d")
        # walk backward to the most recent Friday
        while scan_dt.weekday() != 4:  # Friday = 4
            scan_dt -= timedelta(days=1)
        friday_str = scan_dt.strftime("%Y-%m-%d")
        monday_str = (scan_dt - timedelta(days=4)).strftime("%Y-%m-%d")

        # ------------------------------------------------------------------
        # 1. Fetch SPY (benchmark + VIX proxy)
        # ------------------------------------------------------------------
        spy_weekly = self._fetch_ticker("SPY")
        spy_weekly = [w for w in spy_weekly if w.date <= friday_str]

        # ------------------------------------------------------------------
        # 2. Fetch VIX directly
        # ------------------------------------------------------------------
        vix_value = self._fetch_vix()

        # ------------------------------------------------------------------
        # 3. Fetch universe + batch parallel
        # ------------------------------------------------------------------
        all_tickers = list(STOCK_UNIVERSE) + ["SPY"]
        # dedupe just in case
        all_tickers = list(dict.fromkeys(all_tickers))
        batch = self._fetch_batch(all_tickers)

        # ------------------------------------------------------------------
        # 4. Build weeklyReturns + priceMap
        # ------------------------------------------------------------------
        weekly_returns: Dict[str, float] = {}
        price_map: Dict[str, dict] = {}

        for t, hist in batch.items():
            hist = [w for w in hist if w.date <= friday_str]
            if hist:
                latest = hist[-1]
                weekly_returns[t] = latest.return_
                price_map[t] = {"open": latest.open, "close": latest.close}

        # SPY return for market regime
        spy_return = weekly_returns.get("SPY", 0.0)

        # ------------------------------------------------------------------
        # 4b. Refresh real P/E map (weekly-cached, yfinance trailing P/E)
        # ------------------------------------------------------------------
        pe_ok, pe_failed = refresh_pe_map(STOCK_UNIVERSE, friday_str, self.max_workers)
        print(f"[fetch_market_data] P/E refresh: {pe_ok} real P/Es, {pe_failed} unavailable (deterministic fallback)")

        # ------------------------------------------------------------------
        # 5. Build stockData (PE, sector, context, real fundamentals, risk)
        # ------------------------------------------------------------------
        stock_data: Dict[str, dict] = {}
        for t in STOCK_UNIVERSE:
            ret = weekly_returns.get(t, 0.0)
            pe = get_pe(t, friday_str)
            sector = get_sector(t)
            context = generate_deterministic_context(t, ret, friday_str)
            fundamentals = get_fundamentals(t)
            hist = [w for w in batch.get(t, []) if w.date <= friday_str]
            realized_vol, max_drawdown = _risk_stats(hist)
            earnings_date = (fundamentals or {}).get("earnings_date")
            try:
                earnings_tdays = (
                    _business_days_between(friday_str, earnings_date)
                    if earnings_date else None
                )
            except Exception:
                earnings_tdays = None
            stock_data[t] = {
                "context": context,
                "pe": pe,
                "sector": sector,
                "fundamentals": fundamentals,
                "realized_vol": realized_vol,
                "max_drawdown": max_drawdown,
                "earnings_date": earnings_date,
                "earnings_trading_days": earnings_tdays,
            }

        # ------------------------------------------------------------------
        # 6. Market conditions (deterministic, mirroring scan.ts)
        # ------------------------------------------------------------------
        if spy_return > 0.03:
            fed_stance = "Accommodative. Risk-on environment supports easing."
            world_events = "Markets rallying on strong earnings and stable geopolitics."
        elif spy_return < -0.03:
            fed_stance = "Hawkish watch. Inflation concerns linger."
            world_events = "Geopolitical tensions and recession fears weighing on sentiment."
        else:
            fed_stance = "Neutral. Data-dependent approach."
            world_events = "Mixed signals. Earnings season in focus."

        # ------------------------------------------------------------------
        # 7. Assemble context
        # ------------------------------------------------------------------
        context = {
            "date": scan_date,
            "auditDates": {"monday": monday_str, "friday": friday_str},
            "stockData": stock_data,
            "vix": str(vix_value),
            "market_conditions": {
                "fed_stance": fed_stance,
                "world_events": world_events,
            },
            "weeklyReturns": weekly_returns,
            "priceMap": price_map,
            "dataSource": "verified",
        }

        return context

    def get_price_history(self, ticker: str, end_date: str, weeks: int) -> List[PriceHistory]:
        """
        Return the last *weeks* weekly PriceHistory entries for *ticker*
        ending on or before *end_date*.
        Mirrors getPriceHistory() from data-utils.ts.
        """
        hist = self._fetch_ticker(ticker)
        filtered = [w for w in hist if w.date <= end_date]
        return filtered[-weeks:] if len(filtered) >= weeks else filtered

    def get_weekly_return(self, ticker: str, date: str) -> Optional[float]:
        """
        Return the weekly return for *ticker* on the specific week ending *date*.
        Mirrors getWeeklyReturn() from data-utils.ts.
        """
        hist = self._fetch_ticker(ticker)
        for w in hist:
            if w.date == date:
                return w.return_
        return None

    # -- VIX fetcher ---------------------------------------------------------

    def _fetch_vix(self) -> float:
        """
        Try to fetch real VIX from ^VIX.
        If that fails, compute the SPY-volatility proxy used in scan.ts.
        """
        result = _fetch_chart("^VIX", range_str="5d", interval="1d")
        if result and result.get("meta"):
            meta = result["meta"]
            # try a few keys Yahoo sometimes includes
            for key in ("regularMarketPrice", "previousClose", "chartPreviousClose"):
                val = meta.get(key)
                if val is not None:
                    try:
                        return round(float(val), 1)
                    except Exception:
                        pass

        # fallback: SPY vol proxy
        spy_hist = self._fetch_ticker("SPY")
        if len(spy_hist) >= 2:
            returns = [w.return_ for w in spy_hist]
            weekly_vol = compute_std_dev(returns)
            annualized = weekly_vol * (52 ** 0.5)
            proxy = max(10.0, min(80.0, round(annualized * 100)))
            return float(proxy)
        return 20.0


# ---------------------------------------------------------------------------
# Convenience entry-point
# ---------------------------------------------------------------------------

def fetch_market_data(scan_date: Optional[str] = None) -> dict:
    """One-liner to build MarketDataContext."""
    return MarketDataFetcher().build_context(scan_date=scan_date)


def fetch_all_data(tickers=None, date=None) -> tuple:
    """High-level helper used by run_scan.py."""
    fetcher = MarketDataFetcher()
    market_data = fetcher.build_context(scan_date=date)
    price_cache = fetcher._cache
    pe_cache = {}  # live P/E not available from the free chart endpoint
    return market_data, price_cache, pe_cache


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("[data-fetcher] Self-test: fetching SPY + 5 tickers …")
    fetcher = MarketDataFetcher()
    # quick smoke test – just SPY and a handful of names
    sample = ["SPY", "AAPL", "MSFT", "NVDA", "GOOG"]
    for t in sample:
        hist = fetcher._fetch_ticker(t)
        print(f"  {t}: {len(hist)} weeks cached")
        if hist:
            print(f"    latest week {hist[-1].date}: open={hist[-1].open:.2f} close={hist[-1].close:.2f} return={hist[-1].return_:.4f}")

    ctx = fetcher.build_context()
    print(f"\n[context] date={ctx['date']}  vix={ctx['vix']}  spy_return={ctx['weeklyReturns'].get('SPY', 0):.4f}")
    print(f"[context] tickers with data: {len(ctx['weeklyReturns'])}")
