#!/usr/bin/env python3
"""audit_series.py -- which session does a committed equity bar belong to?

A weekly file is named for a Friday and commits one close and one volume per
ticker in `series`. In the 105 backfilled files, and for every name merged
into a week afterwards, the writer was backfill_weekly.py::slice_week: the
last bar on or before the Friday, provided it fell inside the Mon..Fri week.
So a ticker with no Friday bar -- halted, delisted mid-week, a gap at the
provider -- carried an earlier session's close under the Friday date. The
only note the writer could leave was file-level, and only when NO ticker had
a Friday bar. scripts/audit_instruments.py measured the same habit in rates /
vol / commodities / fx. This is the other block, the one it left alone.

It left it alone for a reason. These closes are adjusted closes (yfinance
auto_adjust=True), back-adjusted to the day they were fetched, so a committed
close is SUPPOSED to differ from a fresh fetch for every name that has paid a
dividend or split since. "Differs from the provider" is true of more than
half the backfilled bars, every one of them the right session, and says
nothing. Two things do survive, and every bar is asked both:

    volume   is never dividend-adjusted. The committed volume is the volume
             of one session of the week, times any split since.
    close    differs from today's adjusted close FOR THE SAME SESSION by one
             factor per ticker and fetch date: the dividends gone ex since,
             and the splits applied since. The provider states that factor
             itself -- its Adj Close over its Close on the fetch date. So a
             committed close is today's adjusted close for one session times
             that factor, or it is no session's close.

Because the factor is the same for every week a ticker was fetched in one
run, this is also the test that the ratio between two committed weeks equals
the ratio between the provider's two closes; the factor only makes it work
for a week fetched on its own.

A session that fits both is the bar. The close alone decides only when the
volume fits no session at all -- restated since, or read before it was
final -- and those are counted, with the ones whose close is also another
session's of the same week counted apart.

    ok              the bar of the session the file names: as_of, or the
                    date in a holiday file's session_note. Not listed.
    prior_session   that session has a bar at the provider, and the committed
                    bar is an earlier session of the same week.
    stand_in        the provider has no bar for the ticker on that session --
                    it did not trade -- and the committed bar is an earlier
                    session of the week. What slice_week was written to do;
                    the file does not say that it did.
    other_session   the bar of a session the file does not name and that is
                    not earlier in its week: a day just outside it.
    differs         no session's close on the file's adjustment basis. The
                    provider restated the bar, or it was read before the
                    session was final.
    conflict        close and volume name different sessions. No session is
                    given; both are shown.
    unverified      the provider could not answer: it has no bar for the
                    ticker anywhere in the week, or the fetch failed. Never
                    read as ok.

What it cannot do is audit a ticker the provider has dropped. Of a delisted
symbol it keeps one bar, the last, and sometimes returns not even that; so
a dead ticker's weeks are unverified however ordinary they look. A bar with
no volume behind it is printed as such, because that is the one thing the
file can say for itself.

A run also reports its reach, because "none found" is worth what could have
been found: for every bar that passed, the session before it is put in its
place, as slice_week would have committed it, and the audit is asked again.

The baseline, macro/series_audit.json, is the reviewed list, and works as
macro/instrument_audit.json does: a run prints what is NEW, CHANGED or GONE
against it; --write replaces the findings, keeps every hand-written key, and
carries a cause forward only while its finding is unchanged.

Advisory: exit 0 whatever it finds. --strict exits 1 on anything new or
changed. Exit 2 means the provider answered for nothing.

Needs the network and yfinance (requirements-fetch.txt). The tests inject
the history and need neither.

Usage:
  python scripts/audit_series.py [--repo .] [--baseline macro/series_audit.json]
         [--all] [--json OUT] [--write] [--strict]
"""
from __future__ import annotations

import argparse
import datetime as dt
import itertools
import json
import os
import re
import sys
from bisect import bisect_right
from pathlib import Path

# Repo root = the nearest ancestor holding the scan_pipeline package. Copied
# from scripts/daily_observe.py for the reason given there.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PIPELINE_ROOT = _SCRIPT_DIR
while not os.path.isdir(os.path.join(_PIPELINE_ROOT, "scan_pipeline")):
    _parent = os.path.dirname(_PIPELINE_ROOT)
    if _parent == _PIPELINE_ROOT:
        raise RuntimeError(
            "cannot locate the scan_pipeline package above " + _SCRIPT_DIR)
    _PIPELINE_ROOT = _parent
if _PIPELINE_ROOT not in sys.path:
    sys.path.insert(0, _PIPELINE_ROOT)

