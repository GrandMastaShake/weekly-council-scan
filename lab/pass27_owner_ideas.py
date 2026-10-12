#!/usr/bin/env python3
"""Pass 27 -- two of the owner's own ideas, tested as he stated them (registered in lab/README.md, cebc16e).

(a) Pattern DNA: every stock follows a pattern unique to it. For each name pick the best of twelve daily rules on the first 60% of its
days, measure that rule on the last 40%, and compare with the same measure under a randomly assigned eligible rule (2,000 draws).
(b) The Breakfast Indicator: when DBA / QQQ falls more than 10% over six months, QQQ's next three months differ from the other months'.

    python lab/pass27_owner_ideas.py
    python lab/pass27_owner_ideas.py smoke
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass4_marky as p4  # noqa: E402
import pass9_universe as p9  # noqa: E402
import pass19_cecil_trap as p19  # noqa: E402
import pass20_regimes as p20  # noqa: E402

RULES = ["Mon", "Tue", "Wed", "Thu", "Fri", "RSI<30", "RSI>70", "Vol>1.5x", "Gap<-1%", "Gap>+1%", "Near 52w high", "Below 20d avg"]
MIN_FIRING = 20
MIN_HALF_FIRING = 5
SPLIT = 0.6
DRAWS = 2000
BOOT = 5000
BLOCK = 3
MIN_FLAGGED = 12


# ------------------------------------------------------------------------------------------------ (a) Pattern DNA
def rule_flags(df):
    c, o, v = df["close"], df["open"], df["volume"]
    wd = pd.to_datetime(df["date"]).dt.weekday.values
    flags = {nm: wd == i for i, nm in enumerate(RULES[:5])}
    delta = c.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        rsi = 100 - 100 / (1 + gain / loss)
    flags["RSI<30"] = (rsi < 30).values
    flags["RSI>70"] = (rsi > 70).values
    flags["Vol>1.5x"] = (v > 1.5 * v.shift(1).rolling(20).mean()).values
    gap = o / c.shift(1) - 1
    flags["Gap<-1%"] = (gap < -0.01).values
    flags["Gap>+1%"] = (gap > 0.01).values
    flags["Near 52w high"] = (c >= 0.97 * c.rolling(252).max()).values
    flags["Below 20d avg"] = (c < c.rolling(20).mean()).values
    return flags


def stat(nxt, flag, lo, hi, min_firing):
    seg = nxt[lo:hi]
    f = flag[lo:hi]
    if f.sum() < min_firing:
        return None
    return float(seg[f].mean() - seg.mean())


def per_name(rows):
    df = pd.DataFrame(rows)
    if len(df) < 300:
        return None
    nxt = (df["close"].shift(-1) / df["close"] - 1).values
    n = len(df) - 1                                    # the last day has no next return
    cut = int(SPLIT * n)
    mid = cut + (n - cut) // 2
    flags = {k: v[:n] for k, v in rule_flags(df).items()}
    nxt = nxt[:n]
    elig, ins, oos, h1, h2 = [], [], [], [], []
    for k in RULES:
        a = stat(nxt, flags[k], 0, cut, MIN_FIRING)
        b = stat(nxt, flags[k], cut, n, MIN_FIRING)
        if a is None or b is None:
            continue
        elig.append(k)
        ins.append(a)
        oos.append(b)
        h1.append(stat(nxt, flags[k], cut, mid, MIN_HALF_FIRING))
        h2.append(stat(nxt, flags[k], mid, n, MIN_HALF_FIRING))
    if not elig:
        return None
    f = lambda xs: np.array([np.nan if x is None else x for x in xs])
    return {"rules": elig, "ins": np.array(ins), "oos": np.array(oos), "h1": f(h1), "h2": f(h2)}


def pattern_dna(names, adj, smoke=False):
    rng = np.random.default_rng(lab.SEED)
    use = names[:40] if smoke else names
    draws = 500 if smoke else DRAWS
    per = {}
    for t in use:
        s = adj.get(t)
        if s is None:
            continue
        r = per_name(s.rows)
        if r is not None:
            per[t] = r
    real = {"oos": [], "h1": [], "h2": [], "ins": []}
    chosen = {}
    nulls = {k: [] for k in ("oos", "h1", "h2")}
    for t, r in per.items():
        j = int(np.argmax(r["ins"]))
        chosen[r["rules"][j]] = chosen.get(r["rules"][j], 0) + 1
        real["ins"].append(r["ins"][j])
        for k in ("oos", "h1", "h2"):
            real[k].append(r[k][j])
        idx = rng.integers(0, len(r["rules"]), size=draws)
        for k in ("oos", "h1", "h2"):
            nulls[k].append(r[k][idx])
    out = {"names": len(per), "excluded": len(use) - len(per), "chosen": dict(sorted(chosen.items(), key=lambda kv: -kv[1])),
           "in_sample_best_mean": float(np.nanmean(real["ins"]))}
    holds = True
    for k, label in (("oos", "all OOS"), ("h1", "OOS first half"), ("h2", "OOS second half")):
        r_mean = float(np.nanmean(real[k]))
        null = np.nanmean(np.vstack(nulls[k]), axis=0)
        pct = float((null < r_mean).mean() * 100)
        out[k] = {"mean": r_mean, "null_mean": float(null.mean()), "null_sd": float(null.std()), "percentile": pct,
                  "names_positive": float(np.nanmean(np.array(real[k]) > 0)), "n_names": int(np.sum(~np.isnan(real[k])))}
        if k != "oos":
            holds = holds and r_mean > 0 and pct >= 97.5
    out["holds"] = bool(holds)
    return out


# ------------------------------------------------------------------------------------------------ (b) the Breakfast Indicator
def month_end_series(rows):
    df = pd.DataFrame(rows)
    df["m"] = pd.to_datetime(df["date"]).dt.to_period("M")
    return df.groupby("m")["close"].last()


def episodes(months):
    """Runs of flagged months, a gap of more than three months starting a new episode."""
    out, last = 0, None
    for m in months:
        if last is None or (m - last).n > 3:
            out += 1
        last = m
    return out


def test_flag(df, flag):
    """The difference in QQQ's next three months between flagged and other month-ends, with the registered bootstrap and era rule."""
    ret = df["fwd"].values
    flagged = [m for m, f in zip(df.index, flag) if f]
    out = {"months": len(df), "flagged": len(flagged), "flagged_months": [str(m) for m in flagged], "episodes": episodes(flagged),
           "flagged_mean": float(ret[flag].mean()) if flag.any() else None, "other_mean": float(ret[~flag].mean())}
    if len(flagged) < MIN_FLAGGED or out["episodes"] < 3:
        out.update({"testable": False, "verdict": "untestable",
                    "reason": f"{len(flagged)} flagged months in {out['episodes']} episodes (needs {MIN_FLAGGED} and 3)"})
        return out
    diff = float(ret[flag].mean() - ret[~flag].mean())
    rng = np.random.default_rng(lab.SEED)
    n = len(ret)
    nb = int(np.ceil(n / BLOCK))
    boots = []
    for _ in range(BOOT):
        starts = rng.integers(0, n - BLOCK + 1, size=nb)
        ix = np.concatenate([np.arange(s0, s0 + BLOCK) for s0 in starts])[:n]
        f, r = flag[ix], ret[ix]
        if f.sum() == 0 or (~f).sum() == 0:
            continue
        boots.append(r[f].mean() - r[~f].mean())
    boots = np.array(boots)
    p = float((np.abs(boots - boots.mean()) >= abs(diff)).mean())         # two-sided, the bootstrap centered on its own mean
    out.update({"testable": True, "diff": diff, "boot_ci": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
                "p": p, "eras": {}})
    eras_ok = True
    for name, (a, b) in {"2008-2012": (2008, 2012), "2013-2019": (2013, 2019), "2020-2026": (2020, 2026)}.items():
        sel = np.array([a <= m.year <= b for m in df.index])
        ff, nf = flag & sel, (~flag) & sel
        e = {"flagged": int(ff.sum()), "diff": float(ret[ff].mean() - ret[nf].mean()) if ff.sum() and nf.sum() else None}
        out["eras"][name] = e
        eras_ok = eras_ok and e["flagged"] >= 3 and e["diff"] is not None and e["diff"] > 0
    out["holds"] = bool(diff > 0 and p < 0.05 and eras_ok)
    out["verdict"] = "holds" if out["holds"] else "no"
    return out


