# Forward record

Every design registered in the Testing Room, scored on Council weeks that closed
after it was registered -- weeks it could not have been tuned on. `lab/forward.py`
regenerates this page each Monday (scheduled task 8); edits by hand are overwritten.
Scoring is the lab's: Monday open to Friday close, dividend-adjusted, cash earns zero.

Last run: 2026-11-11 17:13. Forward weeks: 7 (2026-09-21, 2026-09-28, 2026-10-05, 2026-10-12, 2026-10-19, 2026-10-26, 2026-11-02).

| Design | Source | Weeks | Alpha / wk | At exposure | Invested | vs production | Better / differed | vs random | Cumulative | Max DD |
|---|---|---|---|---|---|---|---|---|---|---|
| **Real Council** (official book) | engines + LLM layer | 7 | +0.23% | +0.12% | 77% | -0.11% | 4/7 | -- | -3.5% | -7.5% |
| production | engines as live | 7 | +0.34% | +0.32% | 96% | -- | -- | -0.53% (40%) | -2.7% | -5.4% |
| no-screen | Pass 3, H3 | 7 | +0.02% | +0.00% | 97% | -0.32% | 0/1 | -0.85% (38%) | -4.8% | -5.4% |
| O-last | Pass 3, H2 | 7 | +0.84% | +0.82% | 98% | +0.50% | 5/7 | -0.04% (44%) | +0.9% | -2.3% |
| M-skip | Pass 3, H1 | 7 | +0.40% | +0.39% | 96% | +0.06% | 4/7 | -0.48% (42%) | -2.3% | -5.8% |
| O-last+M-skip | Pass 3 | 7 | +1.10% | +1.08% | 98% | +0.76% | 4/7 | +0.20% (50%) | +2.7% | -1.5% |
| O-rs | Pass 2 | 7 | +0.30% | +0.27% | 96% | -0.04% | 3/5 | -0.58% (36%) | -3.0% | -6.6% |
| O-rs+ | Pass 2 | 7 | +0.90% | +0.86% | 96% | +0.55% | 5/7 | +0.01% (45%) | +1.1% | -3.6% |
| M-15 | Pass 2 | 7 | +0.06% | +0.04% | 96% | -0.28% | 0/1 | -0.81% (38%) | -4.6% | -5.4% |
| M-0 | Pass 2 | 7 | +0.73% | +0.71% | 97% | +0.39% | 2/4 | -0.15% (48%) | +0.1% | -4.0% |
| O-rs+M-15 | Pass 2 | 7 | +0.16% | +0.13% | 96% | -0.19% | 3/6 | -0.73% (34%) | -3.9% | -5.5% |
| no-Ophelia | Pass 2, reference | 7 | +0.91% | +0.86% | 94% | +0.57% | 4/7 | +0.01% (42%) | +1.3% | -2.8% |
| Ophelia-solo | Pass 9b, the engine alone | 6 | -0.63% | -0.63% | 100% | -1.09% | 4/6 | -1.87% (53%) | -10.6% | -16.8% |
| Ophelia-solo-ownmap | Pass 10, the owner's map (weekly clusters) | 6 | +0.45% | +0.45% | 100% | -0.01% | 4/6 | -0.79% (40%) | -3.1% | -9.0% |
| Cecil-solo | Pass 11, the engine alone with a point-in-time P/E | 6 | +1.63% | +1.63% | 100% | +1.17% | 2/6 | +0.39% (50%) | +4.1% | -2.5% |
| Union-equal | Pass 13, every engine's five, equal over the union | 6 | +0.44% | +0.44% | 100% | -0.03% | 2/6 | -0.84% (41%) | -3.2% | -5.8% |

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

A five-name weekly book moves about 1.7 points a week against SPY, so a design needs
roughly 40 forward weeks before its mean says much (lab/README.md, "What nine weeks
can and cannot say"). Read this page for direction and for designs that break, not
for proof. "production" is today's engine code replayed, so it follows every
change to production; the Real Council row is what was actually booked.

"At exposure" is the book's return less its invested share of SPY's: cash earns
zero, so a book half in cash is held to half of SPY's week. "Better / differed"
counts the weeks a design beat production out of the weeks its names differed
from production's; a week with the same names is a tie, not a loss.
