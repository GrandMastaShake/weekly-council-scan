"""
Data utilities — price history helpers, sector map, P/E lookups.
Ported from lib/data-utils.ts
"""

import glob
import os
import statistics
from typing import Dict, List, Optional

try:
    import yaml
except Exception:  # PyYAML absent -- hit-rate history degrades to neutral
    yaml = None


# ============================================================================
# SECTOR MAP
# ============================================================================

SECTOR_MAP: Dict[str, str] = {
    "AAPL": "Technology", "ACN": "Technology", "ADBE": "Technology", "ADSK": "Technology",
    "AKAM": "Technology", "AMAT": "Technology", "AMD": "Technology", "ANET": "Technology",
    "APH": "Technology", "AVGO": "Technology", "CDNS": "Technology", "CRM": "Technology",
    "CSCO": "Technology", "EA": "Technology", "FTNT": "Technology", "GOOG": "Technology",
    "GOOGL": "Technology", "HPE": "Technology", "INTC": "Technology", "INTU": "Technology",
    "IONQ": "Technology", "KLAC": "Technology", "LRCX": "Technology", "META": "Technology",
    "MSFT": "Technology", "MSI": "Technology", "MU": "Technology", "NFLX": "Technology",
    "NOW": "Technology", "NTLA": "Technology", "NVDA": "Technology", "NXPI": "Technology",
    "ORCL": "Technology", "PANW": "Technology", "QBTS": "Technology", "QCOM": "Technology",
    "QUBT": "Technology", "RBLX": "Technology", "RGTI": "Technology", "ROKU": "Technology",
    "SIDU": "Technology", "SMCI": "Technology", "SNPS": "Technology", "SYM": "Technology",
    "TEL": "Technology", "TER": "Technology", "VSAT": "Technology", "ZS": "Technology",
    "ABNB": "Consumer", "AMZN": "Consumer", "AZO": "Consumer", "CMG": "Consumer",
    "COST": "Consumer", "DPZ": "Consumer", "HD": "Consumer", "HLT": "Consumer",
    "KDP": "Consumer", "KMB": "Consumer", "KO": "Consumer", "LOW": "Consumer",
    "MAR": "Consumer", "MCD": "Consumer", "MDLZ": "Consumer", "MNST": "Consumer",
    "MO": "Consumer", "NKE": "Consumer", "ORLY": "Consumer", "PEP": "Consumer",
    "PG": "Consumer", "ROST": "Consumer", "SBUX": "Consumer", "SJM": "Consumer",
    "TGT": "Consumer", "TPR": "Consumer", "TSLA": "Consumer", "WMT": "Consumer",
    "YUM": "Consumer",
    "AFL": "Financials", "AIG": "Financials", "AJG": "Financials", "ALL": "Financials",
    "AMP": "Financials", "AON": "Financials", "APO": "Financials", "AXP": "Financials",
    "BAC": "Financials", "BK": "Financials", "BLK": "Financials", "BX": "Financials",
    "C": "Financials", "CB": "Financials", "CME": "Financials", "COIN": "Financials",
    "CPAY": "Financials", "GS": "Financials", "HIG": "Financials", "JKHY": "Financials",
    "JPM": "Financials", "KEY": "Financials", "KKR": "Financials", "MA": "Financials",
    "MCO": "Financials", "MMC": "Financials", "MS": "Financials", "PAYX": "Financials",
    "PGR": "Financials", "PRU": "Financials", "PYPL": "Financials", "SPGI": "Financials",
    "TROW": "Financials", "TRV": "Financials", "UPST": "Financials", "V": "Financials",
    "WFC": "Financials", "WRB": "Financials",
    "ABBV": "Healthcare", "AMGN": "Healthcare", "BAX": "Healthcare", "BDX": "Healthcare",
    "BFLY": "Healthcare", "BIIB": "Healthcare", "BMY": "Healthcare", "BSX": "Healthcare",
    "CI": "Healthcare", "CVS": "Healthcare", "DHR": "Healthcare", "DXCM": "Healthcare",
    "ELV": "Healthcare", "EW": "Healthcare", "GEHC": "Healthcare", "GILD": "Healthcare",
    "HCA": "Healthcare", "HUM": "Healthcare", "IDXX": "Healthcare", "ILMN": "Healthcare",
    "IQV": "Healthcare", "ISRG": "Healthcare", "JNJ": "Healthcare", "KVUE": "Healthcare",
    "LLY": "Healthcare", "MCK": "Healthcare", "MDT": "Healthcare", "MRK": "Healthcare",
    "MRNA": "Healthcare", "PFE": "Healthcare", "REGN": "Healthcare", "SOLV": "Healthcare",
    "SYK": "Healthcare", "TMO": "Healthcare", "UNH": "Healthcare", "VEEV": "Healthcare",
    "VRTX": "Healthcare", "ZTS": "Healthcare",
    "AXON": "Industrials", "BA": "Industrials", "CARR": "Industrials", "CAT": "Industrials",
    "CPRT": "Industrials", "CSX": "Industrials", "CTAS": "Industrials", "DE": "Industrials",
    "EMR": "Industrials", "ETN": "Industrials", "FAST": "Industrials", "FDX": "Industrials",
    "GD": "Industrials", "GE": "Industrials", "GEV": "Industrials", "GWW": "Industrials",
    "HON": "Industrials", "ITW": "Industrials", "JCI": "Industrials", "LMT": "Industrials",
    "MMM": "Industrials", "NDSN": "Industrials", "NOC": "Industrials", "NSC": "Industrials",
    "ODFL": "Industrials", "OTIS": "Industrials", "PCAR": "Industrials", "PH": "Industrials",
    "PNR": "Industrials", "PWR": "Industrials", "ROP": "Industrials", "RSG": "Industrials",
    "RTX": "Industrials", "TDG": "Industrials", "TXT": "Industrials", "UNP": "Industrials",
    "UPS": "Industrials", "URI": "Industrials", "VMI": "Industrials", "WM": "Industrials",
    "XYL": "Industrials",
    "APD": "Energy", "BKR": "Energy", "CVX": "Energy", "DD": "Energy", "DOW": "Energy",
    "ECL": "Energy", "EOG": "Energy", "FCX": "Energy", "HAL": "Energy", "HES": "Energy",
    "KMI": "Energy", "LIN": "Energy", "LYB": "Energy", "MPC": "Energy", "NEM": "Energy",
    "NUE": "Energy", "OKE": "Energy", "OXY": "Energy", "PPG": "Energy", "PSX": "Energy",
    "SHW": "Energy", "SLB": "Energy", "VLO": "Energy", "WMB": "Energy", "XOM": "Energy",
    "AMT": "Real Estate", "ARE": "Real Estate", "AVB": "Real Estate", "BXP": "Real Estate",
    "CBRE": "Real Estate", "CCI": "Real Estate", "COLD": "Real Estate", "COR": "Real Estate",
    "CPT": "Real Estate", "DLR": "Real Estate", "EQIX": "Real Estate", "EQR": "Real Estate",
    "ESS": "Real Estate", "EXR": "Real Estate", "FRT": "Real Estate", "GLPI": "Real Estate",
    "HST": "Real Estate", "INVH": "Real Estate", "IRM": "Real Estate", "KIM": "Real Estate",
    "MAA": "Real Estate", "O": "Real Estate", "PEAK": "Real Estate", "PLD": "Real Estate",
    "PSA": "Real Estate", "REG": "Real Estate", "SBAC": "Real Estate", "SPG": "Real Estate",
    "UDR": "Real Estate", "VICI": "Real Estate", "VTR": "Real Estate", "WELL": "Real Estate",
    "WY": "Real Estate",
    "AEP": "Utilities", "AES": "Utilities", "ATO": "Utilities", "AWK": "Utilities",
    "CMS": "Utilities", "CNP": "Utilities", "D": "Utilities", "DUK": "Utilities",
    "ED": "Utilities", "EIX": "Utilities", "ES": "Utilities", "ETR": "Utilities",
    "EVRG": "Utilities", "EXC": "Utilities", "FE": "Utilities", "LNT": "Utilities",
    "NEE": "Utilities", "NI": "Utilities", "NRG": "Utilities", "PEG": "Utilities",
    "PPL": "Utilities", "SO": "Utilities", "SRE": "Utilities", "WEC": "Utilities",
    "XEL": "Utilities",
}


