#!/usr/bin/env python3
"""Pass 8 -- the Warden taken apart.

Pass 7's Warden, a chair that sizes instead of picking, halved the book's
weekly SD and worst drawdown for -0.30%/wk of edge (t -1.67). It pulls three
levers: inverse 12-week-volatility weights, at most two names a sector (the
two calmest), and 80% invested when SPY closed below its 40-week average.
Registered in lab/README.md before any number was computed. Three questions:

  1. Which lever does the work?  Eight books on the three chairs' names
     (Ophelia, Cecil, Marky -- Dash flopped in Pass 7 and is dismissed):
     every subset of the levers, from none to all three.
  2. Does the Warden still hold over the three live chairs?  That is the book
     the forward record would carry.  Against three chairs, a third each.
  3. Does Cecil's gate on Marky stack with it?  The Warden over Ophelia,
     Cecil and Quality pullback.  Against the Warden over the three chairs.

Names, blackouts, Dash and the members' fives come from Pass 7's code path
unchanged (history: engines from a baseline replay, Marky's channel ranking;
Council weeks: the Room v2 agents' fives on the 111).  A name needs four
weekly returns for its volatility; the same names sit in every ablation book.
One fix from Pass 7: the sector cap looks a name up in the owner's list's
GICS sectors first, because the engines' SECTOR_MAP has no entry for 46 of
the 111 and Pass 7's cap treated them as one "Unknown" sector on the Council
weeks (history's frozen list is fully mapped, more coarsely).  Pass 7's Warden
and Four chairs are rebuilt with Pass 7's lookup as a regression check and
must reproduce Pass 7's history numbers exactly.

Attribution, on the weekly SD of the raw book return:
  cut            = SD(No lever) - SD(Warden, three chairs)
  alone share    = (SD(No lever) - SD(lever only)) / cut
  removed share  = (SD(all but lever) - SD(Warden, three chairs)) / cut
A lever CARRIES the Warden if both shares are at least 50%; it is DEAD WEIGHT
if both are at most 15%; otherwise it HELPS.  The cheapest rule is the book
with the fewest levers whose SD is within 80% of the full cut, ties to the
higher paired edge over No lever.

    python lab/pass8_warden.py
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass7_combos as p7  # noqa: E402

FULL = "Warden, three chairs"
BASE = "No lever"
ABLATION = {  # book: levers on
    BASE: dict(sizing=False, cap=False, dial=False),
    "Sizing only": dict(sizing=True, cap=False, dial=False),
    "Cap only": dict(sizing=False, cap=True, dial=False),
    "Dial only": dict(sizing=False, cap=False, dial=True),
    "All but sizing": dict(sizing=False, cap=True, dial=True),
    "All but cap": dict(sizing=True, cap=False, dial=True),
    "All but dial": dict(sizing=True, cap=True, dial=False),
    FULL: dict(sizing=True, cap=True, dial=True),
}
LEVERS = {"sizing": ("Sizing only", "All but sizing"),
          "cap": ("Cap only", "All but cap"),
          "dial": ("Dial only", "All but dial")}
PAIRS = [("Sizing only", BASE), ("Cap only", BASE), ("Dial only", BASE),
         ("All but sizing", BASE), ("All but cap", BASE), ("All but dial", BASE),
         (FULL, "All but sizing"), (FULL, "All but cap"), (FULL, "All but dial"),
         (FULL, BASE), (FULL, "Three chairs"),
         ("Warden, quality", FULL), ("The Warden", "Four chairs")]
CARRIES, DEAD = 0.50, 0.15
CHEAP_CUT = 0.80
SD_CUT = 0.90          # Pass 7's rule: at least a 10% lower weekly SD


def sector(t):
    """The owner's list's GICS sector first (the engines' SECTOR_MAP has no
    entry for 46 of the 111, and lumps them as 'Unknown'), the engines' map
    for older names on the frozen history list."""
    from scan_pipeline.config.tickers import COUNCIL_SECTORS
    from scan_pipeline.utils.data_utils import get_sector
    return COUNCIL_SECTORS.get(t) or get_sector(t)


def warden_book(names, raw, W, spy_below, sizing=True, cap=True, dial=True, get_sector=sector):
    """Pass 7's warden() with each lever switchable and the sector lookup a
    parameter; all levers on with the engines' lookup, it is identical."""
    from scan_pipeline.fetch_market_data import _aggregate_weekly
    inv = {}
    for t in names:
        wk = _aggregate_weekly(raw[t].before(W, 120)) if t in raw else []
        rets = [h.return_ for h in wk[-12:]]
        sd = statistics.pstdev(rets) if len(rets) >= 4 else None
        if sd:
            inv[t] = 1.0 / sd
    order = sorted(inv, key=lambda t: -inv[t])           # calmest first
    if cap:
        by_sector = {}
        for t in order:
            by_sector.setdefault(get_sector(t), []).append(t)
        keep = [t for ts in by_sector.values() for t in ts[:p7.SECTOR_CAP]]
    else:
        keep = order
    wt = {t: (inv[t] if sizing else 1.0) for t in keep}
    total = sum(wt.values())
    exposure = p7.RISK_OFF_INVESTED if (dial and spy_below) else 1.0
    return [(t, exposure * wt[t] / total) for t in keep] if total else []


