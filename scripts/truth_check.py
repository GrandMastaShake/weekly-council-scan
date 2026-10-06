#!/usr/bin/env python3
"""truth_check.py v6 -- Truth Layer validators for weekly-council-scan.

Stdlib only (no yfinance, no pyyaml): urllib -> Yahoo chart API + regex parsing.
Runs against a LOCAL directory tree containing wiki/ and macro/ (the cron jobs
download repo files to a temp dir first, then point this script at it).

Modes:
  --staleness   Wiki freshness TTL: warn > --warn-days, fail > --fail-days.
  --facts       Verify macro/facts.json against live Yahoo closes within each
                field's tolerance_pct; verify computed spreads; check the
                file's own generated date (< 8 days old).
  --lint        Holdings linter: extract (TICKER, $price) pairs from wiki
                tables and compare against live closes (WARN >3%; FAIL >15%
                for prices >= $10, >35% for micro-cap prices < $10);
                WoW arithmetic lint on rows carrying a weekly-change column;
                column-aware YTD arithmetic lint on rows carrying a YTD
                column; weight-column sum check (any table whose weights sum
                past 100% is internally impossible).
                Skips estimate/target/market-cap rows and earnings-calendar
                sections (their $ figures are not current prices).
  --quarantine  Phantom-anomaly bans from macro/quarantine.json (ticker +
                banned value co-occurring = FAIL) plus a generic phantom-EPS
                net (EPS claim > 20% of same-row share price = FAIL).
  --counterfactuals
                Counterfactual-ledger staleness (NEW in v5, no network):
                scans shadow-book.md, rejections.md, exit-shadow.md,
                reports/*.md and scorecards/*.md for pending markers
                ('to be computed' / 'to be backfilled' / 'pending
                computation'; bare 'TBD' only counts when glued to
                counterfactual vocabulary on the same line, so future-tense
                plans like 'July TBD' are ignored). Each hit is dated from
                the nearest ISO date / 'Week of <date>' / M-D week label on
                the same or nearby lines; a marker whose week is more than
                7 days older than today was never backfilled = FAIL.
  --feed        Weekly data-feed validation (NEW in v6, no network):
                validates every data/weekly/*.json against DATA_FEED.md
                sec.1 -- required keys (as_of, source, fetched_at, session
                "close", series, missing; a missing 'missing' key is a
                FAIL -- a silently absent ticker is the failure mode this
                file exists to prevent), as_of must be a Friday, filename
                must equal as_of (a <date>.corrected.json variant must
                carry 'corrects' pointing at an existing original plus a
                'reason'), every series/special-instrument entry numeric
                close > 0 with volume null or >= 0, file pure ASCII and
                valid JSON. Absent data/weekly/ = SKIP (the feed has not
                launched yet) so the Monday gate keeps passing pre-launch.
                FAILs a file whose `series` is empty or holds no SPY bar:
                SPY is the session witness, and a weekly file written on a
                market holiday by a writer from before 2026-10-06 is
                `series: {}` with nothing to say why. Validates a weekly
                file's `session_note` (the session its bars are from, when
                that is not the Friday). FAILs when a Friday between two
                weekly files has no file -- a week the writer refused and
                nobody came back for -- and WARNs while the newest Friday
                is still owed one.
                Also validates the optional `provenance` block (per-series
                anchors, the per-instrument source that marks US2Y as the
                Treasury 2-year rather than the 2YY=F future, and the
                `observed` date of an instrument whose value is a stand-in
                from an earlier session); FAILs a file dated 2026-10-05 or
                later that carries a futures or dollar-index close read
                before 13:00 UTC the next day, which is a quote and not a
                settlement; FAILs a correction that changes an instrument's
                close without recording what it replaced in `restated` and
                labelling the replacement; and validates
                data/us2y_treasury.json, WARNs for any week that has no
                Treasury 2-year from either place, and FAILs when
                data/market_state.json shows a US2Y level that is not the
                Treasury 2-year for its week (or null where none exists),
                a null weekly change or percentile that the tree can
                supply, or was derived where data/us2y_treasury.json is
                absent.
                The same for the named commodity contracts: validates the
                `contract` label a file gives WTI, WTI_NEXT, GOLD or SILVER
                and data/commodity_settlements.json, WARNs for a week with
                no settlement on a named contract and no recorded reason,
                and FAILs when market_state.json's WTI, GOLD or SILVER is
                not what the nearest-expiry settlements derive (px, the
                contract, and each change), or was derived where
                data/commodity_settlements.json is absent.
                Also WARNs when data/daily/ has stopped being written: the
                newest daily file two or more weekdays behind the last
                weekday before today. Never a FAIL -- an observation feed
                that scores nothing must not stop a Monday; the check that
                fails is the audit step of the Daily observation workflow.
  --derive      Derivation purity check (NEW in v6): calls
                scan_pipeline.snapshot.rederive_and_compare() from the
                pipeline checkout (--pipeline) against the repo's
                data/weekly/ + macro/facts.json (+ data/us2y_treasury.json,
                found beside data/weekly/) and the committed
                data/market_state.json. Absent market_state.json = SKIP;
                pipeline import failure = WARN (the linter may run where
                the pipeline is not checked out); a False result = FAIL
                with the first-differing JSON path; a deriver exception =
                FAIL with the exception text, never a traceback crash.
  --all         Everything (default when no mode flag is given).

Exit code 1 if any FAIL, else 0. Every line is prefixed OK/WARN/FAIL/SKIP.

Usage:
  python scripts/truth_check.py --repo <dir> [--staleness] [--facts] [--lint]
         [--quarantine] [--counterfactuals] [--feed] [--derive]
         [--pipeline <dir>] [--warn-days 7] [--fail-days 14]
         [--today YYYY-MM-DD] [--max-fetch 60]
"""

import argparse
import datetime as dt
import json
import re
import sys
import urllib.request
from pathlib import Path

VERSION = "v6"

# ---------------------------------------------------------------- Yahoo fetch

_UA = {"User-Agent": "Mozilla/5.0"}
_fetch_cache = {}
_splits_cache = {}


def yahoo_close(symbol, end=None, window_days=12):
    """Latest daily close for symbol via the Yahoo chart API (date-pinned)."""
    if symbol in _fetch_cache:
        return _fetch_cache[symbol]
    d1 = end or dt.date.today() + dt.timedelta(days=1)
    d0 = d1 - dt.timedelta(days=window_days)
    p1 = int(dt.datetime(d0.year, d0.month, d0.day, tzinfo=dt.timezone.utc).timestamp())
    p2 = int(dt.datetime(d1.year, d1.month, d1.day, tzinfo=dt.timezone.utc).timestamp())
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{symbol}?period1={p1}&period2={p2}&interval=1d&events=history")
    try:
        raw = json.loads(urllib.request.urlopen(
            urllib.request.Request(url, headers=_UA), timeout=30).read())
        res = (raw.get("chart", {}).get("result") or [None])[0]
        if not res:
            _fetch_cache[symbol] = (None, None)
            return None, None
        tz_off = res.get("meta", {}).get("gmtoffset", 0)
        ts = res.get("timestamp", [])
        closes = res.get("indicators", {}).get("quote", [{}])[0].get("close", [])
        today_utc = dt.datetime.now(tz=dt.timezone.utc).date()
        for t, c in zip(reversed(ts), reversed(closes)):
            if c is not None:
                day = dt.datetime.fromtimestamp(t + tz_off, tz=dt.timezone.utc).date()
                # Skip TODAY's bar on weekdays: before the 4pm ET close it is a
                # forming bar, and comparing a Friday close against a Monday
                # overnight futures gap produces false FAILs (gold 8/24, VIX
                # 8/17). Weekend/holiday runs are unaffected -- their latest
                # bar is already the last completed session.
                if day == today_utc and today_utc.weekday() < 5:
                    continue
                _fetch_cache[symbol] = (float(c), day.isoformat())
                return _fetch_cache[symbol]
    except Exception:
        pass
    _fetch_cache[symbol] = (None, None)
    return None, None


def yahoo_close_on_or_before(symbol, date_str, window_days=14):
    """Close on the last trading day <= date_str (for WoW arithmetic)."""
    d1 = dt.date.fromisoformat(date_str) + dt.timedelta(days=1)
    d0 = d1 - dt.timedelta(days=window_days)
    p1 = int(dt.datetime(d0.year, d0.month, d0.day, tzinfo=dt.timezone.utc).timestamp())
    p2 = int(dt.datetime(d1.year, d1.month, d1.day, tzinfo=dt.timezone.utc).timestamp())
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{symbol}?period1={p1}&period2={p2}&interval=1d&events=history")
    try:
        raw = json.loads(urllib.request.urlopen(
            urllib.request.Request(url, headers=_UA), timeout=30).read())
        res = (raw.get("chart", {}).get("result") or [None])[0]
        if not res:
            return None
        closes = res.get("indicators", {}).get("quote", [{}])[0].get("close", [])
        for c in reversed(closes):
            if c is not None:
                return float(c)
    except Exception:
        pass
    return None


def yahoo_splits(symbol, start="2015-01-01"):
    """Split history via the Yahoo chart API. [(iso_date, "n:d"), ...].

    Returns None on any failure so a network problem is reported as
    "unverified", never as "no split" -- the difference matters, because
    "no split" dismisses a candidate.
    """
    if symbol in _splits_cache:
        return _splits_cache[symbol]
    d0 = dt.date.fromisoformat(start)
    d1 = dt.date.today() + dt.timedelta(days=1)
    p1 = int(dt.datetime(d0.year, d0.month, d0.day, tzinfo=dt.timezone.utc).timestamp())
    p2 = int(dt.datetime(d1.year, d1.month, d1.day, tzinfo=dt.timezone.utc).timestamp())
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{symbol}?period1={p1}&period2={p2}&interval=1d&events=split")
    try:
        raw = json.loads(urllib.request.urlopen(
            urllib.request.Request(url, headers=_UA), timeout=30).read())
        res = (raw.get("chart", {}).get("result") or [None])[0]
        if res is None:
            _splits_cache[symbol] = None
            return None
        ev = (res.get("events") or {}).get("splits") or {}
        out = sorted(
            (dt.datetime.fromtimestamp(v["date"],
                                       tz=dt.timezone.utc).date().isoformat(),
             f'{v.get("numerator")}:{v.get("denominator")}')
            for v in ev.values())
        _splits_cache[symbol] = out
        return out
    except Exception:
        _splits_cache[symbol] = None
        return None


# ------------------------------------------------------------------ reporters

class Report:
    def __init__(self):
        self.counts = {"OK": 0, "WARN": 0, "FAIL": 0, "SKIP": 0}
        self.lines = []

    def add(self, level, msg):
        self.counts[level] += 1
        self.lines.append(f"{level}: {msg}")

    def render(self):
        out = list(self.lines)
        c = self.counts
        out.append(f"SUMMARY: {c['OK']} ok, {c['WARN']} warn, "
                   f"{c['FAIL']} fail, {c['SKIP']} skip")
        return "\n".join(out)


# ------------------------------------------------------------------ staleness

LAST_UPDATED_RE = re.compile(r"Last updated[^\d]*(\d{4}-\d{2}-\d{2})")


def check_staleness(repo, today, warn_days, fail_days, rep):
    wiki = repo / "wiki"
    if not wiki.is_dir():
        rep.add("FAIL", f"staleness: {wiki} not found")
        return
    for f in sorted(wiki.glob("*.md")):
        m = LAST_UPDATED_RE.search(f.read_text(encoding="utf-8", errors="replace"))
        if not m:
            rep.add("WARN", f"staleness: {f.name} has no 'Last updated' stamp")
            continue
        age = (today - dt.date.fromisoformat(m.group(1))).days
        if age > fail_days:
            rep.add("FAIL", f"staleness: {f.name} is {age}d old "
                            f"(updated {m.group(1)}, limit {fail_days}d)")
        elif age > warn_days:
            rep.add("WARN", f"staleness: {f.name} is {age}d old "
                            f"(updated {m.group(1)}, warn at {warn_days}d)")
        else:
            rep.add("OK", f"staleness: {f.name} is {age}d old")


# ---------------------------------------------------------------------- facts

def iter_fact_fields(facts):
    for section in ("rates", "volatility", "cross_asset", "sector_etf"):
        for name, fld in (facts.get(section) or {}).items():
            yield section, name, fld


