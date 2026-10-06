# snapshot_macro.py -- non-equity instrument snapshot for the weekly scan.
#
# Exposes fetch_special_instruments(friday_date) returning the rates / vol /
# commodities / fx blocks of data/weekly/<date>.json (DATA_FEED.md section 1),
# plus a mandatory "missing" list and a "provenance" block naming any
# instrument that did not come from Yahoo, the contract month of each
# commodity, and any value that is not the session the file is named for.
# Closes only; volume is kept when the feed reports a real one and
# normalized to None otherwise (never invented).
#
# Fetch discipline follows truth_layer/sweep/scripts/arena_ingest.py fetch_bar:
# explicit start/end window around the Friday, select that date's bar. No
# period='1d' blind fetches. A date with no bar gets an earlier session's
# only when the provider shows it skipped that date, and the stand-in's own
# date is committed with it; a bar the exchange has not settled is not read
# at all. Both rules are under "The Yahoo path" below.
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
# WTI   -> NAMED     DECISION 2026-10-05, superseding CL=F, GC=F and SI=F:
# GOLD  -> NAMED     the nearest-expiry contract, read under its own symbol
# SILVER-> NAMED     (CLX26.NYM, GCV26.CMX, SIV26.CMX), and the contract
#                    committed beside the close. What the continuous symbols
#                    did, and the rules, are under "Named contracts" below.
#                    Through 2026-10-02 these keys held the continuous
#                    symbols' bars: 2026-08-07 CL=F 78.18 (volume 241222),
#                    GC=F 4340.70, SI=F 63.332, volume real and kept.
# WTI_NEXT -> NAMED  The contract after WTI's, settled the same day. It is
#                    there so that a one-week change can be measured on one
#                    contract in the week the front month changes.
#
# Sanity notes from the smoke run (2026-08-07): GOLD 4340.70 and SILVER
# 63.33 sit above the briefing ranges (3000-3500 / 30-45); both are genuine
# live closes (2025-08-08: GC=F 3439.10, SI=F 38.42 -- a sustained rally,
# not a fetch artifact). All other instruments landed inside their ranges.
#
# CL=F, GC=F and SI=F are CONTINUOUS symbols, and Yahoo does not hold them
# still. Probed 2026-10-05 against yfinance 1.6.0, while auditing every
# committed close (scripts/audit_instruments.py, macro/instrument_audit.json):
#   GC=F  The history was the nearest-expiry contract when the panel was
#         backfilled on 2026-08-12 (median committed volume 491 contracts)
#         and is the active contract now (median 185,701), restated for the
#         whole window. 107 of the 113 committed weeks are no longer Yahoo's
#         GC=F close: always lower, by the carry between the two months, as
#         much as 59.00 or 1.7 percent. From 2026-07-31 on, today's GC=F
#         rows are GCZ26.CMX's, close and volume, row for row.
#   SI=F  The history is still the nearest-expiry chain, but the live quote
#         is the active contract (Dec 26). An evening read and the settled
#         history are different contract months, 0.2 to 0.8 apart.
#   CL=F  The live quote rolls to the next month before the history does.
#         2026-09-18: the quote was CLX26 (Nov), the history is CLV26 (Oct,
#         which expired 09-22). That is the 95.47 against 100.30 of #110.
# Nothing in a file written through 2026-10-02 says which contract month a
# close belongs to, and the volume beside it is not a tell either: on a
# contract's last day the continuous bar is the expiring month's close on
# the next month's volume (CL=F 2026-09-22: 94.59 on 422,683, which is
# CLX26's volume). Since 2026-10-05 the contract is named; see "Named
# contracts" below for the rule and what it rests on.

import calendar
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
    from scan_pipeline.snapshot import PROVIDER, TREASURY_SOURCE
except ImportError:  # same-dir import when repo root is not on sys.path
    from snapshot import PROVIDER, TREASURY_SOURCE

# The bar of an instrument that trades past the US cash close is a live
# quote until the provider loads the exchange settlement. See "The Yahoo
# path" for what that has cost and why the hour is 13.
NEXT_DAY = "next_day"
SETTLED_HOUR_UTC = 13