# The baseline mechanics and the tolerance are the instrument audit's, so the
# two reviewed lists read, diff and round the same way.
import audit_instruments as ai  # noqa: E402
from scan_pipeline.config.tickers import RENAMED, later_symbols  # noqa: E402
from scan_pipeline.snapshot import PROVIDER  # noqa: E402

BASELINE = ("macro", "series_audit.json")
PANEL = "weekly"
BLOCK = "series"

CLASSES = ("prior_session", "stand_in", "other_session", "differs",
           "conflict", "unverified")
# Who wrote a bar: slice_week with the file, slice_week into an existing
# week (provenance.series), or the Friday job.
ORIGINS = ("backfill", "merged", "live")
# Counted per origin: bars compared, bars that are the named session's, and
# how many of those rest on the close alone.
TALLY = ("bars", "ok", "close_alone")
# What the audit could have found (reach): ok bars that have an earlier
# session in their week, how many times that session is named when it is put
# in their place, and how many of those the close alone would miss.
REACH = ("tried", "named", "blind_on_close")

# A ticker whose history the provider now serves under another symbol:
# RENAMED in scan_pipeline/config/tickers.py, the copy the merge reads too
# (scripts/backfill_weekly.py refuses to add a symbol where the panel holds
# its company under another). EQR was the surviving company of the AVB
# merger and trades as VMRK from 2026-08-18 (wiki/universe.md); the provider
# moved its whole history there and keeps at most EQR's last bar. Nothing is
# taken on trust by listing a name here: every committed bar still has to
# match the successor's bar for its session in close and volume, and EQR's
# 105 do. BK, MMC and PEAK are in the map and in no file's `series`, so the
# audit never meets them. AVB, the company that was absorbed, has no
# successor: its history is gone.
SUCCESSORS = RENAMED


def successor(ticker):
    """The symbol that carries `ticker`'s history today: the end of its
    chain in RENAMED, or the ticker itself."""
    later = later_symbols(ticker)
    return later[-1] if later else ticker


# The provider took more than two weeks to carry MNST's 2026-08-11 split back
# through its history: bars fetched on 08-12 and on 08-27 are still on the
# old basis. A split this recent at fetch time may or may not be in the file.
SPLIT_LAG_DAYS = 35

CHUNK = 50

_NOTE_DATE = re.compile(r"bars from (\d{4}-\d{2}-\d{2})")

HEADINGS = {
    "prior_session": "PRIOR SESSION -- the named session has a bar, and the "
                     "committed one is an earlier day of its week",
    "stand_in": "STAND-IN -- the ticker did not trade on the named session; "
                "the committed bar is an earlier day of its week, and the "
                "file does not say so",
    "other_session": "OTHER SESSION -- the bar of a session the file does "
                     "not name",
    "differs": "DIFFERS -- no session's close on the file's adjustment basis "
               "(restated since, or read before the session was final)",
    "conflict": "CONFLICT -- close and volume name different sessions",
    "unverified": "UNVERIFIED -- the provider could not answer; this is not "
                  "an ok",
}


# ----------------------------------------------------------------- provider

def _subframe(frame, symbol):
    """One symbol's columns from a yf.download result. As in
    scripts/backfill_weekly.py: a batch comes back MultiIndexed either way
    round, a single symbol sometimes plain."""
    import pandas as pd

    if frame is None or len(frame) == 0:
        return None
    if isinstance(frame.columns, pd.MultiIndex):
        if symbol in frame.columns.get_level_values(0):
            return frame[symbol]
        if symbol in frame.columns.get_level_values(-1):
            return frame.xs(symbol, axis=1, level=-1)
        return None
    return frame


def _bars(sub):
    """{iso_date: (adj_close, close, volume, split)} from one symbol's frame.
    A row with no close is no bar, which is how the writer read it too. A
    split dated on such a row is not lost with it: it moves to the next bar,
    which is the same thing to every bar before it."""
    out = {}
    if sub is None:
        return out
    carried = 0.0
    for idx, row in sub.iterrows():
        split = row.get("Stock Splits")
        split = 0.0 if split is None or split != split else float(split)
        adj, close = row.get("Adj Close"), row.get("Close")
        if adj is None or close is None or adj != adj or close != close:
            if split:
                carried = split * (carried or 1.0)
            continue
        if carried:
            split, carried = carried * (split or 1.0), 0.0
        volume = row.get("Volume")
        out[idx.date().isoformat()] = (
            float(adj), float(close),
            None if volume is None or volume != volume else int(volume),
            split)
    return out


