#!/usr/bin/env python3
"""Pass 43 -- the owner's channel by size: mega, large, mid, small.

Pass 41's channel and book run inside each size tier of today's full US
listing ($300M and up), with size taken point in time as today's market cap
scaled by the adjusted price then over now, and tiers cut by rank.

Registered in lab/README.md (Pass 43) before any run.

    python lab/pass43_channel_by_size.py fetch    # the listing and the weekly bars -> lab/cache
    python lab/pass43_channel_by_size.py          # the four numbers per tier
    python lab/pass43_channel_by_size.py smoke    # plumbing: 400 names
"""
from __future__ import annotations

import csv
import glob
import json
import math
import pickle
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass38_chart_stack as p38  # noqa: E402
import pass41_owner_channel as p41  # noqa: E402
import pass42_who_breaks_first as p42  # noqa: E402

SMID_CSV = lab.LAB / "universe_smid_2026-09-23.csv"
SMID_DATE = "2026-09-23"
PRICE_MIN = 3.0
START, END = "2006-06-01", "2026-11-14"
BARS = lab.CACHE / f"weekly_adj_{START}_{END}_all.pkl"
TIERS = [("mega", 0, 100, 0.0010), ("large", 100, 500, 0.0010), ("mid", 500, 1100, 0.0020),
         ("small", 1100, 2100, 0.0030), ("smaller", 2100, 10 ** 6, 0.0050)]
DV_MIN = 5e6
R2_MIN = 0.80
H = 13
SLOTS, WEIGHT = 10, 0.10
DRAWS = 200
SEED = 20261124
HALF = p38.HALF
OUT = lab.RESULTS / "pass43_channel_by_size.json"
FLOOR = math.log(1.0 + p41.MIN_SLOPE_YEAR) / 52.0


def universe_file():
    files = sorted(glob.glob(str(lab.LAB / "universe_all_*.csv")))
    return Path(files[-1]) if files else None


def fetch():
    uf = universe_file()
    if uf is None:
        # The Nasdaq listing refused the request (HTTP 403) on 2026-11-20, so the
        # universe is the lab's two frozen lists: the small and mid cap list with
        # its caps of 2026-09-23, and the S&P 500 list with caps read from Yahoo now.
        import yfinance as yf
        rows = {}
        with open(SMID_CSV, encoding="utf-8") as fh:
            for r in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
                rows[r["ticker"]] = (r["cap_m"], r["sector"], SMID_DATE)
        with open(p38.FULL_CSV, encoding="utf-8") as fh:
            sp = [(r["ticker"], r["gics_sector"]) for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))]
        today = datetime.now().strftime("%Y-%m-%d")
        missing = []
        for k, (t, sec) in enumerate(sp):
            cap = None
            for attempt in range(2):
                try:
                    cap = yf.Ticker(t.replace(".", "-")).fast_info["market_cap"]
                    break
                except Exception:                                   # noqa: BLE001
                    time.sleep(2)
            if cap and cap == cap:
                rows[t] = (round(float(cap) / 1e6), sec, today)
            else:
                missing.append(t)
            if k % 100 == 99:
                print(f"caps {k + 1}/{len(sp)}", flush=True)
        uf = lab.LAB / f"universe_all_{today}.csv"
        with open(uf, "w", encoding="utf-8", newline="") as fh:
            fh.write(f"# source: {SMID_CSV.name} (caps of {SMID_DATE}) and {p38.FULL_CSV.name} (caps from Yahoo, {today})\n"
                     f"# built: {datetime.now().astimezone().isoformat(timespec='seconds')}\n"
                     f"# not on it: names above $10B outside the S&P 500; S&P names with no cap returned: {' '.join(missing) or 'none'}\n")
            w = csv.writer(fh)
            w.writerow(["ticker", "cap_m", "sector", "cap_date"])
            w.writerows((t,) + v for t, v in sorted(rows.items()))
        print(f"{len(rows)} names -> {uf.name}; no cap for {len(missing)}")
    names = [r["ticker"] for r in read_universe(uf)]
    if BARS.exists():
        print("bars already cached")
        return
    import pandas as pd
    import yfinance as yf
    frames = {}
    for i in range(0, len(names), 100):
        chunk = names[i:i + 100]
        for attempt in range(3):
            try:
                df = yf.download([t.replace(".", "-") for t in chunk], start=START, end=END, interval="1wk",
                                 auto_adjust=True, progress=False, group_by="ticker", threads=True)
                break
            except Exception as e:                                  # noqa: BLE001
                print("retry", i, e)
                time.sleep(5 + 5 * attempt)
                df = None
        if df is None:
            continue
        for t in chunk:
            y = t.replace(".", "-")
            if y in df.columns.get_level_values(0):
                sub = df[y].dropna(how="all")
                if len(sub) > 30:
                    frames[t] = sub[["Open", "High", "Low", "Close", "Volume"]].astype("float32")
        print(f"{i + len(chunk)}/{len(names)} names, {len(frames)} with bars", flush=True)
        time.sleep(1.0)
    lab.CACHE.mkdir(parents=True, exist_ok=True)
    with open(BARS, "wb") as fh:
        pickle.dump(frames, fh)
    print(f"wrote {BARS.name}: {len(frames)} names")


