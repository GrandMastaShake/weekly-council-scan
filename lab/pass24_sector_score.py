#!/usr/bin/env python3
"""Pass 24 -- the heatmap's mechanical sector score against Ophelia's anchor (registered in lab/README.md, cebc16e).

Each Monday W: for every sector basket the week that closed the Friday before (fresh) and the week before that (stale) give a
breadth, a relative momentum, a volume confirmation and the basket's mean return; the mechanical score is the heatmap's week
weights without its two judgment components. All are scored by the weekly rank correlation (IC) across the sectors with the
coming Monday-open to Friday-close basket return minus SPY's.

    python lab/pass24_sector_score.py
    python lab/pass24_sector_score.py smoke
"""
from __future__ import annotations

import bisect
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass4_marky as p4  # noqa: E402
import pass9_universe as p9  # noqa: E402
import pass10_sectors as p10  # noqa: E402
import pass11_cecil_themes as p11  # noqa: E402
import pass15_exits as p15  # noqa: E402
import pass19_cecil_trap as p19  # noqa: E402
import pass20_regimes as p20  # noqa: E402

MIN_NAMES = 8
MIN_SECTORS = 5
NW_LAGS = 4
W_BREADTH, W_MOM, W_VOL = 0.20, 0.20, 0.15
SCORES = ("mechanical", "breadth", "momentum", "volume", "stale anchor", "fresh anchor")


def sector_labels(uname, names):
    if uname == p9.REFERENCE:
        from scan_pipeline.config.tickers import COUNCIL_SECTORS
        return {t: COUNCIL_SECTORS[t] for t in names if t in COUNCIL_SECTORS}
    full = p10.sp500_full()
    return {t: full[t]["gics_sector"] for t in names if t in full}


def span(series, a, b):
    """Return and volume of the bars dated in [a, b): the close before b over the close before a, and the volume traded."""
    ca, cb = series.last_close_before(a), series.last_close_before(b)
    if ca is None or cb is None:
        return None
    lo, hi = bisect.bisect_left(series.dates, a), bisect.bisect_left(series.dates, b)
    vol = sum(r["volume"] for r in series.rows[lo:hi])
    return cb / ca - 1.0, vol


def target_return(series, W):
    return series.week_return(W)


def rank_score(values):
    """0 to 100 by rank among the sectors (the highest 100); ties share the mean rank."""
    order = sorted(values, key=values.get)
    n = len(order)
    pos = {}
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            pos[order[k]] = (i + j) / 2.0
        i = j + 1
    return {s: 100.0 * pos[s] / (n - 1) for s in order} if n > 1 else {s: 50.0 for s in order}


def week_inputs(W, baskets, adj):
    """Per sector: fresh and stale basket returns, breadth, volume confirmation, and the target."""
    f1, f0, f_1 = W, lab._plus(W, -7), lab._plus(W, -14)
    spy_fresh = span(adj["SPY"], f0, f1)
    spy_target = target_return(adj["SPY"], W)
    if spy_fresh is None or spy_target is None:
        return None
    sec = {}
    for s, members in baskets.items():
        fresh, stale, tgt = [], [], []
        up_vol = tot_vol = 0.0
        up = tot = 0
        for t in members:
            ser = adj.get(t)
            if ser is None:
                continue
            a, b, c = span(ser, f0, f1), span(ser, f_1, f0), target_return(ser, W)
            if a is None or b is None or c is None:
                continue
            fresh.append(a[0])
            stale.append(b[0])
            tgt.append(c)
            tot += 1
            tot_vol += a[1]
            if a[0] > 0:
                up += 1
                up_vol += a[1]
        if tot < MIN_NAMES or tot_vol <= 0:
            continue
        sec[s] = {"fresh": statistics.fmean(fresh), "stale": statistics.fmean(stale), "breadth": 100.0 * up / tot,
                  "volume": 100.0 * up_vol / tot_vol, "target": statistics.fmean(tgt) - spy_target, "names": tot}
    if len(sec) < MIN_SECTORS:
        return None
    mom = rank_score({s: v["fresh"] - spy_fresh[0] for s, v in sec.items()})
    for s, v in sec.items():
        v["momentum"] = mom[s]
        v["mechanical"] = (W_BREADTH * v["breadth"] + W_MOM * v["momentum"] + W_VOL * v["volume"]) / (W_BREADTH + W_MOM + W_VOL)
    return sec


def weekly_ics(sec):
    names = sorted(sec)
    tgt = [sec[s]["target"] for s in names]
    sig = {"mechanical": "mechanical", "breadth": "breadth", "momentum": "momentum", "volume": "volume",
           "stale anchor": "stale", "fresh anchor": "fresh"}
    ics = {k: lab.spearman([sec[s][f] for s in names], tgt) for k, f in sig.items()}
    pairs = {}
    for i, a in enumerate(SCORES):
        for b in SCORES[i + 1:]:
            pairs[(a, b)] = lab.spearman([sec[s][sig[a]] for s in names], [sec[s][sig[b]] for s in names])
    return ics, pairs


