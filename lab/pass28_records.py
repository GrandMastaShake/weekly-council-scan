#!/usr/bin/env python3
"""Pass 28, the records part: grade extracted prediction records by the rules registered in lab/README.md (517e4b7).

The records (JSON, one file per source, written by extraction agents that looked at no prices) and their verifications live OUTSIDE this
repo; pass them with --records-dir. This module maps each record's instrument to a ticker, parses its horizon, prices it from Yahoo's
dividend-adjusted bars and grades it:

  direction  hit if the sign of open(entry) -> close(exit) matches; null = the share of all windows of that length in the instrument's own
             history (2018-01 to 2026-10) that went that way; exact Poisson-binomial p over the calls
  level      holds/stays above X: no close in the window below X; stays below X: none above; breaks/reclaims: some close beyond X (by the
             record's direction); null = the same condition at the same percent distance from the entry open over all windows
  ranking    a sector's outperform/underperform call vs SPY over the window; null = share of windows the ETF outperformed (or lagged) SPY
  pick       buy/add -> outperform SPY, avoid/trim -> underperform (hold is not graded); null = 2,000 draws of a random S&P 500 name (as of
             2024-09) per pick over the same window; percentile of the mean and median excess (sign-adjusted)

Entry: a pre-market call enters at its day's open, any other call at the next session's open after its date; horizon as written, parsed by
HORIZON_RULES below (written before any record was priced); none stated -> 5 sessions, or 1 for an index, yield, dollar, VIX, oil or gold
call. A call whose window has not closed by 2026-10-09, or whose horizon is conditional or open-ended, is counted and not graded.
"""
from __future__ import annotations

import bisect
import glob
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

import engine_lab as lab

LAST_DAY = "2026-10-09"
HISTORY_FROM = "2018-01-01"
DRAWS = 2000
MIN_DECISIVE = 20
INDEX_LIKE = {"^GSPC", "^NDX", "^RUT", "^DJI", "^VIX", "^TNX", "DX-Y.NYB", "CL=F", "GC=F"}

# ---- instrument names -> Yahoo tickers (decided on the names alone, before any price was fetched) --------------------------------------
NAME_MAP = {
    "spx": "^GSPC", "s&p futures": "^GSPC", "equity futures": "^GSPC", "wall street": "^GSPC", "ndx": "^NDX", "rut": "^RUT", "dji": "^DJI",
    "s&p 500 (spy)": "SPY", "nasdaq 100 (qqq)": "QQQ", "russell 2000 (iwm)": "IWM", "small-cap (iwm)": "IWM", "rut/iwm": "IWM", "small-caps": "IWM",
    "vix": "^VIX", "cboe vix (^vix)": "^VIX",
    "ten-year yield": "^TNX", "10-year yields": "^TNX", "10-year yield": "^TNX", "10-year": "^TNX", "us 10y yield (^tnx)": "^TNX", "the 10-year": "^TNX",
    "10-year treasury yield": "^TNX", "us 10-year treasury yield (^tnx)": "^TNX", "10y yields": "^TNX",
    "dollar index": "DX-Y.NYB", "the dollar index": "DX-Y.NYB", "us dollar index (dxy)": "DX-Y.NYB",
    "wti crude oil": "CL=F", "oil": "CL=F", "gold (spot)": "GC=F",
    "semiconductors": "SMH", "semis": "SMH", "chip fund": "SMH", "semiconductors (smh)": "SMH", "semis (chip fund)": "SMH", "chip-related": "SMH",
    "anything semiconductor-adjacent": "SMH", "strongest page on the list (semiconductors)": "SMH", "tech & semis": "SMH",
    "semiconductors (memory and equipment rotation)": "SMH", "the memory and equipment rotation (within semiconductors)": "SMH",
    "tech / semis (xlk)": "XLK", "technology": "XLK", "tech": "XLK", "technology / saas": "XLK", "tech and growth": "XLK", "large-cap tech": "XLK",
    "megacap tech": "XLK", "tech (quality names)": "XLK", "long-duration tech": "XLK", "software": "IGV",
    "healthcare": "XLV", "health care": "XLV", "healthcare (xlv)": "XLV", "financials": "XLF", "financials (xlf)": "XLF",
    "energy": "XLE", "energy (xle)": "XLE", "energy & refining": "XLE", "energy & refining (xle)": "XLE", "energy - refiners": "XLE", "refiners": "XLE",
    "energy & midstream": "XLE", "energy / oilfield": "XLE", "physical energy assets": "XLE",
    "industrials": "XLI", "industrials (xli)": "XLI", "utilities": "XLU", "utilities (xlu)": "XLU", "power & scarcity": "XLU", "power & scarcity (xlu)": "XLU",
    "utilities / power": "XLU", "utilities & power": "XLU", "real estate": "XLRE", "real estate (xlre)": "XLRE",
    "consumer discretionary": "XLY", "consumer disc. (xly)": "XLY", "consumer staples (xlp)": "XLP", "materials": "XLB", "materials (xlb)": "XLB",
    "communication": "XLC", "communications": "XLC", "communication (xlc)": "XLC",
    "microsoft": "MSFT", "micron": "MU", "intel": "INTC", "nucor": "NUE", "nucor (nue)": "NUE", "allstate (all)": "ALL", "hartford (hig)": "HIG",
}
# names that are relative or composite calls, or that could not be tied to one instrument: counted, not graded
SKIP_WORDS = ("over", "all 20", "all twenty", "nothing on this list", "watchlist", "real yield", "fed funds", "precious metals", "metals", "biotech",
              "medical technology", "financials / bdcs", "water", "business services", "solar", "cyber", "exchanges", "dividend sector", "broad regional")


