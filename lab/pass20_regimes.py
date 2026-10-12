#!/usr/bin/env python3
"""Pass 20 -- regime and event splits of the weekly edges (registered in lab/README.md, d1ba76f).

Takes each week's three fives from Pass 19's cached rows (Ophelia's engine five, Cecil's as-is five with the point-in-time P/E,
Marky's channel five), rescores the members and the team under one tag, and splits the weekly clipped edges by what the engines do
not see: VIX, breadth, a four-flag count, CPI/FOMC weeks, the dollar-and-10-year gate. Then three cash dials against exposure-matched
books (rule 7) and the gate on index history. Inputs are the last close before each week's Monday.

    python lab/pass20_regimes.py
    python lab/pass20_regimes.py smoke
"""
from __future__ import annotations

import json
import pickle
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
import pass19_cecil_trap as p19  # noqa: E402

END = "2026-09-26"                       # Pass 19's download end, so the cached bars are reused
LAST_CLOSED_FRIDAY = "2026-09-25"        # and its Council weeks
LONG_START, LONG_END = "2003-01-01", "2026-08-01"
BOOKS = ("Ophelia", "Cecil", "Marky", "Three chairs")
SPLITS = {
    "S1 complacency": "VIX under 16 and breadth under 40%",
    "S2 fear": "VIX over 22",
    "S3 weak breadth": "breadth under 40%",
    "S4 flags": "3+ of: dollar under 100, 10y under 4.3%, VIX over 22, WTI over 100",
    "S5 event week": "a CPI release or an FOMC decision in the week",
    "S6 commodity gate": "dollar over 101 and 10y over 4.5%",
}
DIALS = {"D1": "S1 complacency", "D2": "S4 flags", "D3": "S5 event week"}
MIN_FLAGGED = 8
FOMC = ["2024-09-18", "2024-11-07", "2024-12-18", "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30",
        "2025-09-17", "2025-10-29", "2025-12-10", "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17"]
CPI = ["2024-09-11", "2024-10-10", "2024-11-13", "2024-12-11", "2025-01-15", "2025-02-12", "2025-03-12", "2025-04-10", "2025-05-13",
       "2025-06-11", "2025-07-15", "2025-08-12", "2025-09-11", "2025-10-24", "2025-12-18", "2026-01-13", "2026-02-13", "2026-03-11",
       "2026-04-10", "2026-05-12", "2026-06-10"]
EVENTS = sorted(set(FOMC) | set(CPI))


# ------------------------------------------------------------------------------------------------ statistics
def welch(a, b):
    if len(a) < 2 or len(b) < 2:
        return 0.0, 0.0
    va, vb = statistics.variance(a), statistics.variance(b)
    se = (va / len(a) + vb / len(b)) ** 0.5
    d = statistics.fmean(a) - statistics.fmean(b)
    return d, (d / se if se > 0 else 0.0)


def split_verdict(edges, flags):
    n = len(edges)
    half = n // 2
    F = [e for e, f in zip(edges, flags) if f]
    N = [e for e, f in zip(edges, flags) if not f]
    out = {"flagged": len(F), "unflagged": len(N)}
    if len(F) < MIN_FLAGGED:
        return {**out, "testable": False, "matters": False}
    diff, t = welch(F, N)
    halves = []
    for sl in (slice(0, half), slice(half, n)):
        f = [e for e, fl in zip(edges[sl], flags[sl]) if fl]
        u = [e for e, fl in zip(edges[sl], flags[sl]) if not fl]
        halves.append(statistics.fmean(f) - statistics.fmean(u) if len(f) >= 3 and len(u) >= 3 else None)
    med = statistics.median(F) - statistics.median(N)
    matters = abs(t) >= 2 and all(h is not None and h * diff > 0 for h in halves) and med * diff > 0
    return {**out, "testable": True, "flagged_mean": statistics.fmean(F), "unflagged_mean": statistics.fmean(N), "diff": diff, "t": t,
            "halves": halves, "median_diff": med, "matters": bool(matters)}


def tstat(xs):
    return lab._tstat(xs)


def hac_slope(x, y, lags=3):
    """OLS of y on a 0/1 x with a Newey-West standard error; returns (slope, t)."""
    n = len(x)
    if n < 5:
        return 0.0, 0.0
    mx, my = statistics.fmean(x), statistics.fmean(y)
    xc = [a - mx for a in x]
    sxx = sum(a * a for a in xc)
    if sxx == 0:
        return 0.0, 0.0
    b = sum(a * (yy - my) for a, yy in zip(xc, y)) / sxx
    e = [yy - my - b * a for a, yy in zip(xc, y)]
    u = [a * ee for a, ee in zip(xc, e)]
    s = sum(v * v for v in u)
    for j in range(1, min(lags, n - 1) + 1):
        s += 2 * (1 - j / (lags + 1)) * sum(u[i] * u[i - j] for i in range(j, n))
    var = s / (sxx * sxx)
    return b, (b / var ** 0.5 if var > 0 else 0.0)