PE_MAP: Dict[str, float] = {}


# Tickers the weekly refresh attempted but could NOT source a real P/E for
# (negative EPS, missing yfinance data). For these, fabricating a hash-based
# P/E is BANNED — the 2026-08-03 SYM incident booked a 23.6% position on a
# fabricated 11.3x multiple for a company with negative EPS.
PE_UNAVAILABLE: set = set()


def mark_pe_unavailable(tickers) -> None:
    """Record tickers whose real P/E could not be sourced this refresh."""
    PE_UNAVAILABLE.update(tickers)


# Real per-ticker fundamentals captured during the weekly refresh
# (yfinance .info): dividend yield, payout ratio, revenue growth, leverage,
# free cash flow, forward P/E, next earnings date. Drives Cecil's quality
# leg; empty outside a refresh.
FUNDAMENTALS_MAP: Dict[str, dict] = {}


def record_fundamentals(ticker: str, data: dict) -> None:
    """Store real fundamentals for one ticker (weekly refresh only)."""
    FUNDAMENTALS_MAP[ticker] = data


def get_fundamentals(ticker: str) -> Optional[dict]:
    return FUNDAMENTALS_MAP.get(ticker)


def reset_pe_state() -> None:
    """Clear ALL weekly P/E + fundamentals state.

    Must run at the start of every weekly refresh: a fresh week must not
    inherit last week's multiples (the residual shadowing bug let a stale
    week-N multiple survive tagged pe_source:"real", invisible to the
    synthetic-data gate).
    """
    PE_MAP.clear()
    PE_UNAVAILABLE.clear()
    FUNDAMENTALS_MAP.clear()


