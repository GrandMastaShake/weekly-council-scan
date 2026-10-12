#!/usr/bin/env python3
"""Pass 22 -- the frozen 2025 lists, scored forward against random (registered in lab/README.md, d1ba76f).

    python lab/pass22_frozen.py freeze --archive <path to the owner's Archive folder>   # extract each list's names and scores
    python lab/pass22_frozen.py fetch                                                    # download prices (no analysis)
    python lab/pass22_frozen.py                                                          # score the six cohorts
    python lab/pass22_frozen.py smoke

`freeze` writes lab/frozen_2025_lists.csv (symbol, score, and Jensen's own recorded price) so the pass reads one committed file and
carries no local path. The source files, their SHA-256 and their own timestamps are listed in the CSV's header comments.
A cohort is the list's own top decile by its score (the Cecil v1 cohort is its 20 stored names; the overlap cohort is the names in
the top decile of two or more of sentinel, jensen and elizabet). Entry is the open of the first session after the file's timestamp;
exit the close of the Friday ending week h of 4, 13, 26 and 52. The measure is the cohort's mean (and median) return against 2,000
random draws of the same size from the same file's priced names, and against draws matched on volatility and price.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import random
import statistics
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402

FROZEN = lab.LAB / "frozen_2025_lists.csv"
PRICE_START, PRICE_END = "2025-04-01", "2026-10-10"
HORIZONS = (4, 13, 26, 52)
DRAWS = 2000
VOL_DAYS, MIN_VOL_DAYS = 60, 40
RECORDED_PRICE_TOLERANCE = 0.15
# cohort -> (relative path under the archive, entry date: the first session open after the file's own timestamp)
SOURCES = {
    "threshold": ("bots/core/Reports/Cecil/threshold_analysis_20250727_211832.csv", "2025-07-28"),      # Sun 21:18
    "sentinel": ("reports/Universe_Sentinel/universe_sentinel_full_analysis_20250919_213629.json", "2025-09-22"),   # Fri 21:36
    "jensen": ("reports/Jensen/jensen_elite_discoveries_20250919_231123.json", "2025-09-22"),           # Fri 23:11
    "elizabet": ("reports/Elizabet/elizabet_universe_convergence_report_20250925_032815.json", "2025-09-25"),   # Thu 03:28
    "cecil_v1": ("cecil_ai_council_referrals_complete.json", "2025-09-25"),                             # Thu 03:05
}
DERIVED = {"overlap": "2025-09-25"}


# ------------------------------------------------------------------------------------------------ freeze
def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def read_source(cohort: str, path: Path) -> list[tuple[str, float, str]]:
    """[(symbol, score, recorded_price)] from one source file."""
    if cohort == "threshold":
        rows = list(csv.DictReader(path.open(encoding="utf-8", errors="replace")))
        return [(r["symbol"].strip().upper(), float(r["weighted_score"]), "") for r in rows if r.get("weighted_score") not in (None, "")]
    d = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if cohort == "sentinel":
        return [(s.strip().upper(), float(v["overall_score"]), "") for s, v in d["all_stocks"].items() if v.get("overall_score") is not None]
    if cohort == "jensen":
        best: dict[str, tuple[float, str]] = {}
        for o in d["opportunities"]:
            s = o["symbol"].strip().upper()
            sc = float(o["bagbagger_score"])
            if s not in best or sc > best[s][0]:
                best[s] = (sc, str(o.get("price", "")))
        return [(s, sc, pr) for s, (sc, pr) in best.items()]
    if cohort == "elizabet":
        return [(r["symbol"].strip().upper(), float(r["converging_strategies"]), "") for r in d["convergence_data"]]
    if cohort == "cecil_v1":
        return [(r["symbol"].strip().upper(), float(r["overall_score"]), "") for r in d["live_market_intelligence"]["top_recommendations"]]
    raise ValueError(cohort)


def freeze(archive: Path) -> None:
    lines = ["# Frozen 2025 bot-era lists for Pass 22 (extracted from the owner's Archive; see lab/README.md, Pass 22).",
             "# cohort,entry_date,symbol,score,recorded_price   (recorded_price is Jensen's own price field; blank elsewhere)"]
    rows_out = []
    for cohort, (rel, entry) in SOURCES.items():
        p = archive / rel
        rows = read_source(cohort, p)
        lines.append(f"# {cohort}: {Path(rel).name}  sha256[:16]={_sha(p)}  rows={len(rows)}  entry={entry}")
        rows_out += [(cohort, entry, s, sc, pr) for s, sc, pr in rows]
    with FROZEN.open("w", encoding="ascii", newline="\n") as fh:
        for ln in lines:
            fh.write(ln + "\n")
        w = csv.writer(fh, lineterminator="\n")
        for r in rows_out:
            w.writerow(r)
    print(f"froze {len(rows_out)} rows from {len(SOURCES)} files -> {FROZEN}")


def load_frozen() -> dict[str, dict]:
    out: dict[str, dict] = {}
    with FROZEN.open(encoding="ascii") as fh:
        for r in csv.reader(ln for ln in fh if not ln.startswith("#")):
            cohort, entry, sym, score, price = r
            c = out.setdefault(cohort, {"entry": entry, "scores": {}, "price": {}})
            c["scores"][sym] = float(score)
            if price not in ("", "None"):
                try:
                    c["price"][sym] = float(price)
                except ValueError:
                    pass
    return out


# ------------------------------------------------------------------------------------------------ prices and returns
def load_prices(symbols):
    tickers = sorted(set(symbols) | {"SPY"})
    df = lab.download(tickers, True, PRICE_END, PRICE_START)
    return {t: lab.Series(r) for t, r in lab.bars_by_ticker(df).items()}


def week_end(entry: str, h: int) -> str:
    """The Friday ending week h, counting the entry's own week as week 1."""
    d = lab._d(entry)
    friday = d + timedelta(days=4 - d.weekday()) + timedelta(days=7 * (h - 1))
    return friday.strftime("%Y-%m-%d")


