#!/usr/bin/env python3
"""Pass 11 -- Cecil with a P/E, and the owner's themes.

A. Cecil, properly. Every history pass so far replayed Cecil without a P/E
   (production reads today's multiple, which is not point in time), so his
   value leg sat at its neutral 15 and what got scored was his safety leg,
   a low-volatility screen. This pass hands him a point-in-time P/E: the
   last close before the Monday over the trailing four quarters' reported
   EPS as known by then (the EPS cache the Council Room's Cecil reads;
   prices and reported EPS are both split-adjusted by the source). His
   quality leg stays neutral: there are no point-in-time fundamentals.
   Books, his five each week, on the 111's 109 stocks and on the S&P 500 as
   of 2024-09-09 (463):
     Cecil, no P/E    the lab's Cecil of Passes 1-9                 baseline
     Cecil, P/E       the same engine with the point-in-time multiple
     Cheapest five    the five lowest positive P/E among the week's
                      tradeable names: the multiple alone, no engine
B. The owner's themes. Ophelia's rotation under lab/themes_111.csv (twelve
   themes drawn by the owner's lights on 2026-09-22; every stock in one) on
   the 111, beside engine 8, GICS 11 and our own 11 replayed with Pass 10's
   seeds (they must reproduce Pass 10's 111 numbers). A theme is offensive or
   defensive by the majority engine bucket of its members.

Scored as in Passes 9 and 10: clipped edge over random books from the same
universe's tradeable names, raw beside. Registered in lab/README.md before
any run.

    python lab/pass11_cecil_themes.py            # both parts
    python lab/pass11_cecil_themes.py themes     # part B only (after editing the CSV)
    python lab/pass11_cecil_themes.py smoke      # three weeks on the 111, to the gitignored cache
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import council_room_v2 as v2  # noqa: E402
import engine_lab as lab  # noqa: E402
import pass4_marky as p4  # noqa: E402
import pass7_combos as p7  # noqa: E402
import pass9_universe as p9  # noqa: E402
import pass10_sectors as p10  # noqa: E402

THEMES_CSV = lab.LAB / "themes_111.csv"
CLEAN = "the S&P 500 as of 2024-09"
CECIL_BOOKS = ("Cecil, no P/E", "Cecil, P/E", "Cheapest five")
THEME_SCHEMES = ("engine 8", "GICS 11", "our own 11", "the owner's themes")


# ---- A. Cecil ---------------------------------------------------------------
def _ttm(rows, before):
    past = [e for d, e in rows if d < before and e is not None]
    return sum(past[-4:]) if len(past) >= 4 else None


def pe_builder(names, raw, weeks):
    """engine_lab.run's pe_builder: get_pe(ticker, date) from the EPS cache."""
    eps = v2.eps_history(sorted(names))

    def get_pe(ticker, date=None):
        s = raw.get(ticker)
        px = s.last_close_before(date) if s and date else None
        ttm = _ttm(eps.get(ticker) or [], date) if date else None
        return px / ttm if px and ttm else None      # ttm <= 0 -> a negative multiple, which Cecil scores 0
    return get_pe


def cecil_replay(uname, names, weeks, start, cal, raw, adj, tag):
    get_pe = pe_builder(names, raw, weeks)
    plain = lab.run(verbose=False, knobs=lab.VARIANTS3["base"], weeks=weeks, start=start, earnings=cal, names=names)
    with_pe = lab.run(verbose=False, knobs=dict(lab.VARIANTS3["base"], pe_builder=pe_builder),
                      weeks=weeks, start=start, earnings=cal, names=names)
    out = []
    for r0, r1, (label, W, _) in zip(plain, with_pe, weeks):
        tradeable = p10.pool(names, raw, cal, W)
        tset = set(tradeable)
        fives = {"Cecil, no P/E": [t for t in r0["proposals"]["Cecil"] if t in tset][:p7.TOP],
                 "Cecil, P/E": [t for t in r1["proposals"]["Cecil"] if t in tset][:p7.TOP]}
        pes = {t: get_pe(t, W) for t in tradeable}
        cheap = sorted((t for t, pe in pes.items() if pe and pe > 0), key=lambda t: pes[t])[:p7.TOP]
        fives["Cheapest five"] = cheap
        known = sum(1 for pe in pes.values() if pe is not None)
        out.append({"week": label, "spy": adj["SPY"].week_return(W) or 0.0, "five": fives["Cecil, P/E"],
                    "fives": fives, "pe_known": known, "tradeable": len(tradeable),
                    "pe_of_five": {t: round(pes[t], 1) for t in fives["Cecil, P/E"] if pes.get(t)},
                    "books": p7.score_week({b: p7.equal(fives[b]) for b in CECIL_BOOKS}, adj, W, tradeable,
                                           f"p11-{uname}-{tag}")})
    return out


