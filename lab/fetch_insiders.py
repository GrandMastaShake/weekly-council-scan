#!/usr/bin/env python3
"""Freeze insider purchases for the lab, from the SEC's quarterly Form 3/4/5
data sets (sec.gov, "Insider Transactions Data Sets"), 2024 Q3 to 2026 Q2.

A row is one open-market or private purchase (non-derivative table,
transaction code P, acquired) with a price, reported on an original Form 4
(amendments are skipped so nothing counts twice), not flagged as a 10b5-1
plan trade, whose filing names at least one reporting owner who is a
director or an officer. The owners column lists only those directors and
officers. The filing date is when the market could know it: EDGAR's day
closes at 10 pm ET, so a filing dated the Friday before a Monday is public
by that Monday.

Writes lab/insider_purchases_2024q3_2026q2.csv with the source and fetch
time in its header. The zips are cached in lab/cache/sec_form345
(gitignored); the SEC's filter refuses a User-Agent containing a URL, and
this one carries no personal contact.

    python lab/fetch_insiders.py
"""
from __future__ import annotations

import csv
import io
import sys
import time
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

LAB = Path(__file__).resolve().parent
CACHE = LAB / "cache" / "sec_form345"
OUT = LAB / "insider_purchases_2024q3_2026q2.csv"
UA = {"User-Agent": "weekly-council-scan research bot"}
PAGE = "https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets"
QUARTERS = {q: f"/files/structureddata/data/insider-transactions-data-sets/{q}_form345.zip"
            for q in ("2024q3", "2024q4", "2025q1", "2025q2", "2025q3", "2025q4", "2026q1")}
QUARTERS["2026q2"] = "/files/datastandardsinnovation/data/insider-transactions-data-sets/2026q2_form345.zip"
COLS = ["filing_date", "trans_date", "ticker", "issuer_cik", "owners", "roles", "titles",
        "shares", "price", "value", "ownership", "accession"]


def _iso(s):
    return datetime.strptime(s.strip(), "%d-%b-%Y").strftime("%Y-%m-%d") if s and s.strip() else ""


def _table(z, name):
    with z.open(name) as fh:
        yield from csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", errors="replace"),
                                  delimiter="\t", quoting=csv.QUOTE_NONE)


def fetch():
    CACHE.mkdir(parents=True, exist_ok=True)
    for q, path in QUARTERS.items():
        dest = CACHE / f"{q}_form345.zip"
        if not dest.exists():
            with urllib.request.urlopen(urllib.request.Request("https://www.sec.gov" + path, headers=UA),
                                        timeout=120) as r:
                data = r.read()
            with open(dest, "wb") as fh:
                fh.write(data)
            time.sleep(0.5)


def extract(z):
    subs = {}
    for s in _table(z, "SUBMISSION.tsv"):
        if s["DOCUMENT_TYPE"].strip() != "4":
            continue
        if s["AFF10B5ONE"].strip().lower() in ("1", "true"):
            continue
        t = s["ISSUERTRADINGSYMBOL"].strip().upper().replace(".", "-")
        if not t or t in ("NONE", "N/A", "NA"):
            continue
        subs[s["ACCESSION_NUMBER"]] = (s["FILING_DATE"], t, s["ISSUERCIK"].strip())
    owners = {}
    for o in _table(z, "REPORTINGOWNER.tsv"):
        rel = o["RPTOWNER_RELATIONSHIP"]
        if o["ACCESSION_NUMBER"] in subs and ("Director" in rel or "Officer" in rel):
            owners.setdefault(o["ACCESSION_NUMBER"], []).append(
                (o["RPTOWNERCIK"].strip(), rel.strip(), (o["RPTOWNER_TITLE"] or "").strip()))
    out = []
    for tr in _table(z, "NONDERIV_TRANS.tsv"):
        acc = tr["ACCESSION_NUMBER"]
        if acc not in owners or tr["TRANS_CODE"].strip() != "P" or tr["TRANS_ACQUIRED_DISP_CD"].strip() != "A":
            continue
        try:
            shares, price = float(tr["TRANS_SHARES"] or 0), float(tr["TRANS_PRICEPERSHARE"] or 0)
        except ValueError:
            continue
        if shares <= 0 or price <= 0:
            continue
        filed, ticker, cik = subs[acc]
        own = owners[acc]
        out.append({"filing_date": _iso(filed), "trans_date": _iso(tr["TRANS_DATE"]), "ticker": ticker,
                    "issuer_cik": cik, "owners": ";".join(o[0] for o in own), "roles": ";".join(o[1] for o in own),
                    "titles": ";".join(o[2] for o in own).replace(",", " "), "shares": round(shares, 2),
                    "price": round(price, 4), "value": round(shares * price, 2),
                    "ownership": tr["DIRECT_INDIRECT_OWNERSHIP"].strip(), "accession": acc})
    return out


def main():
    fetch()
    rows = []
    for q in QUARTERS:
        with zipfile.ZipFile(CACHE / f"{q}_form345.zip") as z:
            got = extract(z)
        print(f"  {q}: {len(got)} purchases", flush=True)
        rows.extend(got)
    rows.sort(key=lambda r: (r["filing_date"], r["ticker"], r["accession"]))
    with open(OUT, "w", encoding="ascii", errors="replace", newline="") as fh:
        fh.write(f"# source: {PAGE} (quarterly Form 3/4/5 data sets, {', '.join(QUARTERS)})\n"
                 f"# fetched: {datetime.now().astimezone().isoformat(timespec='seconds')}\n"
                 "# rows: original Form 4, code P, acquired, priced, not 10b5-1, a director or officer among the owners\n")
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} purchases, {len({r['ticker'] for r in rows})} tickers -> {OUT.name} "
          f"({OUT.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