def to_ticker(name):
    k = name.strip().lower()
    if k in NAME_MAP:
        return NAME_MAP[k]
    if any(w in k for w in SKIP_WORDS):
        return None
    m = re.search(r"\(([A-Z]{1,5})\)\s*$", name.strip())
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Z]{1,5}(\.[A-Z])?", name.strip()):
        return name.strip()
    return None


# ---- horizons ------------------------------------------------------------------------------------------------------------------------
UNGRADEABLE_HZ = re.compile(r"conditional|\bif\b|until|\byet\b|3yr|target|on dips|no end|shopping|strategy|long-term|after friday|pick performance", re.I)
ONE_SESSION = re.compile(r"today|intraday|immediate|morning|midday|opening|session bias|after the bell|opening hour|regular trading|friday, june 26|daily move|"
                         r"thursday's opening|during the", re.I)
MONTH_DAY = re.compile(r"(?:before|by|through)\s+[A-Za-z ]*?(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? (\d{1,2})", re.I)
MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def parse_horizon(text, made_on, entry_date, default_k):
    """-> ("k", sessions) | ("date", iso) | ("friday", None) | ("nextfriday", None) | None (ungradeable)."""
    t = (text or "none stated").strip()
    low = t.lower()
    if UNGRADEABLE_HZ.search(low):
        return None
    m = re.search(r"(\d+)\s*-\s*(\d+)\s*(d|day|days|w|week|weeks|m|month|months)\b", low)
    if m:
        hi, unit = int(m.group(2)), m.group(3)
        per = 1 if unit.startswith("d") else 5 if unit.startswith("w") else 21
        return ("k", hi * per)
    if "next week" in low:
        return ("nextfriday", None)
    if re.search(r"week of|this week|weekly close|before friday|friday", low) and "june 26" not in low:
        return ("friday", None)
    m = MONTH_DAY.search(t)
    if m:
        year = made_on[:4]
        return ("date", f"{year}-{MONTHS[m.group(1).lower()[:3]]:02d}-{int(m.group(2)):02d}")
    if ONE_SESSION.search(low):
        return ("k", 1)
    return ("k", default_k)


def friday_of(day):
    from datetime import datetime, timedelta
    d = datetime.strptime(day, "%Y-%m-%d").date()
    return (d + timedelta(days=(4 - d.weekday()) % 7)).isoformat() if d.weekday() <= 4 else (d + timedelta(days=11 - d.weekday())).isoformat()


# ---- windows -------------------------------------------------------------------------------------------------------------------------
def entry_index(s, made_on, tod):
    return bisect.bisect_left(s.dates, made_on) if tod == "pre-market" else bisect.bisect_right(s.dates, made_on)


def exit_index(s, i0, hz):
    kind, v = hz
    if kind == "k":
        return i0 + v - 1
    if kind == "friday":
        end = friday_of(s.dates[i0])
    elif kind == "nextfriday":
        end = lab._plus(friday_of(s.dates[i0]), 7)
    else:
        end = v
    return bisect.bisect_right(s.dates, end) - 1


def poisson_binomial_p(hits, probs):
    """P(X >= hits) for a sum of independent Bernoulli(p_i)."""
    dist = np.zeros(len(probs) + 1)
    dist[0] = 1.0
    for p in probs:
        dist[1:] = dist[1:] * (1 - p) + dist[:-1] * p
        dist[0] *= (1 - p)
    return float(dist[hits:].sum())


