#!/usr/bin/env python3
"""Pass 56 -- after a 20% sale: what tells the good ones from the bad, and
which way back in is best.

Every sale the 20% exit makes in a top-500 name is an event. Part A counts
what was known that day (MACD, the fall, the market, the stock, Yahoo's
earnings history) against whether the stock went back above its old high
within a year. Part B compares ways back in.

Registered in lab/README.md (Pass 56) before any run.

    python lab/pass56_back_in.py fetch    # Yahoo earnings history
    python lab/pass56_back_in.py fetchsec # SEC quarterly sales, gross profit, net income (needs SEC_CONTACT)
    python lab/pass56_back_in.py          # full run
    python lab/pass56_back_in.py smoke    # plumbing: 150 names
"""
from __future__ import annotations

import json
import math
import pickle
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass41_owner_channel as p41  # noqa: E402
import pass43_channel_by_size as p43  # noqa: E402
import pass48_screen_book as p48  # noqa: E402
import pass52_ten_good_channels as p52  # noqa: E402
import pass53_other_history as p53  # noqa: E402

p41.MIN_AGE = 8                       # a channel counts after 8 weeks (Pass 54)
OFF_HIGH = 0.20
TOP = 500
AHEAD = 52
AFTER = 26
EPS = lab.CACHE / "yahoo_earnings_history_2026-11-21.pkl"
OUT = lab.RESULTS / "pass56_back_in.json"
SEC = lab.CACHE / "sec_frames_2026-11-21.pkl"
SEC_LAG_DAYS = 75                     # a quarter is taken as known 75 days after it ends
SEC_STALE_DAYS = 200
SEC_CONCEPTS = {"revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"],
                "gross": ["GrossProfit"], "net": ["NetIncomeLoss"]}
DECADES = {"2016-26": ("2016-11-11", "9"), "2006-16": ("2006-11-10", "2016-11-11")}
WAYS = ["the screen", "MACD cross", "above the 10-week average", "half back", "new high"]


def load():
    import pandas as pd
    uni = {r["ticker"]: r for r in p43.read_universe(p43.universe_file())}
    with open(p53.BARS, "rb") as fh:
        frames = pickle.load(fh)
    for t, f in frames.items():
        if len(f) and f.index[0].weekday() != 0:
            f.index = pd.DatetimeIndex([d + pd.Timedelta(days=(7 - d.weekday()) % 7) for d in f.index])
    names = sorted(t for t in frames if t in uni)
    idx = pd.DatetimeIndex([d for d in frames["SPY"].index if d.weekday() == 0 and d >= pd.Timestamp("2004-01-01")])
    Cw = np.column_stack([frames[t]["Close"].reindex(idx).to_numpy(dtype=float) for t in names])
    fridays = [(d + pd.Timedelta(days=4)).date().isoformat() for d in idx]
    cap_now = np.array([float(uni[t]["cap_m"]) for t in names])
    ref_px = np.full(len(names), np.nan)
    for j, t in enumerate(names):
        good = np.flatnonzero(~np.isnan(Cw[:, j]))
        if len(good):
            upto = [w for w in good if fridays[w] <= uni[t]["cap_date"]]
            ref_px[j] = Cw[upto[-1] if upto else good[0], j]
    with np.errstate(invalid="ignore", divide="ignore"):
        size = cap_now[None, :] * Cw / ref_px[None, :]
    member = np.zeros(Cw.shape, dtype=bool)
    for w in range(len(idx)):
        ok = np.flatnonzero(~np.isnan(size[w]))
        member[w, ok[np.argsort(-size[w, ok])][:TOP]] = True
    w06 = next(i for i, d in enumerate(fridays) if d >= "2006-01-01")
    keep = np.flatnonzero(member[w06:].any(axis=0))
    return frames, idx, fridays, [names[j] for j in keep], member[:, keep]


