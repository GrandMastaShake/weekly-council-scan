# Backfilling the 44 new universe names

> **Status: done.** Run 2026-08-26 via the Actions workflow with `--merge`.
> The panel went from 30,915 to 35,571 series -- every week 289 -> 332 (43 new
> plus SPCX, correctly absent pre-IPO) -- and `2026-08-21.corrected.json`
> reached 330. `panel_guard` reported 107 files grew and none lost series.
> This document is kept for the rationale and for the next universe expansion;
> the commands below are the corrected ones.

The universe went from 277 to 321 on 2026-08-25. The 44 added names have no
history in `data/weekly/`. This fills it.

## Why not just import the spreadsheet

`Watchlist_110_Weekly_History_1Year.xlsx` has all 110 names with 52 weekly
bars, and it agrees with `data/weekly/` to 0.0000% on the most recent week.
It cannot be used.

The two sources diverge monotonically going backwards: 0% recently, 1.56%
median a year ago. The split is exact:

    NVDA  AMZN  TSLA  ISRG  VRTX  AMD    +0.00% to +0.13%
    XOM   +2.24%   PEP  +3.96%   PSA  +4.15%
    D     +4.42%   SPG  +4.76%   O    +5.48%   PGR  +6.50%

Non-payers agree exactly; dividend payers diverge in proportion to a year of
accumulated yield. `backfill_weekly.py` uses `yfinance auto_adjust=True`, so
`data/weekly/` is total-return adjusted. The spreadsheet is price-only.

Splicing them puts one basket on two bases. Breadth would read as though the
dividend payers underperformed by roughly 2.7 points of phantom dispersion
over a year -- systematic, not noise, and worst in Utilities, Real Estate,
Staples and Energy. It would look like a signal.

So the 44 go through the same code path as the other 277.

## Run it -- easiest path: GitHub Actions

Actions -> "Backfill weekly panel" -> Run workflow:

    tickers  ALB,BKNG,BLFS,CALM,CCJ,CEG,COP,CRSP,CRWD,CVNA,DDOG,DIS,FIVE,FIZZ,FSLR,HIMS,IMAX,INOD,LNG,LYV,MLM,MOD,MP,MTCH,OKLO,ORA,PLTR,PM,RDDT,RKLB,SCHW,SM,SOFI,SOUN,SPCX,SPOT,SSD,STZ,TMUS,TSM,TTWO,ULTA,UMH,VST
    start    2024-08-09
    end      2026-08-21
    dry_run  true   (then re-run with false)

Named tickers are merged in; the workflow passes `--merge` for you.

The runner has the network access that agent sandboxes do not, and the workflow
rebuilds corrections and runs truth_check before committing. It prints the
per-file series counts before and after so the correction-shadowing failure is
visible rather than silent.

## Or run it locally

Windows, from the repo root. Needs network; the run takes a few minutes.

    python scripts\backfill_weekly.py ^
      --out data ^
      --start 2024-08-09 ^
      --end 2026-08-21 ^
      --only ALB,BKNG,BLFS,CALM,CCJ,CEG,COP,CRSP,CRWD,CVNA,DDOG,DIS,FIVE,FIZZ,FSLR,HIMS,IMAX,INOD,LNG,LYV,MLM,MOD,MP,MTCH,OKLO,ORA,PLTR,PM,RDDT,RKLB,SCHW,SM,SOFI,SOUN,SPCX,SPOT,SSD,STZ,TMUS,TSM,TTWO,ULTA,UMH,VST ^
      --merge

`--merge` adds the named tickers to each existing week and leaves every other
series, the special blocks and the file-level adjustment anchor alone. Add
`--dry-run` first to see the plan.

**This document said `--force` until 2026-08-26, on the reasoning that "the
target weekly files already exist; the run adds the new names to `series` in
each". That was wrong, and it is the sentence that emptied the panel.**
`--force` writes a WHOLE file from the ticker set it was given, so with
`--only` it deletes every name outside that set -- 287 series became 44 across
107 files, and the workflow reported success. `backfill_weekly.py` now refuses
`--only` with `--force` outright and names this incident when it does.

`--force` is still correct for its actual purpose: a full-universe rewrite with
no `--only`, where writing each whole file is the operation you want.

## Rebuild corrections -- REQUIRED, do not skip

    python scripts\rebuild_corrections.py

A correction file is a full copy of its base plus `corrects` and `reason`, so
it is a snapshot and goes stale the moment the base changes. `2026-08-21` has
one. The backfill writes the 44 new names into `2026-08-21.json`, but readers
prefer `2026-08-21.corrected.json`, which would still hold the old 286-name
series -- the new tickers would be silently invisible for that week and every
sector's coverage would stay short forever.

This was caught by running the pipeline against a simulated backfill, not by
reading the code. Run it after every backfill that touches a corrected week.

It aborts rather than guessing if a dropped ticker no longer has volume 0 in
the base, since that would mean the provider restated and the correction needs
a human.

## Verify afterwards

    python scripts\truth_check.py

Expected:

- SPCX appears in `missing` for every week before 2026-06-12, reason noting
  pre-IPO. It listed on Nasdaq that day. Do not treat this as a failure --
  the spreadsheet independently shows exactly 11 bars for SPCX, first one
  2026-06-12, which corroborates it.
- The other 43 should be present in every week from 2024-08-09 unless they
  were also not yet trading.
- `data/weekly/2026-08-21.corrected.json` should carry roughly 330 series
  entries, not 286. If it still says 286, `rebuild_corrections.py` did not run.
- Spot-check any dividend payer among the 44 (PM, STZ, TMUS) against the
  spreadsheet: the backfilled value should be BELOW the spreadsheet's for
  older weeks, by roughly the accumulated yield. If it matches exactly, the
  adjustment did not apply and the run should be discarded.

## Known defects in the spreadsheet

Recorded here because it stays useful as an independent price-basis
cross-check even though it cannot be imported.

- NVDA carries a stray `2026-08-24` bar. That is a Monday, volume 57.8M
  against a ~98M norm: a forming bar, the exact case `truth_check v6.1`
  was written to skip. It is the only ticker with 53 rows.
- AVB is missing `2026-08-21` and has 51 rows.
- Three week-endings are labelled with the actual Thursday session
  (2026-04-02, 2026-06-18, 2026-07-02) where `data/weekly/` uses the nominal
  Friday and records `session_note`. Same bars, different label.
- `DivYield_%` in the Enhanced workbook is populated for 69 of 110 names.
  Do not use that column.
