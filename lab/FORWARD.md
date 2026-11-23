# Forward record

Every design registered in the Testing Room, scored on Council weeks that closed
after it was registered -- weeks it could not have been tuned on. `lab/forward.py`
regenerates this page each Monday (scheduled task 8); edits by hand are overwritten.
Scoring is the lab's: Monday open to Friday close, dividend-adjusted, cash earns zero.

Last run: 2026-11-23 12:10. Forward weeks: 9 (2026-09-21, 2026-09-28, 2026-10-05, 2026-10-12, 2026-10-19, 2026-10-26, 2026-11-02, 2026-11-09, 2026-11-16).

| Design | Source | Weeks | Alpha / wk | At exposure | Invested | vs production | Better / differed | vs random | Cumulative | Max DD |
|---|---|---|---|---|---|---|---|---|---|---|
| **Real Council** (official book) | engines + LLM layer | 9 | +0.67% | +0.47% | 78% | +0.34% | 6/9 | -- | -5.3% | -7.5% |
| production | engines as live | 9 | +0.33% | +0.29% | 96% | -- | -- | -0.45% (43%) | -8.3% | -8.3% |
| no-screen | Pass 3, H3 | 9 | +0.16% | +0.13% | 98% | -0.17% | 1/2 | -0.65% (41%) | -9.7% | -9.7% |
| O-last | Pass 3, H2 | 9 | +0.82% | +0.78% | 97% | +0.49% | 5/9 | -0.00% (46%) | -4.1% | -6.8% |
| M-skip | Pass 3, H1 | 9 | +0.69% | +0.66% | 98% | +0.36% | 6/9 | -0.15% (48%) | -5.2% | -5.8% |
| O-last+M-skip | Pass 3 | 9 | +1.19% | +1.15% | 99% | +0.86% | 6/9 | +0.35% (53%) | -0.8% | -5.2% |
| O-rs | Pass 2 | 9 | +0.64% | +0.63% | 97% | +0.31% | 5/8 | -0.16% (43%) | -5.9% | -7.4% |
| O-rs+ | Pass 2 | 9 | +1.05% | +1.03% | 97% | +0.72% | 6/9 | +0.24% (49%) | -2.4% | -7.4% |
| M-15 | Pass 2 | 9 | +0.41% | +0.37% | 96% | +0.07% | 2/3 | -0.37% (45%) | -7.7% | -7.7% |
| M-0 | Pass 2 | 9 | +0.74% | +0.72% | 98% | +0.41% | 3/6 | -0.08% (49%) | -4.7% | -5.6% |
| O-rs+M-15 | Pass 2 | 9 | +0.43% | +0.41% | 95% | +0.10% | 4/8 | -0.36% (43%) | -7.6% | -7.6% |
| no-Ophelia | Pass 2, reference | 9 | +0.92% | +0.84% | 93% | +0.59% | 4/9 | +0.07% (47%) | -3.4% | -7.0% |
| Ophelia-solo | Pass 9b, the engine alone | 8 | -0.15% | -0.15% | 100% | -0.68% | 6/8 | -1.20% (54%) | -13.9% | -16.8% |
| Ophelia-solo-ownmap | Pass 10, the owner's map (weekly clusters) | 8 | +1.00% | +1.00% | 100% | +0.47% | 5/8 | -0.06% (44%) | -4.1% | -6.5% |
| Cecil-solo | Pass 11, the engine alone with a point-in-time P/E | 8 | +2.11% | +2.11% | 100% | +1.58% | 5/8 | +1.05% (59%) | +4.5% | -6.8% |
| Union-equal | Pass 13, every engine's five, equal over the union | 8 | +0.79% | +0.79% | 100% | +0.26% | 5/8 | -0.32% (49%) | -5.8% | -5.8% |

## By week (book return)

| Week | SPY | Real Council | production | no-screen | O-last | M-skip | O-last+M-skip | O-rs | O-rs+ | M-15 | M-0 | O-rs+M-15 | no-Ophelia | Ophelia-solo | Ophelia-solo-ownmap | Cecil-solo | Union-equal |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-09-21 | +0.67% | +0.41% | -0.56% | -0.56% | +0.74% | -0.95% | +0.56% | -3.23% | -3.21% | -0.56% | -0.56% | -3.97% | -2.28% | -- | -- | -- | -- |
| 2026-09-28 | +0.17% | -1.15% | -3.49% | -3.49% | -2.81% | -3.04% | -2.29% | -2.53% | -2.26% | -3.49% | +0.33% | -2.50% | -2.56% | -2.89% | -3.04% | -2.26% | -2.27% |
| 2026-10-05 | +1.15% | -1.36% | +1.66% | +1.66% | +0.68% | +0.75% | +0.63% | +1.53% | +5.31% | +1.65% | +1.16% | +1.49% | +1.29% | +4.19% | +0.32% | +3.19% | +2.13% |
| 2026-10-12 | -1.99% | -5.16% | -3.03% | -3.03% | +0.49% | -2.68% | +1.05% | -0.66% | -0.86% | -3.03% | -2.88% | -0.44% | +2.52% | -16.84% | -3.86% | +5.07% | -4.60% |
| 2026-10-19 | -0.95% | +2.12% | +0.76% | +0.76% | +1.01% | +2.24% | +2.73% | +2.71% | +2.50% | +0.79% | -0.02% | +2.46% | +1.18% | +2.37% | +1.04% | +1.23% | +2.01% |
| 2026-10-26 | -0.86% | +1.25% | +0.87% | +1.15% | -0.14% | +1.55% | +0.16% | -0.69% | -0.34% | +0.88% | +0.63% | -0.64% | +0.39% | +1.77% | +2.05% | +0.87% | +0.72% |
| 2026-11-02 | -3.18% | +0.51% | +1.02% | -0.72% | +0.99% | +0.20% | +0.16% | +2.18% | +1.89% | +0.95% | +0.86% | -0.01% | +0.66% | +1.99% | +3.24% | +0.57% | +0.57% |
| 2026-11-09 | +1.67% | +0.91% | +0.60% | +0.50% | +1.94% | +1.19% | +1.57% | +2.50% | +2.52% | +1.05% | +0.79% | +3.07% | +2.74% | -1.08% | -0.45% | +3.02% | +1.48% |
| 2026-11-16 | -7.98% | -2.76% | -6.14% | -6.13% | -6.81% | -4.37% | -5.18% | -7.38% | -7.39% | -5.88% | -4.93% | -6.88% | -6.97% | -2.68% | -3.27% | -6.81% | -5.70% |

A five-name weekly book moves about 1.7 points a week against SPY, so a design needs
roughly 40 forward weeks before its mean says much (lab/README.md, "What nine weeks
can and cannot say"). Read this page for direction and for designs that break, not
for proof. "production" is today's engine code replayed, so it follows every
change to production; the Real Council row is what was actually booked.

"At exposure" is the book's return less its invested share of SPY's: cash earns
zero, so a book half in cash is held to half of SPY's week. "Better / differed"
counts the weeks a design beat production out of the weeks its names differed
from production's; a week with the same names is a tie, not a loss.
