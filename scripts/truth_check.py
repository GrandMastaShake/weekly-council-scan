#!/usr/bin/env python3
"""truth_check.py v5 -- Truth Layer validators for weekly-council-scan.

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
  --all         Everything (default when no mode flag is given).

Exit code 1 if any FAIL, else 0. Every line is prefixed OK/WARN/FAIL/SKIP.

Usage:
  python scripts/truth_check.py --repo <dir> [--staleness] [--facts] [--lint]
         [--quarantine] [--counterfactuals] [--warn-days 7] [--fail-days 14]
         [--today YYYY-MM-DD] [--max-fetch 60]
"""

import argparse
import datetime as dt
import json
import re
import sys
import urllib.request
from pathlib import Path

VERSION = "v5"

# ---------------------------------------------------------------- Yahoo fetch

_UA = {"User-Agent": "Mozilla/5.0"}
_fetch_cache = {}


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
        for t, c in zip(reversed(ts), reversed(closes)):
            if c is not None:
                day = dt.datetime.fromtimestamp(t + tz_off, tz=dt.timezone.utc).date()
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
    ap.add_argument("--warn-days", type=int, default=7)
    ap.add_argument("--fail-days", type=int, default=14)
    ap.add_argument("--today", default=None, help="YYYY-MM-DD override (testing)")
    ap.add_argument("--max-fetch", type=int, default=60)
    args = ap.parse_args()

    repo = Path(args.repo)
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    run_all = not (args.staleness or args.facts or args.lint
                   or args.quarantine or args.counterfactuals)
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

    print(rep.render())
    sys.exit(1 if rep.counts["FAIL"] else 0)


if __name__ == "__main__":
    main()