def build_books(fives, prev_ophelia, dash, ranking, value_ok, raw, W):
    three = [fives["Ophelia"], fives["Cecil"], fives["Marky"]]
    quality = [t for t in ranking if t in value_ok][:p7.TOP]
    names3 = sorted({t for g in three for t in g})
    namesq = sorted({t for g in (fives["Ophelia"], fives["Cecil"], quality) for t in g})
    names4 = sorted({t for g in three + [dash] for t in g})
    below = p7.spy_below_40w(raw, W)
    books = {"Three chairs": p7.slices(three), "Four chairs": p7.slices(three + [dash])}
    for name, levers in ABLATION.items():
        books[name] = warden_book(names3, raw, W, below, **levers)
    books["Warden, quality"] = warden_book(namesq, raw, W, below)
    from scan_pipeline.utils.data_utils import get_sector     # Pass 7 as it ran, for the regression check
    books["The Warden"] = warden_book(names4, raw, W, below, get_sector=get_sector)
    return books


def summarize(rows):
    names = sorted({n for r in rows for n in r["books"]})
    s = {}
    for n in names:
        rs = [r["books"][n] for r in rows if n in r["books"]]
        half = len(rs) // 2
        e = [x["clipped"]["edge"] for x in rs]
        ret = [x["raw"]["ret"] for x in rs]
        sd = statistics.pstdev(ret)
        s[n] = {"weeks": len(rs), "edge": statistics.fmean(e), "t": lab._tstat(e),
                "ahead": sum(1 for x in e if x > 0),
                "halves": [statistics.fmean(e[:half]), statistics.fmean(e[half:])] if half else None,
                "raw_edge": statistics.fmean(x["raw"]["edge"] for x in rs),
                "mean_ret": statistics.fmean(ret), "sd": sd,
                "ret_over_sd": statistics.fmean(ret) / sd if sd else None,
                "max_dd": lab._curve(ret)[1],
                "invested": statistics.fmean(x["invested"] for x in rs),
                "names": statistics.fmean(len(x["book"]) for x in rs)}
    return s


def paired(rows, a, b):
    diff = [r["books"][a]["clipped"]["edge"] - r["books"][b]["clipped"]["edge"]
            for r in rows if a in r["books"] and b in r["books"]]
    if not diff:
        return None
    half = len(diff) // 2
    return {"mean": statistics.fmean(diff), "t": lab._tstat(diff),
            "halves": [statistics.fmean(diff[:half]), statistics.fmean(diff[half:])] if half else None,
            "weeks_better": sum(1 for x in diff if x > 0), "weeks": len(diff)}


def attribution(s, p):
    base, full = s[BASE], s[FULL]
    cut, dd_cut = base["sd"] - full["sd"], full["max_dd"] - base["max_dd"]
    out = {"sd_cut": cut, "sd_cut_share": cut / base["sd"] if base["sd"] else None,
           "dd_cut": dd_cut, "edge_cost": p[f"{FULL} vs {BASE}"]["mean"], "levers": {}}
    for lever, (alone, without) in LEVERS.items():
        a = (base["sd"] - s[alone]["sd"]) / cut if cut else None
        r = (s[without]["sd"] - full["sd"]) / cut if cut else None
        role = ("carries" if a >= CARRIES and r >= CARRIES else
                "dead weight" if a <= DEAD and r <= DEAD else "helps")
        out["levers"][lever] = {
            "alone_share": a, "removed_share": r, "role": role,
            "dd_alone": s[alone]["max_dd"] - base["max_dd"], "dd_removed": full["max_dd"] - s[without]["max_dd"],
            "edge_alone": p[f"{alone} vs {BASE}"]["mean"], "edge_removed": p[f"{FULL} vs {without}"]["mean"]}
    target = base["sd"] - CHEAP_CUT * cut
    cands = [(sum(lv.values()), -(p[f"{n} vs {BASE}"]["mean"] if n != BASE else 0.0), n)
             for n, lv in ABLATION.items() if s[n]["sd"] <= target]
    out["cheapest"] = min(cands)[2] if cands else None
    return out