def check_facts(repo, today, rep, max_fetch):
    path = repo / "macro" / "facts.json"
    if not path.exists():
        rep.add("FAIL", "facts: macro/facts.json not found")
        return
    facts = json.loads(path.read_text(encoding="utf-8"))

    gen = facts.get("generated")
    if not gen:
        rep.add("FAIL", "facts: no 'generated' date")
    else:
        age = (today - dt.date.fromisoformat(gen)).days
        if age > 8:
            rep.add("FAIL", f"facts: facts.json is {age}d old (generated {gen}, limit 8d)")
        else:
            rep.add("OK", f"facts: facts.json generated {gen} ({age}d old)")

    fetches = 0
    for section, name, fld in iter_fact_fields(facts):
        src = fld.get("source", "")
        if fld.get("stale"):
            rep.add("SKIP", f"facts: {section}.{name} marked stale "
                            f"(as_of {fld.get('as_of')}) -- not verified")
            continue
        if not src.startswith("yahoo:"):
            continue
        if fetches >= max_fetch:
            rep.add("SKIP", f"facts: {section}.{name} (fetch cap reached)")
            continue
        fetches += 1
        symbol = src.split(":", 1)[1]
        recorded = fld.get("value") if "value" in fld else fld.get("close")
        live, live_date = yahoo_close(symbol)
        if live is None:
            rep.add("WARN", f"facts: {section}.{name} live fetch failed ({symbol})")
            continue
        tol = fld.get("tolerance_pct", 3.0)
        dev = abs(live - recorded) / recorded * 100 if recorded else float("inf")
        if dev <= tol:
            rep.add("OK", f"facts: {section}.{name} {recorded} vs live {live} "
                          f"({symbol} {live_date}, dev {dev:.2f}% <= {tol}%)")
        else:
            rep.add("FAIL", f"facts: {section}.{name} {recorded} vs live {live} "
                            f"({symbol} {live_date}, dev {dev:.2f}% > {tol}%) "
                            f"-- canonical table disagrees with market data")

    # computed spreads (arithmetic lint on the fact table itself)
    rates = facts.get("rates", {})
    def _v(n):
        f = rates.get(n) or {}
        return f.get("value")
    if _v("ust_10y") and _v("ust_3m") and _v("curve_10y_3m_bps"):
        expect = round((_v("ust_10y") - _v("ust_3m")) * 100)
        got = _v("curve_10y_3m_bps")
        if abs(expect - got) <= 3:
            rep.add("OK", f"facts: curve_10y_3m arithmetic {got} ~ {expect} bps")
        else:
            rep.add("FAIL", f"facts: curve_10y_3m says {got} bps but "
                            f"10y-3m computes to {expect} bps")


# ----------------------------------------------------------------------- lint

STOPWORDS = {
    "THE", "AND", "FOR", "WITH", "FROM", "NEW", "ALL", "NOT", "ETF", "MA",
    "PE", "CEO", "CPI", "PPI", "FOMC", "NIM", "ROE", "CRE", "CMBS", "ERBA",
    "LTV", "ATH", "AUM", "YTD", "WOW", "IG", "HY", "EM", "SA", "PT", "DA",
    "EPS", "NII", "PPA", "MW", "QoQ", "YoY", "FDIC", "OCC", "FRED", "CBOE",
    "USD", "WTI", "DXY", "VIX", "VVIX", "CDS", "IPO", "PPP", "SEC", "FDA",
    "VC",
    "CURRENT", "PRICE", "RANK", "TICKER", "NAME", "WEIGHT", "HIGH", "LOW",
    "VS", "EST", "AVG", "MAX", "MIN", "NIL", "TLT", "US", "UK", "EU", "BoJ",
    "A", "I",
}
# Lookarounds: a ticker must not be glued to letters/digits/slashes on either
# side -- kills "W/W" (WTI weekly), "P/E", "10Y" fragments, "Q3/Q4".
TICKER_RE = re.compile(r"(?<![A-Za-z0-9/])([A-Z][A-Z0-9.]{0,4})(?![A-Za-z0-9/])")
# B/M/K suffix after a $ amount = market cap / revenue / volume, not a price.
PRICE_RE = re.compile(
    r"\*\*\$([\d,]+\.\d{2})\*\*(?!\s*[BMK]\b)|\$([\d,]+\.\d{2})(?!\s*[BMK]\b)")
WOW_RE = re.compile(r"([+\-−]\s?\d+(?:\.\d+)?)\s?%")

# Sections whose $ figures are estimates/targets, never current prices.
# surprise/gauntlet/preview/whisper/implied: earnings-surveillance tables
# carry EPS estimates, surprise %s, and implied moves, not prices.
SKIP_SECTION_RE = re.compile(
    r"earnings|calendar|analyst|target|surprise|gauntlet|preview|whisper"
    r"|implied", re.I)
HEADER_RE = re.compile(r"^\s{0,3}(#{1,4})\s+(.*)$")
# Rows whose $ figure is an EPS estimate, price target, or market cap even
# outside a skippable section header.
SKIP_LINE_RE = re.compile(
    r"\bEPS\b|price target|\bPT\s|estimate|market cap", re.I)
# Phantom-EPS detector: "$X EPS" claims inside table rows (post-quarantine net).
EPS_CLAIM_RE = re.compile(r"\$([\d,]+(?:\.\d+)?)\s*(?:EPS|per share)", re.I)

# --- table-structure helpers (column-aware YTD / weight-sum lint) ------------
TABLE_SEP_RE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
TICKER_COL_RE = re.compile(r"^\s*(ticker|symbol)\s*$", re.I)
PRICE_HDR_RE = re.compile(r"\bprice\b|\bclose\b|\blast\b", re.I)
YTD_HDR_RE = re.compile(r"\bytd\b|year.to.date", re.I)
WOW_HDR_RE = re.compile(r"\bw/w\b|\bwow\b|weekly|1\s?w\b|\bweek\b", re.I)
WEIGHT_HDR_RE = re.compile(r"\bweight\b|\bwt\b|allocation", re.I)
PCT_CELL_RE = re.compile(r"([+\-−]?\s?\d+(?:\.\d+)?)\s*%")


def split_cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_pct(cell):
    m = PCT_CELL_RE.search(cell or "")
    if not m:
        return None
    try:
        return float(m.group(1).replace("−", "-").replace(" ", ""))
    except ValueError:
        return None


def extract_price_rows(text):
    """Yield (ticker, price, wow_pct, ytd_pct, line_snippet) per row."""
    section = ""
    section_l2 = ""  # stickiest ## parent -- ### day headers don't reset it
    pending = None   # candidate header row, confirmed by the --- separator
    cols = None
    for line in text.splitlines():
        hm = HEADER_RE.match(line)
        if hm:
            if len(hm.group(1)) <= 2:
                section_l2 = hm.group(2)
            section = hm.group(2)
            pending = None
            cols = None
            continue
        s = line.strip()
        if not s.startswith("|"):
            pending = None
            cols = None
            continue
        if TABLE_SEP_RE.match(s):
            if pending is not None:
                cols = split_cells(pending)
            pending = None
            continue
        if cols is None:
            pending = s
            continue
        # data row inside a parsed table
        if SKIP_SECTION_RE.search(section) or \
                SKIP_SECTION_RE.search(section_l2) or \
                SKIP_LINE_RE.search(line):
            continue  # estimates / targets / caps are not current prices
        cells = split_cells(s)
        if len(cells) != len(cols):
            continue
        # Price-column authority: a table with no Price/Close/Last column is
        # a narrative table (debate rows, watchlists, event calendars) -- its
        # $ figures are levels, targets, and estimates, not current prices.
        pidx = None
        for i, h in enumerate(cols):
            if PRICE_HDR_RE.search(h):
                pidx = i
                break
        if pidx is None:
            continue
        pm = PRICE_RE.search(cells[pidx])
        if not pm:
            continue
        price = float((pm.group(1) or pm.group(2)).replace(",", ""))
        ticker = None
        # Column-1 authority: when the table's first header is "Ticker"/"Symbol",
        # that cell IS the ticker -- it may even be a STOPWORD collision (WTI).
        if TICKER_COL_RE.match(cols[0] or ""):
            cand = cells[0].replace("*", "").strip().upper()
            if re.fullmatch(r"[A-Z][A-Z0-9.]{0,4}", cand) and \
                    not cand[0].isdigit():
                ticker = cand
        if ticker is None:
            for tm in TICKER_RE.finditer(line):
                cand = tm.group(1).rstrip(".")
                if cand in STOPWORDS or len(cand) > 5 or cand[0].isdigit():
                    continue
                if any(ch.isdigit() for ch in cand) and cand not in ("CL",):
                    continue
                ticker = cand
                break
        if not ticker:
            continue
        wow = None
        ytd = None
        for i, h in enumerate(cols):
            if YTD_HDR_RE.search(h):
                ytd = parse_pct(cells[i])
            elif WOW_HDR_RE.search(h):
                wow = parse_pct(cells[i])
        if wow is None:
            wm = WOW_RE.search(line)
            if wm:
                try:
                    wow = float(wm.group(1).replace("−", "-").replace(" ", ""))
                except ValueError:
                    pass
        yield ticker, price, wow, ytd, s[:80]


def check_lint(repo, rep, max_fetch):
    wiki = repo / "wiki"
    if not wiki.is_dir():
        rep.add("FAIL", f"lint: {wiki} not found")
        return
    fetches = 0
    checked = 0
    for f in sorted(wiki.glob("*.md")):
        text = f.read_text(encoding="utf-8", errors="replace")
        for ticker, price, wow, ytd, snip in extract_price_rows(text):
            if fetches >= max_fetch:
                rep.add("SKIP", f"lint: fetch cap {max_fetch} reached; "
                                f"remaining rows unchecked")
                return
            live, live_date = yahoo_close(ticker)
            fetches += 1
            if live is None:
                continue  # not a real ticker or no data -- ignore quietly
            checked += 1
            dev = abs(live - price) / price * 100
            # Micro-caps move 20-30% in a weekend; scale the impossible-row
            # threshold so the small/mid-cap lane doesn't false-positive.
            fail_thresh = 15.0 if price >= 10 else 35.0
            if dev > fail_thresh:
                rep.add("FAIL", f"lint: {f.name} {ticker} ${price} vs live "
                                f"${live} ({live_date}, dev {dev:.1f}% > "
                                f"{fail_thresh:.0f}%) -- impossible row :: {snip}")
            elif dev > 3:
                rep.add("WARN", f"lint: {f.name} {ticker} ${price} vs live "
                                f"${live} ({live_date}, dev {dev:.1f}%) :: {snip}")
            if wow is not None:
                ref = yahoo_close_on_or_before(ticker, _week_ago(live_date))
                if ref:
                    real_wow = (live - ref) / ref * 100
                    if (wow > 0) != (real_wow > 0) and abs(real_wow) > 0.5:
                        rep.add("WARN", f"lint: {f.name} {ticker} WoW sign "
                                        f"mismatch: row {wow:+.2f}% vs computed "
                                        f"{real_wow:+.2f}% :: {snip}")
                    elif abs(real_wow - wow) > 2.0:
                        rep.add("WARN", f"lint: {f.name} {ticker} WoW row "
                                        f"{wow:+.2f}% vs computed {real_wow:+.2f}% "
                                        f":: {snip}")
            if ytd is not None:
                ref = yahoo_close_on_or_before(ticker, _year_start(live_date))
                if ref:
                    real_ytd = (live - ref) / ref * 100
                    if (ytd > 0) != (real_ytd > 0) and abs(real_ytd) > 1.0:
                        rep.add("WARN", f"lint: {f.name} {ticker} YTD sign "
                                        f"mismatch: row {ytd:+.2f}% vs computed "
                                        f"{real_ytd:+.2f}% :: {snip}")
                    elif abs(real_ytd - ytd) > 3.0:
                        rep.add("WARN", f"lint: {f.name} {ticker} YTD row "
                                        f"{ytd:+.2f}% vs computed {real_ytd:+.2f}% "
                                        f":: {snip}")
    rep.add("OK", f"lint: {checked} priced rows verified against live closes")
    check_weight_sums(repo, rep)


def _week_ago(live_date_str):
    return (dt.date.fromisoformat(live_date_str) - dt.timedelta(days=7)).isoformat()


def _year_start(live_date_str):
    """Prior year's final trading day -- the YTD performance basis."""
    y = dt.date.fromisoformat(live_date_str).year
    return f"{y - 1}-12-31"


def iter_tables(lines):
    """Yield (columns, [data_row, ...]) for each well-formed markdown table."""
    pending = None
    cols = None
    rows = []
    for line in lines:
        s = line.strip()
        if s.startswith("|"):
            if TABLE_SEP_RE.match(s):
                if pending is not None:
                    if cols is not None and rows:
                        yield cols, rows
                    cols = split_cells(pending)
                    rows = []
                pending = None
            elif cols is None:
                pending = s
            else:
                rows.append(s)
        else:
            if cols is not None and rows:
                yield cols, rows
            pending = None
            cols = None
            rows = []
    if cols is not None and rows:
        yield cols, rows


def check_weight_sums(repo, rep):
    """Weight-column arithmetic: top-holdings excerpts correctly sum below
    100%; any table whose Weight column sums PAST 100% is internally
    impossible (double-counted row, duplicated holding, or bad carry)."""
    wiki = repo / "wiki"
    if not wiki.is_dir():
        return
    tables_checked = 0
    for f in sorted(wiki.glob("*.md")):
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        for cols, rows in iter_tables(lines):
            widx = [i for i, h in enumerate(cols) if WEIGHT_HDR_RE.search(h)]
            if not widx:
                continue
            i = widx[0]
            total = 0.0
            n = 0
            for r in rows:
                cells = split_cells(r)
                if len(cells) != len(cols):
                    continue
                v = parse_pct(cells[i])
                if v is not None:
                    total += v
                    n += 1
            if n >= 3:
                tables_checked += 1
                if total > 100.5:
                    rep.add("FAIL", f"lint: {f.name} '{cols[i]}' column sums to "
                                    f"{total:.1f}% across {n} rows (>100%) -- "
                                    f"impossible table")
    rep.add("OK", f"lint: {tables_checked} weight table(s) sum-checked "
                  f"(failures reported above)")