def fetch_history(symbols, start, end):
    """{symbol: {iso_date: (adj_close, close, volume, split)}}, raw.

    yf.download in batches, the accessor the backfill writer used, with
    auto_adjust off so that both closes come back: "Adj Close" is the number
    auto_adjust=True commits as the close, "Close" is the same bar before
    dividends, and their ratio is the provider's adjustment factor. A symbol
    that returns nothing is asked once more on its own and then left out,
    and the caller reports its bars unverified. The second ask is not a
    courtesy: in a batch of fifty the provider returned nothing for AVB or
    EA, and asked alone it returned the last bar of each."""
    import yfinance as yf

    def download(what, threads):
        try:
            return yf.download(what, start=start, end=end, interval="1d",
                               group_by="ticker", auto_adjust=False,
                               actions=True, progress=False, threads=threads)
        except Exception:               # one dead batch must not end the audit
            return None

    symbols = sorted(symbols)
    out = {}
    for i in range(0, len(symbols), CHUNK):
        chunk = symbols[i:i + CHUNK]
        frame = download(chunk, True)
        for symbol in chunk:
            bars = _bars(_subframe(frame, symbol))
            if bars:
                out[symbol] = bars
    for symbol in symbols:
        if symbol not in out:
            bars = _bars(_subframe(download(symbol, False), symbol))
            if bars:
                out[symbol] = bars
    return out


# -------------------------------------------------------------------- panel

def named_session(doc):
    """The session a file says its equity bars are from: as_of, unless a
    file-level session_note names another day (the five holiday Fridays)."""
    note = doc.get("session_note")
    found = _NOTE_DATE.search(note) if isinstance(note, str) else None
    return found.group(1) if found else doc["as_of"]


def bars_of(doc):
    """(ticker, entry, origin, fetched_at) for every series bar of one file.

    A bar named in provenance.series was merged in later and carries its own
    fetch time, which is its adjustment anchor. Every other bar carries the
    file's."""
    labels = (doc.get("provenance") or {}).get(BLOCK) or {}
    backfilled = str(doc.get("source") or "").endswith("-backfill")
    for ticker, entry in sorted((doc.get(BLOCK) or {}).items()):
        label = labels.get(ticker)
        if isinstance(label, dict) and label.get("fetched_at"):
            yield ticker, entry, "merged", label["fetched_at"]
        else:
            yield (ticker, entry, "backfill" if backfilled else "live",
                   doc.get("fetched_at"))


# ------------------------------------------------------------------- basis

def _recent(split, at):
    """Whether a split is dated on `at` or in the SPLIT_LAG_DAYS before it."""
    gap = (dt.date.fromisoformat(at) - dt.date.fromisoformat(split)).days
    return 0 <= gap < SPLIT_LAG_DAYS


def bases(history, fetched_at):
    """[(day, pending)]: every adjustment basis a bar fetched at `fetched_at`
    can be on, according to the provider's own record.

    day is the session whose Adj Close / Close is the factor in force, which
    is the dividends gone ex since: the last session dated on or before the
    fetch date. When the fetch date is itself a session the one before it is
    offered too, because the stamp is a UTC time and a dividend enters the
    history some hours into its ex-date. A Saturday fetch has no such doubt.

    pending is the split dates the file's numbers do not carry and the
    provider's now do: the splits after the fetch. A recent split is unsure
    either way. One just before the fetch may not have been in the history
    yet, and one just before the provider's newest bar may not be in it even
    now. Every combination of the unsure ones is offered, the likeliest
    first."""
    if not isinstance(fetched_at, str):
        return []
    days = sorted(history)
    stamp = fetched_at[:10]
    i = bisect_right(days, stamp) - 1
    if i < 0:
        return []
    anchors = days[max(0, i - 1):i + 1] if days[i] == stamp else [days[i]]
    splits = [d for d in days if history[d][3]]
    out = []
    for day in anchors:
        if not (history[day][0] > 0 and history[day][1] > 0):
            continue
        after = [d for d in splits if d > day]
        late = [d for d in after if _recent(d, days[-1])]
        unsure = ([d for d in splits if d <= day and _recent(d, day)]
                  + late)[-4:]
        settled = [d for d in after if d not in unsure]
        for flips in itertools.product((False, True), repeat=len(unsure)):
            # Unflipped is the ordinary case: a split after the fetch has
            # reached the history by now, one before it had by then.
            picked = [d for d, flip in zip(unsure, flips)
                      if (d > day) != flip]
            basis = (day, tuple(sorted(settled + picked)))
            if basis not in out:
                out.append(basis)
    return out


