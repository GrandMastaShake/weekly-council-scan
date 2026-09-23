#!/usr/bin/env python3
"""Freeze the daily screen's universe for the lab: today's Nasdaq listing at
$300M to $10B and $3 or more (the screen's cap and price rules, without its
dollar-volume rule, which the lab applies point in time from the trailing
20 sessions). Writes lab/universe_smid_<date>.csv with source and fetch time
in its header. Names are on it because they are that size TODAY, so the
list carries survivorship; Pass 14 uses it for within-universe comparisons.

    python lab/fetch_smid.py
"""
from __future__ import annotations

import csv
import sys
from datetime import date, datetime
from pathlib import Path

LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB.parent / "screen"))
import daily_screen as ds  # noqa: E402

URL = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&download=true"
OUT = LAB / f"universe_smid_{date.today():%Y-%m-%d}.csv"


def main():
    d = ds.get(URL)
    rows = (d or {}).get("data", {}).get("rows", []) or []
    if len(rows) < 3000:
        sys.exit(f"listing came back with {len(rows)} rows; not writing")
    keep = []
    for r in rows:
        s = r.get("symbol", "")
        if not s or any(ch in s for ch in "^/ "):
            continue
        try:
            mc = float(r.get("marketCap") or 0)
            px = float(str(r.get("lastsale", "0")).replace("$", "").replace(",", ""))
        except ValueError:
            continue
        if ds.CAP_MIN <= mc <= ds.CAP_MAX and px >= ds.PRICE_MIN:
            keep.append((s, round(mc / 1e6), (r.get("sector") or "").strip(), (r.get("industry") or "").strip()))
    keep.sort()
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        fh.write(f"# source: {URL}\n# fetched: {datetime.now().astimezone().isoformat(timespec='seconds')}\n"
                 f"# rule: market cap {ds.CAP_MIN/1e6:.0f}M-{ds.CAP_MAX/1e9:.0f}B, price >= {ds.PRICE_MIN}; no volume rule\n")
        w = csv.writer(fh)
        w.writerow(["ticker", "cap_m", "sector", "industry"])
        w.writerows(keep)
    print(f"{len(keep)} names -> {OUT.name}")


if __name__ == "__main__":
    main()