# ============================================================================
# Static market history cache (populated via load_static_market_history)
# ============================================================================

STATIC_MARKET_HISTORY: Dict[str, Dict[str, Dict[str, float]]] = {}


def load_static_market_history(history: Dict[str, Dict[str, Dict[str, float]]]) -> None:
    """Load static market history data into the module-level cache."""
    global STATIC_MARKET_HISTORY
    STATIC_MARKET_HISTORY = history


# ============================================================================
# PriceHistory dataclass
# ============================================================================

class PriceHistory:
    def __init__(self, date: str, open_price: float, close_price: float, volume: float = 0.0):
        self.date = date
        self.open = open_price
        self.close = close_price
        self.volume = volume
        self.return_ = (close_price - open_price) / open_price if open_price else 0.0

    def __repr__(self) -> str:
        return f"PriceHistory(date={self.date}, open={self.open}, close={self.close}, return_={self.return_:.4f})"

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "open": self.open,
            "close": self.close,
            "return": self.return_,
            "volume": self.volume,
        }


# ============================================================================
# Helpers
# ============================================================================

def resolve_ticker_alias(ticker: str) -> str:
    if ticker == "SPY":
        return "S&P 500"
    if ticker == "GOOGL":
        return "GOOG"
    return ticker


def get_sector(ticker: str) -> str:
    return SECTOR_MAP.get(ticker, "Unknown")


def get_pe(ticker: str, date: Optional[str] = None) -> Optional[float]:
    if ticker in PE_UNAVAILABLE:
        # Real data was attempted and failed. Never fabricate a multiple.
        # Checked FIRST so a stale PE_MAP entry can never shadow this flag.
        return None
    real = PE_MAP.get(ticker)
    if real is not None:
        # Negative trailing P/E = loss-making company. Return it as-is so
        # engines can score it honestly (a negative multiple is NOT deep
        # value — Cecil guards pe <= 0 separately).
        return real
    # Refresh never ran for this ticker (ad-hoc call, backtest without
    # refresh) — deterministic estimate is the documented fallback.
    return deterministic_pe(ticker, date)


