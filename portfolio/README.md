# Paper Portfolio Tracker

> *"The Council recommends. The Tracker records. The Scoreboard judges."*

The Paper Portfolio Tracker treats every weekly Council pick as if it were a real trade — with real entry prices, real stop losses, and real P&L.

## How It Works

### Monday Morning (9:17 AM ET)
1. The Weekly Council Scan generates 5 picks with weights
2. The Tracker records **entry prices** for each pick (Monday's price)
3. The Tracker records **SPY entry price** as the benchmark
4. Positions are saved to `current.yaml`

### Friday Close
1. The Tracker fetches **Friday closing prices** for all positions
2. It checks if any **stop losses** were hit during the week
3. It calculates **P&L per position** and **weighted portfolio return**
4. It calculates **alpha vs SPY buy-and-hold**
5. Everything is archived to `history/YYYY-MM-DD.yaml`

### The Next Monday
1. Before opening new positions, the Tracker **closes the prior week**
2. It generates a **scorecard** (`scorecards/YYYY-MM-DD-scorecard.md`)
3. It appends a row to the **Historical Scoreboard** in `scoreboard.md`
4. It recalculates **rolling metrics** (Sharpe, max drawdown, hit rate)

## File Structure

```
portfolio/
  tracker.py          # Main engine — run this
  README.md           # This file
  current.yaml        # Currently open positions (if any)
  metrics.json        # Rolling performance metrics
  history/
    2026-07-15.yaml   # Closed positions from that week
    2026-07-22.yaml
    ...
```

## Metrics Tracked

| Metric | Description |
|--------|-------------|
| **Weighted Return** | Portfolio return weighted by pick allocations |
| **SPY Return** | Buy-and-hold SPY for the same period |
| **Alpha** | Council return minus SPY return |
| **Hit Rate** | % of picks with positive return |
| **Sharpe (4W)** | Risk-adjusted return, 4-week rolling |
| **Max Drawdown** | Worst peak-to-trough decline |
| **Per-Agent Avg Return** | Cecil vs Marky vs Ophelia |
| **Per-Agent Hit Rate** | Who bats above .500? |

## Usage

```bash
# Close prior week + open new week (Monday cron does this)
python portfolio/tracker.py --full 2026-07-21 --report reports/2026-07-21-report.md

# Just close the current week
python portfolio/tracker.py --close 2026-07-21

# Just open a new week
python portfolio/tracker.py --open 2026-07-21 --report reports/2026-07-21-report.md

# Recalculate metrics from history
python portfolio/tracker.py --metrics
```

## Stop Losses

The Tracker checks for stop losses **daily** during the week. If a stop is hit, the position is recorded as exited at that day's price with reason `"stop_loss"`. If no stop is hit, the position exits at Friday close with reason `"week_end"`.

> **Note:** Stop loss levels are currently read from agent journals. If a journal doesn't specify a stop, the Tracker uses a default 8% stop. You can override this by adding explicit stops to each agent's weekly entry template.

## Data Sources

- **Entry/exit prices:** Yahoo Finance via `yfinance` (same as the scan pipeline)
- **Benchmark:** SPY
- **Stop checking:** Intra-week daily closes

## Integration with Monday Cron

The Monday cron job now runs the Tracker as part of its workflow:

```
1. Close prior week's positions (if any)
2. Generate scorecard + update scoreboard
3. Recalculate metrics
4. Run new Council Scan
5. Record new entry prices
6. Push everything to GitHub
```

## Honesty Rules

1. **No cherry-picking.** If the Council picks it, the Tracker trades it. No exceptions.
2. **No late entries.** Monday's price is the price. No "I would have entered lower."
3. **No early exits.** Unless a stop hits, Friday close is the exit. No "I felt like selling."
4. **Cash counts.** If the Council allocates 60% cash, the Tracker earns 0% on that 60%. No free rides.

> *"The difference between a guru and a fraud is a paper portfolio that actually gets graded."*

---

*The Tracker is neutral. It does not care about your thesis. It cares about your price.*
