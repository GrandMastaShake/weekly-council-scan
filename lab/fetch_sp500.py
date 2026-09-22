#!/usr/bin/env python3
"""Fetch today's S&P 500 constituents (ticker, GICS sector) from Wikipedia and
write lab/universe_sp500_<date>.csv with the source URL and fetch time in its
header. Today's list has survivorship bias (names are in it because they
rose into it); Pass 9 uses it for within-universe comparisons only.

    python lab/fetch_sp500.py          # ticker, gics_sector
    python lab/fetch_sp500.py dates    # also the index's "Date added", to universe_sp500_added_<date>.csv
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


def main(dates=False):
    import pandas as pd
    req = urllib.request.Request(URL, headers={"User-Agent": "weekly-council-scan lab (research; contact via GitHub)"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        html = resp.read().decode("utf-8")
    tables = pd.read_html(io.StringIO(html))
    table = next(t for t in tables if "Symbol" in t.columns and "GICS Sector" in t.columns)
    cols = ["ticker", "gics_sector"] + (["date_added"] if dates else [])
    rows = []
    for _, r in table.iterrows():
        row = [str(r["Symbol"]).strip().replace(".", "-"), str(r["GICS Sector"]).strip()]
        if dates:
            added = str(r.get("Date added", "")).strip()
            row.append(added[:10] if added[:4].isdigit() else "")     # "1957-03-04"; blank when unknown
        rows.append(tuple(row))
    rows = sorted(set(rows))
    out = OUT.with_name(OUT.name.replace("sp500_", "sp500_added_")) if dates else OUT
    with open(out, "w", encoding="ascii", newline="") as fh:
        fh.write(f"# source: {URL}\n# fetched: {datetime.now().astimezone().isoformat(timespec='seconds')}\n")
        w = csv.writer(fh)
        w.writerow(cols)
        w.writerows(rows)
    sectors = {}
    for row in rows:
        sectors[row[1]] = sectors.get(row[1], 0) + 1
    print(f"{len(rows)} names -> {out.name}")
    for s, n in sorted(sectors.items(), key=lambda kv: -kv[1]):
        print(f"  {s:<24}{n:>4}")
    if dates:
        known = [r[2] for r in rows if r[2]]
        print(f"  date added known for {len(known)} of {len(rows)}; added on or after 2024-09-09: "
              f"{sum(1 for d in known if d >= '2024-09-09')}")
    return 0


if __name__ == "__main__":
    sys.exit(main(dates=sys.argv[1:] == ["dates"]))
