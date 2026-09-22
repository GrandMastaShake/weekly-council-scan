#!/usr/bin/env python3
"""Pass 13 -- holding on, and managing the week.

Two of the owner's questions on the engine members' fives (Ophelia, Cecil
with a point-in-time P/E, Marky's channel) and all fifteen together, on the
S&P 500 as of 2024-09-09 (decides) and the 111 (reported), 96 history weeks.

A. Holding on. Each pick held 1, 2, 4 and 8 weeks: Monday's open of the
   pick week to Friday's close of week k, against random books of the same
   size from the pick week's tradeable names held the same way. The edge is
   per week of holding, clipped per name at +/-20% a week of horizon, and
   also net of a round-trip cost of 0.10% spread over the hold. The t for
   horizon k uses every k-th pick week, so the windows do not overlap.
B. Managing the week, on daily bars. Entry at Monday's open; the decision
   at the second session's close ("Tuesday"); everything held to Friday's
   close. Five rules, each against the plain hold, paired by week, and each
   also applied to the random books so a rule that helps random picks as
   much as the members' is read as mechanical, not skill:
     stop         a name below its entry at Tuesday's close is sold there;
                  cash for the rest of the week
     stop vs SPY  sold if trailing SPY since entry
     rotate       the owner's rule: the worst two (worst 40% of a bigger
                  book) are sold at Tuesday's close and the cash goes equally
                  into the best three (best 60%)
     rotate Wed   the same at the third session's close
     reverse      the mirror: the best two sold into the worst three
   Costs: 0.05% a side on the weight moved (a stop pays one side, a rotation
   two). Part B is scored raw, paired: the same names sit on both sides.

Registered in lab/README.md before any run.

    python lab/pass13_hold_manage.py
    python lab/pass13_hold_manage.py smoke
"""
from __future__ import annotations

import bisect
import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass4_marky as p4  # noqa: E402
import pass7_combos as p7  # noqa: E402
import pass9_universe as p9  # noqa: E402
import pass10_sectors as p10  # noqa: E402
import pass11_cecil_themes as p11  # noqa: E402

BOOKS = ("Ophelia", "Cecil", "Marky", "all 15")
HORIZONS = (1, 2, 4, 8)
ROUND_TRIP = 0.0010
SIDE = 0.0005
RULES = ("plain", "stop", "stop vs SPY", "rotate", "rotate Wed", "reverse")
DRAWS = 200


# ---- picks -----------------------------------------------------------------
def fives_for(names, raw, adj, cal, weeks, start):
    rows = lab.run(verbose=False, knobs=dict(lab.VARIANTS3["base"], pe_builder=p11.pe_builder),
                   weeks=weeks, start=start, earnings=cal, names=names)
    out = {}
    for r, (label, W, _) in zip(rows, weeks):
        tradeable = p10.pool(names, raw, cal, W)
        tset = set(tradeable)
        eligible = [t for t in names if t in raw]
        f = {"Ophelia": [t for t in r["proposals"]["Ophelia"] if t in tset][:p7.TOP],
             "Cecil": [t for t in r["proposals"]["Cecil"] if t in tset][:p7.TOP],
             "Marky": p7.channel_ranking(raw, eligible, W, tset)[:p7.TOP]}
        f["all 15"] = sorted({t for g in f.values() for t in g})
        out[W] = {"label": label, "fives": f, "tradeable": tradeable}
    return out


# ---- A. holding on ---------------------------------------------------------
def hold_return(s, W, k):
    """Monday's open of the pick week to Friday's close of week k; None if the data ends first."""
    fri = lab._plus(W, 7 * (k - 1) + 4)
    lo = bisect.bisect_left(s.dates, W)
    hi = bisect.bisect_right(s.dates, fri)
    if lo >= hi or s.dates[hi - 1] < lab._plus(fri, -4):
        return None
    return s.rows[hi - 1]["close"] / s.rows[lo]["open"] - 1.0