def rebased(history, session, basis):
    """(close, scale) of the provider's bar for `session` on `basis`: the
    close a fetch on that basis would have committed for that session, and
    the factor that takes a committed volume to the provider's.

    A bar is never adjusted for a dividend that went ex on or before its own
    date, so the factor is read no earlier than the session itself. close is
    None where the provider's own numbers give no factor."""
    day, pending = basis
    at = max(day, session)
    adj_at, close_at = history[at][0], history[at][1]
    scale = 1.0
    for split in pending:
        if split > session:
            scale *= history[split][3]
    if not (adj_at > 0 and close_at > 0):
        return None, scale
    return history[session][0] * scale * close_at / adj_at, scale


# ----------------------------------------------------------------- classify

def close_basis(close, history, session, basis_list):
    """The first basis on which `close` is the close of `session`, or None."""
    for basis in basis_list:
        theirs = rebased(history, session, basis)[0]
        if theirs is not None and ai.same(close, theirs):
            return basis
    return None


def volume_fits(volume, history, session, basis_list):
    """Whether `volume` is the volume of `session` on any basis.

    Compared in the provider's units, to half a share either side of the
    split: after a reverse split the provider has rounded its own figure,
    and dividing that back out would miss by the rounding."""
    theirs = history[session][2]
    if volume is None or theirs is None:
        return False
    for basis in basis_list:
        scale = rebased(history, session, basis)[1]
        if abs(volume * scale - theirs) <= 0.5 * max(1.0, scale):
            return True
    return False


def classify(close, volume, as_of, named, history, basis_list):
    """(class, session, witnesses) for one committed bar. Pure.

    `named` is the session the file says the bar is from. `session` is the
    session the bar actually is, or None. A session that fits both close and
    volume is the bar, wherever it is; the close alone decides only when the
    volume fits nothing."""
    if not basis_list:
        return "unverified", None, None
    day = dt.date.fromisoformat(as_of)
    monday = (day - dt.timedelta(days=day.weekday())).isoformat()
    # No bar is from a session after it was fetched.
    limit = max(basis[0] for basis in basis_list)
    week = sorted(d for d in history if monday <= d <= min(as_of, limit))

    def by_close(session):
        return close_basis(close, history, session, basis_list) is not None

    def by_volume(session):
        return volume_fits(volume, history, session, basis_list)

    def nearest(days):
        return min(days, key=lambda d: (
            abs((dt.date.fromisoformat(d) - day).days), d))

    closes = [d for d in week if by_close(d)]
    volumes = [d for d in week if by_volume(d)]
    both = [d for d in closes if d in volumes]
    if named in both:
        return "ok", named, "close+volume"

    lo = (day - dt.timedelta(days=ai.NEAR_DAYS)).isoformat()
    hi = min((day + dt.timedelta(days=ai.NEAR_DAYS)).isoformat(), limit)
    near = [d for d in sorted(history) if lo <= d <= hi and d not in week]
    if not both:
        outside = [d for d in near if by_close(d) and by_volume(d)]
        if outside:
            return "other_session", nearest(outside), "close+volume"
        if named in closes and not volumes:
            # The named session's close. A volume that fits no session has
            # been restated since, or was read before it was final; it is
            # not evidence of another day. Where another session of the week
            # closed at the same price the close cannot say which bar this
            # is, and that is said.
            return "ok", named, "close, tied" if len(closes) > 1 else "close"
    if closes:
        if volumes and not both:
            return "conflict", None, "close is %s's, volume is %s's" % (
                closes[-1], volumes[-1])
        session = (both or closes)[-1]
        if session > named:
            cls = "other_session"
        else:
            cls = "prior_session" if named in history else "stand_in"
        return cls, session, "close+volume" if both else "close"

    hits = [d for d in near if by_close(d)]
    if hits:
        if volumes:
            return "conflict", None, "close is %s's, volume is %s's" % (
                nearest(hits), volumes[-1])
        return "other_session", nearest(hits), "close"
    if not week:
        # Nothing to differ from. The provider keeps one bar of a delisted
        # symbol, its last, so most of a dead ticker's weeks end here.
        return "unverified", None, None
    return "differs", (volumes[-1] if len(volumes) == 1 else None), (
        "volume" if len(volumes) == 1 else None)