class BaseRates:
    def __init__(self, series, spy):
        self.series, self.spy, self.cache = series, spy, {}

    def arrays(self, t, k):
        key = (t, k)
        if key in self.cache:
            return self.cache[key]
        s = self.series[t]
        o = np.array([r["open"] for r in s.rows])
        c = np.array([r["close"] for r in s.rows])
        dates = s.dates
        lo = bisect.bisect_left(dates, HISTORY_FROM)
        hi = bisect.bisect_right(dates, LAST_DAY)
        n = hi - k + 1
        if n - lo < 100:
            self.cache[key] = None
            return None
        idx = np.arange(lo, n)
        from numpy.lib.stride_tricks import sliding_window_view
        win = sliding_window_view(c[:hi], k)[lo:n]
        ret = c[idx + k - 1] / o[idx] - 1.0
        out = {"ret": ret, "minr": win.min(axis=1) / o[idx], "maxr": win.max(axis=1) / o[idx], "dates": [dates[i] for i in idx], "dates_end": [dates[i + k - 1] for i in idx]}
        self.cache[key] = out
        return out

    def up(self, t, k, want_up):
        a = self.arrays(t, k)
        if a is None:
            return None
        return float((a["ret"] > 0).mean() if want_up else (a["ret"] < 0).mean())

    def outperform(self, t, k, want_out):
        a = self.arrays(t, k)
        if a is None:
            return None
        sp = self.spy
        d2i = {d: i for i, d in enumerate(sp.dates)}
        s = self.series[t]
        diffs = []
        for d0, d1, r in zip(a["dates"], a["dates_end"], a["ret"]):
            if d0 in d2i and d1 in d2i:
                diffs.append(r - (sp.rows[d2i[d1]]["close"] / sp.rows[d2i[d0]]["open"] - 1.0))
        if len(diffs) < 100:
            return None
        diffs = np.array(diffs)
        return float((diffs > 0).mean() if want_out else (diffs < 0).mean())

    def level(self, t, k, rule, ratio):
        a = self.arrays(t, k)
        if a is None:
            return None
        if rule == "no_close_below":
            return float((a["minr"] >= ratio).mean())
        if rule == "no_close_above":
            return float((a["maxr"] <= ratio).mean())
        if rule == "some_close_below":
            return float((a["minr"] < ratio).mean())
        return float((a["maxr"] > ratio).mean())


def level_rule(rec):
    """Relation and direction are read together: 'above' with direction up is a call to get above X (some close above), 'above' or 'holds' with no
    direction is a call to stay above (no close below); 'below' with direction down is a break below (some close below), 'below' with no direction a
    ceiling (no close above). Fixed after the first partial run showed targets read as floors (a plumbing correction, made on the quotes' meaning)."""
    rel, d = rec.get("level_relation"), rec.get("direction")
    if rel == "above":
        return "some_close_above" if d == "up" else "no_close_below"
    if rel == "holds":
        return "no_close_below" if d != "down" else None
    if rel == "below":
        return "some_close_below" if d == "down" else "no_close_above"
    if rel == "breaks":
        return "some_close_below" if d == "down" else "some_close_above" if d == "up" else None
    if rel == "reclaims":
        return "some_close_above"
    return None


def grade_level(rule, X, bars, i0, i1):
    closes = [r["close"] for r in bars.rows[i0:i1 + 1]]
    return {"no_close_below": min(closes) >= X, "no_close_above": max(closes) <= X,
            "some_close_below": min(closes) < X, "some_close_above": max(closes) > X}[rule]