# ------------------------------------------------------------------ quarantine

def check_quarantine(repo, rep):
    """Phantom-anomaly quarantine: banned values from past data outages must
    never reappear in any wiki. List lives in macro/quarantine.json:
      [{"ticker": "GOOGL", "banned": "9.11", "reason": "...", "added": "..."}]
    A line containing BOTH the ticker and the banned string = FAIL.
    Also runs a generic phantom-EPS net: a $X EPS claim inside a table row is
    absurd when X exceeds 20% of the share price shown in the same row."""
    qpath = repo / "macro" / "quarantine.json"
    entries = []
    if qpath.exists():
        try:
            entries = json.loads(qpath.read_text(encoding="utf-8"))
        except Exception as e:
            rep.add("FAIL", f"quarantine: macro/quarantine.json unreadable ({e})")
            return
    else:
        rep.add("WARN", "quarantine: macro/quarantine.json not found -- "
                        "no phantom bans active")
    wiki = repo / "wiki"
    if not wiki.is_dir():
        rep.add("FAIL", f"quarantine: {wiki} not found")
        return
    hits = 0
    for f in sorted(wiki.glob("*.md")):
        for n, line in enumerate(f.read_text(
                encoding="utf-8", errors="replace").splitlines(), 1):
            for e in entries:
                tick, banned = e.get("ticker", ""), e.get("banned", "")
                if tick and banned and tick in line and banned in line:
                    hits += 1
                    rep.add("FAIL", f"quarantine: {f.name}:{n} contains banned "
                                    f"{tick} value '{banned}' "
                                    f"({e.get('reason', 'no reason recorded')}) "
                                    f":: {line.strip()[:80]}")
            # generic phantom-EPS net (table rows only)
            if line.strip().startswith("|"):
                em = EPS_CLAIM_RE.search(line)
                pm = PRICE_RE.search(line)
                if em and pm:
                    eps = float(em.group(1).replace(",", ""))
                    price = float((pm.group(1) or pm.group(2)).replace(",", ""))
                    if price > 0 and eps > price * 0.20:
                        hits += 1
                        rep.add("FAIL", f"quarantine: {f.name}:{n} phantom-EPS "
                                        f"candidate: ${eps} EPS vs ${price} price "
                                        f"-- quarantine or correct this row "
                                        f":: {line.strip()[:80]}")
    if hits == 0:
        rep.add("OK", f"quarantine: {len(entries)} ban(s) active, no hits; "
                      f"phantom-EPS net clean")


# ------------------------------------------------------------ counterfactuals

CF_FILES = ("shadow-book.md", "rejections.md", "exit-shadow.md")
CF_DIRS = ("reports", "scorecards")
CF_STALE_DAYS = 7
# Primary pending markers; "to be computed" is the canonical ledger phrase.
# Bare "TBD" is deliberately NOT a marker on its own -- it false-positives on
# future-tense prose ("July TBD", "week in progress"). TBD counts only when
# glued to counterfactual vocabulary on the same line (CF_TBD_CONTEXT_RE).
CF_MARKER_RE = re.compile(
    r"to be computed|to be backfilled|pending computation", re.I)
CF_TBD_RE = re.compile(r"\bTBD\b")
CF_TBD_CONTEXT_RE = re.compile(
    r"backfill|counterfactual|shadow|realized|p&l|basket", re.I)
ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
WEEK_OF_RE = re.compile(r"week of[^\d]*(\d{4}-\d{2}-\d{2})", re.I)
MD_LABEL_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})\b")


def _cf_dates_on(line):
    out = []
    for m in ISO_RE.finditer(line):
        try:
            out.append((m.start(), dt.date(int(m.group(1)), int(m.group(2)),
                                           int(m.group(3)))))
        except ValueError:
            pass
    return out


def _cf_marker_date(lines, idx, today):
    """Best-effort week/date for a pending marker on lines[idx]."""
    line = lines[idx]
    mm = CF_MARKER_RE.search(line) or CF_TBD_RE.search(line)
    pos = mm.start() if mm else 0
    dated = _cf_dates_on(line)
    if dated:
        # nearest ISO date to the marker; ties prefer the later date
        dated.sort(key=lambda t: (abs(t[0] - pos), -t[1].toordinal()))
        return dated[0][1]
    # 'Week of <date>' headers within 5 lines above
    for back in range(idx, max(idx - 6, -1), -1):
        wm = WEEK_OF_RE.search(lines[back])
        if wm:
            return dt.date.fromisoformat(wm.group(1))
    # any ISO date within +/-3 lines, nearest line first
    for off in range(1, 4):
        for j in (idx + off, idx - off):
            if 0 <= j < len(lines):
                dated = _cf_dates_on(lines[j])
                if dated:
                    return dated[0][1]
    # last resort: M/D week label on the marker line (year = today's,
    # rolled back one year if that lands in the future)
    mdl = MD_LABEL_RE.search(line)
    if mdl:
        mo, dy = int(mdl.group(1)), int(mdl.group(2))
        if 1 <= mo <= 12 and 1 <= dy <= 31:
            try:
                d = dt.date(today.year, mo, dy)
                if d > today:
                    d = dt.date(today.year - 1, mo, dy)
                return d
            except ValueError:
                pass
    return None


def check_counterfactuals(repo, today, rep):
    """Counterfactual-ledger staleness. The shadow book, rejection log, exit
    shadow, weekly reports and scorecards log entries as 'to be computed'
    and backfill them after the week's Friday/Monday closes. A pending
    marker whose week is more than 7 days older than today was never
    backfilled = FAIL. Pure text scan -- no network needed."""
    targets = [repo / name for name in CF_FILES if (repo / name).exists()]
    for d in CF_DIRS:
        sub = repo / d
        if sub.is_dir():
            targets.extend(sorted(sub.glob("*.md")))
    if not targets:
        rep.add("WARN", "counterfactuals: no ledger files found "
                        "(shadow-book.md / rejections.md / exit-shadow.md / "
                        "reports/*.md / scorecards/*.md)")
        return
    hits = 0
    for f in targets:
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, line in enumerate(lines):
            if CF_MARKER_RE.search(line) or (
                    CF_TBD_RE.search(line) and CF_TBD_CONTEXT_RE.search(line)):
                hits += 1
                rel = f.relative_to(repo)
                d = _cf_marker_date(lines, i, today)
                snip = line.strip()[:80]
                if d is None:
                    rep.add("WARN", f"counterfactuals: {rel}:{i + 1} pending "
                                    f"marker with no week/date context "
                                    f":: {snip}")
                    continue
                age = (today - d).days
                if age > CF_STALE_DAYS:
                    rep.add("FAIL", f"counterfactuals: {rel}:{i + 1} stale "
                                    f"pending marker -- week {d.isoformat()} "
                                    f"is {age}d old (limit {CF_STALE_DAYS}d), "
                                    f"never backfilled :: {snip}")
                else:
                    rep.add("OK", f"counterfactuals: {rel}:{i + 1} pending "
                                  f"marker week {d.isoformat()}, age {age}d "
                                  f"(within {CF_STALE_DAYS}d grace) :: {snip}")
    if hits == 0:
        rep.add("OK", f"counterfactuals: {len(targets)} ledger file(s) "
                      f"scanned, no pending markers")


# ----------------------------------------------------------------------- feed

FEED_REQUIRED_KEYS = ("as_of", "source", "fetched_at", "session",
                      "series", "missing")
# Optional special-instrument blocks share the {close, volume} shape
# (Job V contract supersedes the bare-number sketch in DATA_FEED.md sec.1).
FEED_EXTRA_BLOCKS = ("rates", "vol", "commodities", "fx")


def _feed_entry_check(fname, section, ticker, entry, rep):
    """Type/range lint on one {close, volume} observation."""
    where = f"{fname} {section}.{ticker}"
    if not isinstance(entry, dict):
        rep.add("FAIL", f"feed: {where} is not an object")
        return
    close = entry.get("close")
    if isinstance(close, bool) or not isinstance(close, (int, float)):
        rep.add("FAIL", f"feed: {where} close is not numeric: {close!r}")
    elif close <= 0:
        rep.add("FAIL", f"feed: {where} close {close} <= 0")
    vol = entry.get("volume")
    if vol is not None:
        if isinstance(vol, bool) or not isinstance(vol, (int, float)):
            rep.add("FAIL", f"feed: {where} volume is not numeric: {vol!r}")
        elif vol < 0:
            rep.add("FAIL", f"feed: {where} volume {vol} < 0")


def _observed_check(where, observed, as_of, rep):
    """`observed` is a stand-in: the session a value was published for when
    the instrument printed nothing on the file's date. It is therefore
    always an earlier day of the same Mon..Fri week, and anything else is a
    wrong label."""
    try:
        day = dt.date.fromisoformat(observed)
        of = dt.date.fromisoformat(as_of)
    except (TypeError, ValueError):
        rep.add("FAIL", f"feed: {where} observed {observed!r} is not an "
                        f"ISO date")
        return
    monday = of - dt.timedelta(days=of.weekday())
    if not monday <= day < of:
        rep.add("FAIL", f"feed: {where} observed {observed} is not an "
                        f"earlier day in the week of {as_of}; a stand-in "
                        f"comes from the same week or not at all")


