"""backfill_commodities.py -- settlements of the nearest-expiry contract for
weeks whose weekly file cannot supply one.

WTI, GOLD and SILVER are named contracts since 2026-10-05: the listed month
with the earliest last trade date on or after the session, read under its
own symbol, with the contract committed in provenance.commodities (see
"Named contracts" in scan_pipeline/snapshot_macro.py). Every weekly file
through 2026-10-02 holds a continuous symbol's bar instead and names
nothing. Those files are observations and are never edited, so what a
reader needs to know about them lives beside them in
<data>/commodity_settlements.json, and snapshot.commodity_series() is the
one reader:

  * "audited_through": the committed closes up to this week were audited
    against the rule (macro/instrument_audit.json, 2026-10-05) and may be
    read without a label, except the weeks listed below;
  * "series": the settlement for a week whose committed close is NOT the
    nearest-expiry contract's, or has no label and came after the audit, or
    is missing from its file;
  * "unavailable": a week for which no such settlement can be had, and why.

This writes that file. Three things it does, and one it does not:

  * By default it fills gaps: a week after "audited_through" where an
    instrument has no labelled close in its own file and no entry here. That
    is a Friday the fetch failed, a Friday that was a contract's last day
    (read on the Saturday, after the provider had dropped it), or a file
    written by a runner still on the old writer.
  * --week and --instrument add an entry for one named week. This is how a
    committed close that is not the rule's contract is superseded, so it
    needs --reason, and the entry records what it replaces.
  * --unavailable records that a week has no settlement, after showing it:
    the provider answers with nothing for the contract, and the continuous
    symbol cannot be shown to have held it.
  * It never rewrites an entry. Append-only, like the panel beside it.
    --check re-reads the provider and REPORTS a difference.

A settlement is read by contract name through the writer's own fetch, so the
writer's rules hold here too: the bar dated the week's as_of or a proven
stand-in from the same week, and nothing the exchange has not settled.

The provider drops a contract within days of its last trade, so an old week
usually cannot be read by name. --from-continuous allows the continuous
symbol to answer instead, on proof and never by default: its bars for the
sessions after that contract expired must be the next contract's, by name.
That shows the continuous history was the nearest-expiry chain at that roll,
which is all that makes its earlier bar the expired month's. GC=F fails the
test today (it holds the active month), and so cannot stand in for gold.
An entry read this way names the contract the calendar gives; "symbol" says
it was the continuous symbol that answered.

A new entry changes what market_state.json should say, so after a write the
state is re-derived through the whole chain.

CLI:
  python scripts/backfill_commodities.py [--data data] [--facts PATH]
         [--dry-run] [--check]
  python scripts/backfill_commodities.py --week 2026-09-18 --instrument WTI \\
         --reason "..." [--from-continuous | --unavailable]

  --data     the data root; reads <data>/weekly, writes
             <data>/commodity_settlements.json and re-derives
             <data>/market_state.json
  --facts    macro facts for the re-derive (default: macro/facts.json
             beside the data root)
  --dry-run  fetch and report; write nothing
  --check    compare every committed settlement that can still be asked
             about against the provider; exit 1 on any difference; write
             nothing
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

# Repo root = the nearest ancestor holding the scan_pipeline package. Copied
# from scripts/backfill_weekly.py deliberately; see the note there.
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
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from scan_pipeline import snapshot          # noqa: E402
from scan_pipeline import snapshot_macro    # noqa: E402
import rederive_market_state                # noqa: E402

SCHEMA = "commodity-settlements/v1"
SOURCE = snapshot.PROVIDER + "-backfill"            # "yahoo-backfill"
BLOCK = "commodities"
INSTRUMENTS = snapshot_macro.INSTRUMENTS[BLOCK]

# The last weekly file the audit of 2026-10-05 covered, and the last one
# written before contracts were named. Used once, when the file is created.
AUDITED_THROUGH = "2026-10-02"

# Equal, for a committed close and a fresh one: the float32 the provider
# serves, rounded to 4 dp (scripts/audit_instruments.py has the reasoning).
TOL_ABS = 1.5e-4
TOL_REL = 2e-6

# The continuous symbol has to match the next contract on every settled
# session in this many days after the expired one's last trade, and on at
# least PROOF_MIN of them.
PROOF_DAYS = 7
PROOF_MIN = 2

ABOUT = (
    "Settlements of the nearest-expiry contract for WTI, WTI_NEXT, GOLD and "
    "SILVER, for the weeks whose weekly file does not name its contract or "
    "does not hold that contract's settlement. Weekly files through "
    "2026-10-02 carry a continuous symbol's bar and are never edited; "
    "'audited_through' is the last week whose committed close may be read "
    "without a label, 'series' supersedes a committed close or supplies a "
    "missing one (keyed by the weekly file's as_of; 'replaces' is what the "
    "file holds), and 'unavailable' lists weeks for which no settlement of "
    "the rule's contract can be had. An entry whose 'symbol' is a "
    "continuous one names the contract the calendar gives; the provider no "
    "longer listed it to confirm. Append-only. Written by "
    "scripts/backfill_commodities.py; read by snapshot.commodity_series(). "
    "DATA_FEED.md sec.1d."
)


class Refused(RuntimeError):
    """The entry was not written, and why."""


def _stamp(now: dt.datetime) -> str:
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def same(a: float, b: float) -> bool:
    return abs(a - b) <= max(TOL_ABS, TOL_REL * abs(b))


def empty_history() -> dict:
    doc = {"schema": SCHEMA, "rule": "nearest-expiry", "session": "close",
           "about": ABOUT, "instruments": {}}
    for ticker, cfg in INSTRUMENTS.items():
        rec = {"root": cfg["root"], "audited_through": AUDITED_THROUGH,
               "series": {}, "unavailable": {}}
        if cfg.get("continuous"):
            rec["continuous"] = cfg["continuous"]
        doc["instruments"][ticker] = rec
    return doc


def load_history(path: str) -> dict:
    """The committed settlement document, or a fresh empty one."""
    if not os.path.exists(path):
        return empty_history()
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    if not isinstance(doc, dict) or not isinstance(doc.get("instruments"),
                                                   dict):
        raise SystemExit(
            "backfill_commodities: %s has no 'instruments' object -- "
            "refusing to extend a file whose shape I do not recognize" % path)
    for ticker in INSTRUMENTS:
        rec = doc["instruments"].setdefault(ticker, {})
        rec.setdefault("series", {})
        rec.setdefault("unavailable", {})
    return doc


def committed(doc: dict, ticker: str):
    """The {close, volume} a weekly document holds for one commodity."""
    rec = (doc.get(BLOCK) or {}).get(ticker)
    if isinstance(rec, dict) and rec.get("close") is not None:
        return {"close": rec["close"], "volume": rec.get("volume")}
    return None


def gaps(docs: list, history: dict) -> list:
    """(ticker, week) pairs with no settlement and no reason for it: after
    the instrument's audited week, no labelled close in the week's own file,
    no entry here, not listed as unavailable. Oldest first."""
    out = []
    for ticker in INSTRUMENTS:
        rec = history["instruments"][ticker]
        through = rec.get("audited_through") or ""
        for week, doc in docs:
            if week <= through or week in rec["series"] \
                    or week in rec["unavailable"]:
                continue
            if committed(doc, ticker) is not None and \
                    snapshot.named_contract(doc, BLOCK, ticker):
                continue
            out.append((ticker, week))
    return sorted(out, key=lambda pair: (pair[1], pair[0]))


# ------------------------------------------------------------------ fetching

def contract_of(ticker: str, week: str) -> str:
    cfg = INSTRUMENTS[ticker]
    return snapshot_macro.contract_for(
        cfg["root"], dt.date.fromisoformat(week), cfg.get("position", 0))


def by_name(ticker: str, week: str):
    """(entry, error) for one week, by contract name, through the writer."""
    entry, err = snapshot_macro._fetch_one(
        ticker, INSTRUMENTS[ticker], dt.date.fromisoformat(week))
    if err is not None:
        return None, err
    contract = entry["contract"]
    out = {"close": entry["close"], "volume": entry.get("volume"),
           "contract": contract,
           "symbol": snapshot_macro.contract_symbol(contract)}
    if entry.get("observed"):
        out["observed"] = entry["observed"]
    return out, None


def answers_for(contract: str, week: str) -> bool:
    """Does the provider still serve this contract around `week`? Raises on
    a failed fetch: no answer is not the answer "nothing"."""
    day = dt.date.fromisoformat(week)
    monday = day - dt.timedelta(days=day.weekday())
    return bool(snapshot_macro.history(
        snapshot_macro.contract_symbol(contract), monday.isoformat(),
        (day + dt.timedelta(days=8)).isoformat()))


def from_continuous(ticker: str, week: str, now: dt.datetime):
    """(entry, refusal) for one week, from the continuous symbol.

    The continuous bar dated `week` is taken as the expired contract's only
    on proof that the continuous history was the nearest-expiry chain when
    that contract expired: on every settled session of the following
    PROOF_DAYS days its close is the next contract's, read by name. A
    refusal is evidence (the bars were read and do not show it). A failed
    fetch raises instead."""
    cfg = INSTRUMENTS[ticker]
    symbol = cfg.get("continuous")
    if not symbol or cfg.get("position", 0):
        return None, "%s has no continuous symbol to ask" % ticker
    day = dt.date.fromisoformat(week)
    contract = contract_of(ticker, week)
    ltd = snapshot_macro.last_trade_date(
        *snapshot_macro.contract_parts(contract))
    successor = snapshot_macro.contract_for(
        cfg["root"], ltd + dt.timedelta(days=1))
    monday = day - dt.timedelta(days=day.weekday())
    until = (ltd + dt.timedelta(days=PROOF_DAYS + 1)).isoformat()

    rolling = snapshot_macro.history(symbol, monday.isoformat(), until)
    named = snapshot_macro.history(snapshot_macro.contract_symbol(successor),
                                   ltd.isoformat(), until)
    if day not in rolling:
        return None, "%s has no bar dated %s" % (symbol, week)

    def close(row):
        return snapshot_macro.normalize_bar(row["Close"], row.get("Volume"),
                                            cfg)

    proof = [d for d in sorted(named)
             if ltd < d <= ltd + dt.timedelta(days=PROOF_DAYS)
             and snapshot_macro.settled_at(d) <= now]
    if len(proof) < PROOF_MIN:
        return None, (
            "%s cannot be shown to have held %s: the provider has %d settled "
            "%s session(s) by name in the %d days after %s's last trade on "
            "%s, and %d are needed"
            % (symbol, contract, len(proof), successor, PROOF_DAYS, contract,
               ltd.isoformat(), PROOF_MIN))
    off = [d for d in proof
           if d not in rolling
           or not same(close(rolling[d])[0], close(named[d])[0])]
    if off:
        d = off[0]
        got = close(rolling[d])[0] if d in rolling else None
        return None, (
            "%s is not the nearest-expiry chain at that roll: on %s, after "
            "%s's last trade, it holds %r where %s settled %r. Its bar for "
            "%s is another contract month's"
            % (symbol, d.isoformat(), contract, got, successor,
               close(named[d])[0], week))
    value, volume = close(rolling[day])
    return {"close": value, "volume": volume, "contract": contract,
            "symbol": symbol}, None


# -------------------------------------------------------------------- modes

def finish(entry: dict, doc: dict, ticker: str, stamp: str,
           reason: str | None) -> dict:
    """The entry as it is committed: labelled, and saying what it replaces."""
    entry = dict(entry, source=SOURCE, fetched_at=stamp)
    held = committed(doc, ticker)
    if held is not None and not same(float(held["close"]), entry["close"]):
        entry["replaces"] = held
    if reason:
        entry["reason"] = reason.strip()
    return entry


def describe(ticker: str, week: str, entry: dict) -> str:
    was = entry.get("replaces")
    return "  + %s %-8s %10.4f  %s via %s%s%s" % (
        week, ticker, entry["close"], entry["contract"], entry["symbol"],
        "  (observed %s)" % entry["observed"] if "observed" in entry else "",
        "  replaces %r" % was["close"] if was else "")


def write(history: dict, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(snapshot.canonical_json(history))


def rederive(data_root: str, facts_path: str | None) -> int:
    # The file is an input to market_state.json, so a new entry makes the
    # committed state stale, and `truth_check --feed` says so.
    if os.path.isfile(os.path.join(data_root, "market_state.json")):
        return rederive_market_state.rederive(data_root, facts_path)
    return 0


def run_fill(docs: list, history: dict, path: str, data_root: str,
             facts_path: str | None, dry_run: bool,
             now: dt.datetime) -> int:
    todo = gaps(docs, history)
    if not todo:
        print("Nothing to add: no week after the audit lacks a settlement.")
        return 0
    by_week = dict(docs)
    print("%d settlement(s) to find: %s .. %s"
          % (len(todo), todo[0][1], todo[-1][1]))
    added, failed = 0, []
    for ticker, week in todo:
        entry, err = by_name(ticker, week)
        if err is not None:
            failed.append((ticker, week, err))
            continue
        entry = finish(entry, by_week[week], ticker, _stamp(now), None)
        history["instruments"][ticker]["series"][week] = entry
        print(describe(ticker, week, entry))
        added += 1
    for ticker, week, err in failed:
        print("  ! %s %-8s not filled: %s" % (week, ticker, err))
    if failed:
        print("A week that cannot be read by name can be asked of the "
              "continuous symbol, on proof: --week <as_of> --instrument "
              "<name> --from-continuous --reason \"...\". If that is "
              "refused too, record it with --unavailable.")

    # A week still without a value is not a success, whatever else was
    # written: market_state carries a null for it.
    status = 1 if failed else 0
    if dry_run:
        print("DRY RUN: nothing written (%d would be added)" % added)
        return status
    if not added:
        return status
    write(history, path)
    print("Wrote %s: %d added" % (path, added))
    return max(status, rederive(data_root, facts_path))


def run_named(docs: list, history: dict, path: str, data_root: str,
              facts_path: str | None, dry_run: bool, now: dt.datetime,
              week: str, tickers: list, reason: str, continuous: bool,
              unavailable: bool) -> int:
    """One reviewed week. Every instrument named is written, or none is."""
    by_week = dict(docs)
    if week not in by_week:
        raise Refused("no weekly file dated %s" % week)
    if not tickers:
        raise Refused("no instrument named")
    if len(set(tickers)) != len(tickers):
        raise Refused("an instrument is named twice")
    if not reason or not reason.strip():
        raise Refused("an entry for a named week is a reviewed statement "
                      "and needs --reason")
    doc = by_week[week]
    staged = []
    for ticker in tickers:
        if ticker not in INSTRUMENTS:
            raise Refused("%s is not a commodity this feed names; expected "
                          "one of %s" % (ticker, ", ".join(INSTRUMENTS)))
        rec = history["instruments"][ticker]
        if week in rec["series"]:
            raise Refused("%s already has an entry for %s; an entry is "
                          "never rewritten" % (ticker, week))
        if snapshot.named_contract(doc, BLOCK, ticker) \
                and committed(doc, ticker) is not None:
            raise Refused("the file for %s names the contract of its own %s "
                          "close; readers take that one, and a second value "
                          "here could only disagree with it" % (week, ticker))
        contract = contract_of(ticker, week)
        expired = snapshot_macro.last_trade_date(
            *snapshot_macro.contract_parts(contract)) < now.date()

        if week in rec["unavailable"]:
            raise Refused("%s is already recorded as unavailable for %s (%s)"
                          "; remove that by hand first if it is no longer "
                          "true" % (ticker, week,
                                    rec["unavailable"][week].get("reason")))

        def ask(what, *args):
            # No answer is not the answer "nothing", so it proves nothing.
            try:
                return what(*args)
            except Exception as exc:
                raise Refused("%s %s: the provider did not answer (%s: %s)"
                              % (ticker, week, type(exc).__name__,
                                 str(exc)[:120]))

        if unavailable:
            if ask(answers_for, contract, week):
                raise Refused("the provider still serves %s for %s; read it "
                              "(drop --unavailable)" % (contract, week))
            got, why = ask(from_continuous, ticker, week, now)
            if got is not None:
                raise Refused("%s can be shown to have held %s on %s; read "
                              "it with --from-continuous"
                              % (got["symbol"], contract, week))
            staged.append((ticker, None, {
                "contract": contract, "reason": reason.strip(),
                "evidence": "the provider serves nothing for %s; %s"
                            % (contract, why),
                "checked_at": _stamp(now)}))
            continue

        entry, err = by_name(ticker, week)
        if err is not None:
            if not (continuous and expired):
                hint = ("; its contract %s has expired, so the continuous "
                        "symbol may be asked with --from-continuous"
                        % contract if expired else "")
                raise Refused("%s %s: %s%s" % (ticker, week, err, hint))
            entry, why = ask(from_continuous, ticker, week, now)
            if entry is None:
                raise Refused("%s %s: %s" % (ticker, week, why))
        staged.append((ticker, finish(entry, doc, ticker, _stamp(now),
                                      reason), None))

    for ticker, entry, gone in staged:
        rec = history["instruments"][ticker]
        if entry is not None:
            rec["series"][week] = entry
            print(describe(ticker, week, entry))
        else:
            rec["unavailable"][week] = gone
            print("  - %s %-8s unavailable (%s): %s"
                  % (week, ticker, gone["contract"], gone["reason"]))
    if dry_run:
        print("DRY RUN: nothing written")
        return 0
    write(history, path)
    print("Wrote %s" % path)
    return rederive(data_root, facts_path)


def run_check(docs: list, history: dict, now: dt.datetime) -> int:
    """Every committed settlement that can still be asked about, against the
    provider. Writes nothing."""
    rows = []       # (ticker, week, close, symbol, where)
    for ticker in INSTRUMENTS:
        for week, rec in sorted(history["instruments"][ticker]["series"]
                                .items()):
            rows.append((ticker, rec.get("observed", week), rec.get("close"),
                         rec.get("symbol"), "%s %s (%s)" % (
                             week, ticker, snapshot.COMMODITY_HISTORY_FILE)))
        for week, doc in docs:
            contract = snapshot.named_contract(doc, BLOCK, ticker)
            held = committed(doc, ticker)
            if contract and held is not None:
                label = doc["provenance"][BLOCK][ticker]
                rows.append((ticker, label.get("observed", week),
                             held["close"],
                             snapshot_macro.contract_symbol(contract),
                             "%s %s (weekly/%s.json)" % (week, ticker, week)))

    diffs, expired, checked = [], 0, 0
    for ticker, session, close, symbol, where in rows:
        day = dt.date.fromisoformat(session)
        try:
            bars = snapshot_macro.history(
                symbol, day.isoformat(),
                (day + dt.timedelta(days=1)).isoformat())
        except Exception as exc:
            diffs.append("%s: %s not readable: %s: %s"
                         % (where, symbol, type(exc).__name__,
                            str(exc)[:120]))
            continue
        if day not in bars:
            # A named contract the provider has dropped can no longer be
            # asked about; a continuous symbol always answers, so its
            # silence is a difference.
            if "=" in symbol:
                diffs.append("%s: %s has no bar dated %s"
                             % (where, symbol, session))
            else:
                expired += 1
            continue
        checked += 1
        got = snapshot_macro.normalize_bar(
            bars[day]["Close"], bars[day].get("Volume"),
            INSTRUMENTS[ticker])[0]
        if not same(float(close), got):
            diffs.append("%s: committed %r, %s now says %r"
                         % (where, close, symbol, got))
    print("%d settlement(s) on file: %d checked against the provider, %d on "
          "a contract it no longer serves" % (len(rows), checked, expired))
    if diffs:
        print("%d differ:" % len(diffs))
        for line in diffs:
            print("  " + line)
        print("Nothing was changed. A committed value the provider no "
              "longer agrees with is a decision for a person; a continuous "
              "symbol that has moved is what this file exists to survive.")
        return 1
    print("OK: every settlement that could be checked matches")
    return 0


def main(argv: list | None = None, now: dt.datetime | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Fill data/commodity_settlements.json: settlements of "
                    "the nearest-expiry contract for weeks whose weekly "
                    "file cannot supply one.")
    p.add_argument("--data", default="data", help="data root (default: data)")
    p.add_argument("--facts", default=None,
                   help="macro facts file for the market_state re-derive "
                        "(default: macro/facts.json beside the data root)")
    p.add_argument("--dry-run", action="store_true",
                   help="fetch and report; write nothing")
    p.add_argument("--check", action="store_true",
                   help="compare committed settlements against the "
                        "provider; exit 1 on any difference; write nothing")
    p.add_argument("--week", default=None, metavar="YYYY-MM-DD",
                   help="add an entry for this weekly file's as_of")
    p.add_argument("--instrument", action="append", default=[],
                   metavar="NAME", help="with --week; repeatable")
    p.add_argument("--reason", default=None,
                   help="with --week: why, in a sentence; it is committed")
    p.add_argument("--from-continuous", action="store_true",
                   help="with --week: if the contract has expired, take the "
                        "continuous symbol's bar, on proof")
    p.add_argument("--unavailable", action="store_true",
                   help="with --week: record that no settlement can be had")
    a = p.parse_args(argv)
    now = now or snapshot_macro._utcnow()

    weekly_dir = os.path.join(a.data, "weekly")
    if not os.path.isdir(weekly_dir):
        print("No such directory: " + weekly_dir)
        return 1
    docs = snapshot._load_weekly_files(weekly_dir)
    path = snapshot.commodity_history_path(weekly_dir)
    history = load_history(path)

    if a.check:
        return run_check(docs, history, now)
    if a.week is None:
        if a.instrument or a.reason or a.from_continuous or a.unavailable:
            p.error("--instrument, --reason, --from-continuous and "
                    "--unavailable describe one week: name it with --week")
        return run_fill(docs, history, path, a.data, a.facts, a.dry_run, now)
    if a.from_continuous and a.unavailable:
        p.error("--from-continuous reads a settlement; --unavailable "
                "records that there is none")
    try:
        return run_named(docs, history, path, a.data, a.facts, a.dry_run,
                         now, a.week, a.instrument, a.reason or "",
                         a.from_continuous, a.unavailable)
    except Refused as exc:
        print("REFUSED: " + str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
