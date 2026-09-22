#!/usr/bin/env python3
"""Add the engine Ophelia under the owner's "our own" sector map (Pass 10:
weekly correlation clusters, no human labels) to a live week's record, on
the 111. Prices are capped at the week's Monday; the clusters and the five
use nothing after the Friday before.

    python lab/live_ownmap.py 2026-09-21
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import live_week as lw  # noqa: E402
import pass4_marky as p4  # noqa: E402
import pass9_universe as p9  # noqa: E402
import pass10_sectors as p10  # noqa: E402

NAME = "Ophelia engine, our own map"


def main(label):
    U = p9.universes()
    names = U[p9.REFERENCE]
    W = lw._monday(label)
    real = lab.download
    lab.download = lambda tickers, adjusted, end, start: real(tickers, adjusted, min(end, W), start)
    try:
        tickers = sorted(set(names)) + lab.EXTRA
        adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, True, W, p4.HIST_START)).items()}
        weeks = [(label, W, None)]
        cm, off, dfn = p10.cluster_maps(names, adj, weeks)
        cal = lab.earnings_calendar(names)
        from scan_pipeline.utils import data_utils
        original = data_utils.SECTOR_MAP
        data_utils.SECTOR_MAP = p10.WeekMap(cm)
        try:
            knobs = dict(lab.VARIANTS3["base"], **{"ophelia.OFFENSIVE_SECTORS": p10.WeekSet(off),
                                                   "ophelia.DEFENSIVE_SECTORS": p10.WeekSet(dfn)})
            row = lab.run(verbose=False, knobs=knobs, weeks=weeks, earnings=cal, names=names)[0]
        finally:
            data_utils.SECTOR_MAP = original
    finally:
        lab.download = real
    black = lw._blackout(label, names)
    five = [t for t in row["proposals"]["Ophelia"] if t not in black][:5]
    lab._TAP["week"] = W
    clusters = {t: cm[W].get(t, "?") for t in five}
    sizes = {}
    for c in cm[W].values():
        sizes[c] = sizes.get(c, 0) + 1
    window = lw._add_variant(label, NAME, {
        "picks": five, "universe": "the 111", "clusters": clusters,
        "cluster_sizes": dict(sorted(sizes.items())),
        "rule": "Pass 10: the engine Ophelia's five with sectors replaced by weekly correlation clusters (k=11, 52 weeks)"})
    print(f"  {NAME}: {', '.join(f'{t} ({clusters[t]})' for t in five)}" + (f"  (scored from {window})" if window else ""))
    print(f"  clusters this week: {dict(sorted(sizes.items()))}")


if __name__ == "__main__":
    main(sys.argv[1])