def deterministic_pe(ticker: str, date: Optional[str] = None) -> float:
    hash_val = 0
    for ch in ticker:
        hash_val = ((hash_val << 5) - hash_val) + ord(ch)
        hash_val |= 0
    abs_hash = abs(hash_val)
    base = 10.0 + (abs_hash % 2500) / 100.0
    if date:
        # Drift the P/E slightly each scan date (±3%) so the fundamental
        # picture is anchored to the week being scanned, not frozen forever.
        drift = 0.97 + (deterministic_hash(ticker, "pe" + date) % 60) / 1000.0
        base = round(base * drift, 2)
    return base


def deterministic_hash(ticker: str, salt: str) -> int:
    hash_val = 0
    s = ticker + salt
    for ch in s:
        hash_val = ((hash_val << 5) - hash_val) + ord(ch)
        hash_val |= 0
    return abs(hash_val)


def generate_deterministic_context(ticker: str, return_val: float, date: Optional[str] = None) -> str:
    # Salt with the scan date so the synthetic context rotates week to week
    # instead of being frozen per ticker.
    h = deterministic_hash(ticker, "context" + (date or ""))
    positive_contexts = [
        "Strong earnings beat with raised guidance.",
        "Announced dividend increase and buyback expansion.",
        "Positive momentum, bullish sentiment.",
        "Strong momentum on high volume.",
    ]
    negative_contexts = [
        "Missed earnings expectations, guidance cut.",
        "Regulatory headwinds creating uncertainty.",
        "Negative sentiment, selling pressure.",
        "Under pressure, breaking support.",
    ]
    neutral_contexts = [
        "Trading in line with sector.",
        "Quiet week with no material news.",
        "Consolidating after recent moves.",
        "Awaiting next catalyst.",
    ]
    if return_val > 0.03:
        return positive_contexts[h % len(positive_contexts)]
    if return_val < -0.03:
        return negative_contexts[h % len(negative_contexts)]
    return neutral_contexts[h % len(neutral_contexts)]


def week_hash(ticker: str, date: Optional[str]) -> int:
    """Deterministic per-week hash used as the final tie-breaker.

    Same ticker + same scan date -> same hash, but the ordering rotates
    from week to week, so tied scores never resolve alphabetically.
    """
    return deterministic_hash(ticker, "wk" + (date or "")) % 1000


def parse_vix(value) -> Optional[float]:
    """VIX arrives as a string in the market context; parse defensively."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def dynamic_confidence(score: float, rank: int, next_score: Optional[float], vix: Optional[float]) -> int:
    """Convert a raw engine score into a calibrated confidence (5-95).

    - Rank penalty: each subsequent pick carries less conviction.
    - Margin bonus: reward clear separation from the runner-up.
    - VIX penalty: high-vol regimes discount everyone's conviction.
    Hard-capped at 95 — no engine is ever 100% confident.

    NOTE: retained for backward compatibility (Cecil). Bucketed scores
    saturate against the 95 cap (the 2026-07-27 flat-95 incident); engines
    with continuous scores should use pick_confidence() instead.
    """
    margin = 0.0
    if next_score is not None and score > next_score:
        margin = min(5.0, (score - next_score) * 0.25)
    vix_penalty = 0.0
    if vix is not None:
        if vix >= 30:
            vix_penalty = 15.0
        elif vix >= 25:
            vix_penalty = 10.0
        elif vix >= 20:
            vix_penalty = 5.0
    conf = score - (rank * 5.0) + margin - vix_penalty
    return int(max(5, min(95, round(conf))))


def vix_confidence_penalty(vix: Optional[float]) -> float:
    """High-vol regimes discount everyone's conviction."""
    if vix is None:
        return 0.0
    if vix >= 30:
        return 15.0
    if vix >= 25:
        return 10.0
    if vix >= 20:
        return 5.0
    return 0.0


def vix_complacency_penalty(vix: Optional[float]) -> float:
    """VIX < 16 = complacency regime (Marky's journal rule, previously
    unencoded): a low-vol tape breeds overconfidence, so tax it."""
    if vix is None:
        return 0.0
    if vix < 16.0:
        return 5.0
    return 0.0


# Closed weekly portfolios (one YAML per week, positions carry sponsor:
# and pnl_pct:). Used for per-persona hit-rate confidence calibration.
PORTFOLIO_HISTORY_DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "StockApp", "portfolio", "history",
))


