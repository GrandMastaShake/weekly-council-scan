#!/usr/bin/env python3
"""Pass 37 -- the pinned-price screen: does it do harm anywhere else?

The screen (scan_pipeline/utils/data_utils.py, pinned_price) passes over a
name whose weekly history holds at least 8 bars and whose weekly returns have
an annualized volatility under 5%. The threshold was fitted to two names
(AES and TECH, November 2026), so this pass does not ask whether it catches
them. Measurement A counts its flags on the frozen S&P 500 list on every
Monday since 2007; measurement B replays production over the Council weeks
with the screen on and off.

Registered in lab/README.md (Pass 37) before any run.

    python lab/pass37_pinned.py          # both measurements
    python lab/pass37_pinned.py smoke    # plumbing: 2024 on, 60 names, last four Council weeks
"""
from __future__ import annotations

import json
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass32_stop_random as p32  # noqa: E402

from scan_pipeline.utils.data_utils import PINNED_MIN_WEEKS, PINNED_VOL_MAX  # noqa: E402

FIRST_MONDAY = "2007-01-08"
OUT = lab.RESULTS / "pass37_pinned.json"


def measure_a(smoke=False):
    tickers = sorted(p32.members())
    df = lab.download(tickers + ["SPY"], True, p32.DATA_END, start=p32.DATA_START)
    names = [t for t in tickers if t in set(df.columns.get_level_values(1))]
    if smoke:
        names = names[:60]
    days = [x.date() for x in df.index]
    O = df["Open"][names].to_numpy(dtype=float)
    C = df["Close"][names].to_numpy(dtype=float)
    spy = df["Close"]["SPY"].to_numpy(dtype=float)
    keep = [i for i, v in enumerate(spy) if v == v]
    days, O, C = [days[i] for i in keep], O[keep], C[keep]
    iso = [d.isocalendar()[:2] for d in days]
    ords = np.array([d.toordinal() for d in days])

    W = date.fromisoformat("2024-01-08" if smoke else FIRST_MONDAY)
    last = date.fromisoformat(p32.LAST_MONDAY)
    flagged, all_abs, flag_abs, n_all, mondays = [], [], [], 0, 0
    while W <= last:
        lo = int(np.searchsorted(ords, (W - timedelta(days=lab.LOOKBACK_DAYS)).toordinal()))
        hi = int(np.searchsorted(ords, W.toordinal()))
        nxt = int(np.searchsorted(ords, (W + timedelta(days=5)).toordinal()))
        if hi - lo < 40 or nxt <= hi:
            W += timedelta(days=7)
            continue
        groups, start = [], lo
        for i in range(lo + 1, hi + 1):
            if i == hi or iso[i] != iso[start]:
                groups.append((start, i - 1))
                start = i
        rets = np.array([(C[b] - O[a]) / O[a] for a, b in groups])          # weeks x names
        whole = ~np.isnan(C[lo:hi]).any(axis=0) & ~np.isnan(O[lo:hi]).any(axis=0)
        vol = rets.std(axis=0) * 52 ** 0.5                                   # population SD, as production
        fwd = np.abs(C[nxt - 1] / O[hi] - 1.0)
        ok = whole & ~np.isnan(fwd) & (len(groups) >= lab.MIN_WEEKS)
        pin = ok & (vol < PINNED_VOL_MAX) & (len(groups) >= PINNED_MIN_WEEKS)
        n_all += int(ok.sum())
        all_abs.extend(fwd[ok].tolist())
        flag_abs.extend(fwd[pin].tolist())
        for j in np.flatnonzero(pin):
            flagged.append((names[j], W.isoformat(), float(vol[j]), float(fwd[j])))
        mondays += 1
        W += timedelta(days=7)

    spans = {}
    for t, w, v, f in flagged:
        s = spans.setdefault(t, {"weeks": 0, "first": w, "last": w, "min_vol": v, "max_abs_next_week": f})
        s["weeks"] += 1
        s["last"] = w
        s["min_vol"] = min(s["min_vol"], v)
        s["max_abs_next_week"] = max(s["max_abs_next_week"], f)
    share = len(flagged) / n_all if n_all else None
    med_all = statistics.median(all_abs) if all_abs else None
    med_flag = statistics.median(flag_abs) if flag_abs else None
    harmless = None if share is None else bool(share < 0.005 and (med_flag is None or med_flag < 0.5 * med_all))
    return {"mondays": mondays, "names": len(names), "name_weeks": n_all, "flagged_name_weeks": len(flagged),
            "flagged_share": share, "distinct_flagged": len(spans), "by_name": spans,
            "median_abs_next_week_all": med_all, "median_abs_next_week_flagged": med_flag,
            "harmless": harmless, "threshold": PINNED_VOL_MAX, "min_weeks": PINNED_MIN_WEEKS}


