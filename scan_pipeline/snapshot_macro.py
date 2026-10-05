# snapshot_macro.py -- non-equity instrument snapshot for the weekly scan.
#
# Exposes fetch_special_instruments(friday_date) returning the rates / vol /
# commodities / fx blocks of data/weekly/<date>.json (DATA_FEED.md section 1),
# plus a mandatory "missing" list and a "provenance" block naming any
# instrument that did not come from Yahoo. Closes only; volume is kept when
# the feed reports a real one and normalized to None otherwise (never
# invented).
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
# US2Y  -> TREASURY  DECISION 2026-10-04, superseding 2YY=F: the U.S. Treasury
#                    daily par yield curve, column "2 Yr". 2026-10-02 = 4.83,
#                    2026-09-25 = 4.81, 2026-08-07 = 4.19. Not Yahoo, because
#                    Yahoo has no cash 2-year at all: its CBOE yield indices
#                    are ^IRX (13w), ^FVX (5y), ^TNX (10y) and ^TYX (30y), and
#                    ^UST2Y, ^US2Y and US2Y=RR return nothing. Fetch rules are
#                    under "The Treasury path" below.
# US2Y_FUT -> 2YY=F  CME 2-Year Yield futures: the instrument this feed
#                    committed as "US2Y" through 2026-10-02, on the belief
#                    that it tracks the cash 2Y within a few bp. It does not,
#                    and the cause is not a basis. Nobody trades it. Probed
#                    2026-10-04: volume 0 on 51 of the 54 sessions since
#                    2026-07-20, open interest 4, last trade 2026-09-22, and
#                    O=H=L=C on every untraded day. What Yahoo serves is an
#                    exchange mark that can sit still for weeks (4.170 on 16
#                    consecutive sessions, 2026-08-07..08-28) and meets the
#                    cash yield only when the contract cash-settles on the
#                    last business day of the month:
#                      2026-09-29  4.548   Treasury 4.89   -34 bp
#                      2026-09-30  4.885   Treasury 4.88   +0.5 bp  settles
#                      2026-10-01  4.610   Treasury 4.78   -17 bp   next month
#                    Over the 113 committed weeks it is more than 10 bp from
#                    the Treasury 2Y in 24 (21 of them in 2026) and more than
#                    20 bp in 13; the worst is -36 bp on 2026-09-18. ^TNX,
#                    for scale, is within 2 bp of the Treasury 10Y in 108.
#                    Kept under a name that says what it is, so the series
#                    the panel already holds does not simply stop. It is
#                    NEVER a stand-in for US2Y: a failed Treasury fetch puts
#                    US2Y in "missing". Volume ~0 -> None.
#                    The two candidates rejected in August stay rejected:
#                      ^IRX  2026-08-07 = 3.71 -- 13-week T-bill, a DIFFERENT
#                            instrument; refused to relabel it as US2Y.
#                      ZT=F  2026-08-07 = 102.9766 -- 2Y note futures PRICE,
#                            not a yield; conversion would be invented data.
# DXY   -> DX-Y.NYB  2026-08-07 close 99.60, volume 0 -> None.
# WTI   -> CL=F      2026-08-07 close 78.18, volume 241222 (real, kept).
# GOLD  -> GC=F      2026-08-07 close 4340.70, volume real, kept.
# SILVER-> SI=F      2026-08-07 close 63.332, volume real, kept.
#
# Sanity notes from the smoke run (2026-08-07): GOLD 4340.70 and SILVER
# 63.33 sit above the briefing ranges (3000-3500 / 30-45); both are genuine
# live closes (2025-08-08: GC=F 3439.10, SI=F 38.42 -- a sustained rally,
# not a fetch artifact). All other instruments landed inside their ranges.

import csv
import datetime as dt
import io
import time
import urllib.request

try:
    import yfinance as yf
except ImportError as exc:
    raise ImportError("snapshot_macro requires yfinance") from exc

try:
    from scan_pipeline.snapshot import TREASURY_SOURCE
except ImportError:  # same-dir import when repo root is not on sys.path
    from snapshot import TREASURY_SOURCE