def persona_hit_rate(persona: str, history_dir: Optional[str] = None) -> Optional[float]:
    """Trailing realized hit rate for a persona from portfolio history.

    hit rate = fraction of the persona's CLOSED positions with pnl_pct > 0,
    across every weekly YAML in history_dir. Returns None when history is
    missing/unparseable or the persona has no closed positions -- the caller
    treats None as neutral (multiplier 1.0).
    """
    if yaml is None:
        return None
    directory = history_dir or PORTFOLIO_HISTORY_DIR
    try:
        files = sorted(glob.glob(os.path.join(directory, "*.yaml")))
    except Exception:
        return None
    wins = 0
    total = 0
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                doc = yaml.safe_load(f)
        except Exception:
            continue  # one bad week must not poison the calibration
        if not isinstance(doc, dict):
            continue
        for pos in doc.get("positions") or []:
            if not isinstance(pos, dict):
                continue
            if str(pos.get("sponsor", "")).strip().lower() != persona.strip().lower():
                continue
            if pos.get("status") != "closed":
                continue
            pnl = pos.get("pnl_pct")
            if pnl is None:
                continue
            try:
                pnl = float(pnl)
            except (TypeError, ValueError):
                continue
            total += 1
            if pnl > 0:
                wins += 1
    if total == 0:
        return None
    return wins / total


def hit_rate_multiplier(hit_rate: Optional[float]) -> float:
    """Map a trailing hit rate to a confidence multiplier, clamped to
    [0.8, 1.2]. None (no usable history) is neutral."""
    if hit_rate is None:
        return 1.0
    return clamp(0.8 + 0.4 * hit_rate, 0.8, 1.2)


def pick_confidence(
    strength: float,
    rank: int,
    vix: Optional[float],
    margin: float = 0.0,
    persona: Optional[str] = None,
    history_dir: Optional[str] = None,
):
    """Pick-level confidence (Fix 3, 2026-08-01).

    Confidence is a continuous function of the pick's OWN signal inputs —
    the caller condenses those inputs into `strength` (0..1) from pick-level
    data (momentum strength, distance from MA, realized volatility, sector
    flow, etc.). It is never a constant and never a bucketed score saturating
    against the cap.

    Additive kwargs (backward compatible):
      - persona / history_dir: scale confidence by the persona's trailing
        realized hit rate from closed portfolio history
        (multiplier 0.8 + 0.4 * hit_rate, clamped to [0.8, 1.2]; missing or
        unparseable history is neutral 1.0).

    Returns (raw, published):
      - raw: the pre-cap, pre-round value. Always log it alongside the
        published value so future flatness is diagnosable.
      - published: clamped to 5..97 at 0.1 granularity. The 97 ceiling keeps
        "no engine is ever 100% confident" while leaving headroom so a
        strong pick does not collide with the cap.
    """
    raw = (
        35.0
        + 55.0 * clamp(strength, 0.0, 1.0)
        + margin
        - (rank * 3.0)
        - vix_confidence_penalty(vix)
        - vix_complacency_penalty(vix)
    )
    if persona:
        raw *= hit_rate_multiplier(persona_hit_rate(persona, history_dir))
    published = round(clamp(raw, 5.0, 97.0), 1)
    return raw, published


def avg_dollar_volume(history: List[PriceHistory]) -> Optional[float]:
    """Mean weekly dollar volume over the given history; None if no volume data."""
    dollars = [h.close * h.volume for h in history if getattr(h, "volume", 0.0)]
    if not dollars:
        return None
    return sum(dollars) / len(dollars)


