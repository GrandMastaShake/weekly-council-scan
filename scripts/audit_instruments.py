#!/usr/bin/env python3
"""audit_instruments.py -- which session does a committed instrument close belong to?

A weekly file is named for a Friday and commits one close per instrument in
rates / vol / commodities / fx. Nothing in the file says which session that
close was read from. The writer took the bar dated the Friday when the
provider had one and the last earlier bar when it did not, and the note it
attached to the second case never reached the committed file. So a prior
session's value can sit under the Friday date with no trace, and a bar read
before the exchange settled it can sit there as if it were the close.

This script asks the provider again. For every committed file and every
instrument it fetches the symbol's daily history once and answers one
question: which session's close, if any, is the committed number?

    ok                the bar dated as_of. Not listed.
    prior_session     as_of has a bar, the committed close is not it, and it
                      IS the close of the session before. A prior-day value
                      under the as_of date.
    holiday_stand_in  the provider has no bar dated as_of -- not a session
                      for this instrument -- and the committed close is the
                      last session of the same Mon..Fri week. The documented
                      holiday rule. Listed unless the file records the date
                      itself in provenance.<block>.<ticker>.observed.
    other_session     the close of some other nearby session.
    differs           no session's close. The provider restated the series
                      since, or the bar was read before it settled, or it
                      belonged to another contract month.
    absent            the file has no close for the instrument and the
                      provider has a bar dated as_of now.
    unverified        the provider could not answer, or the session is too
                      recent for its answer to be final. Never read as ok.

One missing close is the rule and not a loss. An instrument that settles the
day after its session is not read before 13:00 UTC on that day
(snapshot_macro.select_bar), and both of the daily job's attempts run
earlier (DATA_FEED.md sec.4): every daily file written since 2026-10-05
lists all of them in `missing`. The first such file put five rows under NEW,
and a row a session for each would bury the ones that want a reviewer. In
data/daily they are counted, as "before_settlement", and not listed. The
file's own fetched_at decides, never the reason it wrote down. In
data/weekly the same state is a job that ran before the hour it is scheduled
after; that file cannot be completed afterwards, and it is listed as absent.

What it cannot tell you is WHY. A "differs" on WTI is the same line whether
the committed number was a last trade ahead of the settlement or the next
contract month's quote. Committed volume beside the provider's is printed
because it usually decides between the two. The reasoning is a reviewer's:
each finding on file carries a "cause", and the baseline's "causes" say what
each one is and what was decided about it.

WTI, GOLD and SILVER are asked about in two ways, because they are two kinds
of close. A file that names its contract (provenance.commodities, since
2026-10-05) is compared with that contract's own history, while the provider
still serves it; once the contract has expired the close cannot be asked
about again, and it is left out rather than called ok or unverified. A file
that names none holds a continuous symbol's bar and is compared with the
continuous symbol, as it always was. That comparison says what the provider
shows under GC=F today, not whether the close is the nearest-expiry
contract's: 104 committed gold closes "differ" and are right. Which weeks
are off the rule, and what stands in for them, is
data/commodity_settlements.json's to say (DATA_FEED.md sec.1d).

The baseline, macro/instrument_audit.json, is the reviewed list. A run prints
what is NEW, CHANGED or GONE against it and stays quiet about the rest, the
way truth_check --splits goes quiet once an action is acknowledged. --write
replaces the findings, keeps every hand-written key, and carries a finding's
cause forward only while the finding itself is unchanged; anything new or
changed lands with no cause and is reported as unreviewed until it has one.

Advisory: exit 0 whatever it finds. --strict exits 1 on anything new or
changed. Exit 2 means the provider answered for nothing, so nothing was
audited -- which is not the same as nothing being wrong.

Needs the network and yfinance (requirements-fetch.txt), through the same
accessor the writer uses, so a difference is the provider's and not the
route's. The tests inject the history and need neither.

Usage:
  python scripts/audit_instruments.py [--repo .] [--panel weekly|daily|all]
         [--baseline macro/instrument_audit.json] [--all] [--json OUT]
         [--write] [--strict]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
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

from scan_pipeline import snapshot_macro  # noqa: E402
from scan_pipeline.snapshot import PROVIDER, SPECIAL_BLOCKS  # noqa: E402

BASELINE = ("macro", "instrument_audit.json")
PANELS = ("weekly", "daily")

# rates.US2Y was the 2YY=F future in every file through 2026-10-02. Once the
# feed reads the Treasury 2-year under that name the provider map stops
# saying so, but the old files still hold the future. Which kind a file holds
# is decided by the file, never by its date: a provenance label naming
# another publisher, or the future filed beside it under its own name
# ("successor"), means US2Y there is not Yahoo's and not this audit's.
LEGACY_INSTRUMENTS = {
    ("rates", "US2Y"): {"symbol": "2YY=F", "divisor": 1.0, "kind": "yield",
                        "successor": "US2Y_FUT"},
}

# Committed closes are rounded to 4 dp. Yahoo serves float32, whose spacing
# near a 4,000 gold price is 0.0005, so the 4th decimal of a large close is
# the float and not the market. Equal means equal to within that.
TOL_ABS = 1.5e-4
TOL_REL = 2e-6

# How far from as_of another session's close is still worth naming.
NEAR_DAYS = 7

CLASSES = ("prior_session", "holiday_stand_in", "other_session", "differs",
           "absent", "unverified")

# The panels in which a close the writer declined to read before its
# settlement hour is counted and not listed (module docstring). The count is
# a key of its own beside the classes, because it is not a finding: nothing
# in the baseline answers for it and nothing needs a cause.
COUNTED_BEFORE_SETTLEMENT = ("daily",)
BEFORE_SETTLEMENT = "before_settlement"

HEADINGS = {
    "prior_session": "PRIOR SESSION -- the as_of bar exists, and the "
                     "committed close is the session before it",
    "holiday_stand_in": "HOLIDAY STAND-IN -- no as_of bar for this "
                        "instrument; the committed close is the last session "
                        "of its week, and the file does not say so",
    "other_session": "OTHER SESSION -- the close of a different nearby "
                     "session",
    "differs": "DIFFERS -- equals no session's close (restated since, read "
               "before settlement, or another contract month)",
    "absent": "ABSENT -- no close in the file; the provider has a bar dated "
              "as_of now",
    "unverified": "UNVERIFIED -- the provider could not answer; this is not "
                  "an ok",
}


# ----------------------------------------------------------------- provider

def instrument_map():
    """{(block, ticker): cfg} for every instrument Yahoo supplies.

    A commodity has no fixed symbol since 2026-10-05: the writer reads the
    contract the roll calendar names. Its "symbol" here is the continuous
    one, which is what every file from before that date holds and is
    audited against; symbol_for() picks the named contract instead for a
    file that names one."""
    out = {}
    for block, instruments in snapshot_macro.INSTRUMENTS.items():
        for ticker, cfg in instruments.items():
            if cfg.get("symbol"):
                out[(block, ticker)] = cfg
            elif cfg.get("root"):
                out[(block, ticker)] = dict(cfg,
                                            symbol=cfg.get("continuous"))
    for key, cfg in LEGACY_INSTRUMENTS.items():
        out.setdefault(key, cfg)
    return out


def named_symbol(contract):
    """The provider's symbol for a contract a file names, or None."""
    try:
        return snapshot_macro.contract_symbol(contract)
    except (ValueError, TypeError):
        return None