# ---- loading -------------------------------------------------------------------------------------------------------------------------
def load_records(dir_):
    dir_ = Path(dir_)
    out, counts = [], Counter()
    for f in sorted(dir_.glob("records_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        sid = d["source_id"]
        vf = dir_ / f"verified_{sid}.json"
        if not vf.exists():
            counts["unverified_source"] += len(d["records"])
            continue
        v = json.loads(vf.read_text(encoding="utf-8"))
        keep = set(v.get("keep", []))
        fixes = defaultdict(dict)
        for fx in v.get("fix", []):
            fixes[fx["id"]][fx["field"]] = fx["value"]
        for r in d["records"]:
            if r["id"] not in keep:
                counts["dropped_by_verifier"] += 1
                continue
            r = dict(r, **fixes.get(r["id"], {}))
            r["family"] = re.split(r"[-_]", sid)[0].replace("fsw", "watchlist")
            r["source_id"] = sid
            out.append(r)
    seen, dedup = set(), []
    for r in out:
        key = (r["family"], r["made_on"], r["instrument"].lower(), r["kind"], r.get("direction"), r.get("level"), r.get("level_relation"))
        if key in seen:
            counts["duplicate"] += 1
            continue
        seen.add(key)
        dedup.append(r)
    counts["kept"] = len(dedup)
    return dedup, counts


# ---- grading -------------------------------------------------------------------------------------------------------------------------
OUT_WORDS = {"outperform", "up", "buy", "add"}
UNDER_WORDS = {"underperform", "down", "avoid", "trim"}


def window_return(s, d0, d1):
    """Open of the first bar on or after d0 to the close of the last bar on or before d1; None if the series does not cover it."""
    lo, hi = bisect.bisect_left(s.dates, d0), bisect.bisect_right(s.dates, d1) - 1
    if lo > hi or hi < 0 or s.dates[hi] < lab._plus(d1, -4) or s.dates[lo] > lab._plus(d0, 4):
        return None
    return s.rows[hi]["close"] / s.rows[lo]["open"] - 1.0


def grade_one(r, series, br, uni):
    t = to_ticker(r["instrument"])
    if t is None:
        return {"status": "unmapped"}
    s = series.get(t)
    if s is None or len(s.dates) < 250:
        return {"status": "no_bars", "ticker": t}
    kind = r["kind"]
    default_k = 1 if (t in INDEX_LIKE and kind in ("direction", "level")) else 5
    hz = parse_horizon(r.get("horizon_as_written"), r["made_on"], None, default_k)
    if hz is None:
        return {"status": "ungradeable_horizon", "ticker": t}
    i0 = entry_index(s, r["made_on"], r.get("time_of_day", "unstated"))
    if i0 >= len(s.rows):
        return {"status": "open", "ticker": t}
    i1 = exit_index(s, i0, hz)
    if i1 < i0:
        return {"status": "bad_window", "ticker": t}
    if i1 >= len(s.rows) or s.dates[i1] > LAST_DAY:
        return {"status": "open", "ticker": t}
    k = i1 - i0 + 1
    d0, d1 = s.dates[i0], s.dates[i1]
    base = {"ticker": t, "k": k, "entry": d0, "exit": d1, "family": r["family"], "kind": kind, "source_id": r["source_id"], "id": r["id"]}
    ret = s.rows[i1]["close"] / s.rows[i0]["open"] - 1.0
    if kind == "direction":
        d = r.get("direction")
        if d not in ("up", "down"):
            return {"status": "not_graded_direction", "ticker": t}
        p0 = br.up(t, k, d == "up")
        return dict(base, status="graded", hit=bool((ret > 0) == (d == "up")) if ret != 0 else False, base_rate=p0, ret=ret)
    if kind == "level":
        rule, X = level_rule(r), r.get("level")
        if rule is None or X is None:
            return {"status": "not_graded_level", "ticker": t}
        entry = s.rows[i0]["open"]
        ratio = X / entry
        if not 0.5 <= ratio <= 2.0:
            return {"status": "scale_mismatch", "ticker": t}
        p0 = br.level(t, k, rule, ratio)
        return dict(base, status="graded", hit=bool(grade_level(rule, X, s, i0, i1)), base_rate=p0, ret=ret)
    # ranking and pick: relative to SPY
    d = r.get("direction")
    want_out = d in OUT_WORDS
    if not (want_out or d in UNDER_WORDS):
        return {"status": "not_graded_direction", "ticker": t}
    spy = br.spy
    sr = window_return(spy, d0, d1)
    if sr is None:
        return {"status": "no_spy", "ticker": t}
    excess = ret - sr
    out = dict(base, status="graded", hit=bool((excess > 0) == want_out) if excess != 0 else False, ret=ret, excess=excess, want_out=want_out)
    if kind == "ranking":
        out["base_rate"] = br.outperform(t, k, want_out)
    else:
        sgn = 1.0 if want_out else -1.0
        vec = []
        for u in uni.values():
            x = window_return(u, d0, d1)
            vec.append(np.nan if x is None else sgn * (x - sr))
        out["signed_excess"] = sgn * excess
        out["null_vec"] = np.array(vec)
    return out


def aggregate(graded, rng):
    groups = defaultdict(list)
    for g in graded:
        if g.get("status") == "graded":
            groups[(g["family"], g["kind"])].append(g)
    out = {}
    for (fam, kind), gs in sorted(groups.items()):
        n = len(gs)
        row = {"family": fam, "kind": kind, "graded": n, "hits": sum(1 for g in gs if g["hit"]), "decisive": n >= MIN_DECISIVE}
        row["hit_rate"] = row["hits"] / n
        if kind in ("direction", "level", "ranking"):
            ps = [g["base_rate"] for g in gs if g.get("base_rate") is not None]
            if len(ps) == n:
                row["mean_base_rate"] = float(np.mean(ps))
                row["p_one_sided"] = poisson_binomial_p(row["hits"], ps)
            else:
                row["note"] = f"{n - len(ps)} calls had too little history for a base rate"
            row["beats_base_rate"] = bool(row["decisive"] and row.get("p_one_sided", 1.0) <= 0.05)
        else:
            sig = np.array([g["signed_excess"] for g in gs])
            row["mean_excess"], row["median_excess"] = float(sig.mean()), float(np.median(sig))
            mats = [g["null_vec"][~np.isnan(g["null_vec"])] for g in gs]
            if all(len(m) >= 50 for m in mats):
                draws = np.vstack([rng.choice(m, size=DRAWS) for m in mats])
                dm, dmed = draws.mean(axis=0), np.median(draws, axis=0)
                row["pct_mean"] = float((dm < row["mean_excess"]).mean() * 100)
                row["pct_median"] = float((dmed < row["median_excess"]).mean() * 100)
                row["beats_random"] = bool(row["decisive"] and row["pct_mean"] >= 97.5 and row["pct_median"] >= 97.5)
            else:
                row["note"] = "too few random-draw names priced for the window"
        row["by_document"] = cluster_check(gs, kind)
        out[f"{fam}/{kind}"] = row
    return out


def cluster_check(gs, kind):
    """Calls inside one document share a day, a regime and often a name, so the binomial over calls overstates the evidence. This groups by
    source document and asks the same question one level up (an unregistered check, reported beside the registered rule, never instead of it)."""
    docs = defaultdict(list)
    for g in gs:
        docs[g["source_id"]].append(g)
    diffs = []
    for sid, ds in docs.items():
        if kind == "pick":
            sig = [g["signed_excess"] - float(np.nanmean(g["null_vec"])) for g in ds if g.get("null_vec") is not None and np.isfinite(g["null_vec"]).any()]
            if sig:
                diffs.append(float(np.mean(sig)))
        else:
            ps = [g["base_rate"] for g in ds if g.get("base_rate") is not None]
            if ps:
                diffs.append(float(np.mean([1.0 if g["hit"] else 0.0 for g in ds if g.get("base_rate") is not None]) - np.mean(ps)))
    n = len(diffs)
    out = {"documents": n, "documents_above_null": sum(1 for d in diffs if d > 0)}
    if n >= 2:
        k = out["documents_above_null"]
        from math import comb
        out["sign_test_p"] = float(sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n)
        if n >= 3 and float(np.std(diffs, ddof=1)) > 0:
            out["mean_diff"] = float(np.mean(diffs))
            out["t"] = float(np.mean(diffs) / (np.std(diffs, ddof=1) / np.sqrt(n)))
    return out


def run(records_dir):
    from pass9_universe import sp500_asof
    records, load_counts = load_records(records_dir)
    tickers = {to_ticker(r["instrument"]) for r in records} - {None}
    tickers |= {"SPY"}
    series = {t: lab.Series(b) for t, b in lab.bars_by_ticker(lab.download(sorted(tickers), True, "2026-10-13", "2017-12-01")).items()}
    thin = sorted(t for t in tickers if t not in series or len(series[t].dates) < 250)
    uni_names = sp500_asof()
    uni = {t: lab.Series(b) for t, b in lab.bars_by_ticker(lab.download(uni_names, True, "2026-10-13", "2026-05-01")).items() if b}
    br = BaseRates(series, series["SPY"])
    graded = [dict(grade_one(r, series, br, uni), family=r["family"], kind=r["kind"], source_id=r["source_id"], id=r["id"]) for r in records]
    status = Counter((g["family"], g["status"]) for g in graded)
    rng = np.random.default_rng(lab.SEED)
    agg = aggregate(graded, rng)
    return {"registered": "517e4b7", "load": dict(load_counts), "thin_tickers": thin, "status": {f"{f}/{s}": n for (f, s), n in sorted(status.items())},
            "tests": agg, "graded_rows": [{k: v for k, v in g.items() if k != "null_vec"} for g in graded if g.get("status") == "graded"]}