def _timestamp_check(where, got, rep):
    if not isinstance(got, str) or not got.endswith("Z"):
        rep.add("FAIL", f"feed: {where} fetched_at {got!r} is not a UTC "
                        f"...Z timestamp")
        return
    try:
        dt.datetime.strptime(got, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        rep.add("FAIL", f"feed: {where} fetched_at {got!r} is not "
                        f"YYYY-MM-DDTHH:MM:SSZ")


def _feed_provenance_check(fname, doc, rep):
    """Per-entry provenance (DATA_FEED.md sec.1, `provenance`).

    `provenance.series` names the adjustment anchor of a series merged into
    a week after the fact. `provenance.<block>` names a special instrument
    the file-level stamp does not describe: one from another publisher (the
    Treasury 2-year, under `rates`), one whose value is a stand-in from an
    earlier session (`observed`), or one a correction restated from a later
    fetch. Both are optional; when present they must be exact, because a
    consumer that trusts one and is wrong reports one anchor for two, reads
    a futures mark as a cash yield, or takes Thursday's close for Friday's.
    """
    prov = doc.get("provenance")
    if prov is None:
        return
    if not isinstance(prov, dict):
        rep.add("FAIL", f"feed: {fname} 'provenance' is not an object")
        return
    if not prov:
        rep.add("FAIL", f"feed: {fname} 'provenance' is empty; a file with "
                        f"nothing to name omits the block")
        return
    known = ("series",) + FEED_EXTRA_BLOCKS
    unknown = sorted(set(prov) - set(known))
    if unknown:
        rep.add("FAIL", f"feed: {fname} 'provenance' has unknown key(s) "
                        f"{unknown}; only {', '.join(known)} are defined")
    for label in known:
        if label not in prov:
            continue
        entries = prov[label]
        if not isinstance(entries, dict):
            rep.add("FAIL", f"feed: {fname} 'provenance.{label}' is not an "
                            f"object")
            continue
        target = doc.get(label)
        present = set(target) if isinstance(target, dict) else set()
        for ticker, rec in sorted(entries.items()):
            if ticker not in present:
                rep.add("FAIL", f"feed: {fname} provenance names {ticker!r}, "
                                f"which is not in '{label}' -- an anchor for "
                                f"a series that is not there describes "
                                f"nothing")
            where = f"{fname} provenance[{ticker!r}]"
            if not isinstance(rec, dict):
                rep.add("FAIL", f"feed: {where} is not an object")
                continue
            src_ = rec.get("source")
            if not isinstance(src_, str) or not src_:
                rep.add("FAIL", f"feed: {where} lacks a non-empty 'source'")
            _timestamp_check(where, rec.get("fetched_at"), rep)
            if "observed" in rec:
                _observed_check(where, rec["observed"], doc.get("as_of"), rep)
            if "contract" in rec:
                if label != "commodities":
                    rep.add("FAIL", f"feed: {where} carries a 'contract' "
                                    f"under provenance.{label}; only a "
                                    f"commodity is a named contract month")
                else:
                    _contract_check(where, ticker, rec["contract"],
                                    rec.get("observed", doc.get("as_of")),
                                    rep)


# ---------------------------------------------------- the Treasury 2-year

# Mirrors scan_pipeline/snapshot.py (TREASURY_SOURCE, US2Y_HISTORY_FILE).
# This script stays importable with nothing but the standard library, so the
# two names are repeated here and tests/test_us2y_source.py pins them equal.
TREASURY_SOURCE = "treasury"
US2Y_HISTORY = ("data", "us2y_treasury.json")


def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _treasury_us2y(doc):
    """A weekly doc's own Treasury-sourced US2Y close, or None.

    None is the ordinary answer for every file through 2026-10-02: their
    US2Y is the 2YY=F future, which no label claims is anything else."""
    prov = doc.get("provenance") if isinstance(doc, dict) else None
    rates = prov.get("rates") if isinstance(prov, dict) else None
    rec = rates.get("US2Y") if isinstance(rates, dict) else None
    if not isinstance(rec, dict) or rec.get("source") != TREASURY_SOURCE:
        return None
    entry = (doc.get("rates") or {}).get("US2Y")
    close = entry.get("close") if isinstance(entry, dict) else None
    return float(close) if _is_number(close) else None


def check_us2y_history(repo, rep):
    """Every week needs exactly one Treasury 2-year (DATA_FEED.md sec.1a).

    A weekly file's US2Y is the cash yield only where provenance names
    Treasury. For every other week -- all of them through 2026-10-02 -- the
    value lives in data/us2y_treasury.json. This validates that file and
    then asks the question that matters: is there a week with neither?
    Such a week is not a FAIL, because the honest outcome is already in
    place (market_state carries the 2-year as null with the reason). It is
    a WARN, because scripts/backfill_us2y.py can fill it and nobody will
    unless told.

    The file being ABSENT is different, and a FAIL wherever a
    market_state.json was derived: the weekly job does not write the
    history, so a runner that never received it derives a null weekly
    change and a null percentile for a 2-year whose level looks fine.
    Pure stdlib, no network.
    """
    weekly = repo / "data" / "weekly"
    if not weekly.is_dir():
        return
    weeks = {}                  # as_of -> the file's own Treasury 2Y or None
    for f in sorted(weekly.glob("*.json")):
        if f.name.endswith(".corrected.json"):
            continue
        corrected = f.with_name(f.stem + ".corrected.json")
        try:
            doc = json.loads((corrected if corrected.is_file() else f)
                             .read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue            # check_feed has already reported it
        weeks[f.stem] = _treasury_us2y(doc)
    if not weeks:
        return

    name = "/".join(US2Y_HISTORY)
    path = repo.joinpath(*US2Y_HISTORY)
    series = {}
    if path.is_file():
        before = rep.counts["FAIL"]
        try:
            hist = json.loads(path.read_bytes().decode("ascii"))
        except UnicodeDecodeError as e:
            rep.add("FAIL", f"feed: {name} is not pure ASCII ({e})")
            hist = None
        except json.JSONDecodeError as e:
            rep.add("FAIL", f"feed: {name} does not parse as JSON ({e})")
            hist = None
        if hist is not None:
            got = hist.get("series") if isinstance(hist, dict) else None
            if isinstance(got, dict):
                series = got
            else:
                rep.add("FAIL", f"feed: {name} has no 'series' object")
        for week, rec in sorted(series.items()):
            where = f"{name} series[{week!r}]"
            if week not in weeks:
                rep.add("FAIL", f"feed: {where} names a week with no weekly "
                                f"file -- a value for a week the panel does "
                                f"not have describes nothing")
            if not isinstance(rec, dict):
                rep.add("FAIL", f"feed: {where} is not an object")
                continue
            close = rec.get("close")
            if not _is_number(close):
                rep.add("FAIL", f"feed: {where} close is not numeric: "
                                f"{close!r}")
            elif close <= 0:
                rep.add("FAIL", f"feed: {where} close {close} <= 0")
            else:
                own = weeks.get(week)
                if own is not None and abs(own - close) > 1e-9:
                    rep.add("FAIL", f"feed: {week} has two different "
                                    f"Treasury 2-year values -- "
                                    f"weekly/{week}.json says {own}, "
                                    f"{name} says {close}. The deriver "
                                    f"reads the weekly file's; one of them "
                                    f"is wrong.")
            _timestamp_check(where, rec.get("fetched_at"), rep)
            if "observed" in rec:
                _observed_check(where, rec["observed"], week, rep)
        if rep.counts["FAIL"] == before:
            rep.add("OK", f"feed: {name} validated ({len(series)} week(s))")

    gaps = sorted(w for w, own in weeks.items()
                  if own is None and w not in series)
    derived_here = (repo / "data" / "market_state.json").is_file()
    have_history = path.is_file()
    if gaps and not have_history and derived_here:
        rep.add("FAIL", f"feed: {name} not found, but {len(gaps)} of "
                        f"{len(weeks)} week(s) can only get their Treasury "
                        f"2-year from it and market_state.json was derived "
                        f"in this tree. Without it the deriver nulls the "
                        f"2-year's weekly change and its percentile. The "
                        f"weekly job does not write this file: copy it from "
                        f"the repo, then re-derive.")
    elif gaps:
        span = gaps[0] if len(gaps) == 1 else f"{gaps[0]} .. {gaps[-1]}"
        absent = "" if have_history else f" ({name} not found)"
        rep.add("WARN", f"feed: {len(gaps)} of {len(weeks)} week(s) have no "
                        f"Treasury 2-year{absent}: {span}. market_state "
                        f"derives US2Y for them as null, never from the "
                        f"2YY=F future. Fill with "
                        f"`python scripts/backfill_us2y.py`, which also "
                        f"re-derives market_state.json.")
    else:
        own_n = sum(1 for own in weeks.values() if own is not None)
        rep.add("OK", f"feed: all {len(weeks)} week(s) have a Treasury "
                      f"2-year ({own_n} in their own file, "
                      f"{len(weeks) - own_n} from {name})")

    _market_state_us2y_check(repo, weeks, series, have_history or not gaps,
                             rep)


def _market_state_us2y_check(repo, weeks, series, history_ok, rep):
    """market_state's 2-year is the Treasury 2-year for its week, or null.

    The regression gate for the defect itself. Any other number is the
    2YY=F future back under the name -- which is exactly what a deriver from
    before 2026-10-04 writes, and the Friday job runs the runner's copy of
    scan_pipeline/, not this repo's. Because that job fetches this script
    fresh and stops on a FAIL, a stale runner is caught before it pushes.

    `lvl` is checked by value: it is one rounding of one committed number,
    so it cannot drift from the deriver. `d1w_bps` and `pctile_2y` are
    checked only for being null exactly when they have to be, which is what
    a state derived without the history file, or before a gap was filled,
    gets wrong. Their values are --derive's business.
    """
    path = repo / "data" / "market_state.json"
    if not path.is_file():
        return
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        as_of = state["as_of"]
        us2y = state["rates"]["US2Y"]
        lvl, d1w, pct = us2y["lvl"], us2y["d1w_bps"], us2y["pctile_2y"]
        prior_week = (dt.date.fromisoformat(as_of)
                      - dt.timedelta(weeks=1)).isoformat()
    except (ValueError, KeyError, TypeError):
        rep.add("FAIL", "feed: data/market_state.json has no readable "
                        "as_of / rates.US2Y (lvl, d1w_bps, pctile_2y)")
        return
    if as_of not in weeks:
        rep.add("WARN", f"feed: market_state.json is as_of {as_of}, which "
                        f"has no weekly file here; its US2Y was not checked")
        return

    def cash(week):
        """(Treasury 2-year, where it lives) by the deriver's own rule: the
        week's labelled value, else the history entry, else nothing."""
        if weeks.get(week) is not None:
            return weeks[week], f"weekly/{week}.json"
        rec = series.get(week)
        close = rec.get("close") if isinstance(rec, dict) else None
        return (float(close) if _is_number(close) else None,
                "/".join(US2Y_HISTORY))

    now, where = cash(as_of)
    prior, _ = cash(prior_week)
    want = round(now, 2) if now is not None else None
    fix = ("Check that the deriver that wrote it is the Treasury-aware one "
           "(scan_pipeline/ on the runner is synced by hand), then "
           "`python scripts/rederive_market_state.py`.")

    if not ((lvl is None and want is None)
            or (_is_number(lvl) and want is not None
                and abs(lvl - want) < 1e-9)):
        truth = ("there is no Treasury 2-year for that week, so it must be "
                 "null" if want is None
                 else f"the Treasury 2-year is {want} ({where})")
        rep.add("FAIL", f"feed: market_state.json carries US2Y {lvl!r} for "
                        f"{as_of}, but {truth}. A number that is neither is "
                        f"the 2YY=F future again, or a state derived before "
                        f"the value existed. {fix}")
        return

    stale = []
    if (d1w is None) != (now is None or prior is None):
        stale.append(
            f"d1w_bps is {d1w!r} although "
            + (f"the Treasury 2-year exists for both {prior_week} and "
               f"{as_of}" if d1w is None
               else f"there is no Treasury 2-year for "
                    f"{as_of if now is None else prior_week}"))
    if history_ok and (pct is None) != (now is None):
        stale.append(f"pctile_2y is {pct!r} although the level is {lvl!r}")
    if stale:
        rep.add("FAIL", f"feed: market_state.json US2Y for {as_of}: "
                        f"{'; '.join(stale)}. It was derived without a "
                        f"value this tree has, or with one it lacks -- "
                        f"typically {'/'.join(US2Y_HISTORY)} missing where "
                        f"it was derived, or a gap filled since. {fix}")
        return
    shown = ("null (no Treasury 2-year for that week)" if want is None
             else f"{lvl}, the Treasury 2-year ({where})")
    rep.add("OK", f"feed: market_state.json US2Y for {as_of} is {shown}")


# ------------------------------------------------------ the named contracts

# Mirrors scan_pipeline: snapshot.COMMODITY_HISTORY_FILE, COMMODITY_TICKERS
# and NEXT_CONTRACT, and the "root" and "position" of each commodity in
# snapshot_macro.INSTRUMENTS. This script stays importable with nothing but
# the standard library, so they are repeated here and
# tests/test_commodity_contracts.py pins them equal.
COMMODITY_HISTORY = ("data", "commodity_settlements.json")
COMMODITY_ROOTS = {"WTI": "CL", "WTI_NEXT": "CL", "GOLD": "GC", "SILVER": "SI"}
COMMODITY_STATE = ("WTI", "GOLD", "SILVER")     # market_state's entries
NEXT_CONTRACT = {"WTI": "WTI_NEXT"}
CONTRACT_RE = re.compile(r"^([A-Z]{2})([FGHJKMNQUVXZ])(\d{2})$")
# How many calendar months after the session's own month a contract's
# delivery month can be: crude stops trading the month before delivery, the
# metals in it. A second-position contract is one further out. This is a
# bound, not the roll calendar; that lives with the writer.
CONTRACT_MONTHS_AHEAD = {"CL": (1, 2), "GC": (0, 1), "SI": (0, 1)}
COMMODITY_POSITION = {"WTI": 0, "WTI_NEXT": 1, "GOLD": 0, "SILVER": 0}


def _contract_check(where, ticker, contract, session, rep):
    """A contract label is the exchange's name for a month this instrument
    could hold on that session. Returns True when it is."""
    m = CONTRACT_RE.match(contract) if isinstance(contract, str) else None
    root = COMMODITY_ROOTS.get(ticker)
    if m is None or root is None or m.group(1) != root:
        rep.add("FAIL", f"feed: {where} contract {contract!r} is not a "
                        f"{root or 'known'} contract (product, month letter, "
                        f"two-digit year, e.g. "
                        f"{(root or 'CL')}X26)")
        return False
    try:
        day = dt.date.fromisoformat(session)
    except (TypeError, ValueError):
        return True             # the session's own check reports it
    ahead = ((2000 + int(m.group(3))) * 12 + "FGHJKMNQUVXZ".index(m.group(2))
             - (day.year * 12 + day.month - 1))
    lo, hi = CONTRACT_MONTHS_AHEAD[root]
    shift = COMMODITY_POSITION.get(ticker, 0)
    if not lo + shift <= ahead <= hi + shift:
        rep.add("FAIL", f"feed: {where} names {contract} for the session of "
                        f"{session}. That month cannot be the "
                        f"{'next' if shift else 'nearest-expiry'} contract "
                        f"then, so the close is another month's or the label "
                        f"is wrong")
        return False
    return True


def _named_contract(doc, ticker):
    """The contract month a weekly doc names for one commodity, or None.

    None is the ordinary answer for every file through 2026-10-02: they
    hold a continuous symbol's bar and name nothing."""
    prov = doc.get("provenance") if isinstance(doc, dict) else None
    labels = prov.get("commodities") if isinstance(prov, dict) else None
    rec = labels.get(ticker) if isinstance(labels, dict) else None
    contract = rec.get("contract") if isinstance(rec, dict) else None
    if isinstance(contract, str) and CONTRACT_RE.match(contract):
        return contract
    return None


def _committed_close(doc, ticker):
    entry = (doc.get("commodities") or {}).get(ticker) \
        if isinstance(doc, dict) else None
    close = entry.get("close") if isinstance(entry, dict) else None
    return float(close) if _is_number(close) else None


def _same_close(a, b):
    """Equal, for a committed close and a fresh one: the provider serves
    float32, so the 4th decimal of a large close is the float and not the
    market. scripts/backfill_commodities.py decides `replaces` by this."""
    return abs(a - b) <= max(1.5e-4, 2e-6 * abs(b))


def _commodity_values(weeks, instruments, ticker):
    """{week: (settlement, contract or None)} by the deriver's own rule
    (snapshot.commodity_series): the week's own close where its file names
    the contract; else the settlement file's entry; else nothing where that
    file says none can be had; else the week's unlabelled close, through
    the audited week only; else nothing."""
    rec = instruments.get(ticker) if isinstance(instruments, dict) else None
    rec = rec if isinstance(rec, dict) else {}
    entries = rec.get("series") if isinstance(rec.get("series"), dict) else {}
    gone = rec.get("unavailable") \
        if isinstance(rec.get("unavailable"), dict) else {}
    through = rec.get("audited_through")
    out = {}
    for week, doc in weeks.items():
        own = _committed_close(doc, ticker)
        contract = _named_contract(doc, ticker)
        entry = entries.get(week)
        if own is not None and contract:
            out[week] = (own, contract)
        elif isinstance(entry, dict) and _is_number(entry.get("close")):
            named = entry.get("contract")
            out[week] = (float(entry["close"]),
                         named if isinstance(named, str)
                         and CONTRACT_RE.match(named) else None)
        elif week in gone:
            continue
        elif own is not None and isinstance(through, str) and week <= through:
            out[week] = (own, None)
    return out


def check_commodity_history(repo, rep):
    """Every week has one settlement of the nearest-expiry contract per
    commodity, or a recorded reason for none (DATA_FEED.md sec.1d).

    A weekly file's WTI, GOLD or SILVER is known to be that contract's
    settlement only where provenance.commodities names the contract. For
    every other week -- all of them through 2026-10-02 -- the answer is in
    data/commodity_settlements.json: the committed close stands (it was
    audited), or an entry supersedes it, or none can be had. This validates
    that file, then asks which weeks have neither a value nor a reason.

    Such a week is a WARN, not a FAIL, for the reason a week with no
    Treasury 2-year is: the honest outcome is already in place (market_state
    carries the field as null) and scripts/backfill_commodities.py can
    usually fill it. The file being ABSENT where a market_state.json was
    derived is a FAIL: the weekly job does not write it, and without it the
    deriver can read no week from before contracts were named.
    Pure stdlib, no network.
    """
    weekly = repo / "data" / "weekly"
    if not weekly.is_dir():
        return
    weeks = {}
    for f in sorted(weekly.glob("*.json")):
        if f.name.endswith(".corrected.json"):
            continue
        corrected = f.with_name(f.stem + ".corrected.json")
        try:
            doc = json.loads((corrected if corrected.is_file() else f)
                             .read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue            # check_feed has already reported it
        if isinstance(doc, dict):
            weeks[f.stem] = doc
    if not weeks:
        return

    name = "/".join(COMMODITY_HISTORY)
    path = repo.joinpath(*COMMODITY_HISTORY)
    have_history = path.is_file()
    instruments = {}
    if have_history:
        before = rep.counts["FAIL"]
        hist = None
        try:
            hist = json.loads(path.read_bytes().decode("ascii"))
        except UnicodeDecodeError as e:
            rep.add("FAIL", f"feed: {name} is not pure ASCII ({e})")
        except json.JSONDecodeError as e:
            rep.add("FAIL", f"feed: {name} does not parse as JSON ({e})")
        if hist is not None:
            got = hist.get("instruments") if isinstance(hist, dict) else None
            if isinstance(got, dict):
                instruments = got
            else:
                rep.add("FAIL", f"feed: {name} has no 'instruments' object")
        entries = declared = 0
        for ticker, rec in sorted(instruments.items()):
            if ticker not in COMMODITY_ROOTS or not isinstance(rec, dict):
                rep.add("FAIL", f"feed: {name} instruments[{ticker!r}] is "
                                f"not one of {', '.join(COMMODITY_ROOTS)}")
                continue
            through = rec.get("audited_through")
            if through is not None:
                try:
                    dt.date.fromisoformat(through)
                except (TypeError, ValueError):
                    rep.add("FAIL", f"feed: {name} {ticker} audited_through "
                                    f"{through!r} is not an ISO date")
            series = rec.get("series")
            gone = rec.get("unavailable")
            series = series if isinstance(series, dict) else {}
            gone = gone if isinstance(gone, dict) else {}
            for week, entry in sorted(series.items()):
                entries += 1
                where = f"{name} {ticker} series[{week!r}]"
                doc = weeks.get(week)
                if doc is None:
                    rep.add("FAIL", f"feed: {where} names a week with no "
                                    f"weekly file -- a value for a week the "
                                    f"panel does not have describes nothing")
                if week in gone:
                    rep.add("FAIL", f"feed: {where} is also listed as "
                                    f"unavailable; it cannot be both")
                if not isinstance(entry, dict):
                    rep.add("FAIL", f"feed: {where} is not an object")
                    continue
                _feed_entry_check(name, ticker + " series", week, entry, rep)
                if not isinstance(entry.get("source"), str) \
                        or not entry.get("source"):
                    rep.add("FAIL", f"feed: {where} lacks a non-empty "
                                    f"'source'")
                if not isinstance(entry.get("symbol"), str) \
                        or not entry.get("symbol"):
                    rep.add("FAIL", f"feed: {where} lacks 'symbol', the "
                                    f"provider symbol that answered")
                _timestamp_check(where, entry.get("fetched_at"), rep)
                if "observed" in entry:
                    _observed_check(where, entry["observed"], week, rep)
                _contract_check(where, ticker, entry.get("contract"),
                                entry.get("observed", week), rep)
                close = entry.get("close")
                if doc is None or not _is_number(close):
                    continue
                held = _committed_close(doc, ticker)
                was = entry.get("replaces")
                if _named_contract(doc, ticker) and held is not None:
                    if abs(held - close) > 1e-9:
                        rep.add("FAIL", f"feed: {week} has two different "
                                        f"{ticker} settlements -- "
                                        f"weekly/{week}.json names its "
                                        f"contract and says {held}, {name} "
                                        f"says {close}. The deriver reads "
                                        f"the weekly file's; one of them is "
                                        f"wrong.")
                elif was is not None:
                    was_close = was.get("close") \
                        if isinstance(was, dict) else None
                    if held is None or not _is_number(was_close) \
                            or abs(held - was_close) > 1e-9:
                        rep.add("FAIL", f"feed: {where} says it replaces "
                                        f"{was_close!r}, but weekly/{week}"
                                        f".json holds {held!r}")
                elif held is not None and not _same_close(held, close):
                    rep.add("FAIL", f"feed: {where} is {close} where "
                                    f"weekly/{week}.json holds {held}, and "
                                    f"does not record that it replaces it")
            for week, entry in sorted(gone.items()):
                declared += 1
                where = f"{name} {ticker} unavailable[{week!r}]"
                if week not in weeks:
                    rep.add("FAIL", f"feed: {where} names a week with no "
                                    f"weekly file")
                why = entry.get("reason") if isinstance(entry, dict) else None
                if not isinstance(why, str) or not why.strip():
                    rep.add("FAIL", f"feed: {where} gives no 'reason'; a "
                                    f"week with no settlement says why")
        if rep.counts["FAIL"] == before:
            rep.add("OK", f"feed: {name} validated ({entries} settlement(s), "
                          f"{declared} week(s) recorded as unavailable)")

    values = {t: _commodity_values(weeks, instruments, t)
              for t in COMMODITY_ROOTS}
    gaps, counts = {}, {"named": 0, "entry": 0, "audited": 0, "none": 0}
    for ticker in COMMODITY_ROOTS:
        rec = instruments.get(ticker)
        rec = rec if isinstance(rec, dict) else {}
        series = rec.get("series") if isinstance(rec.get("series"), dict) \
            else {}
        gone = rec.get("unavailable") \
            if isinstance(rec.get("unavailable"), dict) else {}
        through = rec.get("audited_through") \
            if isinstance(rec.get("audited_through"), str) else ""
        for week, doc in weeks.items():
            if week in values[ticker]:
                kind = ("named" if _named_contract(doc, ticker)
                        and _committed_close(doc, ticker) is not None
                        else "entry" if week in series else "audited")
                counts[kind] += 1
            elif week in gone:
                counts["none"] += 1
            elif week > through:
                gaps.setdefault(ticker, []).append(week)

    derived_here = (repo / "data" / "market_state.json").is_file()
    if gaps and not have_history and derived_here:
        rep.add("FAIL", f"feed: {name} not found, and market_state.json was "
                        f"derived in this tree. Without it no WTI, GOLD or "
                        f"SILVER close from before contracts were named can "
                        f"be read, so every change and percentile that "
                        f"reaches back derives as null. The weekly job does "
                        f"not write this file: copy it from the repo, then "
                        f"re-derive.")
    elif gaps and not have_history:
        every = sorted({w for missing in gaps.values() for w in missing})
        rep.add("WARN", f"feed: {name} not found. Without it no WTI, GOLD "
                        f"or SILVER close from before contracts were named "
                        f"can be read: {len(every)} week(s), {every[0]} .. "
                        f"{every[-1]}, have no settlement on a named "
                        f"contract. Copy the file from the repo before "
                        f"deriving anything here.")
    elif gaps:
        for ticker, missing in sorted(gaps.items()):
            missing.sort()
            span = missing[0] if len(missing) == 1 \
                else f"{missing[0]} .. {missing[-1]}"
            unlabelled = sum(1 for w in missing
                             if _committed_close(weeks[w], ticker) is not None)
            how = (f" {unlabelled} of them carry a close with no contract "
                   f"label, which a writer from before 2026-10-05 produces "
                   f"and no reader uses." if unlabelled else "")
            rep.add("WARN", f"feed: {len(missing)} week(s) have no {ticker} "
                            f"settlement on a named contract: "
                            f"{span}.{how} market_state derives the fields "
                            f"that need them as null. Fill with `python "
                            f"scripts/backfill_commodities.py`, which also "
                            f"re-derives market_state.json.")
    else:
        rep.add("OK", f"feed: every week has its commodity settlements or a "
                      f"recorded reason for none ({counts['named']} named "
                      f"in their own file, {counts['entry']} from {name}, "
                      f"{counts['audited']} audited closes, "
                      f"{counts['none']} unavailable)")

    if gaps and not have_history and derived_here:
        return      # already failed; with no file there is nothing to
                    # compare the state against
    _market_state_commodity_check(repo, weeks, values,
                                  have_history or not gaps, rep)


def _pct_change(now, then):
    """The deriver's own arithmetic (snapshot._pct_delta), to one decimal."""
    if then == 0:
        return None
    return round(float(100.0 * (now / then - 1.0)), 1)


def _market_state_commodity_check(repo, weeks, values, history_ok, rep):
    """market_state's WTI, GOLD and SILVER are the nearest-expiry contract's
    settlements, differenced against themselves, or null.

    The regression gate for the defect: a deriver from before 2026-10-05
    takes commodities.* straight from the weekly files, so it shows the
    December gold contract as GOLD and measures a change from one contract
    month to another. The Friday job runs the runner's copy of
    scan_pipeline/, not this repo's; it fetches this script fresh and stops
    on a FAIL, so a stale runner is caught before it pushes.

    px, contract and the four changes are checked by value. Each is one
    division of two committed numbers, rounded once, and the arithmetic here
    is the deriver's. pctile_2y is checked only for being null exactly when
    px is; its value is --derive's business.
    """
    path = repo / "data" / "market_state.json"
    if not path.is_file():
        return
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        as_of = state["as_of"]
        day = dt.date.fromisoformat(as_of)
        block = state["commodities"]
        shown = {t: {k: block[t][k] for k in (
            "px", "contract", "d1w", "d4w", "d13w", "d52w", "pctile_2y")}
            for t in COMMODITY_STATE}
    except (ValueError, KeyError, TypeError):
        rep.add("FAIL", "feed: data/market_state.json has no readable as_of "
                        "/ commodities (px, contract, d1w, d4w, d13w, d52w, "
                        "pctile_2y for WTI, GOLD and SILVER). A state with "
                        "no 'contract' field was written by a deriver from "
                        "before 2026-10-05: sync scan_pipeline/ on the "
                        "runner, then `python "
                        "scripts/rederive_market_state.py`.")
        return
    if as_of not in weeks:
        rep.add("WARN", f"feed: market_state.json is as_of {as_of}, which "
                        f"has no weekly file here; its commodities were not "
                        f"checked")
        return

    def back(n):
        return (day - dt.timedelta(weeks=n)).isoformat()

    def same(a, b):
        return (a is None and b is None) or (
            _is_number(a) and _is_number(b) and abs(a - b) < 1e-9)

    wrong = []
    for ticker in COMMODITY_STATE:
        pts = values[ticker]
        now = pts.get(as_of)
        want = {"px": round(now[0], 2) if now else None,
                "contract": now[1] if now else None}
        for field, n in (("d1w", 1), ("d4w", 4), ("d13w", 13), ("d52w", 52)):
            then = pts.get(back(n))
            want[field] = (_pct_change(now[0], then[0])
                           if now and then else None)
        if ticker in NEXT_CONTRACT:
            # One contract: last week's settlement of the month px is.
            want["d1w"] = None
            if now and now[1]:
                for name in (ticker, NEXT_CONTRACT[ticker]):
                    then = values[name].get(back(1))
                    if then and then[1] == now[1]:
                        want["d1w"] = _pct_change(now[0], then[0])
                        break
        got = shown[ticker]
        off = [f"{f} is {got[f]!r}, derives as {want[f]!r}"
               for f in ("px", "contract", "d1w", "d4w", "d13w", "d52w")
               if not (got[f] == want[f] if f == "contract"
                       else same(got[f], want[f]))]
        if history_ok and (got["pctile_2y"] is None) != (want["px"] is None):
            off.append(f"pctile_2y is {got['pctile_2y']!r} although px "
                       f"derives as {want['px']!r}")
        if off:
            wrong.append(f"{ticker}: " + "; ".join(off))
    if wrong:
        rep.add("FAIL", f"feed: market_state.json commodities for {as_of} "
                        f"are not what the nearest-expiry settlements "
                        f"derive -- {' | '.join(wrong)}. It was written by a "
                        f"deriver that reads commodities.* straight from the "
                        f"weekly files (before 2026-10-05), or before a "
                        f"settlement was filled, or where "
                        f"{'/'.join(COMMODITY_HISTORY)} was missing. Check "
                        f"that scan_pipeline/ on the runner is current and "
                        f"that file is beside its data/weekly, then `python "
                        f"scripts/rederive_market_state.py`.")
        return
    said = ", ".join(
        f"{t} null" if shown[t]["px"] is None else
        f"{t} {shown[t]['px']!r} "
        f"({shown[t]['contract'] or 'month not on record'})"
        for t in COMMODITY_STATE)
    rep.add("OK", f"feed: market_state.json commodities for {as_of} are the "
                  f"nearest-expiry settlements: {said}")


# ------------------------------------------------- settlement and restatement

# Mirrors scan_pipeline/snapshot_macro.py: the instruments marked "settles"
# there, under the names a file commits them by, and SETTLED_HOUR_UTC. This
# script stays importable with nothing but the standard library, so they are
# repeated here and tests/test_instrument_sessions.py pins them equal.
LATE_SETTLING = {
    "rates": ("US2Y_FUT",),
    "commodities": ("WTI", "WTI_NEXT", "GOLD", "SILVER"),
    "fx": ("DXY",),
}
SETTLED_HOUR_UTC = 13

# The rule dates from 2026-10-05. Eleven files written before it hold
# evening quotes; they cannot be edited, and macro/instrument_audit.json
# lists every one. A file dated from here on has no such excuse.
SETTLEMENT_RULE_SINCE = "2026-10-05"


def _feed_settlement_check(fname, doc, rep):
    """A futures or dollar-index close read on the evening of its own
    session is a quote, not a settlement (snapshot_macro, "The Yahoo path").

    The writer refuses such a bar and lists the instrument in `missing`. A
    file that carries one anyway was written by a copy of scan_pipeline/
    that predates the rule -- the Friday job runs the runner's copy, synced
    by hand -- and since that job stops on a FAIL from this script, the
    file is caught before it is pushed. The test needs no network: the
    file's own fetch time against its own date."""
    as_of = doc.get("as_of")
    if not isinstance(as_of, str) or as_of < SETTLEMENT_RULE_SINCE:
        return
    prov = doc.get("provenance")
    prov = prov if isinstance(prov, dict) else {}
    watched = {block: list(tickers) for block, tickers in LATE_SETTLING.items()}
    if _treasury_us2y(doc) is None:
        # No Treasury label, so this US2Y is the 2YY=F future (sec.1a).
        watched["rates"].append("US2Y")
    for block, tickers in sorted(watched.items()):
        entries = doc.get(block)
        if not isinstance(entries, dict):
            continue
        labels = prov.get(block) if isinstance(prov.get(block), dict) else {}
        for ticker in tickers:
            if ticker not in entries:
                continue
            label = labels.get(ticker)
            label = label if isinstance(label, dict) else {}
            where = f"{fname} {block}.{ticker}"
            fetched = label.get("fetched_at") or doc.get("fetched_at")
            session = label.get("observed") or as_of
            try:
                read = dt.datetime.strptime(
                    fetched, "%Y-%m-%dT%H:%M:%SZ").replace(
                        tzinfo=dt.timezone.utc)
                settled = dt.datetime.combine(
                    dt.date.fromisoformat(session) + dt.timedelta(days=1),
                    dt.time(SETTLED_HOUR_UTC), tzinfo=dt.timezone.utc)
            except (TypeError, ValueError):
                rep.add("FAIL", f"feed: {where} has no readable fetch time "
                                f"({fetched!r}) or session ({session!r}), "
                                f"so it cannot be shown to be a settlement")
                continue
            if read < settled:
                rep.add("FAIL", f"feed: {where} was read at {fetched}, "
                                f"before {settled:%Y-%m-%dT%H:%MZ}. Until "
                                f"the exchange settlement for {session} is "
                                f"loaded the bar is a quote, not a close "
                                f"(WTI 2026-09-18: 95.47 read, 100.30 "
                                f"settled). The writer lists such an "
                                f"instrument in 'missing'; a file that "
                                f"carries it came from a copy of "
                                f"scan_pipeline/ older than 2026-10-05. "
                                f"Sync the runner, and run the weekly job "
                                f"after 13:00 UTC on the Saturday.")


def _feed_restated_check(fname, doc, base, rep):
    """A correction that changes a close says which one and what it replaced.

    Dropping a bar is recorded in `missing` (the AVB correction). Replacing
    one is recorded in `restated`: [{"block", "ticker", "was": {"close",
    "volume"}}]. The replacement was fetched at another time than the file,
    so it carries its own `provenance.<block>.<ticker>` label. Without the
    record rebuild_corrections.py cannot re-apply the edit when the base
    changes, and a reader cannot tell a restated close from an observed one.

    Special instruments only. A restated equity close would also need an
    adjustment anchor, and no correction has needed one.
    """
    restated = doc.get("restated")
    recorded = {}
    if restated is not None:
        if not isinstance(restated, list) or not restated:
            rep.add("FAIL", f"feed: {fname} 'restated' is not a non-empty "
                            f"list; a correction that restates nothing "
                            f"omits the key")
            restated = []
        for item in restated:
            ok = (isinstance(item, dict)
                  and item.get("block") in FEED_EXTRA_BLOCKS
                  and isinstance(item.get("ticker"), str)
                  and isinstance(item.get("was"), dict)
                  and _is_number(item["was"].get("close")))
            if not ok:
                rep.add("FAIL", f"feed: {fname} 'restated' entry {item!r} "
                                f"is not {{block, ticker, was: {{close, "
                                f"volume}}}} with block one of "
                                f"{', '.join(FEED_EXTRA_BLOCKS)}")
                continue
            recorded[(item["block"], item["ticker"])] = item["was"]

    prov = doc.get("provenance")
    prov = prov if isinstance(prov, dict) else {}
    for block in FEED_EXTRA_BLOCKS:
        now = doc.get(block) if isinstance(doc.get(block), dict) else {}
        was = base.get(block) if isinstance(base.get(block), dict) else {}
        for ticker in sorted(set(now) | set(was)):
            where = f"{fname} {block}.{ticker}"
            if ticker not in now or ticker not in was:
                side = "the correction" if ticker in now else "its base"
                rep.add("FAIL", f"feed: {where} is only in {side}. A "
                                f"correction may restate a special "
                                f"instrument's close; adding or dropping "
                                f"one is not something "
                                f"rebuild_corrections.py can re-apply")
                continue
            key = (block, ticker)
            if key not in recorded:
                if now[ticker] != was[ticker]:
                    rep.add("FAIL", f"feed: {where} is {now[ticker]!r} in "
                                    f"the correction and {was[ticker]!r} in "
                                    f"its base, and 'restated' does not "
                                    f"record the change")
                continue
            held = recorded.pop(key)
            base_close = was[ticker].get("close") \
                if isinstance(was[ticker], dict) else None
            if base_close != held.get("close"):
                rep.add("FAIL", f"feed: {where} 'restated' says the base "
                                f"held {held.get('close')!r}, but it holds "
                                f"{base_close!r}. The base moved under the "
                                f"correction; rebuild_corrections.py will "
                                f"refuse it. Review by hand.")
            if now[ticker] == was[ticker]:
                rep.add("FAIL", f"feed: {where} is recorded in 'restated' "
                                f"but equals its base; it restates nothing")
            label = prov.get(block) if isinstance(prov.get(block), dict) \
                else {}
            if not isinstance(label.get(ticker), dict):
                rep.add("FAIL", f"feed: {where} is restated but carries no "
                                f"provenance.{block}.{ticker} label. The "
                                f"replacement was fetched at another time "
                                f"than the file and has to say when")
    for block, ticker in sorted(recorded):
        rep.add("FAIL", f"feed: {fname} 'restated' names {block}.{ticker}, "
                        f"which is in neither the correction nor its base")


# ------------------------------------------------------- the session witness

# Mirrors scan_pipeline/snapshot.py (WITNESS, SESSION_NOTE). This script
# stays importable with nothing but the standard library, so the two are
# repeated here and tests/test_weekly_session.py pins them equal.
WITNESS = "SPY"
SESSION_NOTE_RE = re.compile(
    r"^Friday holiday; bars from (\d{4}-\d{2}-\d{2})$")

# The witness rule dates from 2026-10-06. One file written before it has
# series and no SPY bar: 2024-08-09.json was started by a backfill run
# restricted to 44 names, had 270 more merged in, and never got the four
# index or twelve sector ETFs -- which it does not list in `missing` either.
# It cannot be edited, so it is warned about, with the command that adds
# them. A file dated from here on has no such excuse. An EMPTY series fails
# whatever its date: no committed file is one.
WITNESS_RULE_SINCE = "2026-10-06"

# A weekly file is due once its Friday is this many days old. The job that
# writes it runs on the Saturday (DATA_FEED.md sec.1b), so a warning on the
# Saturday itself would fire every week and mean nothing.
WEEKLY_DUE_DAYS = 2


def _feed_session_check(fname, doc, weekly, rep):
    """A file is one equity session, and SPY is the witness that it happened
    (DATA_FEED.md sec.1c).

    Run on a market holiday, the weekly writer used to commit `series: {}`:
    every ticker in `missing` for want of a bar dated the Friday, nothing to
    say the Friday was not a session, and this gate passed it (run for
    2026-07-03 on 2026-10-05). Derived from such a week, market_state.json
    is null in every index and sector field, and sector-regime-heatmap
    scores eleven sectors on no constituents in three separate runs. The
    writer refuses now (snapshot.write_weekly, NoSessionWitness). A file
    that gets here anyway came from a copy of scan_pipeline/ older than
    2026-10-06 -- the Saturday job runs the runner's copy, synced by hand --
    or was built another way, and since that job stops on a FAIL from this
    script it is caught before it is pushed.

    `session_note` is how a weekly file names a session that is not its
    Friday. scripts/audit_series.py reads the date out of it, so its form
    is fixed and the date has to be one that can stand in: an earlier day
    of the same week."""
    series = doc.get("series")
    as_of = doc.get("as_of")
    if isinstance(series, dict) and WITNESS not in series:
        cure = ("The writer refuses such a week and writes it whole once a "
                "later session proves the Friday was skipped. Sync "
                "scan_pipeline/ on the runner and remove the file from its "
                "copy; never commit it.")
        if not series:
            rep.add("FAIL", f"feed: {fname} 'series' is empty -- no equity "
                            f"session was observed, and the file does not "
                            f"say why. It was written on a market holiday, "
                            f"or before the provider had posted, by a "
                            f"writer from before 2026-10-06. {cure}")
        elif isinstance(as_of, str) and as_of < WITNESS_RULE_SINCE:
            listed = any(isinstance(m, dict) and m.get("ticker") == WITNESS
                         for m in doc.get("missing") or [])
            silent = "" if listed else (", and does not list it in "
                                        "'missing'")
            rep.add("WARN", f"feed: {fname} has {len(series)} series and no "
                            f"{WITNESS} bar{silent}. It predates the "
                            f"witness rule and cannot be edited; "
                            f"market_state derives every window that starts "
                            f"or ends on {as_of} as null. A --merge "
                            f"backfill adds the names without touching the "
                            f"rest (Actions -> Backfill weekly panel: the "
                            f"tickers, start and end {as_of}).")
        else:
            rep.add("FAIL", f"feed: {fname} has {len(series)} series and no "
                            f"{WITNESS} bar. {WITNESS} is the session "
                            f"witness: without it nothing shows the date "
                            f"was a settled session, and every figure "
                            f"relative to the benchmark is undefined. "
                            f"{cure}")
    if not weekly or "session_note" not in doc:
        return
    note = doc["session_note"]
    found = SESSION_NOTE_RE.match(note) if isinstance(note, str) else None
    if not found:
        rep.add("FAIL", f"feed: {fname} session_note {note!r} is not "
                        f"'Friday holiday; bars from YYYY-MM-DD'. It is the "
                        f"record of which session the equity bars are from, "
                        f"and readers take the date out of it")
        return
    _observed_check(f"{fname} session_note", found.group(1),
                    doc.get("as_of"), rep)


def _listing(days, limit=6):
    shown = ", ".join(days[:limit])
    if len(days) > limit:
        shown += f", ... and {len(days) - limit} more"
    return shown


def weekly_gaps(have, today):
    """(holes, owed) for a weekly panel. Pure.

    have: the Fridays that have a file, as ISO dates. holes: Fridays between
    the first and the newest of them with no file. owed: Fridays after the
    newest that are WEEKLY_DUE_DAYS old or more."""
    if not have:
        return [], []
    weeks = sorted(have)
    on_file = set(weeks)
    holes, owed = [], []
    day = dt.date.fromisoformat(weeks[0])
    day += dt.timedelta(days=(4 - day.weekday()) % 7)       # the first Friday
    newest = dt.date.fromisoformat(weeks[-1])
    due = today - dt.timedelta(days=WEEKLY_DUE_DAYS)
    while day <= max(newest, due):
        if day.isoformat() not in on_file:
            (holes if day < newest else owed).append(day.isoformat())
        day += dt.timedelta(days=7)
    return holes, owed


def check_weekly_completeness(repo, today, rep):
    """Is every week there? (DATA_FEED.md sec.1c.) No network.

    The weekly writer refuses a Friday it has no session witness for, and a
    refusal is a correct outcome: nothing is written and nothing fails. The
    daily feed lost eight sessions that way with every run green, so the
    panel itself is asked.

      FAIL  a Friday between two weekly files has no file. The job went on
            past a week it had refused. Proof that the Friday was skipped,
            or its own late bar, exists by then, so nothing stands in the
            way of writing it; what does not exist is anything that will.
      WARN  the newest Friday or Fridays have no file yet. That is what a
            refusal looks like until the next session, and what a job that
            did not run looks like. It cannot be told apart from here.
    """
    weekly = repo / "data" / "weekly"
    if not weekly.is_dir():
        return
    have = sorted(f.stem for f in weekly.glob("*.json")
                  if re.fullmatch(r"\d{4}-\d{2}-\d{2}", f.stem))
    if not have:
        return
    holes, owed = weekly_gaps(have, today)
    if holes:
        rep.add("FAIL", f"feed: no weekly file for {_listing(holes)} -- "
                        f"{len(holes)} week(s) missing between {have[0]} "
                        f"and {have[-1]}. The writer refuses a Friday it "
                        f"has no session witness for, and the job went on "
                        f"without coming back. market_state nulls every "
                        f"window that ends on a missing week, and a reader "
                        f"that counts weeks by position "
                        f"(sector-regime-heatmap) reads a window longer "
                        f"than it says. Write them, oldest first, with the "
                        f"weekly job's own calls for each Friday: "
                        f"snapshot.fetch_weekly_bars, "
                        f"snapshot_macro.fetch_special_instruments, "
                        f"snapshot.write_weekly; then re-derive "
                        f"market_state.json through the chain "
                        f"(snapshot.write_market_state_chain). "
                        f"snapshot.unwritten_fridays lists them.")
    if owed:
        rep.add("WARN", f"feed: no weekly file yet for {_listing(owed)} "
                        f"(newest is {have[-1]}). Either the weekly job has "
                        f"not run, or the writer refused: no {WITNESS} bar "
                        f"dated the Friday and none after it, which is what "
                        f"a market holiday looks like until the next "
                        f"session. The next run writes the oldest first "
                        f"(snapshot.unwritten_fridays), before the week "
                        f"after it.")
    if not holes and not owed:
        rep.add("OK", f"feed: weekly panel is complete -- {len(have)} "
                      f"week(s) from {have[0]} through {have[-1]}, none "
                      f"missing")


def check_feed(repo, rep, subdir="weekly", require_friday=True, label="weekly"):
    """Data-feed validation (DATA_FEED.md sec.1). Pure stdlib, no network.
    'missing' is required and never empty-by-omission: a silently absent
    ticker is indistinguishable from one that never existed, and that
    ambiguity is what the agents fill in from priors.

    One contract governs data/weekly/ and data/daily/ alike -- ASCII bytes,
    required keys, entry shape, the session witness, correction pointers and
    what a correction restated, provenance, and no late-settling close read
    before it settled. Only the Friday rule differs, and `session_note` with
    it: a daily file is named for whatever session settled (DATA_FEED.md
    sec.4), so it has no other session to name."""
    weekly = repo / "data" / subdir
    if not weekly.is_dir():
        rep.add("SKIP", f"feed: {weekly} not found -- {label} feed has not "
                        f"launched yet")
        return
    files = sorted(weekly.glob("*.json"))
    if not files:
        rep.add("SKIP", f"feed: {weekly} holds no *.json files yet")
        return
    for f in files:
        try:
            text = f.read_bytes().decode("ascii")
        except UnicodeDecodeError as e:
            rep.add("FAIL", f"feed: {f.name} is not pure ASCII ({e})")
            continue
        try:
            doc = json.loads(text)
        except json.JSONDecodeError as e:
            rep.add("FAIL", f"feed: {f.name} does not parse as JSON ({e})")
            continue
        if not isinstance(doc, dict):
            rep.add("FAIL", f"feed: {f.name} top level is not an object")
            continue
        for key in FEED_REQUIRED_KEYS:
            if key not in doc:
                note = (" -- a silently absent ticker is the failure mode "
                        "this file exists to prevent" if key == "missing"
                        else "")
                rep.add("FAIL", f"feed: {f.name} lacks required key "
                                f"'{key}'{note}")
        if doc.get("session") != "close":
            rep.add("FAIL", f"feed: {f.name} session is "
                            f"{doc.get('session')!r}, must be 'close'")
        as_of = doc.get("as_of")
        as_of_date = None
        if isinstance(as_of, str):
            try:
                as_of_date = dt.date.fromisoformat(as_of)
            except ValueError:
                rep.add("FAIL", f"feed: {f.name} as_of {as_of!r} is not an "
                                f"ISO date")
        else:
            rep.add("FAIL", f"feed: {f.name} as_of is not a string: "
                            f"{as_of!r}")
        if as_of_date is not None:
            if require_friday and as_of_date.weekday() != 4:
                rep.add("FAIL", f"feed: {f.name} as_of {as_of} is not a "
                                f"Friday (weekday {as_of_date.weekday()})")
            if not require_friday and as_of_date.weekday() >= 5:
                rep.add("FAIL", f"feed: {f.name} as_of {as_of} falls on a "
                                f"weekend (weekday {as_of_date.weekday()}); "
                                f"no US session settled that day")
            if f.name == f"{as_of}.json":
                pass
            elif f.name == f"{as_of}.corrected.json":
                corrects = doc.get("corrects")
                if not isinstance(corrects, str) or \
                        not (weekly / corrects).exists():
                    rep.add("FAIL", f"feed: {f.name} correction lacks "
                                    f"'corrects' pointing at an existing "
                                    f"original (got {corrects!r})")
                if not doc.get("reason"):
                    rep.add("FAIL", f"feed: {f.name} correction lacks "
                                    f"'reason'")
                if isinstance(corrects, str) and (weekly / corrects).is_file():
                    try:
                        base = json.loads(
                            (weekly / corrects).read_text(encoding="utf-8"))
                    except (ValueError, OSError):
                        base = None     # reported under the base's own name
                    if isinstance(base, dict):
                        _feed_restated_check(f.name, doc, base, rep)
            else:
                rep.add("FAIL", f"feed: filename {f.name} does not match "
                                f"as_of {as_of}")
        series = doc.get("series")
        if "series" in doc and not isinstance(series, dict):
            rep.add("FAIL", f"feed: {f.name} 'series' is not an object")
        elif isinstance(series, dict):
            for ticker, entry in series.items():
                _feed_entry_check(f.name, "series", ticker, entry, rep)
        for block in FEED_EXTRA_BLOCKS:
            blk = doc.get(block)
            if blk is None:
                continue
            if not isinstance(blk, dict):
                rep.add("FAIL", f"feed: {f.name} '{block}' is not an object")
                continue
            for ticker, entry in blk.items():
                _feed_entry_check(f.name, block, ticker, entry, rep)
        _feed_session_check(f.name, doc, require_friday, rep)
        _feed_provenance_check(f.name, doc, rep)
        _feed_settlement_check(f.name, doc, rep)
    rep.add("OK", f"feed: {len(files)} {label} file(s) validated against "
                  f"DATA_FEED.md sec.1 (failures reported above)")


def check_daily_freshness(repo, today, rep):
    """Is data/daily/ still being written? (DATA_FEED.md sec.4.) No network.

    check_feed validates the files that exist, and a file that was never
    written fails nothing: the daily feed stopped on 2026-09-23 and this
    gate went on reporting every file valid for eleven days.

    A WARN, never a FAIL. This is an observation feed that scores nothing
    and it must not stop a Monday. It also has no calendar of holidays, so
    it counts weekdays, not sessions, and stays quiet about a single one --
    the check that asks the provider which sessions exist, and fails, is
    `daily_observe.py --audit` in the Daily observation workflow. This one
    is for the case that workflow has stopped running altogether.
    """
    daily = repo / "data" / "daily"
    if not daily.is_dir():
        return
    days = sorted(f.stem for f in daily.glob("*.json")
                  if re.fullmatch(r"\d{4}-\d{2}-\d{2}", f.stem))
    if not days:
        return
    newest = dt.date.fromisoformat(days[-1])
    # Yesterday at the latest: today's session may not have closed, and this
    # runs on machines in more than one timezone.
    expected = today - dt.timedelta(days=1)
    while expected.weekday() >= 5:
        expected -= dt.timedelta(days=1)
    behind = []
    d = newest + dt.timedelta(days=1)
    while d <= expected:
        if d.weekday() < 5:
            behind.append(d)
        d += dt.timedelta(days=1)
    if len(behind) >= 2:
        rep.add("WARN", f"feed: data/daily has stopped being written -- "
                        f"newest file {newest}, {len(behind)} weekdays "
                        f"behind {expected} (weekdays, not sessions: this "
                        f"check knows no holidays). Run `python "
                        f"scripts/daily_observe.py --audit` for the sessions "
                        f"that are missing")
    else:
        rep.add("OK", f"feed: data/daily is current through {newest}")


# --------------------------------------------------------------------- splits

# Ratios a corporate action produces, as the percent change an UNADJUSTED
# panel shows when it straddles one. A forward split divides the price.
CORPORATE_ACTION_MOVES = {
    -50.0:   "2:1 forward split",
    -66.667: "3:1 forward split",
    -33.333: "3:2 forward split",
    -75.0:   "4:1 forward split",
    -80.0:   "5:1 forward split",
    -90.0:   "10:1 forward split",
    -95.0:   "20:1 forward split",
    100.0:   "1:2 reverse split",
    200.0:   "1:3 reverse split",
    400.0:   "1:5 reverse split",
    900.0:   "1:10 reverse split",
}

# A split is exact arithmetic, so the observed move lands very close to the
# ratio. The slack covers the genuine market move in the same window.
SPLIT_TOLERANCE_PCT = 2.5

# Below this nothing is examined. A real one-week move this large is rare and
# worth a look regardless of whether it matches a ratio.
LARGE_MOVE_PCT = 30.0

ACK_PATH = ("macro", "known_corporate_actions.json")


def _load_panel_docs(directory):
    """Weekly/daily docs oldest first, corrections preferred (sec.1)."""
    out = []
    for f in sorted(directory.glob("*.json")):
        if f.name.endswith(".corrected.json"):
            continue
        doc = json.loads(f.read_text(encoding="utf-8"))
        corrected = f.with_name(f.stem + ".corrected.json")
        if corrected.is_file():
            doc = json.loads(corrected.read_text(encoding="utf-8"))
        out.append((f.name, doc))
    out.sort(key=lambda kv: kv[1].get("as_of", kv[0]))
    return out


def _classify(pct):
    for move, label in CORPORATE_ACTION_MOVES.items():
        if abs(pct - move) <= SPLIT_TOLERANCE_PCT:
            return label
    return None


def check_splits(repo, rep):
    """Find panel discontinuities that look like unhandled corporate actions.

    Adjusted closes are back-adjusted to the FETCH date. A split between two
    fetches therefore lands in the panel as a step: the file fetched before it
    is on the pre-split basis, the one after is on the post-split basis, and
    the week-over-week return across them is the split ratio rather than a
    market move.

    APH is the worked example. It split 2:1 on 2026-09-03; 2026-08-28.json was
    fetched 08-29 and 2026-09-04.json on 09-05, so the panel shows -50%.
    Nothing caught it: the heatmap's extreme-move flag only covers names
    inside a scored basket, and APH is not in the 110.

    WARN, not FAIL, matching the extreme-move convention -- real crashes
    happen and a detector that refuses the panel would be worse than one that
    names the suspect. Acknowledge a reviewed action in
    macro/known_corporate_actions.json and it goes quiet.
    """
    ack_file = repo.joinpath(*ACK_PATH)
    ack = {}
    if ack_file.is_file():
        try:
            ack = {(e["ticker"], e["between"]): e
                   for e in json.loads(ack_file.read_text(encoding="utf-8"))
                                  .get("actions", [])}
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            rep.add("FAIL", f"splits: {'/'.join(ACK_PATH)} does not parse "
                            f"({exc})")
            return

    scanned = 0
    candidates = []
    for label, subdir in (("weekly", "weekly"), ("daily", "daily")):
        d = repo / "data" / subdir
        if not d.is_dir():
            continue
        docs = _load_panel_docs(d)
        if len(docs) < 2:
            continue
        scanned += len(docs)
        for (n0, a), (n1, b) in zip(docs, docs[1:]):
            sa = a.get("series") or {}
            sb = b.get("series") or {}
            for ticker in sorted(set(sa) & set(sb)):
                try:
                    p0 = float(sa[ticker]["close"])
                    p1 = float(sb[ticker]["close"])
                except (TypeError, ValueError, KeyError):
                    continue
                if p0 <= 0:
                    continue
                pct = (p1 / p0 - 1.0) * 100.0
                if abs(pct) < LARGE_MOVE_PCT:
                    continue
                span = f"{a.get('as_of')}..{b.get('as_of')}"
                if _classify(pct) is None:
                    continue
                if (ticker, span) in ack:
                    continue
                candidates.append((ticker, span, pct, label,
                                   a.get("as_of"), b.get("as_of")))
    if not scanned:
        rep.add("SKIP", "splits: no panel files to scan")
        return

    # Verify each candidate against the provider's split history. The ratio
    # alone is not evidence: a 3:2 split is -33.3% and so is an ordinary
    # crash. The first draft of this check flagged SOUN, IONQ and QUBT for the
    # same week of 2025-01-10, which was the quantum-stock selloff, not three
    # simultaneous splits. Only a real split date confirms one.
    confirmed = unverified = 0
    for ticker, span, pct, label, d0, d1 in candidates:
        hist = yahoo_splits(ticker)
        if hist is None:
            unverified += 1
            rep.add("WARN",
                    f"splits: {ticker} moved {pct:+.1f}% across {span} "
                    f"({label} panel) -- matches a split ratio but the split "
                    f"history could not be fetched, so this is UNVERIFIED. "
                    f"Re-run with network access before concluding anything.")
            continue
        hit = [(d, r) for d, r in hist if d0 < d <= d1]
        if not hit:
            continue        # a real market move; not this check's business
        confirmed += 1
        when, ratio = hit[0]
        rep.add("WARN",
                f"splits: {ticker} split {ratio} on {when}, and the {label} "
                f"panel straddles it -- {span} shows {pct:+.1f}%, which is the "
                f"ratio, not a market move. Adjusted closes are anchored to "
                f"the fetch date, so the file fetched before the action is on "
                f"the pre-split basis and the one after is not. Record it in "
                f"{'/'.join(ACK_PATH)} once reviewed.")

    dismissed = len(candidates) - confirmed - unverified
    rep.add("OK", f"splits: scanned {scanned} panel file(s); "
                  f"{len(candidates)} ratio candidate(s), {confirmed} "
                  f"confirmed against provider split history, {dismissed} "
                  f"dismissed as real market moves")


# --------------------------------------------------------------------- config

# Symbols the docs describe. If CLAUDE.md talks about one, it has to exist.
#
# This gate exists because the absence of it cost two weeks. Commit 009f7f6
# added SECTOR_FOCUS_110 and FOCUS_TICKERS; 7cf7025 deleted them along with
# their asserts; CLAUDE.md went on documenting both and nothing anywhere
# noticed, because unlike sector-regime-heatmap this repo had no config-drift
# check. The heatmap's preflight.py catches exactly this class -- three copies
# of the same fact that disagree -- and the panel is too important to be the
# one repo without it.
DOCUMENTED_SYMBOLS = (
    "STOCK_UNIVERSE",
    "BACKFILL_44_TICKERS",
    "COUNCIL_WATCHLIST",
    "PRICE_FEED_UNIVERSE",
    "SECTOR_FOCUS_110",
    "FOCUS_TICKERS",
)


def _name_list(names, limit=12):
    """Names for a message: all of a short list, the head of a long one. A
    writer that lost a whole set would otherwise print three hundred."""
    names = sorted(names)
    if len(names) <= limit:
        return str(names)
    return f"{names[:limit]} and {len(names) - limit} more"


def check_config(repo, rep):
    """Config-drift gate: the docs, the constants, the weekly writer and the
    panel must agree."""
    before = rep.counts["FAIL"]
    sys.path.insert(0, str(repo))
    try:
        from scan_pipeline.config import tickers as t
    except Exception as exc:                        # noqa: BLE001
        rep.add("FAIL", f"config: cannot import scan_pipeline.config.tickers "
                        f"({exc}). The module-level asserts fire on import, so "
                        f"this is how a broken focus set surfaces.")
        return

    claude = repo / "CLAUDE.md"
    text = claude.read_text(encoding="utf-8") if claude.is_file() else ""
    for sym in DOCUMENTED_SYMBOLS:
        if f"`{sym}`" in text and not hasattr(t, sym):
            rep.add("FAIL", f"config: CLAUDE.md documents `{sym}` but "
                            f"scan_pipeline/config/tickers.py does not define "
                            f"it -- the docs and the code disagree")

    # Structural invariants. Counts are asserted here and deliberately NOT
    # hardcoded in the docs: a number in prose is a third copy that drifts.
    feed = set(getattr(t, "PRICE_FEED_UNIVERSE", ()))
    focus = getattr(t, "SECTOR_FOCUS_110", None)
    focus_names = set()
    if isinstance(focus, dict):
        if len(focus) != 11:
            rep.add("FAIL", f"config: SECTOR_FOCUS_110 has {len(focus)} "
                            f"sectors, expected 11")
        names = [x for xs in focus.values() for x in xs]
        focus_names = set(names)
        expected = getattr(t, "FOCUS_SIZE", 110)   # declared beside the set
        if len(names) != expected:
            rep.add("FAIL", f"config: SECTOR_FOCUS_110 holds {len(names)} "
                            f"names, expected {expected}")
        if len(set(names)) != len(names):
            dupes = sorted({n for n in names if names.count(n) > 1})
            rep.add("FAIL", f"config: SECTOR_FOCUS_110 repeats {dupes}")
        outside = sorted(set(names) - feed)
        if outside:
            rep.add("FAIL", f"config: focus names outside the price feed "
                            f"{outside} -- they would be scored without a bar")

    # The weekly writer has to fetch the whole feed. PRICE_FEED_UNIVERSE says
    # what the files commit; snapshot.equity_universe() is what the Saturday
    # job and a full backfill hand to the fetch, and it is another module.
    # From 2026-09-21 to 2026-10-06 it spelled the union out for itself,
    # without the Council watchlist: BTC and GLD were in the constant and in
    # the daily files, and in no weekly file.
    writer = None
    try:
        from scan_pipeline import snapshot
        writer = set(snapshot.equity_universe())
    except Exception as exc:                        # noqa: BLE001
        rep.add("FAIL", f"config: cannot ask scan_pipeline.snapshot which "
                        f"names the weekly writer fetches ({exc}), so the "
                        f"feed is not known to be fetched")
    if writer is not None:
        unfetched = feed - writer
        if unfetched:
            rep.add("FAIL", f"config: snapshot.equity_universe() leaves out "
                            f"{_name_list(unfetched)} of PRICE_FEED_UNIVERSE "
                            f"-- the weekly writer fetches that set, so a "
                            f"week it writes holds neither a bar nor a "
                            f"`missing` entry for them")

    # And the newest weekly file has to account for every one of those names:
    # a bar, or a `missing` entry that says why not. Until 2026-10-06 this
    # asked for the focus names only, so a feed name outside the focus set
    # could be in no weekly file at all and pass. The base file, not a
    # correction: this is about what the writer was asked to fetch.
    expected_names = feed | focus_names | (writer or set())
    weekly = repo / "data" / "weekly"
    files = sorted(weekly.glob("*.json")) if weekly.is_dir() else []
    files = [f for f in files if "corrected" not in f.name]
    if files and expected_names:
        doc = json.loads(files[-1].read_text(encoding="utf-8"))
        series = set(doc.get("series") or {})
        declared_missing = {m.get("ticker") for m in (doc.get("missing") or [])}
        absent = expected_names - series - declared_missing
        if absent:
            rep.add("FAIL", f"config: {files[-1].name} has no bar and no "
                            f"`missing` entry for {_name_list(absent)}, which "
                            f"the feed commits -- a silently absent ticker is "
                            f"the ambiguity the feed contract exists to "
                            f"remove. A name joins a week that exists through "
                            f"scripts/backfill_weekly.py --only <names> "
                            f"--merge (Actions -> Backfill weekly panel).")
    if rep.counts["FAIL"] == before:
        rep.add("OK", "config: docs, constants, the weekly writer and the "
                      "latest panel agree")


# --------------------------------------------------------------------- derive

DEFAULT_PIPELINE = ("C:/Users/alexa/Desktop/Death_Star/Ember/Professional/"
                    "BookApp/MarketStockPicker")


def check_derive(repo, pipeline, rep):
    """Derivation purity check (DATA_FEED.md sec.2: 'Derivation is pure').
    Re-derives market_state.json from the weekly files via the scan
    pipeline and compares against the committed file. Pipeline import
    failure is a WARN, not a FAIL -- the linter may run where the pipeline
    is not checked out."""
    ms = repo / "data" / "market_state.json"
    if not ms.exists():
        rep.add("SKIP", f"derive: {ms} not found -- nothing committed to "
                        f"re-derive yet")
        return
    if str(pipeline) not in sys.path:
        sys.path.insert(0, str(pipeline))
    try:
        from scan_pipeline import snapshot
    except Exception as e:
        rep.add("WARN", f"derive: scan_pipeline.snapshot not importable "
                        f"from {pipeline} ({type(e).__name__}: {e}) -- "
                        f"purity check deferred")
        return
    try:
        match, diff = snapshot.rederive_and_compare(
            weekly_dir=str(repo / "data" / "weekly"),
            facts_path=str(repo / "macro" / "facts.json"),
            market_state_path=str(ms))
    except Exception as e:
        rep.add("FAIL", f"derive: rederive_and_compare raised "
                        f"{type(e).__name__}: {e}")
        return
    if match:
        rep.add("OK", "derive: market_state.json re-derives byte-identical "
                      "from data/weekly/ -- derivation is pure")
    else:
        rep.add("FAIL", f"derive: market_state.json does not re-derive "
                        f"from data/weekly/ -- first difference at {diff}")


# ----------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Truth Layer validators")
    ap.add_argument("--version", action="version",
                    version=f"%(prog)s {VERSION}")
    ap.add_argument("--repo", required=True, help="local dir containing wiki/ and macro/")
    ap.add_argument("--staleness", action="store_true")
    ap.add_argument("--facts", action="store_true")
    ap.add_argument("--lint", action="store_true")
    ap.add_argument("--quarantine", action="store_true")
    ap.add_argument("--counterfactuals", action="store_true")
    ap.add_argument("--feed", action="store_true")
    ap.add_argument("--config", action="store_true")
    ap.add_argument("--splits", action="store_true")
    ap.add_argument("--derive", action="store_true")
    ap.add_argument("--pipeline", default=DEFAULT_PIPELINE,
                    help="scan_pipeline checkout root for --derive")
    ap.add_argument("--warn-days", type=int, default=7)
    ap.add_argument("--fail-days", type=int, default=14)
    ap.add_argument("--today", default=None, help="YYYY-MM-DD override (testing)")
    ap.add_argument("--max-fetch", type=int, default=60)
    args = ap.parse_args()

    repo = Path(args.repo)
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    run_all = not (args.staleness or args.facts or args.lint
                   or args.quarantine or args.counterfactuals
                   or args.feed or args.derive or args.config
                   or args.splits)
    rep = Report()

    if run_all or args.staleness:
        check_staleness(repo, today, args.warn_days, args.fail_days, rep)
    if run_all or args.facts:
        check_facts(repo, today, rep, args.max_fetch)
    if run_all or args.lint:
        check_lint(repo, rep, args.max_fetch)
    if run_all or args.quarantine:
        check_quarantine(repo, rep)
    if run_all or args.counterfactuals:
        check_counterfactuals(repo, today, rep)
    if run_all or args.feed:
        check_feed(repo, rep)
        check_weekly_completeness(repo, today, rep)
        check_us2y_history(repo, rep)
        check_commodity_history(repo, rep)
        check_feed(repo, rep, subdir="daily", require_friday=False,
                   label="daily")
        check_daily_freshness(repo, today, rep)
    if run_all or args.config:
        check_config(repo, rep)
    if run_all or args.splits:
        check_splits(repo, rep)
    if run_all or args.derive:
        check_derive(repo, args.pipeline, rep)

    print(rep.render())
    sys.exit(1 if rep.counts["FAIL"] else 0)


if __name__ == "__main__":
    main()
