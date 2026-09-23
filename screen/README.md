# The daily screen

The owner's small and mid-cap setup finder (2026-09-23): names in a rising
120-day channel that have pulled back to the channel's lower half, with the
MACD histogram crossing up or turning, sorted by how much overhead supply
sits above them ("clean air", Alex's rule). Tier A is a clean setup with
clean air; B a clean setup with overhead in the way; C the almost-there
names under $50. Rate-sensitive names are excluded; biotech is flagged.

- `daily_screen.py` runs it. Standard library only. `--force` runs on a
  weekend; `--date YYYY-MM-DD` stamps a re-run by hand.
- `.github/workflows/daily-screen.yml` runs it weekdays at 12:00 UTC, before
  the US open, and commits the day's `reports/screen_<date>.csv` and `.html`
  plus `reports/first_seen.json` (the day each name first appeared).
- Prices are the prior close. Never run it during the session: the source
  includes the forming day.
- The run fails, and commits nothing, when the universe download fails,
  when it comes back with fewer than 1,000 names (mid-session the listing's
  volume is the forming day's, and the dollar-volume filter keeps ~400 names
  instead of ~1,800), or when prices cover less than half the universe. A
  missing day in `reports/` means the sources did not answer that morning,
  not a quiet market. `--force` skips the weekend and universe checks for a
  smoke test; never use it for the record.
- The Monday report is the weekly screen: its prices are Friday's close, so
  it is the list a Monday Council could read. The Testing Room replays the
  same rules on Friday closes to test them as Marky's chair (Pass 14).

Every committed report is a point-in-time record. The Testing Room
(`lab/`) scores them once the record has enough days: entry at the next
open, the 40-day low as the exit, against random names from the same
screened universe. Until then the reports are a watchlist, not a verdict.
Chart-only reads: check catalysts and the daily chart before acting.