def symbol_for(cfg, doc, block, ticker):
    """(symbol, contract) to audit one instrument in one file against.

    A fixed-symbol instrument is always that symbol. A commodity is, in
    order: the contract its file names; else, where the file holds a close
    with no label, the continuous symbol (the file predates named
    contracts); else, where the file has no close for it, the contract the
    calendar gives for the date, which is what the writer asked for."""
    if "root" not in cfg:
        return cfg["symbol"], None
    contract = label_of(doc, block, ticker).get("contract")
    if contract:
        return named_symbol(contract), contract
    entry = (doc.get(block) or {}).get(ticker)
    if isinstance(entry, dict) and entry.get("close") is not None:
        return cfg.get("symbol"), None
    contract = snapshot_macro.contract_for(
        cfg["root"], dt.date.fromisoformat(doc["as_of"]),
        cfg.get("position", 0))
    return named_symbol(contract), contract


def expired(contract, now):
    """True once a named contract has stopped trading. The provider drops
    it within days, so after that it cannot be asked about at all."""
    try:
        return snapshot_macro.last_trade_date(
            *snapshot_macro.contract_parts(contract)) < now.date()
    except (ValueError, TypeError):
        return False


# The writer's own normalization, so a committed close is compared with the
# number the writer would write and not with the provider's raw float.
normalize = snapshot_macro.normalize_bar