def breakfast():
    bars = lab.bars_by_ticker(lab.download(["DBA", "QQQ"], True, p20.END, "2006-12-01"))
    for t in ("DBA", "QQQ"):
        if len(bars.get(t, [])) < 4000:
            raise SystemExit(f"{t} has {len(bars.get(t, []))} bars: delete the cached download in lab/cache and rerun")
    dba, qqq = month_end_series(bars["DBA"]), month_end_series(bars["QQQ"])
    idx = dba.index.intersection(qqq.index)
    dba, qqq = dba[idx], qqq[idx]
    ratio = dba / qqq
    df = pd.DataFrame({"roc": ratio / ratio.shift(6) - 1, "dba_roc": dba / dba.shift(6) - 1, "fwd": qqq.shift(-3) / qqq - 1}).dropna()
    df = df[(df.index >= pd.Period("2007-07", "M")) & (df.index <= pd.Period("2026-06", "M"))]
    out = test_flag(df, (df["roc"] < -0.10).values)
    # NOT registered, a check after the registered flag turned out to fire in a large share of months (the ratio falls whenever QQQ
    # rallies): the same test with DBA's own six-month change below -10%, which is what "a food commodity collapse" says.
    out["dba_alone"] = test_flag(df, (df["dba_roc"] < -0.10).values)
    return out