# ------------------------------------------------------------------------------------------------ inputs
def last_close(series, W):
    return series.last_close_before(W)


def breadth(names, raw, W):
    up = tot = 0
    for t in names:
        s = raw.get(t)
        if s is None:
            continue
        closes = [r["close"] for r in s.before(W, 120)]
        if len(closes) < 50:
            continue
        tot += 1
        up += closes[-1] > statistics.fmean(closes[-50:])
    return up / tot if tot else None


def event_week(W):
    end = lab._plus(W, 4)
    return any(W <= d <= end for d in EVENTS)


def regime_row(names, raw, extra, W):
    vix = last_close(raw["^VIX"], W)
    tnx = last_close(raw["^TNX"], W)
    dxy = last_close(extra["DX-Y.NYB"], W)
    wti = last_close(extra["CL=F"], W)
    if tnx is not None and tnx > 25:        # a quote in tenths of a percent would read 40+; yields here are percent
        raise SystemExit(f"^TNX looks scaled by 10 ({tnx}) on {W}")
    b = breadth(names, raw, W)
    flags4 = sum([dxy is not None and dxy < 100, tnx is not None and tnx < 4.3, vix is not None and vix > 22, wti is not None and wti > 100])
    return {"week": W, "vix": vix, "tnx": tnx, "dxy": dxy, "wti": wti, "breadth": b, "flags4": flags4,
            "S1 complacency": bool(vix is not None and b is not None and vix < 16 and b < 0.40),
            "S2 fear": bool(vix is not None and vix > 22),
            "S3 weak breadth": bool(b is not None and b < 0.40),
            "S4 flags": flags4 >= 3,
            "S5 event week": event_week(W),
            "S6 commodity gate": bool(dxy is not None and tnx is not None and dxy > 101 and tnx > 4.5)}


# ------------------------------------------------------------------------------------------------ scoring
def load_rows(uname, kind, n):
    name = uname.replace(" ", "_").replace("&", "and")
    path = lab.CACHE / f"pass19_rows_{name}_{kind}_{n}.pkl"
    with open(path, "rb") as fh:
        return pickle.load(fh)


def score_rows(uname, names, rows, weeks, raw, adj, cal, tag):
    """Rescore Pass 19's fives as four books under one tag; check the team book against Pass 19's own."""
    monday = {label: W for label, W, _ in weeks}
    out = []
    for r in rows:
        W = monday[r["week"]]
        tradeable = p10.pool(names, raw, cal, W)
        O, C, M = r["ophelia"], r["five"], r["marky"]
        books = {"Ophelia": p7.equal(O), "Cecil": p7.equal(C), "Marky": p7.equal(M), "Three chairs": p7.slices([O, C, M])}
        scored = p7.score_week(books, adj, W, tradeable, f"p20-{uname}-{tag}")
        old = r["books"]["three chairs, as is"]["clipped"]["ret"]
        assert abs(scored["Three chairs"]["clipped"]["ret"] - old) < 1e-12, f"{uname} {W}: team book does not match Pass 19"
        out.append({"week": r["week"], "W": W, "spy": r["spy"], "fives": {"Ophelia": O, "Cecil": C, "Marky": M},
                    "edge": {b: scored[b]["clipped"]["edge"] for b in BOOKS if b in scored},
                    "ret": {b: scored[b]["clipped"]["ret"] for b in BOOKS if b in scored}})
    return out


def dial_stats(returns, flags):
    inv = [0.0 if f else 1.0 for f in flags]
    c = statistics.fmean(inv)
    dial = [i * r for i, r in zip(inv, returns)]
    match = [c * r for r in returns]
    diff = [a - b for a, b in zip(dial, match)]
    half = len(diff) // 2
    sharpe = lambda xs: (statistics.fmean(xs) / statistics.pstdev(xs) * 52 ** 0.5) if statistics.pstdev(xs) > 0 else 0.0  # noqa: E731
    t = tstat(diff)
    halves = [statistics.fmean(diff[:half]), statistics.fmean(diff[half:])]
    return {"exposure": c, "weeks_in_cash": int(sum(1 for f in flags if f)), "mean_diff": statistics.fmean(diff), "t": t, "halves": halves,
            "helps": bool(t >= 2 and all(h > 0 for h in halves)),
            "dial": {"mean": statistics.fmean(dial), "sd": statistics.pstdev(dial), "sharpe": sharpe(dial), "max_dd": lab._curve(dial)[1]},
            "matched": {"mean": statistics.fmean(match), "sd": statistics.pstdev(match), "sharpe": sharpe(match), "max_dd": lab._curve(match)[1]}}