# ---------------------------------------------------------------------------
# Provider map: instrument -> yahoo symbol -> normalization. One place to
# touch on a provider swap. An entry with no "provider" is a Yahoo symbol;
# US2Y is the single one that is not (see the research log).
# ---------------------------------------------------------------------------
INSTRUMENTS = {
    "rates": {
        "US10Y":    {"symbol": "^TNX",  "divisor": 1.0, "kind": "yield"},
        "US2Y":     {"provider": TREASURY_SOURCE, "column": "2 Yr",
                     "kind": "yield"},
        "US2Y_FUT": {"symbol": "2YY=F", "divisor": 1.0, "kind": "yield"},
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

# ---------------------------------------------------------------------------
# The Treasury path (US2Y only)
# ---------------------------------------------------------------------------
# One CSV per calendar year, one row per business day, posted after the
# close. Three rules, each from something that has already gone wrong here:
#
#  * Columns are read BY NAME. The 2025 and 2026 files carry a "1.5 Month"
#    column the 2024 file does not, so "2 Yr" is the 9th field in one and
#    the 8th in the other.
#  * The row dated as_of is the observation, and a missing row is NOT
#    evidence of a holiday. If Treasury posts late, or a stale copy of the
#    file comes back, yesterday's row is on top, and taking "the latest row"
#    would commit Thursday's yield under Friday's date in a file nobody may
#    edit. No clock settles it either: the Friday job always runs after the
#    day has ended. The panel already holds one prior-day value that got in
#    unmarked -- 2026-08-28.json has US10Y 4.672, which is ^TNX's close for
#    the 27th (the 28th closed at 4.720). So: no row dated as_of, no value.
#    US2Y goes to "missing" with the reason.
#  * A stand-in needs proof. If the file already holds a row dated AFTER
#    as_of, Treasury skipped as_of (Good Friday, a bond-market holiday), and
#    the last row of the same Mon..Fri week stands in, with the date it was
#    published for recorded as "observed". That proof never exists on the
#    night itself, so a holiday Friday is filled afterwards, once the next
#    session's row is up: scripts/backfill_us2y.py.
TREASURY_CSV_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/"
    "interest-rates/daily-treasury-rates.csv/%(year)d/all"
    "?type=daily_treasury_yield_curve&field_tdr_date_value=%(year)d"
    "&page&_format=csv")

# Treasury holds a client that does not look like a browser for about 17 s
# before answering (measured 2026-10-04: 16-20 s over seven requests, against
# 0.1-0.4 s with a browser User-Agent). The feed says what it is and waits:
# one file a week makes that cheap, and the timeout is sized for it.
TREASURY_TIMEOUT_S = 90
TREASURY_ATTEMPTS = 2
_UA = {"User-Agent": "weekly-council-scan data feed "
                     "(+https://github.com/GrandMastaShake/weekly-council-scan)"}

_TREASURY_CACHE = {}    # year -> parsed rows, for the life of the process


def _utcnow():
    return dt.datetime.now(dt.timezone.utc)


def _http_get_text(url):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=TREASURY_TIMEOUT_S) as resp:
        return resp.read().decode("utf-8-sig")


def parse_treasury_csv(text):
    """Par yield curve CSV -> {date: {column: float}}.

    A blank or non-numeric cell is simply absent from its row: never zero,
    never carried from a neighbour. An empty body is a year with nothing
    published yet (Treasury answers 200 with zero bytes) and parses to {};
    anything else without a Date column is not this file, and raises."""
    if not text.strip():
        return {}
    reader = csv.DictReader(io.StringIO(text))
    header = [h.strip() for h in (reader.fieldnames or []) if h]
    if "Date" not in header:
        raise ValueError("not the par yield curve CSV; header begins %r"
                         % ", ".join(header)[:80])
    rows = {}
    for rec in reader:
        try:
            day = dt.datetime.strptime((rec.get("Date") or "").strip(),
                                       "%m/%d/%Y").date()
        except ValueError:
            continue
        values = {}
        for col, cell in rec.items():
            if not col or col.strip() == "Date":
                continue
            try:
                values[col.strip()] = float(cell)
            except (TypeError, ValueError):
                continue
        rows[day] = values
    return rows


def fetch_treasury_par_curve(year):
    """One year of the daily par yield curve, {date: {column: float}}.

    Raises on a failed fetch -- callers turn that into a "missing" entry.
    A failure is not cached; a success is, so a 104-week backfill costs
    three requests rather than one per Friday."""
    if year in _TREASURY_CACHE:
        return _TREASURY_CACHE[year]
    last = None
    for attempt in range(1, TREASURY_ATTEMPTS + 1):
        try:
            rows = parse_treasury_csv(
                _http_get_text(TREASURY_CSV_URL % {"year": year}))
        except Exception as exc:
            last = exc
            if attempt < TREASURY_ATTEMPTS:
                time.sleep(2 * attempt)
            continue
        _TREASURY_CACHE[year] = rows
        return rows
    raise last


