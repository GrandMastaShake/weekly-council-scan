#!/usr/bin/env python3
"""Forward record -- every registered design, scored on weeks it never saw.

Each Monday (scheduled task 8) this replays every design registered in the
Testing Room on the Council weeks that closed after it was registered, next
to the real Council's official book, SPY and random picks, and regenerates
lab/FORWARD.md and lab/results/forward.json from scratch. Nothing here can
have been tuned on these weeks: they had not happened when the designs were
written down.

"production" is the engine code as it stands at run time, earnings blackout
included; every other design is production with its knobs on top. The real
Council's book is the official record -- the engines' picks after the LLM
layer's vetoes and trims.

    python lab/forward.py
"""
from __future__ import annotations

import json
import statistics
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402

# (name, knobs, registered Monday, where it came from)
REGISTRY = [
    ("production",    lab.VARIANTS3["base"],          "2026-09-21", "engines as live"),
    ("no-screen",     lab.VARIANTS3["no-screen"],     "2026-09-21", "Pass 3, H3"),
    ("O-last",        lab.VARIANTS3["O-last"],        "2026-09-21", "Pass 3, H2"),
    ("M-skip",        lab.VARIANTS3["M-skip"],        "2026-09-21", "Pass 3, H1"),
    ("O-last+M-skip", lab.VARIANTS3["O-last+M-skip"], "2026-09-21", "Pass 3"),
    ("O-rs",          lab.VARIANTS["O-rs"],           "2026-09-21", "Pass 2"),
    ("O-rs+",         lab.VARIANTS["O-rs+"],          "2026-09-21", "Pass 2"),
    ("M-15",          lab.VARIANTS["M-15"],           "2026-09-21", "Pass 2"),
    ("M-0",           lab.VARIANTS["M-0"],            "2026-09-21", "Pass 2"),
    ("O-rs+M-15",     lab.VARIANTS["O-rs+M-15"],      "2026-09-21", "Pass 2"),
    ("no-Ophelia",    lab.VARIANTS["no-Ophelia"],     "2026-09-21", "Pass 2, reference"),
    ("Ophelia-solo",  {"solo": "Ophelia"},            "2026-09-22", "Pass 9b, the engine alone"),
]
PAGE = lab.LAB / "FORWARD.md"
DATA = lab.RESULTS / "forward.json"


def _pct(x, digits=2):
    return "--" if x is None else f"{x * 100:+.{digits}f}%"


def _summary(rows, prod_rows):
    base = {r["week"]: r["book_ret"] for r in prod_rows}
    diffs = [r["book_ret"] - base[r["week"]] for r in rows if r["week"] in base]
    cum, dd = lab._curve([r["book_ret"] for r in rows])
    return {
        "weeks": len(rows),
        "mean_alpha": statistics.fmean(r["alpha"] for r in rows),
        "alpha_t": lab._tstat([r["alpha"] for r in rows]),
        "mean_vs_production": statistics.fmean(diffs) if diffs else None,
        "weeks_better_than_production": sum(1 for d in diffs if d > 0),
        "mean_vs_random": statistics.fmean(r["vs_random"] for r in rows),
        "mean_pctile_vs_random": statistics.fmean(r["pctile_vs_random"] for r in rows),
        "cumulative": cum, "max_drawdown": dd,
    }


