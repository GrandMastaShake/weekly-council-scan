# Forward record

Every design registered in the Testing Room, scored on Council weeks that closed
after it was registered -- weeks it could not have been tuned on. `lab/forward.py`
regenerates this page each Monday (scheduled task 8); edits by hand are overwritten.
Scoring is the lab's: Monday open to Friday close, dividend-adjusted, cash earns zero.

Last run: 2026-11-02 12:10. Forward weeks: 6 (2026-09-21, 2026-09-28, 2026-10-05, 2026-10-12, 2026-10-19, 2026-10-26).

| Design | Source | Weeks | Alpha / wk | At exposure | Invested | vs production | Better / differed | vs random | Cumulative | Max DD |
|---|---|---|---|---|---|---|---|---|---|---|
| **Real Council** (official book) | engines + LLM layer | 6 | -0.35% | -0.37% | 76% | -0.05% | 4/6 | -- | -4.0% | -7.5% |
| production | engines as live | 6 | -0.30% | -0.32% | 96% | -- | -- | -0.96% (37%) | -3.7% | -5.4% |
| no-screen | Pass 3, H3 | 6 | -0.30% | -0.32% | 97% | +0.00% | 0/0 | -0.97% (37%) | -3.7% | -5.4% |
| O-last | Pass 3, H2 | 6 | +0.28% | +0.26% | 98% | +0.58% | 4/6 | -0.39% (40%) | -0.2% | -2.3% |
| M-skip | Pass 3, H1 | 6 | -0.10% | -0.11% | 96% | +0.20% | 4/6 | -0.77% (40%) | -2.5% | -5.7% |
| O-last+M-skip | Pass 3 | 6 | +0.72% | +0.70% | 98% | +1.02% | 4/6 | +0.03% (47%) | +2.5% | -1.5% |
| O-rs | Pass 2 | 6 | -0.53% | -0.55% | 95% | -0.23% | 2/4 | -1.18% (29%) | -5.0% | -6.6% |
| O-rs+ | Pass 2 | 6 | +0.21% | +0.19% | 96% | +0.51% | 4/6 | -0.46% (40%) | -0.7% | -3.6% |
| M-15 | Pass 2 | 6 | -0.30% | -0.32% | 96% | +0.01% | 0/0 | -0.96% (37%) | -3.6% | -5.4% |
| M-0 | Pass 2 | 6 | +0.10% | +0.08% | 97% | +0.40% | 1/3 | -0.57% (46%) | -1.3% | -3.9% |
| O-rs+M-15 | Pass 2 | 6 | -0.34% | -0.36% | 95% | -0.04% | 3/5 | -1.00% (30%) | -3.9% | -5.5% |
| no-Ophelia | Pass 2, reference | 6 | +0.36% | +0.34% | 94% | +0.66% | 4/6 | -0.31% (40%) | +0.3% | -2.8% |
| Ophelia-solo | Pass 9b, the engine alone | 5 | -1.79% | -1.79% | 100% | -1.50% | 3/5 | -2.82% (47%) | -12.3% | -16.8% |
| Ophelia-solo-ownmap | Pass 10, the owner's map (weekly clusters) | 5 | -0.74% | -0.74% | 100% | -0.46% | 3/5 | -1.78% (31%) | -6.2% | -9.0% |
| Cecil-solo | Pass 11, the engine alone with a point-in-time P/E | 5 | +1.21% | +1.21% | 100% | +1.49% | 2/5 | +0.17% (48%) | +3.5% | -2.5% |
| Union-equal | Pass 13, every engine's five, equal over the union | 5 | -0.22% | -0.22% | 100% | +0.06% | 2/5 | -1.33% (36%) | -3.7% | -5.8% |

## By week (book return)

| Week | SPY | Real Council | production | no-screen | O-last | M-skip | O-last+M-skip | O-rs | O-rs+ | M-15 | M-0 | O-rs+M-15 | no-Ophelia | Ophelia-solo | Ophelia-solo-ownmap | Cecil-solo | Union-equal |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-09-21 | +0.67% | +0.41% | +0.28% | +0.28% | +1.49% | -0.11% | +1.34% | -2.38% | -2.35% | +0.28% | +0.28% | -3.18% | -1.24% | -- | -- | -- | -- |
| 2026-09-28 | +0.17% | -1.15% | -2.25% | -2.25% | -1.63% | -2.06% | -1.35% | -1.51% | -1.25% | -2.25% | +1.53% | -1.48% | -1.58% | -2.89% | -1.95% | -2.53% | -2.36% |
| 2026-10-05 | +1.15% | -1.36% | +0.74% | +0.74% | -0.05% | -0.04% | -0.03% | +0.64% | +4.11% | +0.73% | +0.35% | +0.60% | +0.75% | +4.19% | -2.32% | +2.39% | +1.86% |
| 2026-10-12 | -1.99% | -5.16% | -3.94% | -3.94% | -0.63% | -3.61% | -0.08% | -3.43% | -1.90% | -3.93% | -3.83% | -1.54% | +1.26% | -16.84% | -5.00% | +2.86% | -5.33% |
| 2026-10-19 | -0.95% | +2.12% | +0.73% | +0.73% | +1.01% | +2.02% | +2.50% | +1.97% | +1.05% | +0.76% | -0.11% | +2.01% | +0.95% | +2.37% | +1.04% | +0.52% | +1.74% |
| 2026-10-26 | -0.86% | +1.25% | +0.84% | +0.84% | -0.34% | +1.40% | +0.12% | -0.27% | -0.21% | +0.84% | +0.55% | -0.27% | +0.19% | +1.77% | +2.05% | +0.33% | +0.49% |

A five-name weekly book moves about 1.7 points a week against SPY, so a design needs
roughly 40 forward weeks before its mean says much (lab/README.md, "What nine weeks
can and cannot say"). Read this page for direction and for designs that break, not
for proof. "production" is today's engine code replayed, so it follows every
change to production; the Real Council row is what was actually booked.

"At exposure" is the book's return less its invested share of SPY's: cash earns
zero, so a book half in cash is held to half of SPY's week. "Better / differed"
counts the weeks a design beat production out of the weeks its names differed
from production's; a week with the same names is a tie, not a loss.