def reach(close, as_of, named, history, basis_list):
    """Would an ok bar have been caught, had it been the session before?

    "None found" is worth what the audit could have found. So for a bar that
    passed, the previous session of its week is put in its place -- on the
    basis the real bar is on, rounded as the writer rounds, which is what
    slice_week commits when the named session has no bar -- and asked about.
    Returns (named, blind): whether that session is named, and whether the
    close alone would have let it through, which it does when the close did
    not change. None when the week has no earlier session."""
    day = dt.date.fromisoformat(as_of)
    monday = (day - dt.timedelta(days=day.weekday())).isoformat()
    earlier = [d for d in history if monday <= d < named]
    basis = close_basis(close, history, named, basis_list)
    if not earlier or basis is None:
        return None
    before = max(earlier)
    stand, scale = rebased(history, before, basis)
    if stand is None:
        return None
    stand = round(stand, 4)
    volume = history[before][2]
    if volume is not None:
        volume = int(round(volume / scale))
    cls, session, _ = classify(stand, volume, as_of, named, history,
                               basis_list)
    blind = classify(stand, None, as_of, named, history,
                     basis_list)[0] == "ok"
    return cls == "prior_session" and session == before, blind


def provider_bar(close, session, named, history, basis_list):
    """The provider's bar for the named session, as the file would hold it:
    on the basis the committed bar is on where its close says which that is,
    and failing that on whichever brings the named close nearest."""
    basis = None
    if session in history:
        basis = close_basis(close, history, session, basis_list)
    if basis is None:
        def gap(candidate):
            theirs = rebased(history, named, candidate)[0]
            return float("inf") if theirs is None else abs(theirs - close)
        basis = min(basis_list, key=gap)
    theirs, scale = rebased(history, named, basis)
    volume = history[named][2]
    return {"close": None if theirs is None else round(theirs, 4),
            "volume": None if volume is None else int(round(volume / scale))}


def audit_file(name, doc, histories, failed):
    """Findings for one file, and its counts by origin."""
    as_of = doc["as_of"]
    named = named_session(doc)
    counts = {o: dict.fromkeys(TALLY, 0) for o in ORIGINS}
    counts.update({"named_by_note": 0, "tied": 0, "no_volume": [],
                   "reach": dict.fromkeys(REACH, 0)})
    findings = []
    for ticker, entry, origin, fetched_at in bars_of(doc):
        if not isinstance(entry, dict) or entry.get("close") is None:
            continue                    # check_feed's to report
        counts[origin]["bars"] += 1
        close = float(entry["close"])
        committed = {"close": entry["close"], "volume": entry.get("volume")}
        if not committed["volume"]:
            counts["no_volume"].append(name + " " + ticker)
        symbol = successor(ticker)
        finding = {
            "panel": PANEL, "file": name,
            "instrument": BLOCK + "." + ticker, "origin": origin,
            "fetched_at": fetched_at, "class": None, "committed": committed,
            "provider": None, "session": None,
        }
        if symbol != ticker:
            finding["symbol"] = symbol
        if named != as_of:
            finding["session_note"] = doc.get("session_note")

        history = histories.get(symbol) or {}
        basis_list = bases(history, fetched_at)
        cls, session, witnesses = classify(
            close, committed["volume"], as_of, named, history, basis_list)
        if cls == "ok":
            counts[origin]["ok"] += 1
            counts[origin]["close_alone"] += witnesses != "close+volume"
            counts["tied"] += witnesses == "close, tied"
            counts["named_by_note"] += named != as_of
            tried = reach(close, as_of, named, history, basis_list)
            if tried:
                counts["reach"]["tried"] += 1
                counts["reach"]["named"] += tried[0]
                counts["reach"]["blind_on_close"] += tried[1]
            continue
        finding["class"] = cls
        finding["session"] = session
        if witnesses:
            finding["witnesses"] = witnesses
        if cls != "unverified":
            if named in history:
                finding["provider"] = provider_bar(close, session, named,
                                                   history, basis_list)
        elif symbol in failed:
            finding["reason"] = "the provider returns no history for " + symbol
        elif history and not basis_list:
            finding["reason"] = ("no usable " + symbol + " bar on or before "
                                 "the fetch date to take the adjustment "
                                 "factor from")
        else:
            finding["reason"] = ("the provider has no " + symbol
                                 + " bar in the file's week")
        findings.append(finding)
    return findings, counts


def history_window(docs, now):
    """One ranged request covers every file and every fetch date: from the
    Monday before the first week, as the instrument audit starts on one, to
    tomorrow, so that the factor on the newest fetch date is in it."""
    first = min(dt.date.fromisoformat(doc["as_of"]) for _, doc in docs)
    first -= dt.timedelta(days=ai.NEAR_DAYS)
    start = first - dt.timedelta(days=first.weekday())
    return start.isoformat(), (now.date() + dt.timedelta(days=1)).isoformat()