def show_cecil(title, s, pairs):
    print(f"\n  {title}")
    print(f"  {'book':<16}{'edge/wk':>9}{'t':>7}{'ahead':>8}{'ret/wk':>8}{'weekly SD':>11}{'max DD':>8}   paired")
    for b in CECIL_BOOKS:
        x = s[b]
        p = pairs.get(b)
        tail = f"   {p['mean']*100:+.2f}%/wk (t {p['t']:+.2f}, {p['weeks_better']}/{p['weeks']}; same five {p['same_five']:.0%}) vs Cecil, no P/E" if p else ""
        print(f"  {b:<16}{x['edge']*100:+8.2f}%{x['t']:+7.2f}{x['ahead']:>5}/{x['weeks']:<3}{x['mean_ret']*100:+7.2f}%"
              f"{x['sd']*100:10.2f}%{x['max_dd']*100:+7.1f}%{tail}")
    print("  by half-year, clipped edge/wk: " + " | ".join(
        f"{b}: " + ", ".join(f"{k} {v*100:+.2f}" for k, v in s[b]["by_half_year"].items()) for b in CECIL_BOOKS))


# ---- B. the owner's themes ---------------------------------------------------
def themes():
    with open(THEMES_CSV, encoding="ascii") as fh:
        rows = [r for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))]
    return {r["ticker"]: r["theme"] for r in rows}


def theme_map(names):
    m = themes()
    missing = [t for t in names if t not in m]
    if missing:
        raise SystemExit(f"themes_111.csv lacks: {', '.join(missing)}")
    members = {}
    for t in names:
        members.setdefault(m[t], []).append(p10.bucket(t))
    majority = {theme: Counter(bs).most_common(1)[0][0] for theme, bs in members.items()}
    off = [theme for theme, b in majority.items() if b in p10.OFFENSIVE]
    dfn = [theme for theme, b in majority.items() if b in p10.DEFENSIVE]
    return {t: m[t] for t in names}, off, dfn, {theme: len(bs) for theme, bs in members.items()}


def theme_replays(names, hweeks, cweeks, cal, raw, adj, sp):
    maps, _ = p10.static_maps(p9.REFERENCE, names, sp)
    maps["our own 11"] = p10.own_map(names, adj, hweeks + cweeks)
    tm, off, dfn, sizes = theme_map(names)
    maps["the owner's themes"] = (tm, off, dfn)
    hist, cw = {}, {}
    for scheme in THEME_SCHEMES:
        m, o, d = maps[scheme]
        hist[scheme] = p10.replay(p9.REFERENCE, scheme, names, hweeks, lab.HISTORY_DATA_START, cal, raw, adj, m, o, d, "hist")
        cw[scheme] = p10.replay(p9.REFERENCE, scheme, names, cweeks, lab.DATA_START, cal, raw, adj, m, o, d, "council")
        print(f"    {scheme}: done", flush=True)
    return hist, cw, {"sizes": sizes, "offensive": off, "defensive": dfn}


def reproduces_pass10(hs):
    path = lab.RESULTS / "pass10_sectors.json"
    if not path.exists():
        return None
    old = json.loads(path.read_text(encoding="utf-8"))["universes"][p9.REFERENCE]["history"]["summary"]
    return all(abs(old[s][k] - hs[s][k]) < 1e-9 for s in ("engine 8", "GICS 11", "our own 11") for k in ("edge", "t", "sd"))