def read_universe(uf):
    with open(uf, encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def main(argv):
    mode = argv[1] if len(argv) > 1 else ""
    if mode == "fetch":
        return fetch()
    smoke = mode == "smoke"
    uf = universe_file()
    uni = {r["ticker"]: r for r in read_universe(uf)}
    with open(BARS, "rb") as fh:
        frames = pickle.load(fh)
    names = sorted(t for t in frames if t in uni)
    if smoke:
        names = names[::max(1, len(names) // 400)][:400]
    import pandas as pd
    idx = sorted(set().union(*[set(frames[t].index) for t in names[:200]]))
    idx = pd.DatetimeIndex([d for d in idx if d.weekday() == 0])
    def mat(col):
        return np.column_stack([frames[t][col].reindex(idx).to_numpy(dtype=float) for t in names])
    Ow, Hw, Lw, Cw, Vw = mat("Open"), mat("High"), mat("Low"), mat("Close"), mat("Volume")
    nW, n = Cw.shape
    fridays = [(d + pd.Timedelta(days=4)).date().isoformat() for d in idx]
    print(f"{nW} weeks {fridays[0]} .. {fridays[-1]}, {n} names ({uf.name})")

    cap_now = np.array([float(uni[t]["cap_m"]) for t in names])
    last_px = np.full(n, np.nan)                                   # the close of the week the cap is dated
    for j, t in enumerate(names):
        upto = [w for w in range(nW) if fridays[w] <= max(uni[t]["cap_date"], fridays[0]) and not np.isnan(Cw[w, j])]
        good = upto or [w for w in range(nW) if not np.isnan(Cw[w, j])]
        if good:
            last_px[j] = Cw[good[-1] if upto else good[0], j]
    with np.errstate(invalid="ignore", divide="ignore"):
        size = cap_now[None, :] * Cw / last_px[None, :]
        dv = Cw * Vw
    med_dv = np.full((nW, n), np.nan)
    for w in range(26, nW):
        with np.errstate(invalid="ignore"):
            med_dv[w] = np.nanmedian(dv[max(0, w - 51):w + 1], axis=0)
    tradeable = (Cw >= PRICE_MIN) & (np.nan_to_num(med_dv) >= DV_MIN) & ~np.isnan(size)
    tier = np.full((nW, n), -1, dtype=int)
    scale = n / 3600.0 if smoke else 1.0
    for w in range(nW):
        ok = np.flatnonzero(~np.isnan(size[w]))
        order = ok[np.argsort(-size[w, ok])]
        for k, (_, lo, hi, _) in enumerate(TIERS):
            tier[w, order[int(lo * scale):int(min(hi * scale, len(order)))]] = k

    lower, slope, r2, pos, _ = p41.channel_table(Cw, Hw, Lw)
    rising = ~np.isnan(lower) & (np.nan_to_num(slope, nan=-1.0) >= FLOOR)
    ok_ch = rising & (np.nan_to_num(r2, nan=0.0) >= R2_MIN)
    with np.errstate(invalid="ignore", divide="ignore"):
        logC = np.log(Cw)
        R_hold = Cw[1:] / Cw[:-1] - 1.0
        R_in = Cw[1:] / Ow[1:] - 1.0
        R_out = Ow[1:] / Cw[:-1] - 1.0
    pin = p38.pinned_table(Ow, Cw)

    w0 = 60
    last_w = nW - H
    broken = np.zeros((last_w, n), dtype=bool)
    with np.errstate(invalid="ignore"):
        for k in range(1, H + 1):
            broken |= logC[k:k + last_w] < lower[:last_w] + slope[:last_w] * k
        fwd = Cw[H:H + last_w] / Cw[:last_w] - 1.0
    weeks = list(range(w0, nW - 1))
    wk_dates = [fridays[w + 1] for w in weeks]
    spans = {"all": (fridays[w0], "9999"), "2017 on": (HALF, "9999"), "to 2016": (fridays[w0], HALF)}
    draws = 20 if smoke else DRAWS
    out = {"generated": fridays[-1], "names": n, "weeks": nW, "universe": uf.name, "tiers": {}}

    for k, (tname, lo, hi, slip) in enumerate(TIERS):
        in_tier = (tier == k) & tradeable
        res = {"cost_a_side": slip, "median_names_a_week": float(np.median(in_tier[w0:].sum(axis=1)))}
        # 1-3: how often, how long, does it pay
        for span, (a, b) in spans.items():
            ws = [w for w in range(w0, last_w) if a <= fridays[w] < b]
            have, tot, brk_w, exc_w = 0, 0, [], []
            for w in ws:
                m = in_tier[w] & ~np.isnan(fwd[w])
                c = m & ok_ch[w]
                tot += int(in_tier[w].sum())
                have += int((in_tier[w] & ok_ch[w]).sum())
                if c.sum() >= 3 and m.sum() >= 10:
                    brk_w.append(float(broken[w][c].mean()))
                    exc_w.append(float(fwd[w][c].mean() - fwd[w][m].mean()))
            mean_exc, se = p42.nw_se(exc_w) if exc_w else (None, None)
            res[span] = {"share_with_channel": have / tot if tot else None,
                         "broken_within_13w": float(np.mean(brk_w)) if brk_w else None,
                         "return_13w_over_tier": mean_exc,
                         "return_13w_over_tier_t": (mean_exc / se) if se else None, "weeks": len(brk_w)}
        # 4: the book
        rng = np.random.default_rng(SEED)
        entry_ok = in_tier & ok_ch & ~pin
        pool_ok = in_tier[:-1] & ~np.isnan(R_hold)
        held, since, anchor = [], {}, {}
        rets, counts, holds, gains, tier_avg = [], [], [], [], []
        rand = np.zeros((draws, len(weeks)))
        for i, w in enumerate(weeks):
            keep = []
            for j in held:
                a_, b_, e_, _ = anchor[j]
                if not np.isnan(R_hold[w, j]) and not np.isnan(logC[w, j]) and logC[w, j] >= a_ + b_ * (w - e_):
                    keep.append(j)
            gone = [j for j in held if j not in keep]
            entries = []
            if len(keep) < SLOTS:
                cand = np.flatnonzero(entry_ok[w] & ~np.isnan(R_in[w]))
                kept = set(keep)
                for j in sorted(cand, key=lambda j: (-r2[w, j], names[j])):
                    if len(keep) + len(entries) >= SLOTS:
                        break
                    if j not in kept:
                        entries.append(int(j))
            r = sum(R_hold[w, j] for j in keep)
            r += sum((0.0 if np.isnan(R_out[w, j]) else R_out[w, j]) - slip for j in gone)
            r += sum(R_in[w, j] - slip for j in entries)
            rets.append(WEIGHT * float(r))
            for j in gone:
                holds.append(w - since.pop(j))
                e_px = anchor.pop(j)[3]
                x_px = Ow[w + 1, j] if not np.isnan(Ow[w + 1, j]) else Cw[w, j]
                gains.append(float(x_px / e_px - 1.0))
            for j in entries:
                since[j] = w
                anchor[j] = (float(lower[w, j]), float(slope[w, j]), w, float(Ow[w + 1, j]))
            held = keep + entries
            kk = len(held)
            counts.append(kk)
            pool = np.flatnonzero(pool_ok[w])
            tier_avg.append(float(R_hold[w][pool].mean()) if len(pool) else 0.0)
            if kk and len(pool) >= kk:
                pick = rng.random((draws, len(pool))).argpartition(kk - 1, axis=1)[:, :kk]
                rand[:, i] = WEIGHT * R_hold[w][pool][pick].sum(axis=1)
        book = {}
        for span, (a, b) in spans.items():
            ix = [i for i, d in enumerate(wk_dates) if a <= d < b]
            if len(ix) < 30:
                continue
            rr = [rets[i] for i in ix]
            st = p38.stats(rr, [tier_avg[i] for i in ix], [wk_dates[i] for i in ix])
            ta = p38.stats([tier_avg[i] for i in ix], [tier_avg[i] for i in ix], [wk_dates[i] for i in ix])
            means = rand[:, ix].mean(axis=1)
            book[span] = {"cagr": st["cagr"], "sharpe": st["sharpe"], "max_drawdown": st["max_drawdown"],
                          "tier_average_cagr": ta["cagr"], "tier_average_sharpe": ta["sharpe"],
                          "tier_average_max_drawdown": ta["max_drawdown"],
                          "percentile_among_random": float((means < np.mean(rr)).mean() * 100.0),
                          "arm_mean_week": float(np.mean(rr)), "random_mean_week": float(means.mean())}
        res["book"] = book
        res["book_avg_names_held"] = float(np.mean(counts))
        res["book_median_hold_weeks"] = float(np.median(holds)) if holds else None
        res["book_closed_positions"] = len(holds)
        res["book_share_closed_at_a_gain"] = float(np.mean([g > 0 for g in gains])) if gains else None
        res["book_mean_closed_gain"] = float(np.mean(gains)) if gains else None
        out["tiers"][tname] = res

    def P(x, d=1):
        return "    --" if x is None else f"{100 * x:6.{d}f}%"
    for span in ("all", "to 2016", "2017 on"):
        print(f"--- {span}")
        print(f"{'tier':8} {'names':>6} {'has ch':>7} {'brk13':>7} {'13w over tier':>14} {'t':>6} | {'book':>7} {'tier avg':>8} {'Sharpe':>6} {'avg Sh':>6} {'maxDD':>7} {'avg DD':>7} {'pct':>5}")
        for tname, r in out["tiers"].items():
            a, b = r[span], r["book"].get(span)
            t = a["return_13w_over_tier_t"]
            line = (f"{tname:8} {r['median_names_a_week']:6.0f} {P(a['share_with_channel'])} {P(a['broken_within_13w'])} "
                    f"{P(a['return_13w_over_tier'], 2):>14} {'    --' if t is None else f'{t:6.2f}'} | ")
            if b and b["sharpe"] is not None and b["tier_average_sharpe"] is not None:
                line += (f"{P(b['cagr'])} {P(b['tier_average_cagr']):>8} {b['sharpe']:6.2f} {b['tier_average_sharpe']:6.2f} "
                         f"{P(b['max_drawdown'])} {P(b['tier_average_max_drawdown'])} {b['percentile_among_random']:5.0f}")
            print(line)
    for tname, r in out["tiers"].items():
        print(f"{tname:8} held {r['book_avg_names_held']:.1f}, median hold {r['book_median_hold_weeks']}, closed {r['book_closed_positions']}, "
              f"won {P(r['book_share_closed_at_a_gain'], 0)}, mean gain {P(r['book_mean_closed_gain'])}")
    if not smoke:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=1)
            fh.write("\n")
        print(f"wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