def fetch():
    if EPS.exists():
        print("earnings history already cached")
        return
    import yfinance as yf
    _, _, _, names, _ = load()
    print(f"{len(names)} names", flush=True)
    out, miss = {}, 0
    for k, t in enumerate(names):
        rows = None
        for attempt in range(2):
            try:
                df = yf.Ticker(t.replace(".", "-")).get_earnings_dates(limit=100)
                if df is not None and len(df):
                    rows = [(i.date().isoformat(), float(r["EPS Estimate"]), float(r["Reported EPS"]), float(r["Surprise(%)"]))
                            for i, r in df.iterrows()]
                break
            except Exception:                                       # noqa: BLE001
                time.sleep(3)
        if rows:
            out[t] = sorted(rows)
        else:
            miss += 1
        if k % 100 == 99:
            print(f"{k + 1}/{len(names)}, {len(out)} with history, {miss} without", flush=True)
        time.sleep(0.25)
    with open(EPS, "wb") as fh:
        pickle.dump(out, fh)
    print(f"wrote {EPS.name}: {len(out)} names, {miss} without")


def fetch_sec():
    """Quarterly sales, gross profit and net income from the SEC's XBRL
    frames (one request per concept per calendar quarter, every filer at
    once). The SEC asks automated readers for a contact address: it is read
    from the SEC_CONTACT environment variable and never written anywhere."""
    import os
    import requests
    if SEC.exists():
        print("SEC frames already cached")
        return
    contact = os.environ.get("SEC_CONTACT", "").strip()
    if not contact:
        raise SystemExit("set SEC_CONTACT to the contact address the SEC asks for")
    hdr = {"User-Agent": f"weekly-council-scan lab {contact}", "Accept-Encoding": "gzip, deflate"}
    r = requests.get("https://www.sec.gov/files/company_tickers.json", headers=hdr, timeout=60)
    r.raise_for_status()
    cik_of = {v["ticker"].upper().replace("-", "."): int(v["cik_str"]) for v in r.json().values()}
    _, _, _, names, _ = load()
    want = {cik_of[t]: t for t in names if t in cik_of}
    print(f"{len(want)} of {len(names)} names have an SEC number", flush=True)
    out = {t: {k: {} for k in SEC_CONCEPTS} for t in want.values()}
    periods = [(y, q) for y in range(2009, 2027) for q in (1, 2, 3, 4)]
    for group, concepts in SEC_CONCEPTS.items():
        for (y, q) in periods:
            for c in concepts:
                url = f"https://data.sec.gov/api/xbrl/frames/us-gaap/{c}/USD/CY{y}Q{q}.json"
                data = None
                for attempt in range(3):
                    try:
                        rr = requests.get(url, headers=hdr, timeout=60)
                        if rr.status_code == 404:
                            break
                        rr.raise_for_status()
                        data = rr.json().get("data", [])
                        break
                    except Exception as e:                          # noqa: BLE001
                        print("retry", c, y, q, repr(e)[:80], flush=True)
                        time.sleep(3 + 3 * attempt)
                time.sleep(0.2)
                for row in data or ():
                    t = want.get(int(row["cik"]))
                    if t is None:
                        continue
                    old = out[t][group].get((y, q))
                    if old is None or abs(row["val"]) > abs(old[1]):
                        out[t][group][(y, q)] = (row["end"], float(row["val"]))
        print(f"{group}: {sum(1 for t in out if out[t][group])} names with any quarter", flush=True)
    with open(SEC, "wb") as fh:
        pickle.dump(out, fh)
    print(f"wrote {SEC.name}")


def ema(x, span):
    """Exponential average down each column, starting at the first value."""
    a = 2.0 / (span + 1.0)
    out = np.full(x.shape, np.nan)
    for j in range(x.shape[1]):
        prev = np.nan
        col = x[:, j]
        for i in range(len(col)):
            v = col[i]
            if v == v:
                prev = v if prev != prev else prev + a * (v - prev)
            out[i, j] = prev
    return out