def run_audit(repo, fetch=fetch_history, now=None):
    """Audit data/weekly. Returns the generated part of the baseline:
    {"audited": {...}, "findings": [...]}."""
    now = now or dt.datetime.now(dt.timezone.utc)
    loaded = ai.load_panel(repo, PANEL)
    counts = {"files": len(loaded), "too_recent": []}
    counts.update(dict.fromkeys(TALLY, 0))
    counts.update({o: dict.fromkeys(TALLY, 0) for o in ORIGINS})
    counts.update({"named_by_note": 0, "tied": 0, "no_volume": [],
                   "reach": dict.fromkeys(REACH, 0)})
    counts.update({c: 0 for c in CLASSES})
    result = {
        "audited": {
            "provider": PROVIDER,
            "fetched_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "yfinance": ai.provider_version(),
            "tickers": {"asked": 0, "answered": 0, "failed": {},
                        "through_successor": {}},
            PANEL: counts,
        },
        "findings": [],
    }
    # A bar the provider may still change is not judged against it: the
    # writer's own rule for when a session is final (DATA_FEED.md sec.1b).
    ready = []
    for name, doc in loaded:
        if now < ai.settled_at(doc["as_of"]):
            counts["too_recent"].append(name)
        else:
            ready.append((name, doc))
    if not ready:
        return result

    tickers = sorted({t for _, doc in ready for t in doc.get(BLOCK) or {}})
    symbols = sorted({successor(t) for t in tickers})
    start, end = history_window(ready, now)
    try:
        histories = fetch(symbols, start, end) or {}
        error = None
    except Exception as exc:
        histories = {}
        error = "%s: %s" % (type(exc).__name__, str(exc)[:120])
    failed = {s: error or "no history returned for %s..%s" % (start, end)
              for s in symbols if not histories.get(s)}
    result["audited"]["tickers"] = {
        "asked": len(symbols), "answered": len(symbols) - len(failed),
        "failed": failed,
        "through_successor": {t: successor(t) for t in tickers
                              if successor(t) != t}}

    corrected = {name[:-len(".corrected.json")] for name, _ in ready
                 if name.endswith(".corrected.json")}
    for name, doc in ready:
        found, got = audit_file(name, doc, histories, failed)
        for origin in ORIGINS:
            for key in TALLY:
                counts[origin][key] += got[origin][key]
                counts[key] += got[origin][key]
        for key in ("named_by_note", "tied", "no_volume"):
            counts[key] += got[key]         # two counts, and a list of bars
        for key in REACH:
            counts["reach"][key] += got["reach"][key]
        for finding in found:
            counts[finding["class"]] += 1
            stem = name[:-len(".json")]
            if stem in corrected:
                # Readers prefer the correction, so say that the base
                # file's finding is not the one they see.
                finding["superseded_by"] = stem + ".corrected.json"
            result["findings"].append(finding)
    result["findings"].sort(key=ai._key)
    return result


# ----------------------------------------------------------------- baseline

def _same_finding(a, b):
    """Whether a finding on file and a fresh one are the same finding. The
    provider's close is part of it, compared as closes are: it is rebuilt
    from a factor on every run and its last decimal is the float's."""
    if (a["class"], a.get("session")) != (b["class"], b.get("session")):
        return False
    if (a.get("committed") or {}).get("close") != \
            (b.get("committed") or {}).get("close"):
        return False
    old = (a.get("provider") or {}).get("close")
    new = (b.get("provider") or {}).get("close")
    if old is None or new is None:
        return old is new
    return ai.same(old, new)


def compare(baseline, current):
    """(new, changed, gone, known) between a baseline and a fresh run.

    An unverified finding is never evidence that a baseline entry is gone:
    the provider not answering today says nothing about last month."""
    old = {ai._key(f): f for f in (baseline or {}).get("findings", [])}
    new, changed, known = [], [], []
    seen = set()
    for finding in current["findings"]:
        key = ai._key(finding)
        seen.add(key)
        if key not in old:
            new.append(finding)
        elif finding["class"] == "unverified" \
                and old[key]["class"] != "unverified":
            known.append(old[key])
        elif not _same_finding(old[key], finding):
            changed.append((old[key], finding))
        else:
            known.append(finding)
    gone = [f for key, f in sorted(old.items()) if key not in seen]
    return new, changed, gone, known


