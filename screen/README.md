# The Butterfly Net

The owner's small and mid-cap setup finder (2026-09-23), named the Butterfly
Net on 2026-09-24: names in a rising 120-day channel that have pulled back
into the channel's lower half, with the MACD histogram crossing up or
turning, sorted by how much overhead supply sits above them ("clean air",
Alex's rule). Tier A is a clean setup with clean air; B a clean setup with
overhead in the way; C the almost-there names under $50. Rate-sensitive
names are excluded; biotech is flagged.

## When it runs, and what a report means

- `.github/workflows/daily-screen.yml` casts the net on weekday evenings
  after the US close, for the next session: 7:17 PM ET with a retry at
  9:43 PM (an hour earlier in winter). Friday evening's report is Monday's.
- A report dated D, `reports/screen_D.csv` and `.html`, is the list for the
  session of D, built on closes through the session before it. Each report
  says so in its first line.
- The script refuses to run while the session is open (9:30 to 16:00 ET on a
  weekday) and fails the run, which GitHub reports. It drops any daily bar
  that has not closed, and it does not redo a report that already exists.
- It fails, and commits nothing, when the universe download fails, when the
  universe comes back under 1,000 names (the listing's volume is partial),
  or when prices cover less than half of it. A missing day means the
  sources did not answer, not a quiet market.

## Where to see it

- The run page on GitHub (Actions, "Butterfly Net") shows the day's hits as
  tables.
- `reports/latest.html` is always the newest report; `reports/runs.json`
  lists every run: the session it was for, when it ran, whose closes it
  used, the universe and the hits.
- `python screen/daily_screen.py` runs it by hand: after the close it builds
  the next session's report, before the open today's. `--force` runs in the
  session or over an existing report, for a smoke test only; `--date
  YYYY-MM-DD` stamps a re-run.

## The record

Every committed report is a point-in-time record. The Testing Room (`lab/`)
scores them once there are enough of them: entry at the session's open, the
owner's exits beside (Passes 15 to 18), against random names from the same
screened universe. Until then the reports are a watchlist, not a verdict.
Chart-only reads: check catalysts and the daily chart before acting.

- **2026-09-23**: the owner's own run before the open, seeded into the
  repo; closes through 2026-09-22.
- **2026-09-24**: GitHub started the morning schedule five hours late
  (17:00 UTC, 1 PM ET), so this report screened **intraday prices** and a
  part-day volume listing, while its page said "the prior close". It is kept
  as the record of what the run produced, and `runs.json` marks it: not a
  pre-open list, and not to be scored. The evening schedule replaced the
  morning one that day.
