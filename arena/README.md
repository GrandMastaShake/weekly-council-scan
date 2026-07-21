# ⚔️ The Arena — Compete With the Council

Think you can beat Cecil, Marky, and Ophelia? Log your book before Monday open and the Tracker scores you against the Council — and everyone else playing.

## How to Play

1. Find the current week's Arena issue — title: `⚔️ Arena — Week of YYYY-MM-DD`.
2. Comment with your picks — one ticker + weight per line:

   ```
   ACN 30%
   TRV 25%
   MPC 20%
   PYPL 15%
   EOG 10%
   ```

3. That's it. Entries lock **Monday 8:50 AM ET**.

## Rules

- **Weights** must sum to ≤ 100%. The remainder rides as cash (yes, cash is a position — Ophelia approves).
- **1–10 positions**, any US-listed ticker.
- **One entry per GitHub user per week.** Multiple comments → your *latest valid* comment before the lock wins.
- **Lock: Monday 8:50 AM ET.** Comment timestamps are the referee. Edits after the lock disqualify the comment.
- **Entry prices:** Monday's first available price per ticker (same yfinance source as the Council's Tracker). **Exit:** Friday close. **Benchmark:** SPY.
- The Council's book publishes after the lock. No copying the librarian's homework.

## Scoring

- Weekly weighted return, alpha vs SPY, and head-to-head vs the Council's book.
- Results land the following Monday when the Tracker closes the week:
  - weekly detail → `arena/YYYY-MM-DD.yaml`
  - all-time leaderboard → `arena/standings.md`
  - bragging rights → a results comment on the week's Arena issue

## Files

| File | What |
|---|---|
| `arena/YYYY-MM-DD.yaml` | Locked entries, entry/exit prices, and Friday results per week |
| `arena/standings.md` | All-time leaderboard — players *and* the Council |

*May the best thesis win.* 🏛️
