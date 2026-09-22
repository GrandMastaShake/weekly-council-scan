#!/usr/bin/env python3
"""Fetch today's S&P 500 constituents (ticker, GICS sector) from Wikipedia and
write lab/universe_sp500_<date>.csv with the source URL and fetch time in its
header. Today's list has survivorship bias (names are in it because they
rose into it); Pass 9 uses it for within-universe comparisons only.

    python lab/fetch_sp500.py
"""
from __future__ import annotations

import csv
import io
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path

URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
OUT = Path(__file__).resolve().parent / f"universe_sp500_{date.today():%Y-%m-%d}.csv"


def main():
    import pandas as pd
    req = urllib.request.Request(URL, headers={"User-Agent": "weekly-council-scan lab (research; contact via GitHub)"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        html = resp.read().decode("utf-8")
    tables = pd.read_html(io.StringIO(html))
    table = next(t for t in tables if "Symbol" in t.columns and "GICS Sector" in t.columns)
    rows = [(str(r["Symbol"]).strip().replace(".", "-"), str(r["GICS Sector"]).strip())
            for _, r in table.iterrows()]
    rows = sorted(set(rows))
    with open(OUT, "w", encoding="ascii", newline="") as fh:
        fh.write(f"# source: {URL}\n# fetched: {datetime.now().astimezone().isoformat(timespec='seconds')}\n")
        w = csv.writer(fh)
        w.writerow(["ticker", "gics_sector"])
        w.writerows(rows)
    sectors = {}
    for _, s in rows:
        sectors[s] = sectors.get(s, 0) + 1
    print(f"{len(rows)} names -> {OUT.name}")
    for s, n in sorted(sectors.items(), key=lambda kv: -kv[1]):
        print(f"  {s:<24}{n:>4}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
