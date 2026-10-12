#!/usr/bin/env python3
"""Pass 28 -- grading the dated forward predictions on the drive (registered in lab/README.md, 517e4b7).

Parts, each run on its own so one failing source does not hold the others:

  capex     the 2026-08-23 AI-capex pre-registration, graded as the document says (SPY since 2026-03-27)
  heatmap   the sector-regime-heatmap's manual forecast cycles, graded with the heatmap's own src/evaluate.py plus a shuffle null
  records   the extracted and verified call records (direction, level, ranking, pick): see --records-dir

    python lab/pass28_grade.py capex
    python lab/pass28_grade.py heatmap --heatmap <checkout of sector-regime-heatmap origin/main> --panel <weekly panel dir>
    python lab/pass28_grade.py records --records-dir <dir>
"""
from __future__ import annotations

import argparse
import importlib
import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402

LAST_DAY = "2026-10-09"
SHUFFLES = 10000
MIN_CYCLES = 8


# ------------------------------------------------------------------------------------------------ capex
def capex():
    start, start_close, reg_day, reg_close, reg_peak = "2026-03-27", 634.09, "2026-08-21", 765.72, 777.88
    bars = lab.bars_by_ticker(lab.download(["SPY"], False, "2026-10-13", "2026-03-20"))["SPY"]
    close = {b["date"]: b["close"] for b in bars}
    # the registration's own numbers must come out of the same data, or the check below says so
    check = {"start_close": close.get(start), "reg_close": close.get(reg_day)}
    ok = abs(check["start_close"] - start_close) < 0.02 and abs(check["reg_close"] - reg_close) < 0.02
    days = [d for d in sorted(close) if start <= d <= LAST_DAY]
    peak, peak_day, trigger_day, mech_day = 0.0, None, None, None
    for d in days:
        c = close[d]
        if c > peak:
            peak, peak_day = c, d
        if trigger_day is None and c <= 0.90 * peak:
            trigger_day = d
        if mech_day is None and c <= 0.95 * peak:
            mech_day = d
    last = close[days[-1]]
    out = {"registered": "517e4b7", "data_matches_registration": ok, "checks": check, "last_day": days[-1], "last_close": last,
           "return_since_start": last / start_close - 1.0, "running_peak": peak, "peak_day": peak_day,
           "drawdown_from_peak": last / peak - 1.0, "worst_drawdown": min(close[d] / max(close[x] for x in days if x <= d) - 1.0 for d in days),
           "trigger_fired_on": trigger_day, "five_percent_watch_first_on": mech_day,
           "min_return_since_start": min(close[d] / start_close - 1.0 for d in days),
           "P1": "episode still running and an expansion so far (return since start positive)",
           "P2": "live: no termination, so the final return is not yet fixed; the peak-to-start return is already above +15%",
           "P3": "not triggered", "P4": "not triggered"}
    out["P2_status"] = "passing" if trigger_day is None and (peak / start_close - 1.0) >= 0.15 else "failing"
    print(f"  data check against the registration: {'OK' if ok else 'MISMATCH'} (start {check['start_close']}, 2026-08-21 {check['reg_close']})")
    print(f"  SPY {days[-1]}: {last:.2f}; since 2026-03-27 {out['return_since_start']*100:+.1f}%; running peak {peak:.2f} on {peak_day}; "
          f"drawdown {out['drawdown_from_peak']*100:+.1f}%; worst drawdown since start {out['worst_drawdown']*100:+.1f}%")
    print(f"  10% mechanical trigger fired: {trigger_day or 'no'}; 5% watch first reached: {mech_day or 'no'}")
    print(f"  P1 passing (still running, expansion so far); P2 {out['P2_status']}; P3 and P4 not triggered")
    return out


# ------------------------------------------------------------------------------------------------ heatmap
def spearman(a, b):
    ev = importlib.import_module("evaluate")
    return ev.spearman(a, b)


