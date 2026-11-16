# Forward record

Every design registered in the Testing Room, scored on Council weeks that closed
after it was registered -- weeks it could not have been tuned on. `lab/forward.py`
regenerates this page each Monday (scheduled task 8); edits by hand are overwritten.
Scoring is the lab's: Monday open to Friday close, dividend-adjusted, cash earns zero.

Last run: 2026-11-16 12:09. Forward weeks: 8 (2026-09-21, 2026-09-28, 2026-10-05, 2026-10-12, 2026-10-19, 2026-10-26, 2026-11-02, 2026-11-09).

| Design | Source | Weeks | Alpha / wk | At exposure | Invested | vs production | Better / differed | vs random | Cumulative | Max DD |
|---|---|---|---|---|---|---|---|---|---|---|
| **Real Council** (official book) | engines + LLM layer | 8 | +0.10% | +0.04% | 78% | -0.09% | 5/8 | -- | -2.6% | -7.5% |
| production | engines as live | 8 | +0.20% | +0.18% | 97% | -- | -- | -0.50% (41%) | -1.8% | -5.4% |
| no-screen | Pass 3, H3 | 8 | -0.09% | -0.10% | 97% | -0.29% | 0/1 | -0.79% (38%) | -4.1% | -5.4% |
| O-last | Pass 3, H2 | 8 | +0.66% | +0.64% | 98% | +0.46% | 6/8 | -0.05% (45%) | +1.9% | -2.3% |
| M-skip | Pass 3, H1 | 8 | +0.15% | +0.15% | 96% | -0.05% | 4/8 | -0.55% (40%) | -2.2% | -5.8% |
| O-last+M-skip | Pass 3 | 8 | +0.80% | +0.80% | 98% | +0.61% | 4/8 | +0.08% (48%) | +3.1% | -1.5% |
| O-rs | Pass 2 | 8 | +0.22% | +0.21% | 96% | +0.03% | 4/6 | -0.47% (39%) | -1.7% | -6.6% |
| O-rs+ | Pass 2 | 8 | +0.75% | +0.73% | 96% | +0.55% | 6/8 | +0.04% (47%) | +2.5% | -3.6% |
| M-15 | Pass 2 | 8 | -0.15% | -0.17% | 97% | -0.35% | 0/2 | -0.85% (36%) | -4.5% | -5.4% |
| M-0 | Pass 2 | 8 | +0.39% | +0.38% | 97% | +0.20% | 2/5 | -0.31% (44%) | -0.3% | -4.0% |
| O-rs+M-15 | Pass 2 | 8 | +0.16% | +0.15% | 96% | -0.03% | 4/7 | -0.54% (38%) | -2.1% | -5.5% |
| no-Ophelia | Pass 2, reference | 8 | +0.83% | +0.80% | 94% | +0.63% | 5/8 | +0.11% (46%) | +3.3% | -2.8% |
| Ophelia-solo | Pass 9b, the engine alone | 7 | -0.93% | -0.93% | 100% | -1.21% | 4/7 | -1.91% (48%) | -11.6% | -16.8% |
| Ophelia-solo-ownmap | Pass 10, the owner's map (weekly clusters) | 7 | +0.08% | +0.08% | 100% | -0.20% | 4/7 | -0.90% (37%) | -3.6% | -9.0% |
| Cecil-solo | Pass 11, the engine alone with a point-in-time P/E | 7 | +1.57% | +1.57% | 100% | +1.29% | 3/7 | +0.59% (54%) | +7.1% | -2.5% |
| Union-equal | Pass 13, every engine's five, equal over the union | 7 | +0.34% | +0.34% | 100% | +0.06% | 3/7 | -0.69% (43%) | -1.8% | -5.8% |

## By week (book return)

| Week | SPY | Real Council | production | no-screen | O-last | M-skip | O-last+M-skip | O-rs | O-rs+ | M-15 | M-0 | O-rs+M-15 | no-Ophelia | Ophelia-solo | Ophelia-solo-ownmap | Cecil-solo | Union-equal |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-09-21 | +0.67% | +0.41% | +0.28% | +0.28% | +1.50% | -0.11% | +1.35% | -2.38% | -2.35% | +0.28% | +0.28% | -3.18% | -1.24% | -- | -- | -- | -- |
| 2026-09-28 | +0.17% | -1.15% | -2.26% | -2.26% | -1.63% | -2.06% | -1.35% | -1.51% | -1.25% | -2.26% | +1.52% | -1.48% | -1.58% | -2.89% | -1.95% | -2.53% | -2.36% |
| 2026-10-05 | +1.15% | -1.36% | +0.74% | +0.74% | -0.05% | -0.04% | -0.04% | +0.64% | +4.13% | +0.73% | +0.35% | +0.60% | +0.75% | +4.19% | -2.32% | +2.39% | +1.86% |
| 2026-10-12 | -1.99% | -5.16% | -3.96% | -3.96% | -0.63% | -3.63% | -0.08% | -3.44% | -1.90% | -3.95% | -3.85% | -1.54% | +1.26% | -16.84% | -5.00% | +2.86% | -5.33% |
| 2026-10-19 | -0.95% | +2.12% | +0.73% | +0.73% | +1.01% | +2.02% | +2.50% | +1.98% | +0.97% | +0.76% | -0.11% | +2.02% | +0.95% | +2.37% | +1.04% | +0.52% | +1.74% |
| 2026-10-26 | -0.86% | +1.25% | +0.84% | +0.84% | -0.34% | +1.40% | +0.12% | -0.27% | -0.21% | +0.84% | +0.55% | -0.27% | +0.19% | +1.77% | +2.05% | +0.33% | +0.49% |
| 2026-11-02 | -3.18% | +0.51% | +1.03% | -1.22% | +1.03% | +0.23% | +0.19% | +2.08% | +1.89% | -0.98% | +1.41% | -0.05% | +1.02% | +1.99% | +3.24% | +0.57% | +0.57% |
| 2026-11-09 | +1.67% | +0.91% | +0.86% | +0.80% | +1.05% | +0.07% | +0.43% | +1.39% | +1.39% | +0.04% | -0.32% | +1.89% | +1.97% | -1.08% | -0.45% | +2.84% | +1.42% |

A five-name weekly book moves about 1.7 points a week against SPY, so a design needs
roughly 40 forward weeks before its mean says much (lab/README.md, "What nine weeks
can and cannot say"). Read this page for direction and for designs that break, not
for proof. "production" is today's engine code replayed, so it follows every
change to production; the Real Council row is what was actually booked.

"At exposure" is the book's return less its invested share of SPY's: cash earns
zero, so a book half in cash is held to half of SPY's week. "Better / differed"
counts the weeks a design beat production out of the weeks its names differed
from production's; a week with the same names is a tie, not a loss.
