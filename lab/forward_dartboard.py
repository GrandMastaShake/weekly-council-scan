#!/usr/bin/env python3
"""Pass 34 A -- the dartboard, weekly.

For every closed week in portfolio/history/ not yet in lab/dartboard_ledger.json:
the official book's percentile among 2,000 random books at its own number of
names, weights and cash (lab basis: Monday open to Friday close, adjusted),
against the frozen universe and sector-matched. The first rows are Pass 33's,
copied as computed there. The ledger is append-only. Rewrites lab/DARTBOARD.md.

Registered in lab/README.md (Pass 34) before the first row.

    python lab/forward_dartboard.py
"""
from __future__ import annotations

import csv
import json
import math
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402

FULL_CSV = lab.LAB / "universe_sp500_full_2026-09-22.csv"
LEDGER = lab.LAB / "dartboard_ledger.json"
PAGE = lab.LAB / "DARTBOARD.md"
PASS33 = lab.RESULTS / "pass33_attribution.json"
BY_HAND = {"SYM": "Industrials", "ZS": "Information Technology"}
DRAWS = 2000
SEED = 20261116


def load_ledger():
    if LEDGER.exists():
        with open(LEDGER, encoding="utf-8") as fh:
            return json.load(fh)
    with open(PASS33, encoding="utf-8") as fh:
        p33 = json.load(fh)
    rows = [{"week": r["week"], "book": r["book"], "spy": r["spy"], "invested": r["invested"],
             "pct_frozen": r["pct_frozen"], "pct_sector": r["pct_sector"],
             "dart_frozen_mean": r["dart_frozen_mean"], "dart_sector_mean": r["dart_sector_mean"],
             "source": "Pass 33", "unmapped": []} for r in p33["rows"]]
    return {"registered": "lab/README.md, Pass 34 A", "rows": rows}


def score_week(d, sp, frozen):
    W = str(d["week"])
    day = date.fromisoformat(W)
    mon = (day - timedelta(days=day.weekday())).isoformat()
    picks = [p["ticker"] for p in d["positions"]]
    pool = sorted(set(frozen) | set(sp) | set(picks))
    start = (date.fromisoformat(mon) - timedelta(days=5)).isoformat()
    end = (date.fromisoformat(mon) + timedelta(days=8)).isoformat()
    df = lab.download(pool, True, end, start=start)
    bars = {t: lab.Series(rows) for t, rows in lab.bars_by_ticker(df).items()}
    rng = np.random.default_rng(SEED + int(W.replace("-", "")))
    book = d["weighted_return"] / 100.0
    ws = [p["weight"] for p in d["positions"]]
    fr = np.array([x for x in (bars[t].week_return(mon) for t in frozen if t in bars) if x is not None])
    d1 = np.array([float(np.dot(ws, fr[rng.choice(len(fr), len(ws), replace=False)])) for _ in range(DRAWS)])
    unmapped = [t for t in picks if t not in sp and t not in BY_HAND]
    pct_sector = dart_sector = None
    if not unmapped:
        d2 = np.zeros(DRAWS)
        for p in d["positions"]:
            g = sp.get(p["ticker"]) or BY_HAND[p["ticker"]]
            arr = np.array([x for x in (bars[t].week_return(mon) for t, s in sp.items() if s == g and t in bars)
                            if x is not None])
            d2 += p["weight"] * arr[rng.integers(0, len(arr), DRAWS)]
        pct_sector, dart_sector = float((d2 < book).mean()), float(d2.mean())
    return {"week": W, "book": book, "spy": d["spy_return"] / 100.0, "invested": float(sum(ws)),
            "pct_frozen": float((d1 < book).mean()), "pct_sector": pct_sector,
            "dart_frozen_mean": float(d1.mean()), "dart_sector_mean": dart_sector,
            "source": "forward_dartboard.py", "unmapped": unmapped,
            "logged_at": datetime.now().astimezone().isoformat(timespec="seconds")}


def page(rows):
    def z(xs):
        return (np.mean(xs) - 0.5) * math.sqrt(12 * len(xs)) if xs else float("nan")
    pf = [r["pct_frozen"] for r in rows]
    ps = [r["pct_sector"] for r in rows if r["pct_sector"] is not None]
    P = lambda x: "--" if x is None else f"{100 * x:+.2f}%"  # noqa: E731
    out = ["# The dartboard", "",
           "The official book's percentile among 2,000 random books at its own weights and cash, week by week",
           "(Pass 34 A; the first sixteen rows are Pass 33's). `lab/forward_dartboard.py` regenerates this page each",
           "Monday from `lab/dartboard_ledger.json`, which is append-only; edits by hand are overwritten.", "",
           f"Weeks: {len(rows)} ({rows[0]['week']} .. {rows[-1]['week']}).", "",
           "| | Mean percentile | z | Weeks |", "|---|---|---|---|",
           f"| Against the frozen universe | {100 * np.mean(pf):.0f} | {z(pf):+.2f} | {len(pf)} |",
           f"| Sector-matched | {100 * np.mean(ps):.0f} | {z(ps):+.2f} | {len(ps)} |", "",
           "z at or above +1.64 over at least 40 weeks would be the first evidence of selection skill; at or below",
           "-1.64, worse than chance; anything between is a dartboard. Under 40 weeks this page shows direction, not proof.",
           "", "| Week | Book | SPY | Invested | Random, frozen | Pct | Random, sector-matched | Pct |",
           "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        ps_ = "--" if r["pct_sector"] is None else f"{100 * r['pct_sector']:.0f}"
        out.append(f"| {r['week']} | {P(r['book'])} | {P(r['spy'])} | {100 * r['invested']:.0f}% | {P(r['dart_frozen_mean'])} | "
                   f"{100 * r['pct_frozen']:.0f} | {P(r['dart_sector_mean'])} | {ps_} |")
    bad = [(r["week"], r["unmapped"]) for r in rows if r.get("unmapped")]
    if bad:
        out += ["", "No sector for: " + "; ".join(f"{w} {', '.join(u)}" for w, u in bad) + " (sector-matched cell left empty)."]
    return "\n".join(out) + "\n"


def main():
    with open(FULL_CSV, encoding="ascii") as fh:
        sp = {r["ticker"]: r["gics_sector"] for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))}
    frozen = lab.frozen_universe()
    ledger = load_ledger()
    have = {r["week"] for r in ledger["rows"]}
    added = []
    for f in sorted(lab.HISTORY.glob("*.yaml")):
        with open(f, encoding="utf-8") as fh:
            d = yaml.safe_load(fh)
        if d.get("status") != "closed" or str(d["week"]) in have or not d.get("positions"):
            continue
        row = score_week(d, sp, frozen)
        ledger["rows"].append(row)
        added.append(row["week"])
    ledger["rows"].sort(key=lambda r: r["week"])
    with open(LEDGER, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ledger, fh, indent=1)
        fh.write("\n")
    text = page(ledger["rows"])
    with open(PAGE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(text)
    print("new rows:", added or "none")


if __name__ == "__main__":
    main()