def fetch_history(symbol, start, end):
    """{iso_date: (close, volume)} for one symbol, raw from the provider.

    Ticker.history is the accessor the writer uses. Raises on a failed
    fetch; the caller reports every instrument on that symbol unverified."""
    import yfinance as yf

    hist = yf.Ticker(symbol).history(start=start, end=end)
    out = {}
    if hist is None or hist.empty:
        return out
    for idx, row in hist.iterrows():
        close = row["Close"]
        if close is None or close != close:        # NaN
            continue
        out[idx.date().isoformat()] = (float(close), row.get("Volume"))
    return out


def provider_version():
    try:
        import yfinance as yf
        return getattr(yf, "__version__", None)
    except ImportError:
        return None


# ------------------------------------------------------------------- panels

def load_panel(repo, panel):
    """[(file_name, doc)] for one panel, corrections included under their
    own name. A file that does not parse is check_feed's to report."""
    directory = Path(repo) / "data" / panel
    out = []
    if not directory.is_dir():
        return out
    for path in sorted(directory.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if isinstance(doc, dict) and isinstance(doc.get("as_of"), str):
            out.append((path.name, doc))
    return out


def label_of(doc, block, ticker):
    """The file's own provenance record for one instrument, or {}."""
    prov = doc.get("provenance")
    entries = prov.get(block) if isinstance(prov, dict) else None
    rec = entries.get(ticker) if isinstance(entries, dict) else None
    return rec if isinstance(rec, dict) else {}


def from_provider(label):
    """True when the file does not name another publisher for the value."""
    src = label.get("source")
    return not isinstance(src, str) or src == PROVIDER \
        or src.startswith(PROVIDER + "-")


# ----------------------------------------------------------------- classify

def same(a, b):
    return abs(a - b) <= max(TOL_ABS, TOL_REL * abs(b))


def settled_at(as_of):
    """When the provider's bar for as_of can be taken as final.

    The writer's rule (snapshot_macro, "The Yahoo path"), applied here to
    every instrument: an audit run on the evening of a session would judge
    a file against a number that is itself about to change."""
    return snapshot_macro.settled_at(dt.date.fromisoformat(as_of))


def fetched_before_settlement(doc):
    """True when the file was fetched before the hour at which the bar dated
    its as_of may be read for an instrument that settles the next day.

    The writer's own test (snapshot_macro.select_bar), asked of the stamp
    the file carries. A stamp that cannot be read is not taken for an early
    one: the instrument is then listed, not counted."""
    try:
        fetched = dt.datetime.strptime(
            doc.get("fetched_at"), "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=dt.timezone.utc)
    except (TypeError, ValueError):
        return False
    return fetched < settled_at(doc["as_of"])


def classify(close, as_of, history):
    """(class, session) for one committed close. Pure.

    history is {iso_date: close}, already normalized. `session` is the
    session whose close the committed number equals, or None."""
    here = history.get(as_of)
    if here is not None and same(close, here):
        return "ok", as_of

    day = dt.date.fromisoformat(as_of)
    lo = (day - dt.timedelta(days=NEAR_DAYS)).isoformat()
    hi = (day + dt.timedelta(days=NEAR_DAYS)).isoformat()
    near = sorted(d for d in history if lo <= d <= hi)
    if not near:
        return "unverified", None

    before = [d for d in near if d < as_of]
    if here is not None:
        # An unchanged mark equals both days and was returned ok above, so
        # reaching here means the two sessions really closed differently.
        if before and same(close, history[before[-1]]):
            return "prior_session", before[-1]
    else:
        monday = (day - dt.timedelta(days=day.weekday())).isoformat()
        week = [d for d in before if d >= monday]
        if week and same(close, history[week[-1]]):
            return "holiday_stand_in", week[-1]

    hits = [d for d in near if d != as_of and same(close, history[d])]
    if hits:
        hits.sort(key=lambda d: (abs((dt.date.fromisoformat(d) - day).days),
                                 d))
        return "other_session", hits[0]
    return "differs", None


def audit_file(panel, name, doc, instruments, histories, now):
    """Findings for one file, plus how many closes it compared, how many
    passed, and how many it declined to read before they settled."""
    as_of = doc["as_of"]
    findings, compared, ok, declined = [], 0, 0, 0
    declared = {m.get("ticker"): m.get("reason")
                for m in doc.get("missing") or [] if isinstance(m, dict)}
    for (block, ticker), cfg in sorted(instruments.items()):
        entry = (doc.get(block) or {}).get(ticker)
        label = label_of(doc, block, ticker)
        if not from_provider(label):
            continue            # another publisher's number, not this audit's
        successor = cfg.get("successor")
        if successor and (successor in (doc.get(block) or {})
                          or successor in declared):
            continue            # the name has moved on in this file
        symbol, contract = symbol_for(cfg, doc, block, ticker)
        if not symbol:
            continue            # nothing this file could be compared with
        history = histories.get(symbol)
        if contract and not history and expired(contract, now):
            # A contract month that has stopped trading. The provider no
            # longer serves it, so this close can never be asked about
            # again: not ok, not a finding, and not counted as compared.
            continue
        base = {
            "panel": panel, "file": name,
            "instrument": block + "." + ticker, "symbol": symbol,
            "fetched_at": label.get("fetched_at") or doc.get("fetched_at"),
        }

        if not isinstance(entry, dict) or entry.get("close") is None:
            # Only an instrument the file itself says it lost. One the file
            # never carried (US2Y_FUT before the cutover) is not a finding.
            if ticker not in declared or not history:
                continue
            bar = history.get(as_of)
            if bar is None:
                continue
            if panel in COUNTED_BEFORE_SETTLEMENT \
                    and cfg.get("settles") == snapshot_macro.NEXT_DAY \
                    and fetched_before_settlement(doc):
                # Declined, not lost: at the hour this file was fetched the
                # writer may not read the bar, whatever reason it gave.
                declined += 1
                continue
            findings.append(dict(base, **{
                "class": "absent", "committed": None,
                "provider": {"close": bar[0], "volume": bar[1]},
                "session": None, "reason": declared[ticker]}))
            continue

        compared += 1
        committed = {"close": entry["close"], "volume": entry.get("volume")}
        if history is None:
            findings.append(dict(base, **{
                "class": "unverified", "committed": committed,
                "provider": None, "session": None,
                "reason": "no history returned for " + symbol}))
            continue
        if now < settled_at(as_of):
            findings.append(dict(base, **{
                "class": "unverified", "committed": committed,
                "provider": None, "session": None,
                "reason": "the provider's bar for " + as_of + " is not final "
                          "before " + settled_at(as_of).strftime(
                              "%Y-%m-%dT%H:%MZ")}))
            continue

        closes = {d: bar[0] for d, bar in history.items()}
        cls, session = classify(float(entry["close"]), as_of, closes)
        if cls == "ok":
            ok += 1
            continue
        if cls == "holiday_stand_in" and label.get("observed") == session:
            ok += 1             # the file says which session; nothing hidden
            continue
        bar = history.get(as_of)
        finding = dict(base, **{
            "class": cls, "committed": committed,
            "provider": None if bar is None
            else {"close": bar[0], "volume": bar[1]},
            "session": session})
        if cls == "unverified":
            finding["reason"] = ("no " + symbol + " bar within "
                                 + str(NEAR_DAYS) + " days of " + as_of)
        if label.get("observed"):
            finding["recorded_observed"] = label["observed"]
        if doc.get("session_note"):
            finding["session_note"] = doc["session_note"]
        findings.append(finding)
    return findings, compared, ok, declined


def history_window(docs):
    """One ranged request per symbol covers every file. The start is a
    Monday on purpose: a window that opens on the Sunday US clocks go forward
    returns nothing at all for ^VIX, which is how VIX went missing from
    2025-03-14 and 2026-03-13."""
    days = sorted(dt.date.fromisoformat(doc["as_of"]) for _, doc in docs)
    first = days[0] - dt.timedelta(days=NEAR_DAYS)
    start = first - dt.timedelta(days=first.weekday())
    end = days[-1] + dt.timedelta(days=NEAR_DAYS + 1)
    return start.isoformat(), end.isoformat()


def run_audit(repo, panels=PANELS, fetch=fetch_history, now=None):
    """Audit the named panels. Returns the generated part of the baseline:
    {"audited": {...}, "findings": [...]}."""
    now = now or dt.datetime.now(dt.timezone.utc)
    instruments = instrument_map()
    loaded = {p: load_panel(repo, p) for p in panels}
    every = [item for p in panels for item in loaded[p]]
    result = {
        "audited": {
            "provider": PROVIDER,
            "fetched_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "yfinance": provider_version(),
            "panels": {},
        },
        "findings": [],
    }
    if not every:
        return result

    start, end = history_window(every)
    # One request per symbol: every fixed symbol, and every contract month
    # a file names or (for a commodity it lists as lost) would have named.
    wanted, named = {}, {}
    for cfg in instruments.values():
        if cfg.get("symbol"):
            wanted.setdefault(cfg["symbol"], cfg)
    for _, doc in every:
        lost = {m.get("ticker") for m in doc.get("missing") or []
                if isinstance(m, dict)}
        for (block, ticker), cfg in instruments.items():
            if "root" not in cfg:
                continue
            entry = (doc.get(block) or {}).get(ticker)
            held = isinstance(entry, dict) and entry.get("close") is not None
            if not held and ticker not in lost:
                continue
            symbol, contract = symbol_for(cfg, doc, block, ticker)
            if symbol and contract:
                wanted.setdefault(symbol, cfg)
                named[symbol] = contract

    histories, errors, gone = {}, {}, []
    for symbol, cfg in wanted.items():
        try:
            raw = fetch(symbol, start, end)
        except Exception as exc:        # a dead symbol must not end the audit
            errors[symbol] = "%s: %s" % (type(exc).__name__, str(exc)[:120])
            continue
        if not raw:
            if symbol in named and expired(named[symbol], now):
                gone.append(symbol)     # dropped by the provider, as expected
            else:
                errors[symbol] = "no data returned for %s..%s" % (start, end)
            continue
        histories[symbol] = {d: normalize(c, v, cfg)
                             for d, (c, v) in raw.items()}
    result["audited"]["symbols"] = {
        "answered": sorted(histories), "failed": dict(sorted(errors.items()))}
    if gone:
        result["audited"]["symbols"]["expired"] = sorted(gone)

    for panel in panels:
        counts = {"files": len(loaded[panel]), "closes": 0, "ok": 0}
        counts.update({c: 0 for c in CLASSES})
        counts[BEFORE_SETTLEMENT] = 0
        corrected = {name[:-len(".corrected.json")]
                     for name, _ in loaded[panel]
                     if name.endswith(".corrected.json")}
        for name, doc in loaded[panel]:
            found, compared, ok, declined = audit_file(
                panel, name, doc, instruments, histories, now)
            counts["closes"] += compared
            counts["ok"] += ok
            counts[BEFORE_SETTLEMENT] += declined
            for finding in found:
                counts[finding["class"]] += 1
                stem = name[:-len(".json")]
                if stem in corrected:
                    # Readers prefer the correction, so say that the base
                    # file's finding is not the one they see.
                    finding["superseded_by"] = stem + ".corrected.json"
                result["findings"].append(finding)
        result["audited"]["panels"][panel] = counts
    result["findings"].sort(key=_key)
    return result


# ----------------------------------------------------------------- baseline

def _key(finding):
    return (PANELS.index(finding["panel"]), finding["file"],
            finding["instrument"])


def _essence(finding):
    """What makes two findings the same finding. The provider's close is
    part of it: a baseline entry whose provider number has moved is news."""
    provider = finding.get("provider") or {}
    committed = finding.get("committed") or {}
    return (finding["class"], finding.get("session"),
            committed.get("close"), provider.get("close"))


def compare(baseline, current, panels=PANELS):
    """(new, changed, gone, known) between a baseline and a fresh run.

    An unverified finding is never evidence that a baseline entry is gone:
    the provider not answering today says nothing about last month."""
    old = {_key(f): f for f in (baseline or {}).get("findings", [])
           if f.get("panel") in panels}
    new, changed, known = [], [], []
    seen = set()
    for finding in current["findings"]:
        key = _key(finding)
        seen.add(key)
        if key not in old:
            new.append(finding)
        elif finding["class"] == "unverified" \
                and old[key]["class"] != "unverified":
            known.append(old[key])
        elif _essence(old[key]) != _essence(finding):
            changed.append((old[key], finding))
        else:
            known.append(finding)
    gone = [f for key, f in sorted(old.items()) if key not in seen]
    return new, changed, gone, known


def read_baseline(path):
    path = Path(path)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def unreviewed(doc):
    """Findings on file that nobody has put a cause to."""
    causes = (doc or {}).get("causes") or {}
    return [f for f in (doc or {}).get("findings", [])
            if f.get("cause") not in causes]


def write_baseline(path, result, previous):
    """Replace the generated keys, keep every hand-written one in place.

    A cause is a reviewer's statement about one finding. It survives a
    rewrite only while that finding is the same finding; a changed one has
    not been looked at yet, whatever the old one was."""
    reviewed = {_key(f): f for f in (previous or {}).get("findings", [])
                if f.get("panel") in PANELS}
    for finding in result["findings"]:
        was = reviewed.get(_key(finding))
        same_finding = was is not None and _essence(was) == _essence(finding)
        finding["cause"] = was.get("cause") if same_finding else None
    doc = dict(previous or {})
    doc.setdefault("_purpose", (
        "Reviewed differences between the committed special-instrument "
        "closes (rates / vol / commodities / fx in data/weekly and "
        "data/daily) and the provider's own history, as "
        "scripts/audit_instruments.py found them. An entry is a statement "
        "that the difference was looked at, not that it was fixed: the "
        "files are observations and are never edited (DATA_FEED.md sec.1)."))
    doc.setdefault("_regenerate", (
        "python scripts/audit_instruments.py --write   (replaces 'audited' "
        "and 'findings', keeps everything else; review what is NEW first)"))
    doc.setdefault("causes", {})
    doc["audited"] = result["audited"]
    doc["findings"] = result["findings"]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_baseline(doc), encoding="utf-8", newline="\n")
    return path


def dump_baseline(doc):
    """The baseline as text: indented where a person writes, and one line
    per finding, so a review reads a finding at a glance and a diff shows
    exactly which ones moved."""
    head = {k: v for k, v in doc.items() if k != "findings"}
    text = json.dumps(head, indent=2, ensure_ascii=True)
    rows = ",\n".join("    " + json.dumps(f, ensure_ascii=True)
                      for f in doc["findings"])
    body = '"findings": [\n' + rows + "\n  ]" if rows else '"findings": []'
    joint = ",\n  " if head else "\n  "
    return text[:text.rindex("}")].rstrip() + joint + body + "\n}\n"


# ------------------------------------------------------------------- report

def _num(x):
    return "-" if x is None else ("%.4f" % x)


def line_for(finding):
    committed = finding.get("committed") or {}
    provider = finding.get("provider") or {}
    parts = ["  %-6s %-26s %-18s" % (finding["panel"], finding["file"],
                                     finding["instrument"])]
    if committed:
        parts.append("committed %10s" % _num(committed.get("close")))
    if finding.get("session"):
        parts.append("= " + finding["session"])
    if provider:
        parts.append("as_of %10s" % _num(provider.get("close")))
        if committed.get("close") is not None and provider["close"]:
            diff = committed["close"] - provider["close"]
            parts.append("(%+.4f, %+.2f%%)" % (
                diff, 100.0 * diff / provider["close"]))
        if committed.get("volume") or provider.get("volume"):
            parts.append("vol %s/%s" % (committed.get("volume"),
                                        provider.get("volume")))
    elif finding["class"] not in ("unverified", "absent"):
        parts.append("as_of: no bar")
    if finding.get("reason"):
        parts.append("[" + finding["reason"] + "]")
    if finding.get("fetched_at"):
        parts.append("fetched " + finding["fetched_at"])
    if finding.get("superseded_by"):
        parts.append("(superseded by " + finding["superseded_by"] + ")")
    return " ".join(parts)


def render(result, baseline, show_all, panels=PANELS):
    out = []
    audited = result["audited"]
    out.append("audit_instruments: provider history fetched %s (yfinance %s)"
               % (audited["fetched_at"], audited.get("yfinance")))
    for symbol, why in (audited.get("symbols") or {}).get("failed",
                                                          {}).items():
        out.append("  NO ANSWER for %s: %s" % (symbol, why))
    lapsed = (audited.get("symbols") or {}).get("expired")
    if lapsed:
        out.append("  %d named contract(s) have expired and are no longer "
                   "served; closes on them were not compared: %s"
                   % (len(lapsed), ", ".join(lapsed)))
    for panel, c in audited["panels"].items():
        out.append("%s: %d file(s), %d close(s) compared, %d ok, %d not"
                   % (panel, c["files"], c["closes"], c["ok"],
                      c["closes"] - c["ok"]))
        for cls in CLASSES:
            if c[cls]:
                out.append("  %-17s %d" % (cls, c[cls]))
        if c.get(BEFORE_SETTLEMENT):
            out.append("  %-17s %d  (in `missing` by rule: fetched before the "
                       "settlement hour. Counted, not listed)"
                       % (BEFORE_SETTLEMENT, c[BEFORE_SETTLEMENT]))

    new, changed, gone, known = compare(baseline, result, panels)
    if baseline is None:
        out.append("no baseline: every finding below is unreviewed")
    else:
        out.append("against the baseline: %d new, %d changed, %d gone, "
                   "%d known" % (len(new), len(changed), len(gone),
                                 len(known)))
        pending = unreviewed(baseline)
        if pending:
            out.append("%d finding(s) on file have no cause yet: %s"
                       % (len(pending), ", ".join(
                           "%s %s" % (f["file"], f["instrument"])
                           for f in pending[:6])
                          + (" ..." if len(pending) > 6 else "")))

    listed = result["findings"] if show_all or baseline is None else new
    title = "ALL FINDINGS" if show_all or baseline is None else "NEW"
    if listed:
        out.append("")
        out.append(title)
    for cls in CLASSES:
        rows = [f for f in listed if f["class"] == cls]
        if rows:
            out.append(HEADINGS[cls])
            out.extend(line_for(f) for f in rows)
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
        description="Audit committed instrument closes against the provider.")
    ap.add_argument("--repo", default=".", help="repo root (default: .)")
    ap.add_argument("--panel", choices=PANELS + ("all",), default="all")
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
    panels = PANELS if args.panel == "all" else (args.panel,)
    baseline_path = Path(args.baseline) if args.baseline \
        else repo.joinpath(*BASELINE)
    baseline = read_baseline(baseline_path)

    result = run_audit(repo, panels)
    text, (new, changed, gone, known) = render(result, baseline, args.all,
                                               panels)
    print(text)

    if args.json:
        Path(args.json).write_text(
            json.dumps(result, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8", newline="\n")

    answered = (result["audited"].get("symbols") or {}).get("answered")
    if not answered:
        print("NOTHING AUDITED: the provider answered for no symbol.")
        return 2
    if args.write:
        if panels != PANELS:
            print("REFUSED: --write replaces the whole baseline, so it needs "
                  "--panel all.")
            return 2
        write_baseline(baseline_path, result, baseline)
        print("Wrote " + str(baseline_path))
        return 0
    if args.strict and (new or changed):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