def main(smoke=False):
    result = {"registered": "cebc16e"}
    names = p9.sp500_asof()
    tickers = sorted(set(names) | set(p19.ETFS)) + [x for x in lab.EXTRA if x not in names]
    adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, True, p20.END, p4.HIST_START)).items()}
    a = pattern_dna(names, adj, smoke)
    result["pattern_dna"] = a
    print(f"\n  (a) Pattern DNA on the S&P 500 as of 2024-09: {a['names']} names with a rule eligible in both windows ({a['excluded']} excluded)")
    print(f"      in-sample best rule's mean (rule minus name's mean, per day): {a['in_sample_best_mean']*100:+.4f}%")
    for k, label in (("oos", "all out-of-sample"), ("h1", "OOS first half"), ("h2", "OOS second half")):
        x = a[k]
        print(f"      {label:<18}chosen rule {x['mean']*100:+.4f}%/day vs random eligible rule {x['null_mean']*100:+.4f}% (sd {x['null_sd']*100:.4f}); "
              f"percentile {x['percentile']:.1f}; names positive {x['names_positive']:.0%} of {x['n_names']}")
    print(f"      rules chosen most: " + ", ".join(f"{k} {v}" for k, v in list(a["chosen"].items())[:6]))
    print(f"      -> holds: {'YES' if a['holds'] else 'no'}")
    b = breakfast()
    result["breakfast"] = b

    def show_b(title, x):
        print(f"\n  {title}: {x['months']} month-ends, {x['flagged']} flagged in {x['episodes']} episodes")
        if x["testable"]:
            print(f"      QQQ next three months: flagged {x['flagged_mean']*100:+.2f}% vs other {x['other_mean']*100:+.2f}%, difference {x['diff']*100:+.2f}% "
                  f"(bootstrap 95% {x['boot_ci'][0]*100:+.2f} to {x['boot_ci'][1]*100:+.2f}, p {x['p']:.3f})")
            for k, e in x["eras"].items():
                d = "--" if e["diff"] is None else "%+.2f%%" % (e["diff"] * 100)
                print(f"      {k}: {e['flagged']} flagged, difference {d}")
        else:
            print(f"      untestable: {x['reason']}")
        print(f"      -> {x['verdict']}")

    show_b("(b) Breakfast Indicator as registered (DBA / QQQ six-month change below -10%)", b)
    show_b("(b2) NOT registered: DBA's own six-month change below -10%", b["dba_alone"])
    result["verdicts"] = {"pattern dna": a["holds"], "breakfast": b["verdict"]}
    path = lab.CACHE / "pass27.smoke.json" if smoke else lab.RESULTS / "pass27_owner_ideas.json"
    with open(path, "w", encoding="ascii", newline="\n") as fh:
        json.dump(result, fh, indent=1, default=float)
        fh.write("\n")
    print(f"  wrote {path}")


if __name__ == "__main__":
    main(smoke=sys.argv[1:] == ["smoke"])