def index_leg(smoke=False):
    """Part C: the commodity gate on 2003-2026-07 daily data, Friday to Friday, next four weeks."""
    tick = ["SPY", "XLB", "XLE", "GLD", "DX-Y.NYB", "^TNX"]
    ser = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tick, True, LONG_END, LONG_START)).items()}
    spy = ser["SPY"]
    dates = spy.dates
    by_week = {}
    from datetime import date as _d
    for i, d in enumerate(dates):
        y, m, dd = (int(x) for x in d.split("-"))
        by_week[_d(y, m, dd).isocalendar()[:2]] = i          # the last trading day of each ISO week
    idx = sorted(by_week.values())
    cut = dates.index(max(d for d in dates if d <= "2026-07-03"))
    rows = []

    def close_on(s, day):
        i = lab.bisect.bisect_right(s.dates, day) - 1
        return s.rows[i]["close"] if i >= 0 else None

    for i in idx:
        if i + 20 > cut or dates[i] < LONG_START:
            continue
        F, E = dates[i], dates[i + 20]
        sr = spy.rows[i + 20]["close"] / spy.rows[i]["close"] - 1
        legs = []
        for t in ("XLB", "XLE", "GLD"):
            s = ser.get(t)
            a, b = (close_on(s, F), close_on(s, E)) if s else (None, None)
            if a and b and s.dates[0] <= F:
                legs.append(b / a - 1)
        dxy, tnx = close_on(ser["DX-Y.NYB"], F), close_on(ser["^TNX"], F)
        if not legs or dxy is None or tnx is None:
            continue
        rows.append({"F": F, "y": (statistics.fmean(legs) - sr) / 4.0, "gate": 1.0 if (dxy > 101 and tnx > 4.5) else 0.0})
    if smoke:
        rows = rows[::6]
    x, y = [r["gate"] for r in rows], [r["y"] for r in rows]
    b, t = hac_slope(x, y)
    halves = {}
    for label, pick in (("2003-2014", lambda r: r["F"] < "2015-01-01"), ("2015-2026", lambda r: r["F"] >= "2015-01-01")):
        sub = [r for r in rows if pick(r)]
        halves[label] = hac_slope([r["gate"] for r in sub], [r["y"] for r in sub]) + (sum(r["gate"] for r in sub),)
    share = statistics.fmean(x)
    on = [r["y"] for r in rows if r["gate"]]
    off = [r["y"] for r in rows if not r["gate"]]
    matters = bool(on and b <= -0.003 and abs(t) >= 2 and all(h[0] < 0 for h in halves.values()) and share <= 0.60)
    return {"weeks": len(rows), "gate_share": share, "gate_weeks": len(on), "gate_on_mean": statistics.fmean(on) if on else None,
            "gate_off_mean": statistics.fmean(off), "slope": b, "t": t, "halves": {k: {"slope": v[0], "t": v[1], "gate_weeks": v[2]} for k, v in halves.items()},
            "matters": matters}


# ------------------------------------------------------------------------------------------------ report
def show_splits(title, regs, scored):
    print(f"\n  {title}")
    print(f"  {'split':<20}{'flagged':>8}{'team flagged':>14}{'other':>8}{'diff':>8}{'t':>7}  halves            median  matters")
    result = {}
    for sp in SPLITS:
        flags = [r[sp] for r in regs]
        row = {}
        for b in BOOKS:
            row[b] = split_verdict([w["edge"][b] for w in scored], flags)
        result[sp] = row
        v = row["Three chairs"]
        if v["testable"]:
            h = " / ".join("--" if x is None else f"{x*100:+.2f}" for x in v["halves"])
            print(f"  {sp:<20}{v['flagged']:>8}{v['flagged_mean']*100:>+13.2f}%{v['unflagged_mean']*100:>+7.2f}%{v['diff']*100:>+7.2f}%{v['t']:>+7.2f}  {h:<18}{v['median_diff']*100:>+6.2f}  {'YES' if v['matters'] else 'no'}")
        else:
            print(f"  {sp:<20}{v['flagged']:>8}   untestable: fewer than {MIN_FLAGGED} flagged weeks")
    print("  members (flagged minus other weeks, mean edge; reported, decide nothing):")
    for sp in SPLITS:
        cells = []
        for b in ("Ophelia", "Cecil", "Marky"):
            v = result[sp][b]
            cells.append(f"{b} {'--' if not v['testable'] else format(v['diff']*100, '+.2f') + ' (t ' + format(v['t'], '+.1f') + ')'}")
        print(f"    {sp:<20}" + "   ".join(cells))
    return result