def entry_stats(s: lab.Series, entry: str):
    """(entry open, trailing 60-day volatility or None, entry index) or None when there is no usable price at entry."""
    i = bisect.bisect_left(s.dates, entry)
    if i >= len(s.dates) or s.dates[i] > lab._plus(entry, 5):
        return None
    closes = [r["close"] for r in s.rows[max(0, i - VOL_DAYS - 1):i]]
    rets = [b / a - 1 for a, b in zip(closes, closes[1:]) if a > 0]
    vol = statistics.pstdev(rets) if len(rets) >= MIN_VOL_DAYS else None
    return s.rows[i]["open"], vol, i


def horizon_return(s: lab.Series, i0: int, open0: float, end: str, last_day: str):
    """(return, stopped_early) for exit at the close of `end`; None if the data do not reach `end`."""
    if end > last_day:
        return None
    j = bisect.bisect_right(s.dates, end) - 1
    if j < i0:
        return None
    stopped = s.dates[j] < lab._plus(end, -7)
    return s.rows[j]["close"] / open0 - 1, stopped


def winsorize(vals, lo=0.01, hi=0.99):
    v = sorted(vals)
    a, b = v[int(lo * (len(v) - 1))], v[int(math.ceil(hi * (len(v) - 1)))]
    return a, b


def percentile(stat, draws):
    below = sum(1 for d in draws if d < stat)
    equal = sum(1 for d in draws if d == stat)
    return 100.0 * (below + 0.5 * equal) / len(draws)


def cohort_picks(frozen, name):
    """The list's own selection: top decile by score (ties at the cutoff included); cecil_v1 is all 20."""
    if name == "cecil_v1":
        return set(frozen["cecil_v1"]["scores"])
    sc = frozen[name]["scores"]
    vals = sorted(sc.values())
    cutoff = vals[int(0.90 * (len(vals) - 1))]
    return {s for s, v in sc.items() if v >= cutoff}