# ---------------------------------------------------------------------------
# Provider map: instrument -> yahoo symbol -> normalization. One place to
# touch on a provider swap. An entry with no "provider" is a Yahoo symbol;
# US2Y is the single one that is not (see the research log). "settles" marks
# a bar that is not final on the evening of its own session.
#
# A commodity has no fixed symbol. "root" names the futures product, and the
# symbol is the contract the roll calendar gives for the session ("Named
# contracts" below); "position" 1 is the contract after that one.
# "continuous" is the provider's rolling symbol, which the writer no longer
# reads: it is what every file through 2026-10-02 holds, so the audit and
# the history backfill still need its name.
# ---------------------------------------------------------------------------
INSTRUMENTS = {
    "rates": {
        "US10Y":    {"symbol": "^TNX",  "divisor": 1.0, "kind": "yield"},
        "US2Y":     {"provider": TREASURY_SOURCE, "column": "2 Yr",
                     "kind": "yield"},
        "US2Y_FUT": {"symbol": "2YY=F", "divisor": 1.0, "kind": "yield",
                     "settles": NEXT_DAY},
    },
    "vol": {
        "VIX": {"symbol": "^VIX", "divisor": 1.0, "kind": "index"},
    },
    "commodities": {
        "WTI":      {"root": "CL", "position": 0, "continuous": "CL=F",
                     "divisor": 1.0, "kind": "future", "settles": NEXT_DAY},
        "WTI_NEXT": {"root": "CL", "position": 1,
                     "divisor": 1.0, "kind": "future", "settles": NEXT_DAY},
        "GOLD":     {"root": "GC", "position": 0, "continuous": "GC=F",
                     "divisor": 1.0, "kind": "future", "settles": NEXT_DAY},
        "SILVER":   {"root": "SI", "position": 0, "continuous": "SI=F",
                     "divisor": 1.0, "kind": "future", "settles": NEXT_DAY},
    },
    "fx": {
        "DXY": {"symbol": "DX-Y.NYB", "divisor": 1.0, "kind": "index",
                "settles": NEXT_DAY},
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


# ---------------------------------------------------------------------------
# Named contracts (WTI, WTI_NEXT, GOLD, SILVER)
# ---------------------------------------------------------------------------
# A continuous symbol is the provider's choice of which contract month to
# show, and the provider has changed it without saying so. Probed 2026-10-05:
#
#  * GC=F was the nearest-expiry contract when the panel was backfilled and
#    is the most active one now, for its whole history, 0 to 1.7 percent
#    higher. Its roll day is not constant either: on the first-notice-day
#    Fridays 2024-11-29, 2025-01-31 and 2025-05-30 it holds the outgoing
#    month's close, and on the four since, the incoming month's.
#  * Reading after the settlement does not help. 2026-08-28.json was read at
#    14:10 UTC on the Saturday, an hour past the rule below, and got the
#    December contract for gold and for silver, where every other Saturday
#    read on file got the nearest one.
#  * The individual contracts do not move. GCV26.CMX is the October 2026
#    gold contract on every request, with history back to its listing.
#
# So the feed names the contract (owner decision 2026-10-05), and the rule
# is the one 327 of the panel's 339 committed closes already follow:
#
#    the listed contract with the earliest last trade date on or after the
#    session.
#
# For WTI that is the front month, as EIA defined its "Contract 1". For gold
# and silver it is the COMEX spot month: thinly traded, but the exchange
# settles every listed month off the curve, and the spot month sits within
# days of carry of spot metal. Checked on the 91 committed gold weeks that
# are ten days or more from the active month's first notice day: the gap to
# the active contract implies a carry of 3.3 to 5.9 percent a year, in step
# with short rates, including the weeks that traded 2, 12 and 16 contracts.
# A stale last trade would scatter. The active month was the alternative and
# was not chosen: it steps 0.8 to 1.7 percent at each of five rolls a year,
# the panel's history is not on it, and for silver the provider has no
# history on it at all.
#
# Last trade dates are the exchange rulebook's:
#
#    CL       the third business day before the 25th of the month before the
#             contract month; before the business day preceding the 25th,
#             when the 25th is not one.
#    GC, SI   the third last business day of the contract month.
#
# The calendar reproduces what the provider's chains did. All 32 crude
# expiries from CLH24 to CLV26 show in CL=F's volume (it collapses for two
# sessions, then the last day's bar carries the next month's volume), and by
# name: CLQ26.NYM's last bar is 2026-07-21, CL=F becomes CLX26 on 2026-09-23
# and SI=F becomes SIV26 on 2026-09-29.
#
# A business day is a day the exchange settles, so the table below is the
# exchange's holidays and not the bond market's: Columbus Day and Veterans
# Day are ordinary sessions. One entry is a judgment: New Year's Day on a
# Saturday is not observed on the Friday (the equity exchanges' rule; next
# in 2028). If the table is ever a day out the file is still right about
# itself, because the contract that was read is the one it names.
#
# Three consequences, each deliberate:
#
#  * An expired contract cannot be read. The provider drops a contract
#    within days of its last trade (GCU26, SIU26 and CLV26 were gone by
#    2026-10-05). A rewrite of an old week therefore lists its commodities
#    in "missing"; their settlements live in data/commodity_settlements.json
#    (DATA_FEED.md sec.1d), which scripts/backfill_commodities.py fills.
#  * A Friday that IS a last trade date is read on the Saturday, after the
#    contract has expired. If the provider has already dropped it, the
#    instrument is "missing" that week and is filled the same way. The first
#    such Friday is 2026-11-20 (CLZ26).
#  * A holiday stand-in stays inside one contract. If the week's last
#    session belongs to another month than the date asked for, nothing
#    stands in.

MONTH_CODES = "FGHJKMNQUVXZ"            # January .. December

# root -> the provider's exchange suffix, and how the contract expires.
CONTRACT_ROOTS = {
    "CL": {"exchange": "NYMEX", "suffix": "NYM", "expires": "before_25th"},
    "GC": {"exchange": "COMEX", "suffix": "CMX", "expires": "third_last"},
    "SI": {"exchange": "COMEX", "suffix": "CMX", "expires": "third_last"},
}

_HOLIDAYS = {}      # year -> frozenset of dates, for the life of the process


def _easter(year):
    """Gregorian Easter Sunday (the anonymous algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    g = (b - (b + 8) // 25 + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    month, day = divmod(h + m - 7 * n + 114, 31)
    return dt.date(year, month, day + 1)


def _nth_weekday(year, month, weekday, n):
    first = dt.date(year, month, 1)
    first += dt.timedelta(days=(weekday - first.weekday()) % 7)
    return first + dt.timedelta(weeks=n - 1)


def _last_weekday(year, month, weekday):
    last = dt.date(year, month, calendar.monthrange(year, month)[1])
    return last - dt.timedelta(days=(last.weekday() - weekday) % 7)


def _observed(day, saturday_moves=True):
    """The weekday a fixed-date holiday is kept on, or None."""
    if day.weekday() == 5:
        return day - dt.timedelta(days=1) if saturday_moves else None
    if day.weekday() == 6:
        return day + dt.timedelta(days=1)
    return day


def exchange_holidays(year):
    """The days NYMEX and COMEX do not settle in `year`."""
    if year not in _HOLIDAYS:
        days = {
            _observed(dt.date(year, 1, 1), saturday_moves=False),
            _nth_weekday(year, 1, 0, 3),                # Martin Luther King
            _nth_weekday(year, 2, 0, 3),                # Presidents' Day
            _easter(year) - dt.timedelta(days=2),       # Good Friday
            _last_weekday(year, 5, 0),                  # Memorial Day
            _observed(dt.date(year, 7, 4)),
            _nth_weekday(year, 9, 0, 1),                # Labor Day
            _nth_weekday(year, 11, 3, 4),               # Thanksgiving
            _observed(dt.date(year, 12, 25)),
        }
        if year >= 2022:
            days.add(_observed(dt.date(year, 6, 19)))   # Juneteenth
        days.discard(None)
        _HOLIDAYS[year] = frozenset(days)
    return _HOLIDAYS[year]


def is_business_day(day):
    return day.weekday() < 5 and day not in exchange_holidays(day.year)


def _business_days_before(day, n):
    """The n-th business day strictly before `day`."""
    while n:
        day -= dt.timedelta(days=1)
        if is_business_day(day):
            n -= 1
    return day


def last_trade_date(root, year, month):
    """The last trade date of one contract month. Pure."""
    if CONTRACT_ROOTS[root]["expires"] == "before_25th":
        prior = dt.date(year, month, 1) - dt.timedelta(days=1)
        anchor = dt.date(prior.year, prior.month, 25)
        if not is_business_day(anchor):
            anchor = _business_days_before(anchor, 1)
        return _business_days_before(anchor, 3)
    after = (dt.date(year, month, 28) + dt.timedelta(days=4)).replace(day=1)
    return _business_days_before(after, 3)


def contract_code(root, year, month):
    """("CL", 2026, 11) -> "CLX26", the exchange's own name for it."""
    return "%s%s%02d" % (root, MONTH_CODES[month - 1], year % 100)


def contract_parts(code):
    """"CLX26" -> ("CL", 2026, 11). Raises ValueError on anything else."""
    root, letter, year = code[:-3], code[-3:-2], code[-2:]
    if (root not in CONTRACT_ROOTS or letter not in MONTH_CODES
            or len(letter) != 1 or not year.isdigit()):
        raise ValueError("not a contract this feed names: %r" % (code,))
    return root, 2000 + int(year), MONTH_CODES.index(letter) + 1


def contract_symbol(code):
    """"CLX26" -> "CLX26.NYM", the provider's symbol for that contract."""
    return "%s.%s" % (code, CONTRACT_ROOTS[contract_parts(code)[0]]["suffix"])


def contract_for(root, session, position=0):
    """The contract that answers for `session`: the one with the earliest
    last trade date on or after it, or the one `position` months later.
    Every calendar month is listed for all three roots. Pure."""
    year, month = session.year, session.month
    while last_trade_date(root, year, month) < session:
        year, month = (year, month + 1) if month < 12 else (year + 1, 1)
    month += position
    year, month = year + (month - 1) // 12, (month - 1) % 12 + 1
    return contract_code(root, year, month)


def resolved(cfg, session):
    """(cfg with a "symbol", contract code or None) for one session.

    An instrument with a fixed symbol comes back as it is. A commodity gets
    the symbol of the contract the calendar gives for the session."""
    if "root" not in cfg:
        return cfg, None
    code = contract_for(cfg["root"], session, cfg.get("position", 0))
    return dict(cfg, symbol=contract_symbol(code)), code


# ---------------------------------------------------------------------------
# The Yahoo path (every instrument but US2Y)
# ---------------------------------------------------------------------------
# The same three rules the Treasury path follows, for the same reason: what
# is committed cannot be edited afterwards.
#
#  * The bar dated as_of is the observation, and a missing bar is NOT
#    evidence of a holiday. 2026-08-28.json was fetched on the Saturday at
#    14:10 UTC. Yahoo had no Friday bar for any of its three index symbols
#    by then (or had a copy of Thursday's; the file cannot say which), and
#    "the last bar on or before Friday" put Thursday's 10-year, VIX and
#    dollar index under Friday's date. No bar dated as_of and none after it:
#    "missing", with the reason.
#  * A stand-in needs proof, and is written down. A bar dated AFTER as_of
#    shows the instrument skipped as_of -- Good Friday, or July 4th, when
#    the futures print a short session and the Cboe indices print nothing
#    -- and the last bar of the same Mon..Fri week stands in. Its date goes
#    out as "observed" and is committed in provenance.<block>.<ticker>.
#    Through 2026-10-02 it went out as a "note" the writer dropped, so the
#    28 stand-ins in the five holiday files are unmarked. On the night
#    itself the proof does not exist yet, so a holiday Friday's instruments
#    are "missing" from a live run and filled by a later full rewrite.
#  * A bar the exchange has not settled is not a close. The instruments
#    marked "settles" trade past the cash close, and until Yahoo loads the
#    settlement the bar dated as_of is a quote: the last trade (for a
#    continuous symbol, of whichever contract month is most active), and on
#    a weekday evening the first trades of the NEXT session. Through
#    2026-10-02 the commodities were read as continuous symbols. Read on the
#    evening of the session, WTI,
#    gold, silver and the dollar index were wrong in all 11 files that tried
#    (three weekly, eight daily) and the 2-year future in 10. WTI for
#    2026-09-18 went in at 95.47 against a settled 100.30 (#110); the daily
#    file for 2026-09-22 holds 89.63 against 94.59, on a volume of 1,643.
#    Read from 13:07 UTC the next day onward, WTI was right in five files of
#    five. So they are not read before 13:00 UTC on the day after as_of;
#    earlier they are "missing". That hour is where the evidence starts, not
#    a measured boundary: the latest read that failed was at 02:58 UTC. Nor
#    did it settle which contract month a continuous symbol's bar was (SI=F
#    at 14:10 UTC on 2026-08-29 was the active contract's settlement, and
#    the history has since become the front month's); naming the contract
#    is what settles that. The Cboe indices, ^TNX and ^VIX, are final by
#    evening and were right in all 11.
#
# The window opens on the week's Monday because nothing earlier can be used,
# and because one that opens on the Sunday US clocks go forward returns no
# rows at all for ^VIX: Friday minus five days is that Sunday once a year,
# which is how VIX went missing from 2025-03-14 and 2026-03-13. It runs
# eight days past as_of so that a later bar, where one exists, is in it.

def settled_at(as_of):
    """The first moment the bar dated as_of may be read for an instrument
    that settles the next day. An aware UTC datetime."""
    return dt.datetime.combine(as_of + dt.timedelta(days=1),
                               dt.time(SETTLED_HOUR_UTC),
                               tzinfo=dt.timezone.utc)


def normalize_bar(close, volume, cfg):
    """One provider bar as the feed commits it: (close, volume).

    The divisor, the legacy x10 yield guard, 4 dp, and a zero or absent
    volume as None. scripts/audit_instruments.py goes through this too, so
    it compares a committed close with the number this writer would write."""
    close = float(close) / cfg.get("divisor", 1.0)
    if cfg.get("kind") == "yield" and close > LEGACY_X10_GUARD:
        close = close / 10.0  # legacy x10 feed guard, see research log
    vol = None
    try:
        if volume is not None and volume == volume and int(volume) > 0:
            vol = int(volume)                               # NaN/0 -> None
    except (TypeError, ValueError):
        vol = None
    return round(close, 4), vol


def select_bar(days, as_of, cfg, now):
    """Pick the session that answers for as_of. Pure: no network, no clock.

    days is the set of dates the provider returned a bar for; now is an
    aware UTC datetime. Returns (observed_date, error_str) under the rules
    above."""
    symbol = cfg["symbol"]
    if as_of in days:
        if cfg.get("settles") == NEXT_DAY and now < settled_at(as_of):
            return None, (
                "%s: the bar dated %s is a quote until the exchange "
                "settlement is loaded, and is not read before %s (now %s)"
                % (symbol, as_of.isoformat(),
                   settled_at(as_of).strftime("%Y-%m-%dT%H:%MZ"),
                   now.strftime("%Y-%m-%dT%H:%MZ")))
        return as_of, None
    if not any(d > as_of for d in days):
        return None, (
            "%s: no bar dated %s, and none after it yet; a holiday cannot "
            "be told from a late post, so no earlier session is substituted"
            % (symbol, as_of.isoformat()))
    monday = as_of - dt.timedelta(days=as_of.weekday())
    earlier = [d for d in days if monday <= d < as_of]
    if not earlier:
        return None, ("%s: nothing printed on %s and its week has no "
                      "earlier bar to stand in"
                      % (symbol, as_of.isoformat()))
    return max(earlier), None


def history(symbol, start, end):
    """{date: row} of one symbol's bars in [start, end), ISO dates.

    Raises on a failed fetch. An empty dict means the provider answered and
    has nothing: a window with no sessions, or a contract it has dropped.
    scripts/backfill_commodities.py reads through this too, so a history
    entry and a weekly file see the provider the same way."""
    hist = yf.Ticker(symbol).history(start=start, end=end)
    bars = {}
    if hist is None or hist.empty:
        return bars
    for idx, row in hist.iterrows():
        close = row["Close"]
        if close is None or close != close:     # a NaN bar is not a bar
            continue
        bars[idx.date()] = row
    return bars


def _fetch_one(ticker, cfg, friday):
    """Fetch one instrument's bar for `friday`, which is any session date:
    the daily feed passes its own. Returns (entry_dict, error_str).

    entry is {"close", "volume"}; for a commodity also "contract", the
    contract month the bar belongs to; and when the value is a stand-in from
    an earlier session of the same week, "observed" (that session's date)
    and a "note" saying so in words."""
    cfg, contract = resolved(cfg, friday)
    symbol = cfg["symbol"]
    monday = friday - dt.timedelta(days=friday.weekday())
    start = monday.isoformat()
    end = (friday + dt.timedelta(days=8)).isoformat()
    try:
        bars = history(symbol, start, end)
    except Exception as exc:  # network/parse failure: never kill the batch
        return None, "%s: %s" % (type(exc).__name__, str(exc)[:160])
    if not bars:
        if contract is None:
            return None, "no data returned for window %s..%s" % (start, end)
        # Name the contract, so the gap can be filled, and say so when the
        # reason is the usual one: it has expired and is no longer served.
        last = last_trade_date(*contract_parts(contract))
        gone = ("; its last trade date is %s, and the provider drops a "
                "contract once it has expired" % last.isoformat()
                if last < _utcnow().date() else "")
        return None, ("no data returned for %s in window %s..%s%s"
                      % (symbol, start, end, gone))

    observed, err = select_bar(set(bars), friday, cfg, _utcnow())
    if err is not None:
        return None, err
    if contract is not None and observed != friday:
        there = contract_for(cfg["root"], observed, cfg.get("position", 0))
        if there != contract:
            return None, (
                "%s printed nothing on %s, and the last session of that "
                "week, %s, belongs to %s; one contract month does not "
                "stand in for another"
                % (symbol, friday.isoformat(), observed.isoformat(), there))

    row = bars[observed]
    close, volume = normalize_bar(row["Close"], row.get("Volume"), cfg)
    entry = {"close": close, "volume": volume}
    if contract is not None:
        entry["contract"] = contract
    if observed != friday:
        entry["observed"] = observed.isoformat()
        entry["note"] = ("%s printed nothing on %s; used %s, the last bar "
                         "of that week" % (symbol, friday.isoformat(),
                                           observed.isoformat()))
    return entry, None


def fetch_special_instruments(friday_date: str) -> dict:
    """Fetch rates/vol/commodities/fx closes for a given Friday (YYYY-MM-DD).

    Returns {"rates": {...}, "vol": {...}, "commodities": {...}, "fx": {...},
    "missing": [{"ticker": ..., "reason": ...}], "provenance": {...}}. Each
    instrument entry is {"close": float, "volume": int|None} plus an optional
    "note" when an earlier session of the week stands in for a skipped one.
    Failures land in "missing", never silently -- a bar that is not settled
    yet is one of them -- and one instrument never stands in for another: no
    Treasury row means no US2Y, whatever US2Y_FUT printed, and no bar for
    the named contract means no WTI, whatever CL=F shows.

    "provenance" is {block: {ticker: {"source", "fetched_at"[, "contract"]
    [, "observed"]}}} and names three kinds of instrument: one that did not
    come from Yahoo (US2Y alone); a commodity, where "contract" is the
    contract month the close belongs to; and one whose value is a stand-in,
    where "observed" is the session it was actually published for. Any
    other instrument that came from Yahoo for the date asked has no entry.
    snapshot.write_weekly commits the block; the file-level source stays
    "yahoo".
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
                if err is None and (entry.get("observed")
                                    or entry.get("contract")):
                    prov = {"source": PROVIDER,
                            "fetched_at": _utcnow().strftime(
                                "%Y-%m-%dT%H:%M:%SZ")}
                    for key in ("contract", "observed"):
                        if entry.get(key):
                            prov[key] = entry.pop(key)
            if err is not None:
                out["missing"].append({"ticker": ticker, "reason": err})
                continue
            out[block][ticker] = entry
            if prov is not None:
                out["provenance"].setdefault(block, {})[ticker] = prov
    return out