def verdicts(s, p):
    v = {}
    x, b, vb = s[FULL], s["Three chairs"], p[f"{FULL} vs Three chairs"]
    v[FULL] = bool(x["sd"] <= SD_CUT * b["sd"] and x["max_dd"] > b["max_dd"] and vb["t"] > -2)
    x, b, vb = s["Warden, quality"], s[FULL], p[f"Warden, quality vs {FULL}"]
    v["Warden, quality"] = bool(x["sd"] <= SD_CUT * b["sd"] and x["max_dd"] >= b["max_dd"] and vb["t"] > -2)
    return v


def reproduces_pass7(s):
    """Pass 7's Warden and Four chairs, rebuilt here, must match its results file."""
    doc = json.loads((lab.RESULTS / "pass7_combos.json").read_text(encoding="utf-8"))
    old = doc["history"]["summary"]
    return all(abs(old[n][k] - s[n][k]) < 1e-9 for n in ("The Warden", "Four chairs")
               for k in ("edge", "t", "sd", "max_dd"))


def show(title, s, p):
    order = ["Three chairs"] + list(ABLATION) + ["Warden, quality", "Four chairs", "The Warden"]
    print(f"\n  {title}")
    print(f"  {'book':<22}{'edge/wk':>9}{'t':>7}{'ahead':>8}{'ret/wk':>8}{'weekly SD':>11}{'ret/SD':>8}{'max DD':>8}{'invested':>10}")
    for n in order:
        x = s.get(n)
        if not x:
            continue
        print(f"  {n:<22}{x['edge']*100:+8.2f}%{x['t']:+7.2f}{x['ahead']:>5}/{x['weeks']:<3}{x['mean_ret']*100:+7.2f}%"
              f"{x['sd']*100:10.2f}%{x['ret_over_sd']:+8.2f}{x['max_dd']*100:+7.1f}%{x['invested']*100:9.0f}%")
    print("  paired, clipped edge:")
    for k, x in p.items():
        print(f"    {k:<44}{x['mean']*100:+.2f}%/wk (t {x['t']:+.2f}, {x['weeks_better']}/{x['weeks']})")


def show_attribution(a):
    print(f"\n  The Warden's SD cut over No lever: {a['sd_cut']*100:.2f} points ({a['sd_cut_share']:.0%}); "
          f"drawdown {a['dd_cut']*100:+.1f} points; edge cost {a['edge_cost']*100:+.2f}%/wk")
    print(f"  {'lever':<8}{'alone':>8}{'removed':>9}   role          DD alone  DD removed  edge alone  edge removed")
    for lever, x in a["levers"].items():
        print(f"  {lever:<8}{x['alone_share']:>8.0%}{x['removed_share']:>9.0%}   {x['role']:<12}"
              f"{x['dd_alone']*100:+9.1f}%{x['dd_removed']*100:+11.1f}%{x['edge_alone']*100:+11.2f}%{x['edge_removed']*100:+13.2f}%")
    print(f"  cheapest rule with at least {CHEAP_CUT:.0%} of the cut: {a['cheapest']}")


def main():
    hist, agree = p7.history(build_books)
    hs = summarize(hist)
    hp = {f"{a} vs {b}": paired(hist, a, b) for a, b in PAIRS}
    hp = {k: v for k, v in hp.items() if v}
    show("History, 96 weeks, frozen universe", hs, hp)
    ha = attribution(hs, hp)
    show_attribution(ha)
    ok7 = reproduces_pass7(hs)
    print(f"\n  reproduces Pass 7's Warden and Four chairs: {'yes' if ok7 else 'NO'}")
    risk_off = sum(1 for r in hist if r["books"]["Dial only"]["invested"] < 0.99)
    print(f"  risk-off weeks (SPY below its 40-week average): {risk_off} of {len(hist)}")
    cw = p7.council(build_books)
    cs = summarize(cw)
    cp = {f"{a} vs {b}": paired(cw, a, b) for a, b in PAIRS}
    cp = {k: v for k, v in cp.items() if v}
    show("Council weeks on the 111 (seen weeks: reported, decide nothing)", cs, cp)
    v = verdicts(hs, hp)
    print("\n  registered verdicts (history): " + "; ".join(f"{d} {'PROMISING' if ok else 'no'}" for d, ok in v.items()))
    with open(lab.RESULTS / "pass8_warden.json", "w", encoding="ascii", newline="\n") as fh:
        json.dump({"ablation": ABLATION, "pairs": PAIRS,
                   "history": {"summary": hs, "paired": hp, "attribution": ha, "risk_off_weeks": risk_off,
                               "reproduces_pass7": ok7, "weeks": hist},
                   "council": {"summary": cs, "paired": cp, "weeks": cw}, "verdicts": v},
                  fh, indent=1, default=float)
        fh.write("\n")


if __name__ == "__main__":
    main()