def evaluate(name, picks, pool, entry, px, last_day, tag):
    """Per horizon: the cohort against uncontrolled and matched random draws from `pool`."""
    est = {}
    dropped = {"no_price": 0}
    for sym in pool | picks:
        s = px.get(sym)
        e = entry_stats(s, entry) if s else None
        if e is None:
            dropped["no_price"] += 1
            continue
        est[sym] = e
    live_pool = [s for s in pool if s in est]
    in_pool = set(live_pool)
    live_picks = [s for s in picks if s in in_pool]
    dropped["pick_not_in_pool"] = sum(1 for s in picks if s in est and s not in in_pool)
    res = {"entry": entry, "pool": len(live_pool), "picks": len(live_picks), "picks_listed": len(picks), "dropped": dropped, "horizons": {}}
    vols = sorted(est[s][1] for s in live_pool if est[s][1] is not None)
    if not live_picks or len(vols) < 30:
        return res
    cuts = (vols[len(vols) // 3], vols[2 * len(vols) // 3])

    def cell(sym):
        v, o = est[sym][1], est[sym][0]
        vb = "n" if v is None else (0 if v <= cuts[0] else (1 if v <= cuts[1] else 2))
        pb = 0 if o < 5 else (1 if o < 20 else 2)
        return vb, pb
    cells: dict = {}
    for s in live_pool:
        cells.setdefault(cell(s), []).append(s)
    for h in HORIZONS:
        end = week_end(entry, h)
        rets, stopped = {}, 0
        for sym in live_pool:
            r = horizon_return(px[sym], est[sym][2], est[sym][0], end, last_day)
            if r is None:
                continue
            rets[sym] = r[0]
            stopped += r[1]
        if len(rets) < 30:
            res["horizons"][h] = {"available": False, "end": end}
            continue
        lo, hi = winsorize(list(rets.values()))
        w = {s: max(lo, min(hi, r)) for s, r in rets.items()}
        ps = [s for s in live_picks if s in w]
        if not ps:
            res["horizons"][h] = {"available": False, "end": end}
            continue
        pm, pmed = statistics.fmean(w[s] for s in ps), statistics.median(w[s] for s in ps)
        rng = random.Random(f"{lab.SEED}-p22-{name}-{h}")
        pool_l = [s for s in live_pool if s in w]
        u_mean, u_med, m_mean, m_med = [], [], [], []
        for _ in range(DRAWS):
            d = rng.sample(pool_l, len(ps))
            vals = [w[s] for s in d]
            u_mean.append(statistics.fmean(vals))
            u_med.append(statistics.median(vals))
            mvals = []
            for s in ps:
                members = [x for x in cells.get(cell(s), []) if x in w] or pool_l
                mvals.append(w[rng.choice(members)])
            m_mean.append(statistics.fmean(mvals))
            m_med.append(statistics.median(mvals))
        pct = {"mean": percentile(pm, u_mean), "median": percentile(pmed, u_med),
               "mean_matched": percentile(pm, m_mean), "median_matched": percentile(pmed, m_med)}
        res["horizons"][h] = {"available": True, "end": end, "n_pool": len(pool_l), "n_picks": len(ps), "stopped_early": stopped,
                              "pick_mean": pm, "pick_median": pmed, "random_mean": statistics.fmean(u_mean), "random_median": statistics.fmean(u_med),
                              "matched_mean": statistics.fmean(m_mean), "percentile": pct,
                              "beats_random": bool(min(pct.values()) >= 97.5)}
    res["passes"] = bool(sum(1 for h, x in res["horizons"].items() if x.get("beats_random")) >= 2
                         and any(res["horizons"].get(h, {}).get("beats_random") for h in (26, 52)))
    return res


def show(name, r):
    print(f"\n  {name}: entry {r['entry']}; {r['picks']} priced picks of {r['picks_listed']} listed; pool {r['pool']}; no price at entry: {r['dropped']['no_price']}")
    for h, x in r["horizons"].items():
        if not x["available"]:
            print(f"    {h:>2}w to {x['end']}: data do not reach it yet")
            continue
        p = x["percentile"]
        print(f"    {h:>2}w to {x['end']}: picks {x['pick_mean']*100:+7.2f}% (median {x['pick_median']*100:+6.2f}) vs random {x['random_mean']*100:+7.2f}% / matched {x['matched_mean']*100:+7.2f}%   "
              f"percentile mean {p['mean']:5.1f} med {p['median']:5.1f} | matched mean {p['mean_matched']:5.1f} med {p['median_matched']:5.1f}  "
              f"{'BEATS' if x['beats_random'] else 'no'}  ({x['stopped_early']} stopped early)")
    print(f"    -> {'PASSES' if r.get('passes') else 'no'}")


def main(mode: str, archive: str | None = None) -> None:
    if mode == "freeze":
        freeze(Path(archive))
        return
    frozen = load_frozen()
    names = {c: set(v["scores"]) for c, v in frozen.items()}
    picks = {c: cohort_picks(frozen, c) for c in SOURCES}
    # the Jensen file parsed English words as tickers: keep a name only if its recorded price is near Yahoo's close at the file's date
    symbols = set().union(*names.values())
    if mode == "smoke":
        symbols = set(sorted(symbols)[:300]) | picks["cecil_v1"]
    px = load_prices(symbols)
    if mode == "fetch":
        print(f"downloaded {len(px)} of {len(symbols)} symbols to {PRICE_START} .. {PRICE_END}")
        return
    last_day = px["SPY"].dates[-1]
    jen_px = frozen["jensen"]["price"]
    mismatched = set()
    for s, rec in jen_px.items():
        ser = px.get(s)
        if ser:
            c = ser.last_close_before("2025-09-20")
            if c and rec > 0 and abs(c / rec - 1) > RECORDED_PRICE_TOLERANCE:
                mismatched.add(s)
    print(f"  jensen names whose recorded price is more than {RECORDED_PRICE_TOLERANCE:.0%} off Yahoo's close (dropped as mis-parsed tickers): {len(mismatched)} of {len(jen_px)}")
    pools = {"threshold": names["threshold"], "sentinel": names["sentinel"], "jensen": names["jensen"] - mismatched,
             "elizabet": names["elizabet"], "cecil_v1": names["sentinel"]}
    picks["jensen"] -= mismatched
    top = {c: picks[c] for c in ("sentinel", "jensen", "elizabet")}
    overlap = {s for s in set().union(*top.values()) if sum(s in v for v in top.values()) >= 2}
    both = names["sentinel"] & names["jensen"] & names["elizabet"]
    cohorts = {c: (picks[c], pools[c], frozen[c]["entry"]) for c in SOURCES}
    cohorts["overlap"] = (overlap & both, both - mismatched, DERIVED["overlap"])
    result = {"registered": "d1ba76f", "last_price_day": last_day, "jensen_mismatched": len(mismatched), "cohorts": {}}
    for c, (pk, pool, entry) in cohorts.items():
        if mode == "smoke":
            pk, pool = {s for s in pk if s in px}, {s for s in pool if s in px}
        r = evaluate(c, pk, pool, entry, px, last_day, c)
        show(c, r)
        result["cohorts"][c] = r
    result["verdicts"] = {c: bool(r.get("passes")) for c, r in result["cohorts"].items()}
    print("\n  registered verdicts: " + "; ".join(f"{c} {'PASSES' if ok else 'no'}" for c, ok in result["verdicts"].items()))
    out = lab.CACHE / "pass22.smoke.json" if mode == "smoke" else lab.RESULTS / "pass22_frozen.json"
    with open(out, "w", encoding="ascii", newline="\n") as fh:
        json.dump(result, fh, indent=1, default=float)
        fh.write("\n")
    print(f"  wrote {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", nargs="?", default="run", choices=["freeze", "fetch", "run", "smoke"])
    ap.add_argument("--archive")
    a = ap.parse_args()
    main(a.mode, a.archive)