def part_a(uname, picks, adj, tag):
    out = {b: {k: [] for k in HORIZONS} for b in BOOKS}
    for i, (W, rec) in enumerate(sorted(picks.items())):
        for k in HORIZONS:
            rets = {t: hold_return(adj[t], W, k) for t in rec["tradeable"] if t in adj}
            rets = {t: r for t, r in rets.items() if r is not None}
            if len(rets) < 20:
                continue
            clip = 0.20 * k
            pool = sorted(rets)
            for b in BOOKS:
                names = [t for t in rec["fives"][b] if t in rets]
                if not names:
                    continue
                r = statistics.fmean(max(-clip, min(clip, rets[t])) for t in names)
                rng = random.Random(f"{lab.SEED}-{W}-p13a-{uname}-{tag}-{b}-{k}")
                draws = [statistics.fmean(max(-clip, min(clip, rets[t])) for t in rng.sample(pool, len(names)))
                         for _ in range(DRAWS)]
                out[b][k].append({"week": rec["label"], "i": i, "edge": (r - statistics.fmean(draws)) / k,
                                  "net": (r - statistics.fmean(draws) - ROUND_TRIP) / k, "ret": r})
    return out


def summarize_a(part):
    s = {}
    for b in BOOKS:
        s[b] = {}
        for k in HORIZONS:
            rows = part[b][k]
            if not rows:
                continue
            e_all = [x["edge"] for x in rows]
            ind = [x for x in rows if x["i"] % k == 0]           # non-overlapping windows
            e = [x["edge"] for x in ind]
            n = [x["net"] for x in ind]
            base = {x["week"]: x for x in part[b][1]}
            diff = [x["net"] - base[x["week"]]["net"] for x in ind if x["week"] in base]
            s[b][k] = {"weeks_all": len(rows), "edge_all": statistics.fmean(e_all),
                       "weeks": len(ind), "edge": statistics.fmean(e), "t": lab._tstat(e),
                       "net": statistics.fmean(n), "net_t": lab._tstat(n),
                       "vs_hold1_net": statistics.fmean(diff) if diff else None,
                       "vs_hold1_t": lab._tstat(diff) if len(diff) > 2 else None}
    return s


def show_a(title, s):
    print(f"\n  {title}")
    print(f"  {'book':<9}{'hold':>5}{'edge/wk':>9}{'t':>7}{'net/wk':>8}{'t':>7}{'n':>5}   net vs hold 1 (paired)")
    for b in BOOKS:
        for k in HORIZONS:
            x = s[b].get(k)
            if not x:
                continue
            tail = f"   {x['vs_hold1_net']*100:+.2f}%/wk (t {x['vs_hold1_t']:+.2f})" if x["vs_hold1_t"] is not None else ""
            print(f"  {b:<9}{k:>5}{x['edge']*100:+8.2f}%{x['t']:+7.2f}{x['net']*100:+7.2f}%{x['net_t']:+7.2f}{x['weeks']:>5}{tail}")


# ---- B. managing the week ---------------------------------------------------
def week_path(s, W):
    """(entry open, close at the 2nd session, close at the 3rd, Friday close) or None."""
    fri = lab._plus(W, 4)
    lo = bisect.bisect_left(s.dates, W)
    hi = bisect.bisect_right(s.dates, fri)
    if hi - lo < 3:
        return None
    rows = s.rows[lo:hi]
    return rows[0]["open"], rows[1]["close"], rows[2]["close"], rows[-1]["close"]