def week_rows(as_of, fetch=None):
    """Every published row that could answer for as_of.

    Its own year's file is enough when the row is there. When it is not,
    the stand-in and the proof that allows one can each sit across a year
    boundary: the week's earlier rows in last year's file (Friday January
    1st), the first later row in next year's (Friday December 31st)."""
    fetch = fetch or fetch_treasury_par_curve
    rows = dict(fetch(as_of.year))
    if as_of in rows:
        return rows
    monday = as_of - dt.timedelta(days=as_of.weekday())
    if monday.year != as_of.year:
        rows.update(fetch(monday.year))
    following = (as_of + dt.timedelta(days=7)).year
    if following != as_of.year and not any(d > as_of for d in rows):
        rows.update(fetch(following))
    return rows


def select_treasury_row(rows, as_of, column):
    """Pick the Treasury observation for as_of. Pure: no network, no clock.

    rows is parse_treasury_csv output. Returns (value, observed_date,
    error_str) under the rules above."""
    row = rows.get(as_of)
    if row is not None:
        if column not in row:
            return None, None, ("treasury: the row for %s has no %r value"
                                % (as_of.isoformat(), column))
        observed = as_of
    else:
        if not any(d > as_of for d in rows):
            return None, None, (
                "treasury: no par yield curve row dated %s, and none after "
                "it yet; a holiday cannot be told from a late post, so no "
                "earlier session is substituted" % as_of.isoformat())
        monday = as_of - dt.timedelta(days=as_of.weekday())
        earlier = [d for d, r in rows.items()
                   if monday <= d < as_of and column in r]
        if not earlier:
            return None, None, ("treasury: nothing was published for %s and "
                                "its week has no earlier row to stand in"
                                % as_of.isoformat())
        observed = max(earlier)

    value = rows[observed][column]
    # A committed close cannot be edited afterwards, so a cell that parses
    # but cannot be a yield is refused here rather than written.
    if not 0.0 < value < LEGACY_X10_GUARD:
        return None, None, ("treasury: %r for %s is %r, outside any "
                            "plausible yield"
                            % (column, observed.isoformat(), value))
    return value, observed, None


def _fetch_treasury(ticker, cfg, as_of):
    """Fetch one Treasury par-curve yield for as_of.

    Returns (entry_dict, provenance_dict, error_str). Like _fetch_one it
    never raises, and it never falls back to another instrument."""
    column = cfg["column"]
    try:
        value, observed, err = select_treasury_row(week_rows(as_of), as_of,
                                                   column)
    except Exception as exc:  # network/parse failure: never kill the batch
        return None, None, "treasury: %s: %s" % (type(exc).__name__,
                                                 str(exc)[:160])
    if err is not None:
        return None, None, err

    entry = {"close": round(value, 4), "volume": None}
    prov = {"source": TREASURY_SOURCE,
            "fetched_at": _utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}
    if observed != as_of:
        entry["note"] = ("Treasury published nothing for %s; used %s, the "
                         "last row of that week"
                         % (as_of.isoformat(), observed.isoformat()))
        prov["observed"] = observed.isoformat()
    return entry, prov, None


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
    "missing": [{"ticker": ..., "reason": ...}], "provenance": {...}}. Each
    instrument entry is {"close": float, "volume": int|None} plus an optional
    "note" when a holiday forced a fallback to the prior trading day.
    Failures land in "missing", never silently, and one instrument never
    stands in for another: no Treasury row means no US2Y, whatever US2Y_FUT
    printed.

    "provenance" is {block: {ticker: {"source", "fetched_at"[, "observed"]}}}
    for the instruments that did not come from Yahoo -- today, US2Y alone.
    snapshot.write_weekly commits it; the file-level source stays "yahoo".
    """
    friday = dt.date.fromisoformat(friday_date)
    out = {block: {} for block in INSTRUMENTS}
    out["missing"] = []
    out["provenance"] = {}
    for block, instruments in INSTRUMENTS.items():
        for ticker, cfg in instruments.items():
            prov = None
            if cfg.get("provider") == TREASURY_SOURCE:
                entry, prov, err = _fetch_treasury(ticker, cfg, friday)
            else:
                entry, err = _fetch_one(ticker, cfg, friday)
            if err is not None:
                out["missing"].append({"ticker": ticker, "reason": err})
                continue
            out[block][ticker] = entry
            if prov is not None:
                out["provenance"].setdefault(block, {})[ticker] = prov
    return out
