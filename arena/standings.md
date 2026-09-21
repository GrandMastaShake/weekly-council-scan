# 🏆 Arena Standings

All-time leaderboard. Players are scored on weekly weighted return and alpha vs SPY (Monday open -> Friday close), plus head-to-head vs the Council's book.

## All-Time

| Player | Weeks | Avg Weekly Return | Avg Alpha vs SPY | Head-to-Head vs Council | Best Week |
|---|---|---|---|---|---|
| Umassalum | 4 | +0.71% | +0.04% | 4-0 | +2.52% (2026-08-03) |
| GrandMastaShake | 6 | +0.22% | +0.05% | 3-3 | +2.17% (2026-08-17) |
| 🏛️ The Council | 7 | -0.79% | -1.23% | -- | +0.23% (2026-09-14) |

## Weekly Results

| Week | Player | Weekly Return | Alpha vs SPY | Council Return | Week Winner |
|---|---|---|---|---|---|
| 2026-09-14 | GrandMastaShake | -0.16% | -0.76% | +0.23% | 🏆 The Council |
| 2026-08-31 | Umassalum | +0.82% | +0.45% | -0.04% | 🏆 Umassalum |
| 2026-08-31 | GrandMastaShake | -1.94% | -2.31% | -0.04% | 🏆 The Council |
| 2026-08-24 | GrandMastaShake | -1.22% | -1.82% | +0.05% | 🏆 The Council |
| 2026-08-17 | Umassalum | -0.67% | +0.68% | -3.24% | 🏆 GrandMastaShake |
| 2026-08-17 | GrandMastaShake | +2.17% | +3.52% | -3.24% | 🏆 GrandMastaShake |
| 2026-08-10 | Umassalum | +0.17% | -0.31% | 0.00% (cash -- ENGINE ABORT) | 🏆 GrandMastaShake |
| 2026-08-10 | GrandMastaShake | +1.83% | +1.35% | 0.00% (cash -- ENGINE ABORT) | 🏆 GrandMastaShake |
| 2026-08-03 | Umassalum | +2.52% | -0.66% | -1.03% | 🏆 Umassalum |
| 2026-07-27 | GrandMastaShake | +0.61% | +0.33% | -1.52% | 🏆 GrandMastaShake |

**Basis note (2026-08-31):** player alpha uses the Arena SPY basis (Mon open $767.33 -> Fri close $770.19, +0.37%). The Council's return/alpha come from the Tracker's own basis (same SPY window this week; Council -0.04%, alpha -0.41%). GrandMastaShake's CRWD (-3.76%) and FCX (-5.48%) did the damage; Umassalum's SPCX (+5.66%) and GILD (+4.69%) carried her book despite DDOG's -8.74%. Umassalum wins the week outright; the Council beats GrandMastaShake but loses to Umassalum.

**Basis note (2026-08-24):** player alpha uses the Arena SPY basis (Mon open $764.78 -> Fri close $769.35, +0.60%). The Council's return/alpha come from the Tracker's own basis (SPY +0.43% that week; Council +0.05%, alpha -0.38%). Note: the close run re-fetched entry bars, so locked Monday opens were refreshed at close (MRK $149.12 -> $150.72). First Council week win.

**Basis note (2026-08-17):** player alpha uses the Arena SPY basis (Mon open $776.18 -> Fri close $765.72, -1.35%). The Council's return/alpha come from the Tracker's own basis (SPY -1.29% that week; Council -3.24%, alpha -1.95%). Both books are Monday-entry -> Friday-close.

**Basis note (2026-08-10):** player alpha uses the Arena SPY basis (Mon open $772.60 -> Fri close $776.34, +0.48%). The Council sat the week out (ENGINE ABORT -- sanity gate; see `reports/2026-08-10-report.md`) and is scored at 0.00% cash; the Tracker's SPY basis that week was +0.43%, so Council alpha logs as -0.43% for the week. The Arena Council average now spans three weeks (-1.52%, -1.03%, 0.00%).

**Basis note (2026-08-03):** player alpha uses the Arena SPY basis (Mon open $749.44 -> Fri close $773.26, +3.18%). The Council's return/alpha come from the Tracker's own basis (SPY +2.72% that week; Council -1.03%, alpha -3.75%). Both books are Monday-entry -> Friday-close.