def main(argv):
    mode = argv[1] if len(argv) > 1 else ""
    if mode == "fetch":
        return fetch()
    if mode == "fetchsec":
        return fetch_sec()
    smoke = mode == "smoke"
    frames, idx, fridays, names, member = load()
    if smoke:
        pick = list(range(0, len(names), max(1, len(names) // 150)))[:150]
        names, member = [names[i] for i in pick], member[:, pick]
    eps = {}
    if EPS.exists():
        with open(EPS, "rb") as fh:
            eps = pickle.load(fh)

    sec = {}
    if SEC.exists():
        with open(SEC, "rb") as fh:
            sec = pickle.load(fh)

    def sec_facts(t, friday):
        """Sales, margin and profit facts from the latest quarter that had
        been over for SEC_LAG_DAYS on the sale's Friday."""
        from datetime import timedelta
        g = sec.get(t)
        if not g or not g["revenue"]:
            return {}
        cut = (date.fromisoformat(friday) - timedelta(days=SEC_LAG_DAYS)).isoformat()
        stale = (date.fromisoformat(friday) - timedelta(days=SEC_STALE_DAYS)).isoformat()
        known = sorted(k for k, v in g["revenue"].items() if stale <= v[0] <= cut)
        if not known:
            return {}
        y, q = known[-1]
        rev, prev = g["revenue"][(y, q)][1], g["revenue"].get((y - 1, q))
        o = {}
        if prev and prev[1] > 0 and rev > 0:
            gr = rev / prev[1] - 1.0
            o["sales up on a year before"] = gr > 0
            o["sales up 20% or more on a year before"] = gr >= 0.20
            pq = (y, q - 1) if q > 1 else (y - 1, 4)
            a1, a0 = g["revenue"].get(pq), g["revenue"].get((pq[0] - 1, pq[1]))
            if a1 and a0 and a0[1] > 0 and a1[1] > 0:
                o["sales growth faster than the quarter before"] = gr > a1[1] / a0[1] - 1.0
            gp, gp0 = g["gross"].get((y, q)), g["gross"].get((y - 1, q))
            if gp and gp0:
                o["gross margin up on a year before"] = gp[1] / rev > gp0[1] / prev[1]
        ni = g["net"].get((y, q))
        if ni:
            o["net income positive"] = ni[1] > 0
        return o

    def mat(col):
        return np.column_stack([frames[t][col].reindex(idx).to_numpy(dtype=float) for t in names])
    Ow, Hw, Lw, Cw, Vw = mat("Open"), mat("High"), mat("Low"), mat("Close"), mat("Volume")
    nW, n = Cw.shape
    spy = frames["SPY"]["Close"].reindex(idx).ffill().to_numpy(dtype=float)
    print(f"{nW} weeks {fridays[0]} .. {fridays[-1]}, {n} names, {sum(1 for t in names if t in eps)} with earnings history", flush=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        lC = np.log(Cw)
        dv = Cw * Vw
        wr = np.diff(lC, axis=0)
    med_dv = np.full((nW, n), np.nan)
    swing = np.full((nW, n), np.nan)
    hi52 = np.full((nW, n), np.nan)
    ma10 = np.full((nW, n), np.nan)
    ma40 = np.full((nW, n), np.nan)
    vol26 = np.full((nW, n), np.nan)
    for w in range(26, nW):
        with np.errstate(invalid="ignore"):
            med_dv[w] = np.nanmedian(dv[max(0, w - 51):w + 1], axis=0)
            hi52[w] = np.nanmax(Cw[max(0, w - 51):w + 1], axis=0)
            ma10[w] = np.nanmean(Cw[w - 9:w + 1], axis=0)
            vol26[w] = np.nanmean(Vw[w - 25:w + 1], axis=0)
            if w >= 40:
                ma40[w] = np.nanmean(Cw[w - 39:w + 1], axis=0)
            if w >= 52:
                win = wr[max(0, w - 104):w]
                cnt = (~np.isnan(win)).sum(axis=0)
                swing[w] = np.where(cnt >= 40, np.nanstd(win, axis=0), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        swings_off = (lC - np.log(hi52)) / swing
    tradeable = (np.nan_to_num(med_dv) >= p43.DV_MIN) & (np.nan_to_num(swing) >= p48.SWING_MIN)
    macd = ema(Cw, 12) - ema(Cw, 26)
    hist = macd - ema(macd, 9)
    spy_hi = np.array([spy[max(0, w - 51):w + 1].max() for w in range(nW)])
    spy_ma40 = np.array([spy[max(0, w - 39):w + 1].mean() for w in range(nW)])
    print("drawing channels ...", flush=True)
    T = p52.quality_table(Cw, Hw, Lw)
    channel = ~np.isnan(T["lower"]) & (np.nan_to_num(T["slope"], nan=-1.0) >= p48.FLOOR) & (np.nan_to_num(T["r2"], nan=0.0) >= p48.R2_MIN)
    screen = tradeable & member & channel & (np.nan_to_num(swings_off, nan=-99.0) >= -p48.SWINGS_MAX)

    def wk(d):
        return max(i for i, f in enumerate(fridays) if f <= d)

    def way_fires(way, j, x, c_sale, h):
        c = Cw[x, j]
        if c != c:
            return False
        if way == "the screen":
            return bool(screen[x, j])
        if way == "MACD cross":
            return bool(hist[x, j] > 0 and hist[x - 1, j] <= 0)
        if way == "above the 10-week average":
            return bool(c > ma10[x, j])
        if way == "half back":
            return bool(c >= (c_sale + h) / 2.0)
        return bool(c >= h)

    def trade(j, S, E, way):
        """One name alone over [S, E): the screen buys; after a 20% sale the
        screen or `way` buys back. Returns growth, weeks held, and the sales."""
        held, g, h, weeks_in, sales, last = False, 1.0, 0.0, 0, [], None
        for w in range(S, E):
            c, c1, o1 = Cw[w, j], Cw[w + 1, j], Ow[w + 1, j]
            if c != c or c1 != c1 or o1 != o1:
                continue
            if held:
                h = max(h, c)
                if c <= (1.0 - OFF_HIGH) * h:
                    g *= o1 / c
                    held = False
                    last = (w, c, h)
                    sales.append((w, c, h, entry_w, entry_c))
                else:
                    g *= c1 / c
                    weeks_in += 1
            else:
                by_screen = bool(screen[w, j])
                by_way = (way is not None and last is not None and w > last[0] and way != "the screen"
                          and way_fires(way, j, w, last[1], last[2]))
                if by_screen or by_way:
                    held, h = True, (max(hi52[w, j], c) if by_screen else c)
                    entry_w, entry_c = w, c
                    g *= c1 / o1
                    weeks_in += 1
        return g, weeks_in / max(1, E - S), sales

    def eps_facts(t, friday):
        rows = [r for r in eps.get(t, ()) if r[0] <= friday and r[2] == r[2]]
        if not rows:
            return {}
        o = {"last EPS positive": rows[-1][2] > 0}
        if rows[-1][3] == rows[-1][3]:
            o["last report beat the estimate"] = rows[-1][3] > 0
        beats = [r[3] > 0 for r in rows[-4:] if r[3] == r[3]]
        if len(beats) == 4:
            o["three or more of the last four beat"] = sum(beats) >= 3
        if len(rows) >= 5:
            o["EPS up on a year before"] = rows[-1][2] > rows[-5][2]
        o["sold within two weeks after a report"] = (date.fromisoformat(friday) - date.fromisoformat(rows[-1][0])).days <= 14
        return o

    out = {"generated": fridays[-1], "names": n, "names_with_earnings_history": sum(1 for t in names if t in eps), "decades": {}}
    for dname, (s_date, e_date) in DECADES.items():
        S, E = wk(s_date), (nW - 1 if e_date == "9" else wk(e_date))
        events = []
        for j in range(n):
            _, _, sales = trade(j, S, E, None)
            for (w, c, h, ew, ec) in sales:
                if w + AHEAD > nW - 1:
                    continue
                fut = Cw[w + 1:w + AHEAD + 1, j]
                if np.isnan(fut[-1]):
                    continue
                back = np.flatnonzero(fut >= h)
                hw = max(x for x in range(ew, w + 1) if Cw[x, j] == Cw[x, j] and Cw[x, j] >= h * 0.999999) if any(
                    Cw[x, j] == Cw[x, j] and Cw[x, j] >= h * 0.999999 for x in range(ew, w + 1)) else ew
                ev = {"j": j, "w": w, "c": c, "h": h, "good": bool(len(back)), "weeks_to_old_high": int(back[0] + 1) if len(back) else None,
                      "fwd52": float(fut[-1] / c - 1.0), "fwd52_x": float(fut[-1] / c - spy[w + AHEAD] / spy[w]),
                      "bin": {"MACD line above zero": bool(macd[w, j] > 0), "MACD histogram rising": bool(hist[w, j] > hist[w - 1, j]),
                              "SPY 10% or more under its high": bool(spy[w] <= 0.90 * spy_hi[w]), "SPY under its 40-week average": bool(spy[w] < spy_ma40[w]),
                              "close above its 40-week average": bool(c > ma40[w, j]), "fell in three weeks or fewer": bool(w - hw <= 3)},
                      "num": {"MACD line as a share of price": float(macd[w, j] / c), "weeks from the high to the sale": float(w - hw),
                              "gain from the buy to the high": float(h / ec - 1.0),
                              "volume in the fall against the 26 weeks before": float(np.nanmean(Vw[hw + 1:w + 1, j]) / vol26[hw, j]) if w > hw and vol26[hw, j] > 0 else float("nan"),
                              "the stock's fall less SPY's": float((c / h - 1.0) - (spy[w] / spy[hw] - 1.0)),
                              "weekly swing": float(swing[w, j]), "prior 52-week return": float(c / Cw[w - 52, j] - 1.0) if w >= 52 else float("nan")}}
                ev["bin"].update(eps_facts(names[j], fridays[w]))
                ev["bin"].update(sec_facts(names[j], fridays[w]))
                events.append(ev)
        good = np.array([e["good"] for e in events])
        fx = np.array([e["fwd52_x"] for e in events])
        d = {"from": fridays[S], "to": fridays[E], "sales": len(events), "share_good_to_undo": float(good.mean()) if len(events) else None,
             "median_weeks_to_old_high": float(np.median([e["weeks_to_old_high"] for e in events if e["good"]])) if good.any() else None,
             "mean_fwd52_less_spy": float(fx.mean()) if len(events) else None, "median_fwd52_less_spy": float(np.median(fx)) if len(events) else None,
             "known_on_the_day": {}, "ways_back_in": {}, "traded_alone": {}}
        for key in sorted({k for e in events for k in e["bin"]}):
            yes = np.array([e["bin"].get(key) is True for e in events])
            no = np.array([e["bin"].get(key) is False for e in events])
            if yes.sum() >= 20 and no.sum() >= 20:
                d["known_on_the_day"][key] = {"kind": "yes/no", "yes_n": int(yes.sum()), "no_n": int(no.sum()),
                                              "good_if_yes": float(good[yes].mean()), "good_if_no": float(good[no].mean()),
                                              "fwd52_less_spy_if_yes": float(fx[yes].mean()), "fwd52_less_spy_if_no": float(fx[no].mean())}
        for key in sorted({k for e in events for k in e["num"]}):
            v = np.array([e["num"][key] for e in events])
            ok = ~np.isnan(v)
            if ok.sum() >= 100:
                edges = np.quantile(v[ok], [0.2, 0.4, 0.6, 0.8])
                q = np.digitize(v, edges)
                d["known_on_the_day"][key] = {"kind": "fifths", "edges": [float(x) for x in edges],
                                              "good_by_fifth_low_to_high": [float(good[ok & (q == i)].mean()) for i in range(5)],
                                              "fwd52_less_spy_by_fifth": [float(fx[ok & (q == i)].mean()) for i in range(5)]}
        # ways back in, per event
        base26 = [Cw[e["w"] + AFTER, e["j"]] / e["c"] - spy[e["w"] + AFTER] / spy[e["w"]] for e in events]
        d["ways_back_in"]["never sold (from the sale week)"] = {"share_firing": 1.0, "median_weeks_after_sale": 0.0,
                                                               "after26_less_spy_mean": float(np.nanmean(base26)) if events else None}
        for way in WAYS:
            delay, after, first20, fired = [], [], [], 0
            for e in events:
                j, w = e["j"], e["w"]
                x = next((x for x in range(w + 1, w + AHEAD + 1) if way_fires(way, j, x, e["c"], e["h"])), None)
                if x is None:
                    continue
                fired += 1
                delay.append(x - w)
                if x + AFTER <= nW - 1 and Cw[x + AFTER, j] == Cw[x + AFTER, j]:
                    after.append(Cw[x + AFTER, j] / Cw[x, j] - spy[x + AFTER] / spy[x])
                res = None
                for y in range(x + 1, min(nW, x + AHEAD + 1)):
                    r = Cw[y, j] / Cw[x, j] - 1.0
                    if r <= -0.20:
                        res = "fell"
                        break
                    if r >= 0.20:
                        res = "rose"
                        break
                first20.append(res)
            d["ways_back_in"][way] = {"share_firing": fired / max(1, len(events)), "median_weeks_after_sale": float(np.median(delay)) if delay else None,
                                      "after26_less_spy_mean": float(np.mean(after)) if after else None, "after26_less_spy_median": float(np.median(after)) if after else None,
                                      "fell_20_first": float(np.mean([r == "fell" for r in first20])) if first20 else None,
                                      "rose_20_first": float(np.mean([r == "rose" for r in first20])) if first20 else None}
        # each name traded alone, with each way back in added to the screen
        pop = [j for j in range(n) if med_dv[S, j] == med_dv[S, j] and med_dv[S, j] >= p43.DV_MIN and Cw[S, j] == Cw[S, j] and Cw[E, j] == Cw[E, j]]
        hold = {j: Cw[E, j] / Cw[S, j] for j in pop}
        k = max(3, int(round(0.05 * len(pop))))
        winners = sorted(pop, key=lambda j: -hold[j])[:k]
        rest = [j for j in pop if j not in set(winners)]
        for way in [None] + [w_ for w_ in WAYS if w_ != "the screen"]:
            res = {j: trade(j, S, E, way) for j in pop}
            lab_ = "the screen alone" if way is None else f"screen or {way}"
            d["traded_alone"][lab_] = {g: {"names": len(js), "median_multiple": float(np.median([res[j][0] for j in js])),
                                           "mean_log_growth": float(np.mean([math.log(max(res[j][0], 1e-9)) for j in js])),
                                           "median_weeks_held": float(np.median([res[j][1] for j in js])),
                                           "median_sales": float(np.median([len(res[j][2]) for j in js])),
                                           "hold_median_multiple": float(np.median([hold[j] for j in js]))}
                                       for g, js in (("best movers", winners), ("the rest", rest), ("everyone", pop))}
        out["decades"][dname] = d

    def P(x, d_=0):
        return "  --" if x is None else f"{100 * x:.{d_}f}%"
    for dname, d in out["decades"].items():
        print(f"\n=== {dname}: {d['sales']} sales; good to undo {P(d['share_good_to_undo'])} (median {d['median_weeks_to_old_high']} weeks to the old high); "
              f"next 52 weeks less SPY mean {P(d['mean_fwd52_less_spy'], 1)} median {P(d['median_fwd52_less_spy'], 1)}")
        for key, v in d["known_on_the_day"].items():
            if v["kind"] == "yes/no":
                print(f"  {key:46} yes {P(v['good_if_yes'])} (n {v['yes_n']})  no {P(v['good_if_no'])} (n {v['no_n']})   52w less SPY: yes {P(v['fwd52_less_spy_if_yes'], 1)} no {P(v['fwd52_less_spy_if_no'], 1)}")
            else:
                print(f"  {key:46} good by fifth low to high: " + " ".join(P(x) for x in v["good_by_fifth_low_to_high"])
                      + "   52w less SPY: " + " ".join(P(x, 0) for x in v["fwd52_less_spy_by_fifth"]))
        for way, v in d["ways_back_in"].items():
            print(f"  back in by {way:32} fires {P(v['share_firing'])}, median {v['median_weeks_after_sale']} weeks after; next 26 weeks less SPY mean {P(v['after26_less_spy_mean'], 1)}"
                  + (f" median {P(v['after26_less_spy_median'], 1)}; fell 20% first {P(v['fell_20_first'])}, rose 20% first {P(v['rose_20_first'])}" if "fell_20_first" in v else ""))
        for lab_, v in d["traded_alone"].items():
            print(f"  alone, {lab_:36} " + "  ".join(f"{g}: x{x['median_multiple']:.2f} (hold x{x['hold_median_multiple']:.2f}, in {P(x['median_weeks_held'])}, {x['median_sales']:.0f} sales, mean log {x['mean_log_growth']:.2f})" for g, x in v.items()))
    if not smoke:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=1)
            fh.write("\n")
        print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main(sys.argv)