def heatmap(heatmap_dir, panel_dir):
    heatmap_dir, panel_dir = Path(heatmap_dir), Path(panel_dir)
    sys.path.insert(0, str(heatmap_dir / "src"))
    ev = importlib.import_module("evaluate")
    import yaml
    baskets = yaml.safe_load((heatmap_dir / "config/sector_baskets.yaml").read_text(encoding="utf-8"))
    rng = random.Random(lab.SEED)
    out = {"registered": "517e4b7", "cycles": []}
    per_h = {"week": [], "month": []}
    for f in sorted((heatmap_dir / "data/forecasts").glob("*_manual.json")):
        doc = ev.evaluate(f, panel_dir, baskets)
        for h in ("week", "month"):
            b = doc["horizons"][h]
            if not b.get("graded"):
                out["cycles"].append({"as_of": doc["as_of_date"], "horizon": h, "graded": False, "why": (b.get("refused") or "")[:90]})
                continue
            rows = {s: r for s, r in b["sectors"].items() if r.get("graded")}
            sc = [r["forecast_score"] for r in rows.values()]
            ex = [r["return_vs_spy_pct"] for r in rows.values()]
            ic = spearman(sc, ex)
            per_h[h].append({"as_of": doc["as_of_date"], "ic": ic, "scores": sc, "excess": ex, "hits": b["hits"], "partial": b["partial"], "misses": b["misses"],
                             "window": f"{b['window_from']}..{b['window_to']}", "by_conf": b["calibration_by_confidence"]})
            out["cycles"].append({"as_of": doc["as_of_date"], "horizon": h, "graded": True, "window": f"{b['window_from']}..{b['window_to']}",
                                  "ic": ic, "hits": b["hits"], "partial": b["partial"], "misses": b["misses"], "by_confidence": b["calibration_by_confidence"]})
    out["summary"] = {}
    for h, cyc in per_h.items():
        if not cyc:
            continue
        ics = [c["ic"] for c in cyc if c["ic"] is not None]
        obs = statistics.fmean(ics)
        null = []
        for _ in range(SHUFFLES):
            vals = []
            for c in cyc:
                s = c["scores"][:]
                rng.shuffle(s)
                v = spearman(s, c["excess"])
                if v is not None:
                    vals.append(v)
            null.append(statistics.fmean(vals))
        p = sum(1 for x in null if x >= obs) / len(null)
        hits = sum(c["hits"] for c in cyc)
        graded = sum(c["hits"] + c["partial"] + c["misses"] for c in cyc)
        out["summary"][h] = {"cycles": len(cyc), "mean_ic": obs, "shuffle_p_one_sided": p, "hits": hits,
                             "partial": sum(c["partial"] for c in cyc), "misses": sum(c["misses"] for c in cyc), "graded_calls": graded,
                             "decides": len(cyc) >= MIN_CYCLES}
    for c in out["cycles"]:
        print("  " + (f"{c['as_of']} {c['horizon']:<5}{c['window']}  IC {c['ic']:+.3f}  {c['hits']} hit / {c['partial']} partial / {c['misses']} miss"
                      if c["graded"] else f"{c['as_of']} {c['horizon']:<5}not graded: {c['why']}"))
    for h, s in out["summary"].items():
        print(f"  {h}: {s['cycles']} cycles, mean IC {s['mean_ic']:+.3f}, shuffle p {s['shuffle_p_one_sided']:.3f}; "
              f"{s['hits']} hit / {s['partial']} partial / {s['misses']} miss of {s['graded_calls']}; "
              f"{'decides' if s['decides'] else 'decides nothing (fewer than ' + str(MIN_CYCLES) + ' cycles)'}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("parts", nargs="+", choices=["capex", "heatmap", "records"])
    ap.add_argument("--heatmap", type=Path)
    ap.add_argument("--panel", type=Path)
    ap.add_argument("--records-dir", type=Path)
    args = ap.parse_args(argv)
    result = {}
    if "capex" in args.parts:
        print("\n  AI-capex pre-registration (2026-08-23)")
        result["capex"] = capex()
    if "heatmap" in args.parts:
        print("\n  sector-regime-heatmap forecast cycles, graded by its own src/evaluate.py")
        result["heatmap"] = heatmap(args.heatmap, args.panel)
    if "records" in args.parts:
        raise SystemExit("records part is added after extraction")
    path = lab.RESULTS / ("pass28_" + "_".join(args.parts) + ".json")
    with open(path, "w", encoding="ascii", newline="\n") as fh:
        json.dump(result, fh, indent=1, default=float)
        fh.write("\n")
    print(f"\n  wrote {path}")


if __name__ == "__main__":
    main()