**Basis note (2026-07-27):** player alpha uses the Arena SPY basis (Mon open 744.91 -> Fri close 747.03, +0.28%). The Council's return/alpha come from the Tracker's own basis (SPY +0.71% that week). Both books are Monday-entry -> Friday-close.

**Basis note (2026-09-14, closed 2026-09-21):** player alpha uses the Arena SPY basis (Mon open $757.12 -> Fri close $761.69, +0.60%, dividend-adjusted -- SPY went ex-div 9/18). GrandMastaShake -0.16% (XOM -3.06%, CBOE -4.27% did the damage; TSM +4.77% and DDOG +2.18% carried), alpha -0.76%. The Council's +0.23% / alpha +0.57% is on the Tracker's own basis (Fri 2026-09-11 close -> Fri 2026-09-18 close, SPY -0.34%), so the head-to-head carries the basis caveat below; on a same-window Mon-close basis the Council book was -0.14% (shadow-book.md), which still beats -0.16% by 2bp. **Second Council week win.** The close run re-fetched the settled Monday bars: every open passed low <= open <= high, so the closed yaml uses validated Monday opens in place of the ~09:42 ET live prices recorded at lock (locked-basis result -0.90% vs SPY +0.35%; both are recorded in arena/2026-09-14.yaml).

**Audit correction (2026-09-21, #112):** the same-window figure above enters the Council at Monday's *close* (-0.14%) while players enter at Monday's *open* -- still two windows. On the one basis both books are defined on (date-pinned Monday open -> Friday close, dividend-adjusted total return) the Council book was **-0.31%** (ALL -2.44%, PSX +3.81%, HIG -4.49%, DE +1.62%) vs SPY **+0.60%**, alpha **-0.92%** -- so **GrandMastaShake won the week** (-0.16% vs -0.31%; alpha -0.76% vs -0.92%). The Tracker's +0.23% / +0.57% carries two artifacts: a Friday-close entry that credited the Council with the Monday gap (SPY -0.69% while the book's names rose +0.93%, before the book was decided), and a price-only SPY benchmark across the 9/18 ex-dividend (-0.34% price vs -0.09% total return). Both are fixed in tracker.py from 2026-09-21 (2eeed42). The row above and the all-time tally are left as recorded pending the owner's decision in #112.

**Umassalum did NOT enter this week, and the reason is a process failure worth recording.** Her entry on the still-open Arena issue #83 (NVDA 30 / MSOS 30 / TMO 20 / GE 20) was posted 2026-09-07 at 07:50 ET — a valid, before-the-lock entry for the **week of 2026-09-07**. That week was Labor Day, no `arena/2026-09-07.yaml` was ever opened, and her picks were never scored or acknowledged. The 2026-09-08 session logged that "neither real player had submitted picks," which was **incorrect** — she had. Her entry was not carried forward into 2026-09-14, because booking a week-old submission as if it were this week's would fabricate an entry in her name (the standing rule on this line). She has been asked directly, in the issue thread, to re-enter on the week of 2026-09-21 issue.

**Entry-basis note (2026-09-14):** the provider's Monday daily bar carried a stale Open field (a verbatim copy of Friday 2026-09-11's open) that fell outside the same day's high/low range for 5 of 7 tickers. Those opens were rejected as impossible rows; four of the five entries are recorded at the live Monday price read ~09:42 ET (`live_intraday_open_unavailable`), DDOG at a validated `open`. Exit basis is unchanged (Friday close). The Council's book is on the Tracker's own basis (Friday 2026-09-11 closes) for the same reason — so this week's Council-vs-player comparison carries a wider basis gap than usual and should be read with that caveat.

**The Council was in that week:** ALL 18.3% / PSX 16.7% / HIG 14.8% / DE 10.0% + 40.2% cash (see `reports/2026-09-14-report.md`). No prior Arena week was scored this session: `arena/2026-08-31.yaml` was already closed by the 2026-09-08 run, and no yaml was ever opened for 2026-09-07 or 2026-09-08.

*May the best thesis win.* 🏛️