def managed(names, paths, spy, rule):
    """The week's return of an equal-weight book under a rule, and the weight moved."""
    w = 1.0 / len(names)
    p1 = {t: paths[t] for t in names}
    r2 = {t: p[1] / p[0] - 1.0 for t, p in p1.items()}
    r3 = {t: p[2] / p[0] - 1.0 for t, p in p1.items()}
    final = {t: p[3] / p[0] - 1.0 for t, p in p1.items()}
    if rule == "plain":
        return statistics.fmean(final.values()), 0.0
    if rule in ("stop", "stop vs SPY"):
        bar = 0.0 if rule == "stop" else spy[1] / spy[0] - 1.0
        sold = {t for t in names if r2[t] < bar}
        value = sum(w * (1 + r2[t]) if t in sold else w * (1 + final[t]) for t in names)
        return value - 1.0, sum(w * (1 + r2[t]) for t in sold)
    at, ret_at = (2, r3) if rule == "rotate Wed" else (1, r2)
    order = sorted(names, key=lambda t: ret_at[t])
    n_sell = max(1, round(0.4 * len(names)))
    if rule == "reverse":
        sold, into = order[-n_sell:], order[:len(names) - n_sell]
    else:
        sold, into = order[:n_sell], order[n_sell:]
    cash = sum(w * (1 + ret_at[t]) for t in sold)
    value = 0.0
    for t in names:
        if t in sold:
            continue
        cont = (p1[t][3] / p1[t][at]) - 1.0
        base = w * (1 + ret_at[t])
        add = cash / len(into) if t in into else 0.0
        value += (base + add) * (1 + cont)
    return value - 1.0, 2 * cash


def part_b(uname, picks, adj, tag):
    out = []
    for W, rec in sorted(picks.items()):
        spy = week_path(adj["SPY"], W)
        if not spy:
            continue
        paths = {t: week_path(adj[t], W) for t in rec["tradeable"] if t in adj}
        paths = {t: p for t, p in paths.items() if p}
        pool = sorted(paths)
        row = {"week": rec["label"], "books": {}}
        for b in BOOKS:
            names = [t for t in rec["fives"][b] if t in paths]
            if len(names) < 3:
                continue
            rng = random.Random(f"{lab.SEED}-{W}-p13b-{uname}-{tag}-{b}")
            samples = [rng.sample(pool, len(names)) for _ in range(DRAWS)]
            res = {}
            for rule in RULES:
                r, moved = managed(names, paths, spy, rule)
                cost = moved * SIDE          # a stop moves weight once, a rotation twice (managed() counts both sides)
                rand = [managed(smp, paths, spy, rule)[0] for smp in samples]
                res[rule] = {"ret": r, "net": r - cost, "cost": cost, "random": statistics.fmean(rand)}
            row["books"][b] = res
        out.append(row)
    return out


def summarize_b(rows):
    s = {}
    for b in BOOKS:
        s[b] = {}
        rs = [r["books"][b] for r in rows if b in r["books"]]
        if not rs:
            continue
        for rule in RULES:
            gross = [x[rule]["ret"] - x["plain"]["ret"] for x in rs]
            net = [x[rule]["net"] - x["plain"]["net"] for x in rs]
            mech = [x[rule]["random"] - x["plain"]["random"] for x in rs]
            half = len(net) // 2
            s[b][rule] = {"weeks": len(rs), "ret": statistics.fmean(x[rule]["ret"] for x in rs),
                          "vs_plain_gross": statistics.fmean(gross), "vs_plain_net": statistics.fmean(net),
                          "net_t": lab._tstat(net), "weeks_better": sum(1 for x in net if x > 0),
                          "halves": [statistics.fmean(net[:half]), statistics.fmean(net[half:])] if half else None,
                          "mechanical": statistics.fmean(mech), "skill": statistics.fmean(net) - statistics.fmean(mech)}
    return s