def stat(xs):
    half = len(xs) // 2
    t = p15.nw_t(xs, NW_LAGS)
    return {"weeks": len(xs), "mean": statistics.fmean(xs), "t": t, "halves": [statistics.fmean(xs[:half]), statistics.fmean(xs[half:])],
            "median": statistics.median(xs)}


def run_universe(uname, names, weeks, smoke=False):
    labels = sector_labels(uname, names)
    baskets = {}
    for t, s in labels.items():
        baskets.setdefault(s, []).append(t)
    tickers = sorted(set(names) | set(p19.ETFS)) + [x for x in lab.EXTRA if x not in names]
    adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, True, p20.END, p4.HIST_START)).items()}
    rows = weeks[:20] if smoke else weeks
    ics = {k: [] for k in SCORES}
    pair_acc = {}
    used = []
    for label, W, _ in rows:
        sec = week_inputs(W, baskets, adj)
        if sec is None:
            continue
        i, pr = weekly_ics(sec)
        for k in SCORES:
            ics[k].append(i[k])
        for k, v in pr.items():
            pair_acc.setdefault(k, []).append(v)
        used.append({"week": label, "W": W, "sectors": len(sec)})
    res = {"weeks": len(used), "sectors": {s: len(m) for s, m in sorted(baskets.items())}, "ic": {k: stat(v) for k, v in ics.items()}}
    res["vs_stale"] = {k: stat([a - b for a, b in zip(ics[k], ics["stale anchor"])]) for k in SCORES if k != "stale anchor"}
    res["pair_corr"] = {f"{a} / {b}": statistics.fmean(v) for (a, b), v in pair_acc.items()}
    m, d = res["ic"]["mechanical"], res["vs_stale"]["mechanical"]
    res["has_signal"] = bool(m["mean"] > 0 and m["t"] is not None and m["t"] >= 2 and all(h > 0 for h in m["halves"]))
    res["beats_stale"] = bool(d["t"] is not None and d["t"] >= 2 and all(h > 0 for h in d["halves"]))
    return res


def show(uname, res):
    print(f"\n  {uname}: {res['weeks']} weeks, sectors {res['sectors']}")
    print(f"  {'score':<14}{'mean IC':>9}{'NW t':>7}  halves            median   | vs stale: diff    t   halves")
    for k in SCORES:
        s = res["ic"][k]
        v = res["vs_stale"].get(k)
        tail = f"{v['mean']:+.3f} {v['t']:+6.2f}  {v['halves'][0]:+.3f}/{v['halves'][1]:+.3f}" if v else ""
        print(f"  {k:<14}{s['mean']:>+9.3f}{s['t']:>+7.2f}  {s['halves'][0]:+.3f}/{s['halves'][1]:+.3f}   {s['median']:>+7.3f}   | {tail}")
    print("  mean weekly rank correlation between scores:")
    for k, v in res["pair_corr"].items():
        print(f"    {k:<32}{v:+.2f}")
    print(f"  -> mechanical has signal: {'YES' if res['has_signal'] else 'no'}; beats the stale anchor: {'YES' if res['beats_stale'] else 'no'}")


def main(smoke=False):
    U = p9.universes()
    universes = {p11.CLEAN: p9.sp500_asof(), p9.REFERENCE: U[p9.REFERENCE]}
    if smoke:
        universes = {p9.REFERENCE: U[p9.REFERENCE]}
    hweeks = lab.history_weeks(lab.HISTORY_FIRST_MONDAY, lab.HISTORY_LAST_MONDAY)
    result = {"registered": "cebc16e", "weights": {"breadth": W_BREADTH, "momentum": W_MOM, "volume": W_VOL}, "universes": {}}
    print("  note: the momentum component is the rank of (basket minus SPY), so it ranks the sectors exactly as the fresh anchor does;"
          " their IC rows are identical by construction")
    for uname, names in universes.items():
        res = run_universe(uname, names, hweeks, smoke)
        result["universes"][uname] = res
        show(uname, res)
    clean = result["universes"].get(p11.CLEAN)
    if clean:
        result["verdicts"] = {"mechanical has signal": clean["has_signal"], "mechanical beats the stale anchor": clean["beats_stale"]}
        print("\n  registered verdicts (the clean list): " + "; ".join(f"{k} {'YES' if ok else 'no'}" for k, ok in result["verdicts"].items()))
    path = lab.CACHE / "pass24.smoke.json" if smoke else lab.RESULTS / "pass24_sector_score.json"
    with open(path, "w", encoding="ascii", newline="\n") as fh:
        json.dump(result, fh, indent=1, default=float)
        fh.write("\n")
    print(f"  wrote {path}")


if __name__ == "__main__":
    main(smoke=sys.argv[1:] == ["smoke"])
