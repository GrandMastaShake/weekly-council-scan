"""
snapshot.py -- committed data-feed writer/deriver for weekly-council-scan.

Wave 1 (Job S). Owns the committed data feed:

  * fetch_weekly_bars()     -- date-pinned yfinance fetch for the equity set
  * write_weekly()          -- data/weekly/<friday>.json   (DATA_FEED.md sec.1)
  * derive_market_state()   -- data/market_state.json      (MARKET_GROUNDING sec.1, sec.9)
  * build_universe()        -- data/universe.json + wiki/universe.md mirror (sec.3)
  * rederive_and_compare()  -- purity self-check for the Wave 2 truth gate

Spec amendment (owner, supersedes DATA_FEED.md sec.1 "Ticker set"): weekly
files commit the FULL universe -- STOCK_UNIVERSE (277) + 16 index/sector ETFs
= 293 series tickers -- plus the special-instrument blocks, not just the
charted ~40. Size math adjusts to ~15KB/file.

Special instruments (US10Y, US2Y, VIX, WTI, GOLD, SILVER, DXY) come from
scan_pipeline.snapshot_macro.fetch_special_instruments (Job V, built
concurrently). Contract: returns {"rates": {"US10Y": {...}, "US2Y": {...}},
"vol": {"VIX": {...}}, "commodities": {"WTI": ..., "GOLD": ..., "SILVER": ...},
"fx": {"DXY": {...}}, "missing": [{"ticker", "reason"}]} with values
{"close": float, "volume": float|None}. A defensive stub fallback covers the
module being absent (empty blocks + a missing entry), so this file never
depends on import success.

NOTE on the block shape: DATA_FEED.md sec.1 sketches rates/vol/commodities as
bare numbers ({"US10Y": 4.66}); the Job V contract supersedes that sketch and
blocks are committed as {"close": float, "volume": float|None} dicts, same
shape as series entries. Readers must use block[ticker]["close"].

Byte-stability contract (Wave 2 backfill + truth gate depend on this):
  * Serialization: json.dumps(obj, sort_keys=True, ensure_ascii=True,
    indent=2) + trailing "\n". Pure ASCII, LF newlines, sorted keys.
  * Floats are rounded BEFORE serialization with Python round()
    (banker's rounding -- deterministic across runs and platforms):
      weekly-file close            -> 4 dp   (FX-grade precision)
      market_state px / lvl        -> 2 dp
      pct deltas (d1w/d4w/d13w/d52w) -> 1 dp
      rate deltas / curve          -> integer bps
      pctile_2y                    -> integer 0-100
      correlations                 -> 3 dp
      adv_usd                      -> integer
  * Weekly closes are split/dividend-ADJUSTED closes (yfinance
    auto_adjust=True), matching the house convention in
    fetch_market_data._parse_daily_bars which prefers adjclose.

Derivation purity: derive_market_state() reads ONLY the weekly files and
facts.json. No network, no clocks; as_of comes from the newest weekly file.
Given identical inputs it is byte-identical (see rederive_and_compare).
"""

from __future__ import annotations

import glob
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

try:
    from scan_pipeline.config.tickers import STOCK_UNIVERSE
except ImportError:  # same-dir import when repo root is not on sys.path
    from config.tickers import STOCK_UNIVERSE


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROVIDER = "yahoo"          # the ONE provider constant; backfill appends
                            # "-backfill" at call time, never here

# Instrument classification for the committed feed and market_state.
INDEX_TICKERS = ["SPY", "QQQ", "DIA", "IWM"]
SECTOR_TICKERS = ["SMH", "XLE", "XLF", "XLK", "XLV", "XLP",
                  "XLY", "XLI", "XLB", "XLRE", "XLU", "XLC"]
RATE_TICKERS = ["US10Y", "US2Y"]        # weekly-file "rates" block
VOL_TICKERS = ["VIX"]                   # weekly-file "vol" block
COMMODITY_TICKERS = ["WTI", "GOLD", "SILVER"]   # "commodities" block
FX_TICKERS = ["DXY"]                    # "fx" block
SPECIAL_BLOCKS = ("rates", "vol", "commodities", "fx")

MAX_WORKERS = 10
PCTILE_WINDOW = 104                     # trailing weeks for pctile_2y
CORR_WEEKS = 4                          # trailing weekly returns for corr_spy_4w