def write_baseline(path, result, previous):
    """Replace the generated keys, keep every hand-written one in place. A
    cause survives only while its finding is the same finding.

    A finding on file that the provider would not answer for today is
    carried over as it stands, cause and all, and named in audited.carried.
    The provider answers unevenly for a dead symbol, and writing
    "unverified" over a reviewed finding would erase exactly what compare()
    takes care not to call gone."""
    reviewed = {ai._key(f): f for f in (previous or {}).get("findings", [])}
    audited = json.loads(json.dumps(result["audited"]))
    audited["carried"] = []
    findings = []
    for finding in result["findings"]:
        was = reviewed.get(ai._key(finding))
        if was is not None and finding["class"] == "unverified" \
                and was["class"] != "unverified":
            audited[PANEL]["unverified"] -= 1
            audited[PANEL][was["class"]] += 1
            audited["carried"].append(was["file"] + " " + was["instrument"])
            findings.append(was)
            continue
        kept = was is not None and _same_finding(was, finding)
        findings.append(dict(finding,
                             cause=was.get("cause") if kept else None))
    doc = dict(previous or {})
    doc.setdefault("_purpose", (
        "Reviewed answers to one question about the committed equity bars "
        "(`series` in data/weekly): is each the bar of the session its file "
        "names, as scripts/audit_series.py found. An entry is a statement "
        "that the bar was looked at, not that it was fixed: the files are "
        "observations and are never edited (DATA_FEED.md sec.1)."))
    doc.setdefault("_regenerate", (
        "python scripts/audit_series.py --write   (replaces 'audited' and "
        "'findings', keeps everything else; review what is NEW first)"))
    doc.setdefault("causes", {})
    doc["audited"] = audited
    doc["findings"] = findings
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(ai.dump_baseline(doc), encoding="utf-8", newline="\n")
    return path


# ------------------------------------------------------------------- report

def line_for(finding):
    committed = finding.get("committed") or {}
    provider = finding.get("provider") or {}
    ticker = finding["instrument"].split(".", 1)[1]
    if finding.get("symbol"):
        ticker += " (as " + finding["symbol"] + ")"
    parts = ["  %-25s %-8s %-8s" % (finding["file"], ticker,
                                    finding["origin"]),
             "committed %10s" % ai._num(committed.get("close")),
             "vol %s" % committed.get("volume")]
    if not committed.get("volume"):
        parts.append("(NO VOLUME BEHIND IT)")
    if finding.get("session"):
        parts.append("= " + finding["session"]
                     + " by " + (finding.get("witnesses") or "?"))
    elif finding.get("witnesses"):
        parts.append("(" + finding["witnesses"] + ")")
    if provider:
        parts.append("named session %10s vol %s"
                     % (ai._num(provider.get("close")),
                        provider.get("volume")))
        if provider.get("close"):
            diff = committed["close"] - provider["close"]
            parts.append("(%+.4f, %+.3f%%)"
                         % (diff, 100.0 * diff / provider["close"]))
    if finding.get("reason"):
        parts.append("[" + finding["reason"] + "]")
    if finding.get("session_note"):
        parts.append("[" + finding["session_note"] + "]")
    if finding.get("fetched_at"):
        parts.append("fetched " + finding["fetched_at"])
    if finding.get("superseded_by"):
        parts.append("(superseded by " + finding["superseded_by"] + ")")
    return " ".join(parts)


def unverified_lines(rows):
    """A dropped ticker is unverified in every file that carries it, for one
    reason. Print the run of them as one line, and separately only the bars
    that say something on their own: the ones with no volume behind them."""
    out, runs = [], {}
    for finding in rows:
        if not (finding.get("committed") or {}).get("volume"):
            out.append(line_for(finding))
            continue
        key = (finding["instrument"], finding.get("reason"))
        runs.setdefault(key, []).append(finding["file"])
    for (instrument, reason), files in sorted(runs.items()):
        out.append("  %-8s %d bar(s), %s .. %s [%s]"
                   % (instrument.split(".", 1)[1], len(files), files[0],
                      files[-1], reason))
    return out