def measure_b(smoke=False):
    import forward as fwd
    from scan_pipeline.config.tickers import STOCK_UNIVERSE
    today = date.today()
    last_friday = today - timedelta(days=(today.weekday() - 4) % 7 or 7)
    weeks = lab.council_weeks(last_friday.strftime("%Y-%m-%d"))
    if smoke:
        weeks = weeks[-4:]
    cal = lab.earnings_calendar(sorted(set(STOCK_UNIVERSE)), max_age_days=6)
    start = lab._plus(weeks[0][1], -100)
    arms = {}
    for arm, knobs in (("off", {"data_utils.PINNED_VOL_MAX": 0.0}), ("on", {})):
        arms[arm] = lab.run(verbose=False, knobs=dict(knobs, pe_builder=fwd._pe_builder),
                            weeks=weeks, start=start, earnings=cal)
    lab.run(verbose=False, knobs={}, weeks=weeks[-1:], start=start, earnings=cal)   # knobs back to production
    rows, diffs = [], []
    for off, on in zip(arms["off"], arms["on"]):
        b_off = {b["ticker"]: b["weight"] for b in off["book"]}
        b_on = {b["ticker"]: b["weight"] for b in on["book"]}
        passed = sorted({t for e in ("Cecil", "Marky", "Ophelia")
                         for t in on["earnings_skipped"][e] if t not in off["earnings_skipped"][e]})
        row = {"week": on["week"], "spy": on["spy_ret"], "alpha_off": off["alpha"], "alpha_on": on["alpha"],
               "invested_off": off["invested"], "invested_on": on["invested"], "differs": b_off != b_on,
               "left_book": sorted(set(b_off) - set(b_on)), "entered_book": sorted(set(b_on) - set(b_off)),
               "passed_over_pinned": passed}
        rows.append(row)
        if row["differs"]:
            diffs.append(on["week"])
    a_off = [r["alpha_off"] for r in rows]
    a_on = [r["alpha_on"] for r in rows]
    return {"weeks": len(rows), "weeks_differing": diffs, "mean_alpha_off": statistics.fmean(a_off),
            "mean_alpha_on": statistics.fmean(a_on), "change": statistics.fmean(a_on) - statistics.fmean(a_off),
            "rows": rows}


def main(argv):
    smoke = len(argv) > 1 and argv[1] == "smoke"
    a = measure_a(smoke)
    P = lambda x, d=2: "--" if x is None else f"{100 * x:.{d}f}%"  # noqa: E731
    print(f"A  {a['mondays']} Mondays, {a['names']} names, {a['name_weeks']} name-weeks")
    print(f"   flagged {a['flagged_name_weeks']} ({P(a['flagged_share'], 3)}), {a['distinct_flagged']} distinct names")
    print(f"   median |next week|: all {P(a['median_abs_next_week_all'])}, flagged {P(a['median_abs_next_week_flagged'])}")
    print(f"   harmless: {a['harmless']}")
    for t, s in sorted(a["by_name"].items(), key=lambda kv: -kv[1]["weeks"]):
        print(f"   {t:6} {s['weeks']:4} weeks  {s['first']} .. {s['last']}  min vol {P(s['min_vol'], 1)}  "
              f"largest |next week| {P(s['max_abs_next_week'])}")
    b = measure_b(smoke)
    print(f"B  {b['weeks']} Council weeks; books differ in {len(b['weeks_differing'])}: {', '.join(b['weeks_differing']) or 'none'}")
    print(f"   mean alpha off {P(b['mean_alpha_off'])}, on {P(b['mean_alpha_on'])}, change {100 * b['change']:+.3f}%")
    for r in b["rows"]:
        if r["differs"] or r["passed_over_pinned"]:
            print(f"   {r['week']}  passed over {r['passed_over_pinned']}  out {r['left_book']}  in {r['entered_book']}  "
                  f"alpha {100 * r['alpha_off']:+.2f} -> {100 * r['alpha_on']:+.2f}  SPY {100 * r['spy']:+.2f}")
    if not smoke:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"generated": date.today().isoformat(), "A": a, "B": b}, fh, indent=1)
            fh.write("\n")
        print(f"wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