# Cap tiers (market cap, USD)
CAP_MEGA = 200e9
CAP_LARGE = 10e9
CAP_MID = 2e9

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# Canonical serialization (byte-stability contract -- see module docstring)
# ---------------------------------------------------------------------------
def canonical_json(obj) -> str:
    """Byte-stable serialization: sorted keys, ASCII, 2-space indent, LF,
    trailing newline. Wave 2 diffs committed files byte-for-byte."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, indent=2) + "\n"


def _write_json(path: str, obj) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(canonical_json(obj))
    return path


def _r4(x) -> float:
    return round(float(x), 4)


def _r2(x) -> float:
    return round(float(x), 2)


def _r1(x) -> float:
    return round(float(x), 1)


def _r3(x) -> float:
    return round(float(x), 3)


def _vol_int(v) -> Optional[int]:
    """Volume as int; None stays None (instruments that don't trade shares)."""
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Equity set
# ---------------------------------------------------------------------------
def equity_universe() -> List[str]:
    """Full committed equity set: STOCK_UNIVERSE + index/sector ETFs, deduped.

    Per the owner amendment, weekly files commit this entire set."""
    return sorted(set(STOCK_UNIVERSE) | set(INDEX_TICKERS) | set(SECTOR_TICKERS))


# ---------------------------------------------------------------------------
# Special-instrument bridge (Job V contract, defensive stub fallback)
# ---------------------------------------------------------------------------
def get_special_instruments(friday_date: str) -> dict:
    """Fetch special instruments via snapshot_macro (Job V). On ANY failure
    returns empty blocks plus a missing entry -- never raises, never
    fabricates a level."""
    empty = {"rates": {}, "vol": {}, "commodities": {}, "fx": {}}
    try:
        from scan_pipeline.snapshot_macro import fetch_special_instruments
    except ImportError:
        try:
            from snapshot_macro import fetch_special_instruments  # type: ignore
        except ImportError:
            return dict(empty, missing=[{
                "ticker": "*",
                "reason": "snapshot_macro module absent; special-instrument blocks empty",
            }])
    try:
        result = fetch_special_instruments(friday_date)
    except Exception as exc:
        return dict(empty, missing=[{
            "ticker": "*",
            "reason": "fetch_special_instruments raised: %s" % exc,
        }])
    if not isinstance(result, dict):
        return dict(empty, missing=[{
            "ticker": "*",
            "reason": "fetch_special_instruments returned non-dict",
        }])
    for block in SPECIAL_BLOCKS:
        result.setdefault(block, {})
    result.setdefault("missing", [])
    return result


# ---------------------------------------------------------------------------
# 1. Date-pinned yfinance fetch
# ---------------------------------------------------------------------------
def _extract_bar(df, ticker: str, friday_date: str) -> Optional[dict]:
    """Select the bar for exactly friday_date from a yf.download frame.

    Date-pinned: we pick the row dated friday_date, never 'the last row'.
    Returns {"close": float(4dp), "volume": int|None} or None."""
    if df is None or len(df) == 0:
        return None
    try:
        import pandas as pd  # noqa: F401  (yfinance hard-depends on pandas)
        if isinstance(df.columns, pd.MultiIndex):
            if ticker in df.columns.get_level_values(0):
                sub = df[ticker]
            elif ticker in df.columns.get_level_values(-1):
                sub = df.xs(ticker, axis=1, level=-1)
            else:
                return None
        else:
            sub = df  # single-ticker download: plain columns
    except Exception:
        return None
    # locate the row whose date is exactly friday_date
    try:
        dates = sub.index.strftime("%Y-%m-%d")
    except Exception:
        return None
    matches = [i for i, d in enumerate(dates) if d == friday_date]
    if not matches:
        return None
    row = sub.iloc[matches[0]]
    try:
        close = row["Close"]
    except Exception:
        return None
    try:
        if close != close:  # NaN check without importing math
            return None
        close = float(close)
    except (TypeError, ValueError):
        return None
    volume = None
    try:
        v = row["Volume"]
        if v == v:
            volume = int(v)
    except Exception:
        volume = None
    return {"close": _r4(close), "volume": volume}


def fetch_weekly_bars(tickers: List[str], friday_date: str) -> dict:
    """Date-pinned fetch of one Friday's bar per ticker.

    Window: [friday - 10d, friday + 1d); the bar dated exactly friday_date
    is selected. period='1d'-style blind fetches are banned in this project.
    Batch via yf.download first; tickers that come back without a usable bar
    get one per-ticker retry; remaining failures land in missing with the
    exception text as the reason.

    Returns {"bars": {ticker: {"close": float, "volume": int|None}},
             "missing": [{"ticker": str, "reason": str}]}.
    """
    tickers = sorted(set(tickers))
    friday = datetime.strptime(friday_date, "%Y-%m-%d").date()
    start = (friday - timedelta(days=10)).isoformat()
    end = (friday + timedelta(days=1)).isoformat()

    try:
        import yfinance as yf
    except ImportError as exc:
        return {"bars": {}, "missing": [
            {"ticker": t, "reason": "yfinance import failed: %s" % exc}
            for t in tickers]}

    bars: Dict[str, dict] = {}
    retry: List[Tuple[str, str]] = []

    # -- batch pass -----------------------------------------------------------
    try:
        df = yf.download(tickers, start=start, end=end, interval="1d",
                         group_by="ticker", auto_adjust=True,
                         progress=False, threads=True)
        for t in tickers:
            try:
                bar = _extract_bar(df, t, friday_date)
            except Exception as exc:
                bar = None
                retry.append((t, "batch parse error: %s" % exc))
                continue
            if bar is None:
                retry.append((t, "no bar dated %s in window %s..%s"
                                 % (friday_date, start, end)))
            else:
                bars[t] = bar
    except Exception as exc:
        retry = [(t, "batch download failed: %s" % exc) for t in tickers]

    # -- per-ticker fallback ---------------------------------------------------
    missing: List[dict] = []
    for t, reason in retry:
        try:
            df1 = yf.download(t, start=start, end=end, interval="1d",
                              auto_adjust=True, progress=False, threads=False)
            bar = _extract_bar(df1, t, friday_date)
        except Exception as exc:
            bar = None
            reason = "%s; per-ticker retry raised: %s" % (reason, exc)
        if bar is None:
            missing.append({"ticker": t, "reason": reason})
        else:
            bars[t] = bar

    return {"bars": bars, "missing": missing}


# ---------------------------------------------------------------------------
# 2. Weekly file writer (DATA_FEED.md sec.1)
# ---------------------------------------------------------------------------
def _normalize_block(block) -> Dict[str, dict]:
    """Normalize a special-instrument block to {ticker: {"close","volume"}}.

    Accepts the Job V contract dicts; tolerates bare numbers (older sketch
    shape) by lifting them to {"close": n, "volume": None}."""
    out: Dict[str, dict] = {}
    if not isinstance(block, dict):
        return out
    for t, rec in block.items():
        if isinstance(rec, dict):
            close = rec.get("close")
            vol = rec.get("volume")
        elif isinstance(rec, (int, float)):
            close, vol = rec, None
        else:
            continue
        if close is None:
            continue
        try:
            out[str(t)] = {"close": _r4(close), "volume": _vol_int(vol)}
        except (TypeError, ValueError):
            continue
    return out


def write_weekly(friday_date: str, series_bars: dict, special: Optional[dict] = None,
                 out_dir: str = "data") -> str:
    """Write data/weekly/<friday_date>.json under out_dir.

    series_bars: either a plain {ticker: {"close","volume"}} mapping (missing
        defaults to []) or the full fetch_weekly_bars() result
        {"bars": ..., "missing": ...}.
    special: the snapshot_macro contract dict, or None to call
        get_special_instruments(friday_date) (stub fallback if Job V's module
        is absent).
    out_dir: the data root; the file lands at <out_dir>/weekly/<date>.json.

    'missing' is REQUIRED and never empty-by-omission: it is the union of
    series fetch failures and special-instrument failures, sorted and deduped.
    fetched_at is the real UTC now -- it is how stale-cache scans are caught.
    """
    if not _DATE_RE.match(friday_date):
        raise ValueError("friday_date must be YYYY-MM-DD, got %r" % friday_date)

    if isinstance(series_bars, dict) and ("bars" in series_bars or "missing" in series_bars):
        bars = series_bars.get("bars") or {}
        missing = list(series_bars.get("missing") or [])
    else:
        bars = series_bars
        missing = []

    if special is None:
        special = get_special_instruments(friday_date)
    missing.extend(special.get("missing") or [])

    # dedupe + sort for deterministic output
    seen = set()
    uniq: List[dict] = []
    for m in missing:
        key = (str(m.get("ticker")), str(m.get("reason")))
        if key not in seen:
            seen.add(key)
            uniq.append({"ticker": key[0], "reason": key[1]})
    uniq.sort(key=lambda m: (m["ticker"], m["reason"]))

    series = _normalize_block(bars)

    doc = {
        "as_of": friday_date,
        "source": PROVIDER,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "session": "close",
        "series": series,
        "rates": _normalize_block(special.get("rates")),
        "vol": _normalize_block(special.get("vol")),
        "commodities": _normalize_block(special.get("commodities")),
        "fx": _normalize_block(special.get("fx")),
        "missing": uniq,
    }
    path = os.path.join(out_dir, "weekly", friday_date + ".json")
    return _write_json(path, doc)


# ---------------------------------------------------------------------------
# 3. market_state derivation (MARKET_GROUNDING sec.1 + sec.9) -- PURE
# ---------------------------------------------------------------------------
def _load_weekly_files(weekly_dir: str) -> List[Tuple[str, dict]]:
    """Load weekly files, oldest first. A <date>.corrected.json supersedes
    its original (DATA_FEED.md sec.1 correction rule)."""
    originals = {}
    corrected = set()
    for path in glob.glob(os.path.join(weekly_dir, "*.json")):
        name = os.path.basename(path)
        if name.endswith(".corrected.json"):
            d = name[: -len(".corrected.json")]
            if _DATE_RE.match(d):
                corrected.add(d)
        elif _DATE_RE.match(name[: -len(".json")]):
            originals[name[: -len(".json")]] = path
    docs: List[Tuple[str, dict]] = []
    for d in sorted(set(originals) | corrected):
        path = (os.path.join(weekly_dir, d + ".corrected.json")
                if d in corrected else originals[d])
        with open(path, "r", encoding="utf-8") as f:
            docs.append((d, json.load(f)))
    return docs


def _close_series(docs: List[Tuple[str, dict]], ticker: str,
                  block: Optional[str]) -> Dict[str, float]:
    """{date: close} for one instrument across weekly files. Gaps are
    skipped, never interpolated (backfill gap rule)."""
    pts: Dict[str, float] = {}
    for d, doc in docs:
        src = doc.get("series") if block is None else doc.get(block)
        if not isinstance(src, dict):
            continue
        rec = src.get(ticker)
        if isinstance(rec, dict):
            c = rec.get("close")
        elif isinstance(rec, (int, float)):
            c = rec
        else:
            c = None
        if c is not None:
            try:
                pts[d] = float(c)
            except (TypeError, ValueError):
                pass
    return pts


def _pct_delta(pts: Dict[str, float], as_of: str, weeks: int) -> Tuple[Optional[float], Optional[str]]:
    """Pct change vs the file dated exactly 7*weeks earlier (1dp). Requires
    an exact-date prior file -- adjacent-file substitution would silently
    change the window length."""
    if as_of not in pts:
        return None, "no close for %s" % as_of
    target = (datetime.strptime(as_of, "%Y-%m-%d").date()
              - timedelta(weeks=weeks)).isoformat()
    if target not in pts:
        return None, "no weekly file dated %s (%dw prior)" % (target, weeks)
    base = pts[target]
    if base == 0:
        return None, "prior close is 0"
    return _r1(100.0 * (pts[as_of] / base - 1.0)), None


def _pctile_2y(pts: Dict[str, float], as_of: str) -> Tuple[Optional[int], Optional[str]]:
    """Percent of the trailing <=104 weekly closes strictly below the current
    close (integer 0-100). 0 = lowest of the window. Gaps are skipped, so the
    window is 'up to 104 available observations', not calendar weeks."""
    if as_of not in pts:
        return None, "no close for %s" % as_of
    vals = [v for _, v in sorted(pts.items()) if _ <= as_of][-PCTILE_WINDOW:]
    if not vals:
        return None, "no observations in window"
    cur = pts[as_of]
    below = sum(1 for v in vals if v < cur)
    return int(round(100.0 * below / len(vals))), None


def _level(pts: Dict[str, float], as_of: str, ndp: int = 2) -> Tuple[Optional[float], Optional[str]]:
    if as_of not in pts:
        return None, "no close for %s" % as_of
    return round(pts[as_of], ndp), None


def _rate_delta_bps(pts: Dict[str, float], as_of: str) -> Tuple[Optional[int], Optional[str]]:
    """Week-over-week level change in integer bps for rate series."""
    if as_of not in pts:
        return None, "no close for %s" % as_of
    target = (datetime.strptime(as_of, "%Y-%m-%d").date()
              - timedelta(weeks=1)).isoformat()
    if target not in pts:
        return None, "no weekly file dated %s (1w prior)" % target
    return int(round((pts[as_of] - pts[target]) * 100.0)), None


def _corr_spy_4w(pts: Dict[str, float], spy: Dict[str, float],
                 as_of: str) -> Tuple[Optional[float], Optional[str]]:
    """Pearson r of the trailing 4 weekly returns vs SPY's (3dp). Requires
    exact 7-day-spaced files for both series across all 4 return pairs;
    any gap -> null with the missing week named."""
    base = datetime.strptime(as_of, "%Y-%m-%d").date()
    rt: List[float] = []
    rs: List[float] = []
    for k in range(CORR_WEEKS):
        d1 = (base - timedelta(weeks=k)).isoformat()
        d0 = (base - timedelta(weeks=k + 1)).isoformat()
        for d in (d0, d1):
            if d not in pts:
                return None, "no close for %s (corr window)" % d
            if d not in spy:
                return None, "no SPY close for %s (corr window)" % d
        rt.insert(0, pts[d1] / pts[d0] - 1.0)
        rs.insert(0, spy[d1] / spy[d0] - 1.0)
    n = len(rt)
    mt = sum(rt) / n
    ms = sum(rs) / n
    cov = sum((a - mt) * (b - ms) for a, b in zip(rt, rs))
    vt = sum((a - mt) ** 2 for a in rt)
    vs = sum((b - ms) ** 2 for b in rs)
    if vt == 0 or vs == 0:
        return None, "zero variance in corr window"
    return _r3(cov / (vt * vs) ** 0.5), None


def _entry(fields: Dict[str, Tuple[Optional[float], Optional[str]]]) -> dict:
    """Assemble one instrument entry: every field present always; a null
    value carries a sibling '<field>_reason'."""
    out: Dict[str, object] = {}
    for name, (val, reason) in fields.items():
        out[name] = val
        if val is None:
            out[name + "_reason"] = reason or "unavailable"
    return out


def _px_entry(pts, spy, as_of, prev_corr, prev_corr_reason, with_corr):
    fields = {
        "px": _level(pts, as_of),
        "d1w": _pct_delta(pts, as_of, 1),
        "d4w": _pct_delta(pts, as_of, 4),
        "d13w": _pct_delta(pts, as_of, 13),
        "d52w": _pct_delta(pts, as_of, 52),
        "pctile_2y": _pctile_2y(pts, as_of),
    }
    if with_corr:
        fields["corr_spy_4w"] = _corr_spy_4w(pts, spy, as_of)
        fields["corr_prev"] = (prev_corr, prev_corr_reason)
    return _entry(fields)


def _regime(vix_pctile, curve_bps, fed_stance) -> str:
    """Computed regime label (MARKET_GROUNDING sec.9) -- rule-based, never
    free text. Tokens:
      risk appetite : VIX pctile_2y <=33 risk-on | <=66 risk-mixed | risk-off
      curve         : 2s10s >0 curve-positive | =0 curve-flat | <0 curve-inverted
      policy        : 'policy-' + lead word of facts.json fed_stance, lowercased
    Any unavailable input -> '<leg>-unknown'."""
    if vix_pctile is None:
        risk = "risk-unknown"
    elif vix_pctile <= 33:
        risk = "risk-on"
    elif vix_pctile <= 66:
        risk = "risk-mixed"
    else:
        risk = "risk-off"
    if curve_bps is None:
        curve = "curve-unknown"
    elif curve_bps > 0:
        curve = "curve-positive"
    elif curve_bps == 0:
        curve = "curve-flat"
    else:
        curve = "curve-inverted"
    lead = None
    if isinstance(fed_stance, str):
        m = re.match(r"[A-Za-z]+", fed_stance.strip())
        if m:
            lead = m.group(0).lower()
    policy = "policy-" + (lead or "unknown")
    return "%s / %s / %s" % (risk, curve, policy)


def _derive_from_files(docs: List[Tuple[str, dict]], facts: Optional[dict],
                       prev_market_state: Optional[dict]) -> dict:
    """Core derivation over an explicit (date, doc) list -- the pure core
    shared by derive_market_state() and rederive_and_compare()."""
    if not docs:
        raise ValueError("no weekly files to derive from")
    as_of = docs[-1][0]
    facts = facts if isinstance(facts, dict) else {}

    spy = _close_series(docs, "SPY", None)

    def series_pts(t):
        return _close_series(docs, t, None)

    # -- index ---------------------------------------------------------------
    index = {}
    for t in INDEX_TICKERS:
        index[t] = _px_entry(series_pts(t), spy, as_of, None, None, with_corr=False)

    # -- vol -------------------------------------------------------------------
    vol = {}
    for t in VOL_TICKERS:
        pts = _close_series(docs, t, "vol")
        vol[t] = _entry({
            "lvl": _level(pts, as_of),
            "d1w": _pct_delta(pts, as_of, 1),
            "pctile_2y": _pctile_2y(pts, as_of),
        })

    # -- rates -----------------------------------------------------------------
    rates = {}
    rate_pts = {t: _close_series(docs, t, "rates") for t in RATE_TICKERS}
    for t in RATE_TICKERS:
        pts = rate_pts[t]
        rates[t] = _entry({
            "lvl": _level(pts, as_of),
            "d1w_bps": _rate_delta_bps(pts, as_of),
            "pctile_2y": _pctile_2y(pts, as_of),
        })
    lvl10 = rates.get("US10Y", {}).get("lvl")
    lvl2 = rates.get("US2Y", {}).get("lvl")
    if lvl10 is not None and lvl2 is not None:
        rates["curve_2s10s_bps"] = int(round((lvl10 - lvl2) * 100.0))
    else:
        rates["curve_2s10s_bps"] = None
        rates["curve_2s10s_bps_reason"] = (
            "requires US10Y and US2Y closes for %s" % as_of)

    # -- sectors (with SPY correlation + last week's corr) ---------------------
    prev_sectors = (prev_market_state or {}).get("sectors") or {}
    sectors = {}
    for t in SECTOR_TICKERS:
        if prev_market_state is None:
            prev_corr, prev_reason = None, "no prev_market_state supplied"
        else:
            prev_rec = prev_sectors.get(t) or {}
            prev_corr = prev_rec.get("corr_spy_4w")
            prev_reason = (None if prev_corr is not None
                           else "prev_market_state has no corr_spy_4w for %s" % t)
        sectors[t] = _px_entry(series_pts(t), spy, as_of,
                               prev_corr, prev_reason, with_corr=True)

    # -- commodities / fx -------------------------------------------------------
    commodities = {}
    for t in COMMODITY_TICKERS:
        commodities[t] = _px_entry(_close_series(docs, t, "commodities"),
                                   spy, as_of, None, None, with_corr=False)
    fx = {}
    for t in FX_TICKERS:
        fx[t] = _px_entry(_close_series(docs, t, "fx"),
                          spy, as_of, None, None, with_corr=False)

    # -- policy / macro / upcoming from facts.json ------------------------------
    def fact(*path):
        node = facts
        for p in path:
            if not isinstance(node, dict) or p not in node:
                return None
            node = node[p]
        return node.get("value") if isinstance(node, dict) else node

    def fact_asof(*path):
        node = facts
        for p in path:
            if not isinstance(node, dict) or p not in node:
                return None
            node = node[p]
        return node.get("as_of") if isinstance(node, dict) else None

    policy = {}
    for field, path in (("fed_stance", ("policy", "fed_stance")),
                        ("fed_funds_range", ("policy", "fed_funds_range")),
                        ("next_macro_gate", ("policy", "next_macro_gate"))):
        val = fact(*path)
        policy[field] = val
        if val is None:
            policy[field + "_reason"] = "facts.json missing policy.%s" % path[-1]
        ao = fact_asof(*path)
        policy[field + "_as_of"] = ao
        if ao is None:
            policy[field + "_as_of_reason"] = "facts.json missing policy.%s as_of" % path[-1]

    macro = facts.get("macro_prints")
    macro_reason = None
    if macro is None:
        macro_reason = ("facts.json has no macro_prints block "
                        "(schema %s)" % facts.get("schema", "unknown"))
    upcoming = facts.get("upcoming")
    upcoming_reason = None
    if upcoming is None:
        gate = policy.get("next_macro_gate")
        if gate is not None:
            upcoming = [{"event": gate,
                         "when": policy.get("next_macro_gate_as_of"),
                         "binary": None}]
            upcoming_reason = None
        else:
            upcoming_reason = ("facts.json has no upcoming block and no "
                               "policy.next_macro_gate to fall back on")

    # -- regime (computed, never asked) -----------------------------------------
    regime = _regime(vol.get("VIX", {}).get("pctile_2y"),
                     rates.get("curve_2s10s_bps"),
                     policy.get("fed_stance"))

    state = {
        "schema": "market-state/v1",
        "as_of": as_of,
        "weekly_files_read": len(docs),
        "index": index,
        "vol": vol,
        "rates": rates,
        "sectors": sectors,
        "commodities": commodities,
        "fx": fx,
        "policy": policy,
        "regime": regime,
        "upcoming": upcoming,
        "macro": macro,
    }
    if macro_reason:
        state["macro_reason"] = macro_reason
    if upcoming_reason:
        state["upcoming_reason"] = upcoming_reason
    return state


def derive_market_state(weekly_dir: str, facts_path: str,
                        prev_market_state: Optional[dict] = None) -> dict:
    """Derive the MARKET_GROUNDING sec.1 snapshot from committed weekly
    files + facts.json. PURE: no network, no clocks; as_of is the newest
    weekly file's date. Identical inputs -> byte-identical output.

    prev_market_state: last week's derived state (dict), used only for
    corr_prev. Pass None for the earliest week (corr_prev -> null+reason).
    """
    docs = _load_weekly_files(weekly_dir)
    facts = None
    try:
        with open(facts_path, "r", encoding="utf-8") as f:
            facts = json.load(f)
    except Exception:
        facts = None  # every facts-fed field degrades to null+reason
    return _derive_from_files(docs, facts, prev_market_state)


def write_market_state(weekly_dir: str, facts_path: str, out_path: str,
                       prev_market_state: Optional[dict] = None) -> str:
    """Convenience writer around derive_market_state (canonical bytes)."""
    state = derive_market_state(weekly_dir, facts_path, prev_market_state)
    return _write_json(out_path, state)


# ---------------------------------------------------------------------------
# 4. Purity self-check (Wave 2 truth gate)
# ---------------------------------------------------------------------------
def _first_diff(a, b, path: str = "$") -> Optional[str]:
    """First differing JSON path in sorted-key order; None if equal."""
    if type(a) is not type(b):
        return path
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                return "%s.%s (only in committed)" % (path, k)
            if k not in b:
                return "%s.%s (only in rederived)" % (path, k)
            sub = _first_diff(a[k], b[k], "%s.%s" % (path, k))
            if sub:
                return sub
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return "%s (len %d != %d)" % (path, len(a), len(b))
        for i, (x, y) in enumerate(zip(a, b)):
            sub = _first_diff(x, y, "%s[%d]" % (path, i))
            if sub:
                return sub
        return None
    return None if a == b else path


def rederive_and_compare(weekly_dir: str, facts_path: str,
                         market_state_path: str) -> Tuple[bool, Optional[str]]:
    """Purity self-check for the truth gate.

    Re-derives the WHOLE chain from the earliest weekly file forward -- each
    week's derived state feeds the next as prev_market_state, so corr_prev is
    reproduced rather than skipped -- then compares the final state (as_of =
    newest weekly file) against the committed file, both semantically and as
    canonical bytes.

    Returns (match, first_differing_path). match=True iff canonical bytes
    are identical; first_differing_path is a JSON path like
    '$.sectors.SMH.d1w' or None when matched.
    """
    with open(market_state_path, "r", encoding="utf-8") as f:
        committed_raw = f.read()
    committed = json.loads(committed_raw)

    docs = _load_weekly_files(weekly_dir)
    facts = None
    try:
        with open(facts_path, "r", encoding="utf-8") as f:
            facts = json.load(f)
    except Exception:
        facts = None

    prev = None
    state = None
    for i in range(len(docs)):
        state = _derive_from_files(docs[: i + 1], facts, prev)
        prev = state

    if canonical_json(state) == canonical_json(committed):
        return True, None
    return False, (_first_diff(state, committed) or "<bytes differ>")


# ---------------------------------------------------------------------------
# 5. Universe build (DATA_FEED.md sec.3)
# ---------------------------------------------------------------------------
def _grep_wiki_refs(wiki_dir: str, tickers: List[str]) -> Dict[str, List[str]]:
    """Whole-word, case-sensitive grep of each wiki/*.md for each ticker.
    An empty array is the NAKED flag -- correct, not an error."""
    pages: List[Tuple[str, str]] = []
    for path in sorted(glob.glob(os.path.join(wiki_dir, "*.md"))):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            pages.append(("wiki/" + os.path.basename(path), f.read()))
    refs: Dict[str, List[str]] = {}
    for t in tickers:
        pat = re.compile(r"\b" + re.escape(t) + r"\b")
        refs[t] = [name for name, text in pages if pat.search(text)]
    return refs


def _cap_tier(market_cap) -> Optional[str]:
    if market_cap is None:
        return None
    try:
        mc = float(market_cap)
    except (TypeError, ValueError):
        return None
    if mc >= CAP_MEGA:
        return "MEGA"
    if mc >= CAP_LARGE:
        return "LARGE"
    if mc >= CAP_MID:
        return "MID"
    return "SMALL"


def _enrich_one(ticker: str) -> Tuple[str, dict]:
    """yfinance .info for one ticker, fully defensive."""
    import yfinance as yf
    info = yf.Ticker(ticker).info
    if not isinstance(info, dict):
        raise ValueError("no info dict")
    return ticker, {
        "name": info.get("longName") or info.get("shortName"),
        "sector": info.get("sector"),
        "sub": info.get("industry"),
        "marketCap": info.get("marketCap"),
        "averageVolume": info.get("averageVolume"),
    }


def _batch_latest_closes(tickers: List[str]) -> Dict[str, float]:
    """Latest available close per ticker via one date-windowed batch download
    (last bar in a trailing 10-day window; enrichment only -- this value is
    never committed as a weekly observation)."""
    import yfinance as yf
    end = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
    start = (datetime.now(timezone.utc).date() - timedelta(days=10)).isoformat()
    out: Dict[str, float] = {}
    df = yf.download(tickers, start=start, end=end, interval="1d",
                     group_by="ticker", auto_adjust=True,
                     progress=False, threads=True)
    for t in tickers:
        try:
            import pandas as pd
            sub = df[t] if isinstance(df.columns, pd.MultiIndex) else df
            closes = sub["Close"].dropna()
            if len(closes):
                out[t] = float(closes.iloc[-1])
        except Exception:
            pass
    return out


def build_universe(wiki_dir: str, out_path: str, enrich: bool = True,
                   md_path: Optional[str] = None,
                   tickers: Optional[List[str]] = None) -> dict:
    """Build universe.json (DATA_FEED.md sec.3) and optionally the human
    mirror universe.md.

    wiki_refs are grepped live from wiki_dir so they cannot drift from
    reality; an empty array is the NAKED flag. added/removed stay null --
    this is a legacy universe and we do NOT fabricate dates. With
    enrich=False every enrichment field is null with a '<field>_reason'
    sibling (never invented). as_of/next_review use the real build clock:
    universe.json is a build artifact, not a pure derivation.
    """
    tickers = sorted(set(tickers)) if tickers else sorted(STOCK_UNIVERSE)
    refs = _grep_wiki_refs(wiki_dir, tickers)

    info_map: Dict[str, dict] = {}
    close_map: Dict[str, float] = {}
    enrich_errors: Dict[str, str] = {}
    if enrich:
        try:
            close_map = _batch_latest_closes(tickers)
        except Exception as exc:
            enrich_errors["*closes*"] = "batch close fetch failed: %s" % exc
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futs = {pool.submit(_enrich_one, t): t for t in tickers}
            for fut in as_completed(futs):
                t = futs[fut]
                try:
                    _, info = fut.result()
                    info_map[t] = info
                except Exception as exc:
                    enrich_errors[t] = str(exc)

    entries = []
    for t in tickers:
        info = info_map.get(t, {})
        close = close_map.get(t)
        avg_vol = info.get("averageVolume")
        adv = None
        if avg_vol is not None and close is not None:
            try:
                adv = int(float(avg_vol) * close)
            except (TypeError, ValueError):
                adv = None

        entry = {
            "t": t,
            "name": info.get("name"),
            "sector": info.get("sector"),
            "sub": info.get("sub"),
            "cap": _cap_tier(info.get("marketCap")),
            "adv_usd": adv,
            "added": None,
            "removed": None,
            "wiki_refs": refs.get(t, []),
        }
        if not enrich:
            reason = "enrichment disabled (enrich=False)"
            for f_ in ("name", "sector", "sub", "cap", "adv_usd"):
                entry[f_ + "_reason"] = reason
        else:
            err = enrich_errors.get(t)
            for f_ in ("name", "sector", "sub"):
                if entry[f_] is None:
                    entry[f_ + "_reason"] = ("yfinance info failed: " + err) if err \
                        else "yfinance info field absent"
            if entry["cap"] is None:
                entry["cap_reason"] = (("yfinance info failed: " + err) if err
                                       else "marketCap absent")
            if entry["adv_usd"] is None:
                entry["adv_usd_reason"] = (
                    "averageVolume or latest close unavailable")
        entries.append(entry)

    today = datetime.now(timezone.utc).date()
    # quarterly review convention: next_review is the first day of the next
    # calendar quarter; additions/removals land only at review
    q_next_month = ((today.month - 1) // 3 + 1) * 3 + 1
    if q_next_month > 12:
        next_review = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_review = today.replace(month=q_next_month, day=1)

    doc = {
        "as_of": today.isoformat(),
        "next_review": next_review.isoformat(),
        "source": PROVIDER,
        "tickers": entries,
    }
    _write_json(out_path, doc)

    if md_path:
        _write_universe_md(md_path, doc)
    return doc


def _write_universe_md(md_path: str, doc: dict) -> str:
    """Human mirror wiki/universe.md: dated table of all tickers with
    sector/cap/wiki_refs count, headed by the quarterly review convention."""
    lines = [
        "# Universe",
        "",
        "As of %s. Machine mirror: `data/universe.json`." % doc["as_of"],
        "",
        "Reviewed **quarterly**; next review %s. Tickers enter or leave the"
        % doc["next_review"],
        "universe only at a quarterly review, recorded with a dated note in"
        " this file.",
        "`added` / `removed` dates are never back-filled for the legacy"
        " universe.",
        "",
        "`refs = 0` is the **NAKED** flag -- the wikis never mention the"
        " ticker, so the",
        "council has no narrative coverage for it. NAKED is a state to fix,"
        " not an error.",
        "",
        "| Ticker | Name | Sector | Cap | Refs |",
        "| --- | --- | --- | --- | --- |",
    ]
    for e in doc["tickers"]:
        lines.append("| %s | %s | %s | %s | %d |" % (
            e["t"],
            e.get("name") or "-",
            e.get("sector") or "-",
            e.get("cap") or "-",
            len(e.get("wiki_refs") or []),
        ))
    lines.append("")
    os.makedirs(os.path.dirname(os.path.abspath(md_path)), exist_ok=True)
    with open(md_path, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines))
    return md_path