def main(smoke=False):
    U = p9.universes()
    universes = {p11.CLEAN: p9.sp500_asof(), p9.REFERENCE: U[p9.REFERENCE]}
    hweeks = lab.history_weeks(lab.HISTORY_FIRST_MONDAY, lab.HISTORY_LAST_MONDAY)
    cweeks = lab.council_weeks(LAST_CLOSED_FRIDAY)
    if smoke:
        universes = {p9.REFERENCE: U[p9.REFERENCE]}
    extra = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(["DX-Y.NYB", "CL=F"], False, END, p4.HIST_START)).items()}
    result = {"registered": "d1ba76f", "fomc": FOMC, "cpi": CPI, "universes": {}}
    for uname, names in universes.items():
        cal = lab.earnings_calendar(names)
        tickers = sorted(set(names) | set(p19.ETFS)) + [x for x in lab.EXTRA if x not in names]
        raw = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, False, END, p4.HIST_START)).items()}
        adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, True, END, p4.HIST_START)).items()}
        out = {}
        for kind, weeks in (("hist", hweeks), ("council", cweeks)):
            rows = load_rows(uname, kind, len(weeks))
            if smoke:
                rows = rows[:6]
            scored = score_rows(uname, names, rows, weeks, raw, adj, cal, kind)
            regs = [regime_row(names, raw, extra, w["W"]) for w in scored]
            title = f"{uname}: {'history, ' + str(len(scored)) + ' weeks' if kind == 'hist' else 'Council weeks (seen; decide nothing)'}"
            splits = show_splits(title, regs, scored)
            dials = {}
            if kind == "hist":
                print(f"\n  dials on the team book, {uname} (rule 7: against the same book at the dial's average exposure)")
                for d, sp in DIALS.items():
                    flags = [r[sp] for r in regs]
                    if sum(flags) < MIN_FLAGGED:
                        dials[d] = {"testable": False, "flagged": int(sum(flags))}
                        print(f"  {d} on {sp}: untestable ({int(sum(flags))} flagged weeks)")
                        continue
                    st = dial_stats([w["ret"]["Three chairs"] for w in scored], flags)
                    dials[d] = st
                    print(f"  {d} on {sp:<18} in cash {st['weeks_in_cash']:>2} weeks (exposure {st['exposure']:.0%}): timing value {st['mean_diff']*100:+.3f}%/wk, "
                          f"t {st['t']:+.2f}, halves {st['halves'][0]*100:+.3f}/{st['halves'][1]*100:+.3f}; Sharpe {st['dial']['sharpe']:.2f} vs {st['matched']['sharpe']:.2f}; "
                          f"max DD {st['dial']['max_dd']*100:.1f}% vs {st['matched']['max_dd']*100:.1f}%  -> {'HELPS' if st['helps'] else 'no'}")
            out[kind] = {"regimes": regs, "weeks": scored, "splits": splits, "dials": dials}
        result["universes"][uname] = out
    leg = index_leg(smoke)
    result["commodity_gate"] = leg
    print(f"\n  Part C, the commodity gate on index history: {leg['weeks']} weeks, gate on {leg['gate_weeks']} ({leg['gate_share']:.0%}); "
          f"basket minus SPY per week over the next four: gate on {leg['gate_on_mean']*100:+.3f}% vs off {leg['gate_off_mean']*100:+.3f}%; "
          f"slope {leg['slope']*100:+.3f}%/wk (t {leg['t']:+.2f}); halves " +
          ", ".join(f"{k} {v['slope']*100:+.3f} (t {v['t']:+.2f}, {int(v['gate_weeks'])} gate weeks)" for k, v in leg["halves"].items()) +
          f"  -> {'MATTERS' if leg['matters'] else 'no'}")
    clean = result["universes"].get(p11.CLEAN)
    if clean:
        v = {sp: clean["hist"]["splits"][sp]["Three chairs"].get("matters", False) for sp in SPLITS}
        v.update({d: bool(clean["hist"]["dials"][d].get("helps")) for d in DIALS})
        v["commodity gate"] = leg["matters"]
        result["verdicts"] = v
        print("\n  registered verdicts (history, the clean list): " + "; ".join(f"{k} {'YES' if ok else 'no'}" for k, ok in v.items()))
    out = lab.CACHE / "pass20.smoke.json" if smoke else lab.RESULTS / "pass20_regimes.json"
    with open(out, "w", encoding="ascii", newline="\n") as fh:
        json.dump(result, fh, indent=1, default=float)
        fh.write("\n")
    print(f"  wrote {out}")


if __name__ == "__main__":
    main(smoke=sys.argv[1:] == ["smoke"])
