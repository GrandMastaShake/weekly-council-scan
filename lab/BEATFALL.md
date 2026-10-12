# Beat-then-fall: the corrected contrast, forward

Registered 2026-10-12 as Pass 30 (`lab/README.md`, 36545ad). Flagged beats (a positive surprise after 8 or more positive quarters) against the other beats of the same reaction week, on the five-day market-adjusted return R5, for reports with a reaction day on or after 2026-07-06. `lab/forward_beatfall.py` rebuilds this page from the append-only `lab/beatfall_events.json`; edits by hand are overwritten.

Last run: 2026-10-12 12:13. Latest bar: 2026-10-12. Events in the ledger: 495.

**Status: too early (5 qualifying weeks; 12 are needed).** Mean weekly gap +2.64% (Newey-West t +8.15), halves +1.80% / +3.19%, median +2.60%.

| Reaction week | Events | Flagged beats | Other beats | R5 gap (flagged minus other beats) | R1 gap | Versus all other events | D20 gap |
|---|---|---|---|---|---|---|---|
| 2026-07-13 | 30 | 12 | 17 | +1.01% | +1.91% | +1.10% | -0.16% |
| 2026-07-20 | 85 | 26 | 45 | +2.60% | +0.64% | +3.35% | +0.37% |
| 2026-07-27 | 174 | 56 | 93 | +4.30% | +2.57% | +4.39% | +1.33% |
| 2026-08-03 | 133 | 47 | 67 | +3.69% | +2.85% | +3.65% | +0.02% |
| 2026-08-24 | 19 | 7 | 12 | +1.59% | +6.61% | +1.59% | -8.96% |

Weeks below the floors (not counted): 2026-07-06 (2 events, 0 flagged, 1 other beats); 2026-08-10 (14 events, 7 flagged, 6 other beats); 2026-08-17 (12 events, 5 flagged, 7 other beats); 2026-08-31 (6 events, 3 flagged, 3 other beats); 2026-09-07 (6 events, 3 flagged, 2 other beats); 2026-09-14 (1 events, 0 flagged, 0 other beats); 2026-09-21 (6 events, 1 flagged, 4 other beats); 2026-09-28 (7 events, 5 flagged, 2 other beats).

Reported, never decisive: R1 +2.92%; D20 -1.48%; versus all other events +2.82%. By surprise band: 0-5% +5.35% (4 weeks); 5-10% +1.60% (5 weeks); 10-20% +0.89% (5 weeks); 20-up% +0.06% (5 weeks).

Rule: confirmed at 12 or more qualifying weeks if the mean is -0.3% or lower, the Newey-West t is -2 or lower, both halves and the median are negative; rejected at 12 or more if the mean is 0 or higher; otherwise it keeps running to 24.