def show_b(title, s):
    print(f"\n  {title}")
    print(f"  {'book':<9}{'rule':<13}{'ret/wk':>8}{'vs plain':>10}{'net':>8}{'t':>7}{'better':>8}{'on random':>11}{'skill':>8}")
    for b in BOOKS:
        for rule in RULES:
            x = s[b].get(rule)
            if not x:
                continue
            if rule == "plain":
                print(f"  {b:<9}{rule:<13}{x['ret']*100:+7.2f}%")
                continue
            print(f"  {b:<9}{rule:<13}{x['ret']*100:+7.2f}%{x['vs_plain_gross']*100:+9.2f}%{x['vs_plain_net']*100:+7.2f}%{x['net_t']:+7.2f}"
                  f"{x['weeks_better']:>5}/{x['weeks']:<3}{x['mechanical']*100:+10.2f}%{x['skill']*100:+7.2f}%")


# ---- main --------------------------------------------------------------------
def main(smoke=False):
    U = p9.universes()
    universes = {p11.CLEAN: p9.sp500_asof(), p9.REFERENCE: U[p9.REFERENCE]}
    hweeks = lab.history_weeks(lab.HISTORY_FIRST_MONDAY, lab.HISTORY_LAST_MONDAY)
    cweeks = lab.council_weeks(p9._last_friday())
    if smoke:
        universes, hweeks, cweeks = {p9.REFERENCE: U[p9.REFERENCE]}, hweeks[:4], cweeks[:2]
    end = lab._plus(cweeks[-1][1], 5)
    result = {"horizons": HORIZONS, "round_trip": ROUND_TRIP, "side": SIDE, "rules": RULES, "universes": {}}
    for uname, names in universes.items():
        cal = lab.earnings_calendar(names)
        tickers = sorted(set(names)) + lab.EXTRA
        raw = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, False, end, p4.HIST_START)).items()}
        adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, True, end, p4.HIST_START)).items()}
        print(f"  {uname}: {len(names)} names", flush=True)
        hp = fives_for(names, raw, adj, cal, hweeks, lab.HISTORY_DATA_START)
        cp = fives_for(names, raw, adj, cal, cweeks, lab.DATA_START)
        a = part_a(uname, hp, adj, "hist")
        sa = summarize_a(a)
        show_a(f"A. holding on, {uname}, history (edge per week of holding; net of a 0.10% round trip)", sa)
        bh = part_b(uname, hp, adj, "hist")
        sbh = summarize_b(bh)
        show_b(f"B. managing the week, {uname}, history, {len(bh)} weeks", sbh)
        bc = part_b(uname, cp, adj, "council")
        sbc = summarize_b(bc)
        show_b(f"B. managing the week, {uname}, Council weeks, {len(bc)} (seen; decide nothing)", sbc)
        result["universes"][uname] = {"hold": {"summary": sa, "rows": a},
                                      "manage": {"history": {"summary": sbh, "weeks": bh},
                                                 "council": {"summary": sbc, "weeks": bc}}}
    if p11.CLEAN in result["universes"]:
        u = result["universes"][p11.CLEAN]
        v = {}
        for b in BOOKS:
            for k in HORIZONS[1:]:
                x = u["hold"]["summary"][b].get(k)
                v[f"hold {k} helps {b}"] = bool(x and x["vs_hold1_t"] is not None and x["vs_hold1_t"] >= 2 and x["vs_hold1_net"] > 0)
            for rule in RULES[1:]:
                x = u["manage"]["history"]["summary"][b].get(rule)
                v[f"{rule} helps {b}"] = bool(x and x["net_t"] >= 2 and x["vs_plain_net"] > 0 and x["halves"] and all(h > 0 for h in x["halves"]))
        result["verdicts"] = v
        hits = [k for k, ok in v.items() if ok]
        print("\n  registered verdicts (history, the clean list): " + (", ".join(hits) if hits else "none"))
    out = lab.CACHE / "pass13.smoke.json" if smoke else lab.RESULTS / "pass13_hold_manage.json"
    with open(out, "w", encoding="ascii", newline="\n") as fh:
        json.dump(result, fh, indent=1, default=float)
        fh.write("\n")


if __name__ == "__main__":
    main(smoke=sys.argv[1:] == ["smoke"])