# ---- main ----------------------------------------------------------------------
def main(mode=None):
    smoke = mode == "smoke"
    U = p9.universes()
    sp = p10.sp500_full()
    hweeks = lab.history_weeks(lab.HISTORY_FIRST_MONDAY, lab.HISTORY_LAST_MONDAY)
    cweeks = lab.council_weeks(p9._last_friday())
    if smoke:
        hweeks, cweeks = hweeks[:3], cweeks[:1]
    end = lab._plus(cweeks[-1][1], 5)
    result = {"cecil": {}, "themes": {}}
    universes = {p9.REFERENCE: U[p9.REFERENCE]} if (smoke or mode == "themes") else {p9.REFERENCE: U[p9.REFERENCE], CLEAN: p9.sp500_asof()}
    data = {}
    for uname, names in universes.items():
        cal = lab.earnings_calendar(names)
        tickers = sorted(set(names)) + lab.EXTRA
        raw = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, False, end, p4.HIST_START)).items()}
        adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, True, end, p4.HIST_START)).items()}
        data[uname] = (names, cal, raw, adj)
    if mode != "themes":
        for uname, (names, cal, raw, adj) in data.items():
            print(f"  Cecil on {uname}: {len(names)} names", flush=True)
            hist = cecil_replay(uname, names, hweeks, lab.HISTORY_DATA_START, cal, raw, adj, "hist")
            cw = cecil_replay(uname, names, cweeks, lab.DATA_START, cal, raw, adj, "council")
            out = {}
            for section, rows, title in (("history", hist, f"Cecil on {uname}: history, {len(hweeks)} weeks"),
                                         ("council", cw, f"Cecil on {uname}: Council weeks, {len(cweeks)} (seen; decide nothing)")):
                s = {b: p10.summarize(rows, b) for b in CECIL_BOOKS}
                pairs = {"Cecil, P/E": p10.paired(rows, rows, "Cecil, P/E", "Cecil, no P/E"),
                         "Cheapest five": p10.paired(rows, rows, "Cheapest five", "Cecil, no P/E")}
                for b in pairs:                     # paired() compared a row with itself here
                    pairs[b]["same_five"] = statistics.fmean(
                        1.0 if r["fives"][b] == r["fives"]["Cecil, no P/E"] else 0.0 for r in rows)
                show_cecil(title, s, pairs)
                print(f"  P/E known for {statistics.fmean(r['pe_known'] for r in rows):.0f} of "
                      f"{statistics.fmean(r['tradeable'] for r in rows):.0f} tradeable names a week")
                out[section] = {"summary": s, "paired": pairs, "weeks": rows}
            result["cecil"][uname] = out
    names, cal, raw, adj = data[p9.REFERENCE]
    print(f"  themes on {p9.REFERENCE}:", flush=True)
    hist, cw, info = theme_replays(names, hweeks, cweeks, cal, raw, adj, sp)
    hs = {s: p10.summarize(hist[s]) for s in THEME_SCHEMES}
    hp = {s: p10.paired(hist[s], hist["engine 8"]) for s in THEME_SCHEMES if s != "engine 8"}
    p10.SCHEMES, keep = THEME_SCHEMES, p10.SCHEMES
    try:
        p10.show(f"Ophelia's map on {p9.REFERENCE}: history, {len(hweeks)} weeks", hs, hp)
        cs = {s: p10.summarize(cw[s]) for s in THEME_SCHEMES}
        cp = {s: p10.paired(cw[s], cw["engine 8"]) for s in THEME_SCHEMES if s != "engine 8"}
        p10.show(f"Ophelia's map on {p9.REFERENCE}: Council weeks, {len(cweeks)} (seen; decide nothing)", cs, cp)
    finally:
        p10.SCHEMES = keep
    rep = None if smoke else reproduces_pass10(hs)
    print(f"  themes: {info['sizes']}; offensive {info['offensive']}; defensive {info['defensive']}")
    print(f"  engine 8 / GICS 11 / our own 11 reproduce Pass 10's 111 numbers: {rep}")
    result["themes"] = {"info": info, "reproduces_pass10": rep,
                        "history": {"summary": hs, "paired": hp, "weeks": hist},
                        "council": {"summary": cs, "paired": cp, "weeks": cw}}
    v = {}
    if mode != "themes":
        for uname in universes:
            h = result["cecil"][uname]["history"]
            x, p, c = h["summary"]["Cecil, P/E"], h["paired"]["Cecil, P/E"], h["summary"]["Cheapest five"]
            v[f"Cecil, P/E beats random on {uname}"] = bool(x["t"] >= 2 and x["edge"] > 0 and x["halves"] and all(q > 0 for q in x["halves"]))
            v[f"the P/E helps Cecil on {uname}"] = bool(p["t"] >= 2 and p["mean"] > 0 and p["halves"] and all(q > 0 for q in p["halves"]))
            v[f"cheapest five beats random on {uname}"] = bool(c["t"] >= 2 and c["edge"] > 0 and c["halves"] and all(q > 0 for q in c["halves"]))
    p = hp["the owner's themes"]
    v["the owner's themes help on the 111"] = bool(p["t"] >= 2 and p["mean"] > 0 and p["halves"] and all(q > 0 for q in p["halves"]))
    result["verdicts"] = v
    print("\n  registered verdicts (history): " + "; ".join(f"{k}: {'YES' if ok else 'no'}" for k, ok in v.items()))
    out = lab.CACHE / "pass11.smoke.json" if smoke else lab.RESULTS / ("pass11_themes.json" if mode == "themes" else "pass11_cecil_themes.json")
    with open(out, "w", encoding="ascii", newline="\n") as fh:
        json.dump(result, fh, indent=1, default=float)
        fh.write("\n")


if __name__ == "__main__":
    main(sys.argv[1] if sys.argv[1:] else None)