def build(weeks, results, generated):
    prod = results["production"]
    council = [{"week": r["week"], "book_ret": r["council_ret"], "alpha": r["council_alpha"],
                "invested": r["council_invested"]} for r in prod]
    base = {r["week"]: r["book_ret"] for r in prod}
    c_diffs = [c["book_ret"] - base[c["week"]] for c in council]
    c_cum, c_dd = lab._curve([c["book_ret"] for c in council])
    real = {"weeks": len(council),
            "mean_alpha": statistics.fmean(c["alpha"] for c in council),
            "alpha_t": lab._tstat([c["alpha"] for c in council]),
            "mean_vs_production": statistics.fmean(c_diffs),
            "weeks_better_than_production": sum(1 for d in c_diffs if d > 0),
            "cumulative": c_cum, "max_drawdown": c_dd}
    designs = {}
    for name, knobs, registered, source in REGISTRY:
        rows = results.get(name)
        if not rows:
            continue
        designs[name] = {"knobs": knobs, "registered": registered, "source": source,
                         "summary": _summary(rows, prod),
                         "weekly": [{"week": r["week"], "book_ret": r["book_ret"], "alpha": r["alpha"],
                                     "pctile_vs_random": r["pctile_vs_random"],
                                     "book": [(b["ticker"], b["weight"]) for b in r["book"]],
                                     "earnings_skipped": r["earnings_skipped"]} for r in rows]}
    spy = {r["week"]: r["spy_ret"] for r in prod}

    lines = [
        "# Forward record",
        "",
        "Every design registered in the Testing Room, scored on Council weeks that closed",
        "after it was registered -- weeks it could not have been tuned on. `lab/forward.py`",
        "regenerates this page each Monday (scheduled task 8); edits by hand are overwritten.",
        "Scoring is the lab's: Monday open to Friday close, dividend-adjusted, cash earns zero.",
        "",
        f"Last run: {generated}. Forward weeks: {len(weeks)} "
        f"({', '.join(w[0] for w in weeks)}).",
        "",
        "| Design | Source | Weeks | Alpha / wk | vs production | Weeks better | vs random | Cumulative | Max DD |",
        "|---|---|---|---|---|---|---|---|---|",
        f"| **Real Council** (official book) | engines + LLM layer | {real['weeks']} | "
        f"{_pct(real['mean_alpha'])} | {_pct(real['mean_vs_production'])} | "
        f"{real['weeks_better_than_production']}/{real['weeks']} | -- | {_pct(real['cumulative'], 1)} | "
        f"{_pct(real['max_drawdown'], 1)} |",
    ]
    for name, d in designs.items():
        s = d["summary"]
        vs_prod = "--" if name == "production" else _pct(s["mean_vs_production"])
        better = "--" if name == "production" else f"{s['weeks_better_than_production']}/{s['weeks']}"
        lines.append(f"| {name} | {d['source']} | {s['weeks']} | {_pct(s['mean_alpha'])} | {vs_prod} | "
                     f"{better} | {_pct(s['mean_vs_random'])} ({s['mean_pctile_vs_random']:.0%}) | "
                     f"{_pct(s['cumulative'], 1)} | {_pct(s['max_drawdown'], 1)} |")
    names = list(designs)
    lines += ["", "## By week (book return)", "",
              "| Week | SPY | Real Council | " + " | ".join(names) + " |",
              "|---" * (3 + len(names)) + "|"]
    for w in weeks:
        label = w[0]
        cells = []
        for n in names:
            hit = [x for x in designs[n]["weekly"] if x["week"] == label]
            cells.append(_pct(hit[0]["book_ret"]) if hit else "--")
        c = [x for x in council if x["week"] == label]
        lines.append(f"| {label} | {_pct(spy.get(label))} | {_pct(c[0]['book_ret']) if c else '--'} | "
                     + " | ".join(cells) + " |")
    lines += ["",
              "A five-name weekly book moves about 1.7 points a week against SPY, so a design needs",
              "roughly 40 forward weeks before its mean says much (lab/README.md, \"What nine weeks",
              "can and cannot say\"). Read this page for direction and for designs that break, not",
              "for proof. \"production\" is today's engine code replayed, so it follows every",
              "change to production; the Real Council row is what was actually booked.",
              ""]
    return "\n".join(lines), {"generated": generated, "weeks": [w[0] for w in weeks],
                              "real_council": {"summary": real, "weekly": council},
                              "designs": designs}


def main():
    today = date.today()
    last_friday = today - timedelta(days=(today.weekday() - 4) % 7 or 7)
    first = min(r[2] for r in REGISTRY)
    weeks = [w for w in lab.council_weeks(last_friday.strftime("%Y-%m-%d")) if w[1] >= first]
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    lab.RESULTS.mkdir(parents=True, exist_ok=True)
    if not weeks:
        page = ("# Forward record\n\nNo registered design has a closed forward week yet: the first "
                f"is the week of {first}, scored once it closes and the next session archives it.\n\n"
                f"Last run: {generated}.\n")
        data = {"generated": generated, "weeks": [], "real_council": None, "designs": {}}
    else:
        from scan_pipeline.config.tickers import STOCK_UNIVERSE
        cal = lab.earnings_calendar(sorted(set(STOCK_UNIVERSE)), max_age_days=6)
        start = lab._plus(weeks[0][1], -100)
        results = {}
        for name, knobs, registered, _ in REGISTRY:
            wk = [w for w in weeks if w[1] >= registered]
            if wk:
                results[name] = lab.run(verbose=False, knobs=knobs, weeks=wk, start=start, earnings=cal)
        page, data = build(weeks, results, generated)
        # Each Monday downloads one more week; drop this run's older downloads
        # (the Pass 1-3 caches have other start dates and are kept).
        end = lab._plus(weeks[-1][1], 5)
        for old in lab.CACHE.glob(f"daily_*_{start}_*.pkl"):
            if f"_{end}_" not in old.name:
                old.unlink()
    with open(PAGE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)
    with open(DATA, "w", encoding="ascii", newline="\n") as fh:
        json.dump(data, fh, indent=1, default=float)
        fh.write("\n")
    print(page)


if __name__ == "__main__":
    main()
