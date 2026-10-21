# Forward record

Every design registered in the Testing Room, scored on Council weeks that closed
after it was registered -- weeks it could not have been tuned on. `lab/forward.py`
regenerates this page each Monday (scheduled task 8); edits by hand are overwritten.
Scoring is the lab's: Monday open to Friday close, dividend-adjusted, cash earns zero.

Last run: 2026-10-20 22:48. Forward weeks: 4 (2026-09-21, 2026-09-28, 2026-10-05, 2026-10-12).

| Design | Source | Weeks | Alpha / wk | At exposure | Invested | vs production | Better / differed | vs random | Cumulative | Max DD |
|---|---|---|---|---|---|---|---|---|---|---|
| **Real Council** (official book) | engines + LLM layer | 4 | -1.81% | -1.77% | 73% | -0.52% | 2/4 | -- | -7.2% | -7.5% |
| production | engines as live | 4 | -1.29% | -1.30% | 97% | -- | -- | -1.56% (30%) | -5.1% | -5.4% |
| no-screen | Pass 3, H3 | 4 | -1.29% | -1.30% | 97% | +0.00% | 0/0 | -1.56% (30%) | -5.1% | -5.4% |
| O-last | Pass 3, H2 | 4 | -0.20% | -0.21% | 99% | +1.09% | 3/4 | -0.48% (38%) | -0.8% | -2.3% |
| M-skip | Pass 3, H1 | 4 | -1.45% | -1.46% | 96% | -0.16% | 2/4 | -1.74% (25%) | -5.7% | -5.7% |
| O-last+M-skip | Pass 3 | 4 | -0.03% | -0.04% | 99% | +1.26% | 3/4 | -0.32% (41%) | -0.1% | -1.5% |
| O-rs | Pass 2 | 4 | -1.67% | -1.68% | 94% | -0.38% | 1/2 | -1.93% (17%) | -6.6% | -6.6% |
| O-rs+ | Pass 2 | 4 | -0.34% | -0.37% | 96% | +0.95% | 3/4 | -0.62% (38%) | -1.5% | -3.6% |
| M-15 | Pass 2 | 4 | -1.29% | -1.30% | 97% | -0.00% | 0/0 | -1.56% (30%) | -5.1% | -5.4% |
| M-0 | Pass 2 | 4 | -0.42% | -0.42% | 98% | +0.88% | 1/1 | -0.70% (47%) | -1.7% | -3.8% |
| O-rs+M-15 | Pass 2 | 4 | -1.40% | -1.41% | 94% | -0.10% | 2/3 | -1.66% (18%) | -5.5% | -5.5% |
| no-Ophelia | Pass 2, reference | 4 | -0.20% | -0.22% | 92% | +1.09% | 3/4 | -0.47% (37%) | -0.8% | -2.8% |
| Ophelia-solo | Pass 9b, the engine alone | 3 | -4.96% | -4.96% | 100% | -3.36% | 1/3 | -5.80% (32%) | -15.9% | -16.8% |
| Ophelia-solo-ownmap | Pass 10, the owner's map (weekly clusters) | 3 | -2.87% | -2.87% | 100% | -1.27% | 1/3 | -3.71% (10%) | -9.0% | -9.0% |
| Cecil-solo | Pass 11, the engine alone with a point-in-time P/E | 3 | +1.13% | +1.13% | 100% | +2.73% | 2/3 | +0.29% (49%) | +2.7% | -2.5% |
| Union-equal | Pass 13, every engine's five, equal over the union | 3 | -1.72% | -1.72% | 100% | -0.12% | 1/3 | -2.55% (19%) | -5.8% | -5.8% |

## By week (book return)

| Week | SPY | Real Council | production | no-screen | O-last | M-skip | O-last+M-skip | O-rs | O-rs+ | M-15 | M-0 | O-rs+M-15 | no-Ophelia | Ophelia-solo | Ophelia-solo-ownmap | Cecil-solo | Union-equal |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-09-21 | +0.67% | +0.41% | +0.28% | +0.28% | +1.49% | -0.11% | +1.34% | -2.38% | -2.35% | +0.28% | +0.28% | -3.18% | -1.24% | -- | -- | -- | -- |
| 2026-09-28 | +0.17% | -1.15% | -2.25% | -2.25% | -1.63% | -2.06% | -1.35% | -1.51% | -1.25% | -2.25% | +1.53% | -1.48% | -1.58% | -2.89% | -1.95% | -2.53% | -2.36% |
| 2026-10-05 | +1.15% | -1.36% | +0.74% | +0.74% | -0.05% | -0.04% | -0.03% | +0.64% | +4.11% | +0.73% | +0.35% | +0.60% | +0.75% | +4.19% | -2.32% | +2.39% | +1.86% |
| 2026-10-12 | -1.99% | -5.16% | -3.94% | -3.94% | -0.63% | -3.61% | -0.08% | -3.43% | -1.90% | -3.93% | -3.83% | -1.54% | +1.26% | -16.84% | -5.00% | +2.86% | -5.33% |

A five-name weekly book moves about 1.7 points a week against SPY, so a design needs
roughly 40 forward weeks before its mean says much (lab/README.md, "What nine weeks
can and cannot say"). Read this page for direction and for designs that break, not
for proof. "production" is today's engine code replayed, so it follows every
change to production; the Real Council row is what was actually booked.

"At exposure" is the book's return less its invested share of SPY's: cash earns
zero, so a book half in cash is held to half of SPY's week. "Better / differed"
counts the weeks a design beat production out of the weeks its names differed
from production's; a week with the same names is a tie, not a loss.
