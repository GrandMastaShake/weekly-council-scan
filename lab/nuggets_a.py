#!/usr/bin/env python3
"""Nuggets A: separate member books, Shapley credit, persistence, and the strikes.

Registered in lab/README.md before any number was computed. Data on hand only:
the Council Room v2 archive (results/room_v2), the v2 and v2.1 debate results,
Pass 5's Marky history, and one fresh baseline engine replay over the 96
pre-Council weeks for the engine-era members.

    python lab/nuggets_a.py
"""
from __future__ import annotations

import itertools
import json
import math
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import council_room_v2 as v2  # noqa: E402
import engine_lab as lab  # noqa: E402
import hold_check as hc  # noqa: E402

MEMBERS = v2.MEMBERS
BASE = lab.RESULTS / "room_v2"


def _corr(xs, ys):
    n = len(xs)
    if n < 3:
        return 0.0, 0.0
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    r = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy) if sx and sy else 0.0
    t = r * math.sqrt((n - 2) / (1 - r * r)) if abs(r) < 1 else 0.0
    return r, t


def _thirds(fives, members):
    """The separate-books book for a coalition: each member an equal slice,
    split equally over its own picks; shared names collect both slices."""
    w = {}
    for m in members:
        for t in fives[m]:
            w[t] = w.get(t, 0.0) + 1.0 / len(members) / len(fives[m])
    return sorted(w.items())


# ---------------------------------------------------------------------------
# 1, 2 and 4: the Council weeks
# ---------------------------------------------------------------------------
def council():
    weeks, names, raw, adj = v2._data()
    cal = lab.earnings_calendar(names)
    from scan_pipeline.fetch_market_data import _aggregate_weekly, _business_days_between
    marky = v2._marky_top()
    books_out, shap_out, strikes = [], [], []
    for label, W, council_book in weeks:
        d = BASE / label
        if not (d / "ophelia/pass3/result.json").exists():
            continue
        fives = v2._fives(d, marky)
        F = _aggregate_weekly(raw["SPY"].before(W, 92))[-1].date
        black = set()
        for t in names:
            nxt = lab._next_report(cal.get(t), F) if t in raw else None
            etd = _business_days_between(F, nxt) if nxt else None
            if etd is not None and 0 <= etd <= 5:
                black.add(t)
        load = lambda p: json.loads(p.read_text(encoding="utf-8"))  # noqa: E731
        fixed = {"separate books": _thirds(fives, MEMBERS),
                 "all 15": [(t, 1.0 / len(u)) for u in [sorted(set().union(*map(set, fives.values())))] for t in u],
                 "v2 book": [(b["ticker"], float(b["weight"])) for b in load(d / "debate/final.json")["book"]],
                 "v2.1 book": [(b["ticker"], float(b["weight"])) for b in load(d / "debate21/final.json")["book"]]}
        if council_book:
            fixed["real Council"] = [(t, float(w)) for t, w in council_book]
        row, srow = {"week": label}, {"week": label}
        for h in hc.HORIZONS:
            rets = {t: hc.window(adj[t], W, h) for t in names if t in adj and t not in black}
            rets = {t: r for t, r in rets.items() if r is not None}
            if not rets:
                continue
            pool = sorted(rets)

            def edge(book, tag):
                book = [(t, w) for t, w in book if t in rets]
                if not book:
                    return None
                r = sum(w * rets[t] for t, w in book)
                ws = sorted((w for _, w in book), reverse=True)
                rng = random.Random(f"{lab.SEED}-{W}-nuggets-{tag}-{h}")
                draws = [sum(w * rets[t] for t, w in zip(rng.sample(pool, len(ws)), ws))
                         for _ in range(lab.RANDOM_DRAWS)]
                return r - statistics.fmean(draws)
            row[h] = {name: edge(book, name) for name, book in fixed.items()}
            if h in ("week1", "week2"):
                v = {(): 0.0}
                for k in (1, 2, 3):
                    for S in itertools.combinations(MEMBERS, k):
                        v[S] = edge(_thirds(fives, S), "+".join(S)) or 0.0
                phi = {}
                for m in MEMBERS:
                    others = [x for x in MEMBERS if x != m]
                    total = 0.0
                    for k in range(0, 3):
                        for S in itertools.combinations(others, k):
                            with_m = tuple(x for x in MEMBERS if x in S or x == m)
                            weight = math.factorial(k) * math.factorial(2 - k) / math.factorial(3)
                            total += weight * (v[with_m] - v[S])
                    phi[m] = total
                srow[h] = {"phi": phi, "full": v[MEMBERS]}
            if h == "week1":
                for tag in ("", "21"):
                    draft = load(d / f"debate{tag}/draft.json")
                    names_in = [b["ticker"].upper() for b in draft["book"]]
                    for m in MEMBERS:
                        votes = load(d / f"approve{tag}/{m.lower()}/result.json")["votes"]
                        obj = [x["ticker"].upper() for x in votes if x["vote"] == "object"]
                        app = [t for t in names_in if t not in obj]
                        obj, app = [t for t in obj if t in rets], [t for t in app if t in rets]
                        if obj and app:
                            strikes.append({"week": label, "round": "v2.1" if tag else "v2", "member": m,
                                            "objected": obj, "gap": statistics.fmean(rets[t] for t in obj)
                                            - statistics.fmean(rets[t] for t in app)})
        books_out.append(row)
        shap_out.append(srow)
    return books_out, shap_out, strikes