def render(result, baseline, show_all):
    out = []
    audited = result["audited"]
    asked = audited["tickers"]
    c = audited[PANEL]
    out.append("audit_series: provider history fetched %s (yfinance %s), "
               "%d of %d symbol(s) answered"
               % (audited["fetched_at"], audited.get("yfinance"),
                  asked["answered"], asked["asked"]))
    for symbol, why in asked["failed"].items():
        out.append("  NO ANSWER for %s: %s" % (symbol, why))
    for ticker, symbol in asked["through_successor"].items():
        out.append("  %s is audited against %s, which carries its history"
                   % (ticker, symbol))
    out.append("%s: %d file(s), %d series bar(s): %d are the session the "
               "file names, %d not"
               % (PANEL, c["files"], c["bars"], c["ok"],
                  c["bars"] - c["ok"]))
    for origin, what in (("backfill", "slice_week, with the file"),
                         ("merged", "slice_week, added afterwards"),
                         ("live", "the Friday job")):
        out.append("  %-9s %6d bar(s) %6d ok %5d not   %5d of the ok on the "
                   "close alone   (%s)"
                   % (origin, c[origin]["bars"], c[origin]["ok"],
                      c[origin]["bars"] - c[origin]["ok"],
                      c[origin]["close_alone"], what))
    out.append("  %d of the ok are the session a holiday file's note names; "
               "the close alone means the volume fits no session (restated "
               "since, or not final when read)" % c["named_by_note"])
    out.append("  %d of those on the close alone share that close with "
               "another session of the week, so nothing says which of the "
               "two bars it is" % c["tied"])
    out.append("  %d committed bar(s) have no volume behind them%s"
               % (len(c["no_volume"]),
                  ": " + ", ".join(c["no_volume"]) if c["no_volume"] else ""))
    out.append("  reach: with the session before it put in place of each of "
               "%d ok bar(s), that session is named %d time(s); on the close "
               "alone %d would pass, the close not having changed"
               % (c["reach"]["tried"], c["reach"]["named"],
                  c["reach"]["blind_on_close"]))
    for cls in CLASSES:
        if c[cls]:
            out.append("  %-15s %d" % (cls, c[cls]))
    if c["too_recent"]:
        out.append("  NOT AUDITED, the session is not final at the provider "
                   "yet: " + ", ".join(c["too_recent"]))

    new, changed, gone, known = compare(baseline, result)
    if baseline is None:
        out.append("no baseline: every finding below is unreviewed")
    else:
        out.append("against the baseline: %d new, %d changed, %d gone, "
                   "%d known" % (len(new), len(changed), len(gone),
                                 len(known)))
        pending = ai.unreviewed(baseline)
        if pending:
            out.append("%d finding(s) on file have no cause yet: %s"
                       % (len(pending), ", ".join(
                           "%s %s" % (f["file"], f["instrument"])
                           for f in pending[:6])
                          + (" ..." if len(pending) > 6 else "")))

    listed = result["findings"] if show_all or baseline is None else new
    if listed:
        out.append("")
        out.append("ALL FINDINGS" if show_all or baseline is None else "NEW")
    for cls in CLASSES:
        rows = [f for f in listed if f["class"] == cls]
        if rows:
            out.append(HEADINGS[cls])
            out.extend(unverified_lines(rows) if cls == "unverified"
                       else [line_for(f) for f in rows])
    if changed:
        out.append("")
        out.append("CHANGED since the baseline")
        for was, now in changed:
            out.append(line_for(now))
            out.append("      was: " + line_for(was).strip())
    if gone:
        out.append("")
        out.append("GONE -- in the baseline, not reproduced (a correction "
                   "landed, or the provider restated again)")
        out.extend(line_for(f) for f in gone)
    return "\n".join(out), (new, changed, gone, known)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Audit committed equity bars against the provider.")
    ap.add_argument("--repo", default=".", help="repo root (default: .)")
    ap.add_argument("--baseline", default=None,
                    help="reviewed findings (default: <repo>/%s)"
                         % "/".join(BASELINE))
    ap.add_argument("--all", action="store_true",
                    help="list every finding, not only what is new")
    ap.add_argument("--json", default=None, help="also write the run here")
    ap.add_argument("--write", action="store_true",
                    help="write this run to the baseline")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if anything is new or changed")
    args = ap.parse_args(argv)

    repo = Path(args.repo)
    baseline_path = Path(args.baseline) if args.baseline \
        else repo.joinpath(*BASELINE)
    baseline = ai.read_baseline(baseline_path)

    result = run_audit(repo)
    asked = result["audited"]["tickers"]
    if asked["asked"] and not asked["answered"]:
        # Every bar would be listed unverified; say the one thing instead.
        print("NOTHING AUDITED: the provider answered for no symbol.")
        return 2
    text, (new, changed, gone, known) = render(result, baseline, args.all)
    print(text)

    if args.json:
        Path(args.json).write_text(
            json.dumps(result, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8", newline="\n")

    if args.write:
        if not asked["asked"]:
            print("REFUSED: no file was audited, and a baseline written from "
                  "nothing would say every finding on file is gone.")
            return 2
        write_baseline(baseline_path, result, baseline)
        print("Wrote " + str(baseline_path))
        return 0
    if args.strict and (new or changed):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