def log_ties(sorted_scores: List[dict], agent_name: str, watchlist: set, mentions: Dict[str, int]) -> List[str]:
    """Inspect adjacent equal-score pairs and name the documented rule that
    separated them. Tie-break order (Fix 4): (a) synthesis.md watchlist,
    (b) any sector wiki mention, (c) liquidity (avg dollar volume),
    (d) alphabetical. Arbitrary/dict-order selection is prohibited.
    """
    logs = []
    for i in range(len(sorted_scores) - 1):
        a, b = sorted_scores[i], sorted_scores[i + 1]
        if abs(a["score"] - b["score"]) > 1e-6:
            continue
        if (a["ticker"] in watchlist) != (b["ticker"] in watchlist):
            rule = "synthesis-watchlist"
        elif mentions.get(a["ticker"], 0) != mentions.get(b["ticker"], 0):
            rule = "wiki-mentions"
        elif (a.get("avg_dollar_volume") or 0.0) != (b.get("avg_dollar_volume") or 0.0):
            rule = "liquidity"
        else:
            rule = "alphabetical"
        logs.append(
            f"[tiebreak] {agent_name}: {a['ticker']} over {b['ticker']} "
            f"(score {a['score']:.4f}) via {rule}"
        )
    return logs


# ============================================================================
# Math helpers
# ============================================================================

def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp value into [lo, hi]."""
    return max(lo, min(hi, value))


def compute_simple_ma(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def compute_std_dev(values: List[float]) -> Optional[float]:
    """Population std-dev of values; None when history is insufficient (<2)."""
    if len(values) < 2:
        return None
    ma = compute_simple_ma(values)
    variance = sum((v - ma) ** 2 for v in values) / len(values)
    return variance ** 0.5


def compute_4_week_return(history: List[PriceHistory]) -> float:
    if len(history) < 2:
        return 0.0
    oldest = history[0].close
    latest = history[-1].close
    return (latest - oldest) / oldest if oldest else 0.0


# ============================================================================
# Price history lookups
# ============================================================================

def get_price_history(
    ticker: str,
    end_date: str,
    weeks: int,
    price_cache: Optional[Dict[str, List[PriceHistory]]] = None,
) -> List[PriceHistory]:
    target = resolve_ticker_alias(ticker)
    if price_cache is not None:
        data = price_cache.get(target, [])
        # Fix (2026-08-10): the live cache is keyed by the real ticker
        # ("SPY"), but resolve_ticker_alias maps SPY -> "S&P 500" (a
        # STATIC_MARKET_HISTORY key). An empty alias hit must fall back to
        # the raw ticker or every SPY lookup silently returns [] -- which
        # flattened Ophelia's regime term and zeroed her vol ratios.
        if not data and target != ticker:
            data = price_cache.get(ticker, [])
        filtered = [entry for entry in data if entry.date <= end_date]
        return filtered[-weeks:] if len(filtered) >= weeks else filtered

    # Use module-level STATIC_MARKET_HISTORY
    ticker_data = STATIC_MARKET_HISTORY.get(target)
    if not ticker_data:
        return []

    entries = []
    for date, price in ticker_data.items():
        if date <= end_date:
            open_p = price.get("open", 0.0)
            close = price.get("close", 0.0)
            ret = (close - open_p) / open_p if open_p else 0.0
            entries.append(PriceHistory(date=date, open_price=open_p, close_price=close))
    entries.sort(key=lambda x: x.date)
    return entries[-weeks:]


def get_weekly_return(
    ticker: str,
    date: str,
    price_cache: Optional[Dict[str, List[PriceHistory]]] = None,
) -> Optional[float]:
    target = resolve_ticker_alias(ticker)
    if price_cache is not None:
        data = price_cache.get(target, [])
        for entry in data:
            if entry.date == date:
                return entry.return_
        # Weekly bars are labeled by their last trading day (usually Friday),
        # so an exact calendar-date match usually misses. Fall back to the
        # most recent weekly bar on or before the requested date.
        eligible = [e for e in data if e.date <= date]
        if eligible:
            return eligible[-1].return_
        return None

    # Use module-level STATIC_MARKET_HISTORY
    ticker_data = STATIC_MARKET_HISTORY.get(target)
    if not ticker_data:
        return None
    price = ticker_data.get(date)
    if not price:
        eligible_dates = [d for d in ticker_data.keys() if d <= date]
        if not eligible_dates:
            return None
        price = ticker_data[max(eligible_dates)]
    open_p = price.get("open", 0.0)
    close = price.get("close", 0.0)
    if open_p == 0:
        return None
    return (close - open_p) / open_p