# ---------------------------------------------------------------------------
# 3: persistence on the 96 history weeks
# ---------------------------------------------------------------------------
def persistence():
    frozen = lab.frozen_universe()
    cal = lab.earnings_calendar(frozen)
    hweeks = lab.history_weeks(lab.HISTORY_FIRST_MONDAY, lab.HISTORY_LAST_MONDAY)
    cap = {}
    rows = lab.run(verbose=False, knobs=lab.VARIANTS3["base"], capture=cap, weeks=hweeks,
                   start=lab.HISTORY_DATA_START, earnings=cal, names=frozen)
    series = {m: {"edge": [], "hit": []} for m in MEMBERS}
    for r in rows:
        rets = cap[r["monday"]]["ret"]
        ew = statistics.fmean(rets.values())
        for m in MEMBERS:
            picks = [t for t in r["proposals"][m][:5] if t in rets]
            if picks:
                series[m]["edge"].append(statistics.fmean(rets[t] for t in picks) - ew)
                series[m]["hit"].append(sum(1 for t in picks if rets[t] > 0) / len(picks))
            else:
                series[m]["edge"].append(None)
                series[m]["hit"].append(None)
    p5 = json.loads((lab.RESULTS / "pass5_marky.json").read_text(encoding="utf-8"))
    series["Marky (channel)"] = {"edge": [w["channel"]["vs_random"] for w in p5["weeks"]["history"]], "hit": None}
    out = {}
    for name, s in series.items():
        res = {}
        for kind in ("edge", "hit"):
            xs = s[kind]
            if xs is None:
                continue
            pairs = [(a, b) for a, b in zip(xs, xs[1:]) if a is not None and b is not None]
            r1, t1 = _corr([a for a, _ in pairs], [b for _, b in pairs])
            trail = [(statistics.fmean(xs[i - 8:i]), xs[i]) for i in range(8, len(xs))
                     if None not in xs[i - 8:i + 1]]
            r8, t8 = _corr([a for a, _ in trail], [b for _, b in trail])
            res[kind] = {"weeks": len([x for x in xs if x is not None]), "lag1_r": r1, "lag1_t": t1,
                         "trailing8_r": r8, "trailing8_t": t8,
                         "mean": statistics.fmean(x for x in xs if x is not None)}
        out[name] = res
    return out


def main():
    books, shap, strikes = council()
    print("1. Separate member books -- mean edge over random (weeks ahead)")
    names = ["separate books", "all 15", "v2 book", "v2.1 book", "real Council"]
    summary = {"books": {}, "shapley": {}, "strikes": {}, "persistence": None}
    for h in hc.HORIZONS:
        line = f"   {h:<6}"
        summary["books"][h] = {}
        for n in names:
            xs = [r[h][n] for r in books if h in r and r[h].get(n) is not None]
            if xs:
                per = 4.0 if h == "month" else 1.0
                summary["books"][h][n] = {"weeks": len(xs), "mean": statistics.fmean(xs), "per_week": statistics.fmean(xs) / per,
                                          "ahead": sum(1 for x in xs if x > 0), "t": lab._tstat(xs)}
                line += f"  {n} {statistics.fmean(xs)/per*100:+.2f}%/wk ({sum(1 for x in xs if x > 0)}/{len(xs)})"
        print(line)
    print("2. Shapley credit -- mean over weeks, per member (share of the full book's edge)")
    for h in ("week1", "week2"):
        rows = [s[h] for s in shap if h in s]
        full = statistics.fmean(s["full"] for s in rows)
        phi = {m: statistics.fmean(s["phi"][m] for s in rows) for m in MEMBERS}
        summary["shapley"][h] = {"weeks": len(rows), "full": full, "phi": phi}
        print(f"   {h}: full book {full*100:+.2f}%/wk = " + " + ".join(f"{m} {phi[m]*100:+.2f}%" for m in MEMBERS))
    print("4. Strikes -- objected minus approved, week 1, per member vote")
    for key, sel in [("all", strikes)] + [(m, [s for s in strikes if s["member"] == m]) for m in MEMBERS] + \
            [(rd, [s for s in strikes if s["round"] == rd]) for rd in ("v2", "v2.1")]:
        g = [s["gap"] for s in sel]
        if len(g) >= 2:
            summary["strikes"][key] = {"n": len(g), "mean_gap": statistics.fmean(g), "t": lab._tstat(g),
                                       "objected_ahead": sum(1 for x in g if x > 0)}
            print(f"   {key:<8} n {len(g):>2}  gap {statistics.fmean(g)*100:+.2f}%  (t {lab._tstat(g):+.2f}),"
                  f" objected names ahead {sum(1 for x in g if x > 0)}/{len(g)}")
    print("3. Persistence on 96 history weeks (edge over the equal-weighted universe; hit rate)")
    per = persistence()
    summary["persistence"] = per
    for name, res in per.items():
        for kind, s in res.items():
            print(f"   {name:<16} {kind:<4} lag-1 r {s['lag1_r']:+.2f} (t {s['lag1_t']:+.2f})   "
                  f"trailing-8 -> next r {s['trailing8_r']:+.2f} (t {s['trailing8_t']:+.2f})   mean {s['mean']*100:+.2f}"
                  + ("%" if kind == "edge" else " pts"))
    with open(lab.RESULTS / "nuggets_a.json", "w", encoding="ascii", newline="\n") as fh:
        json.dump({"summary": summary, "books": books, "shapley": shap, "strikes": strikes}, fh, indent=1, default=float)
        fh.write("\n")


if __name__ == "__main__":
    main()
