# 🏆 Arena Standings

All-time leaderboard. Players are scored on weekly weighted return and alpha vs SPY (Monday open -> Friday close), plus head-to-head vs the Council's book.

## All-Time

| Player | Weeks | Avg Weekly Return | Avg Alpha vs SPY | Head-to-Head vs Council | Best Week |
|---|---|---|---|---|---|
| GrandMastaShake | 8 | +0.31% | +0.09% | 4-4 | +3.40% (2026-09-21) |
| Umassalum | 6 | -0.24% | -0.83% | 5-1 | +2.52% (2026-08-03) |
| 🏛️ The Council | 9 | -0.70% | -1.13% | -- | +0.41% (2026-09-21) |

## Weekly Results

| Week | Player | Weekly Return | Alpha vs SPY | Council Return | Week Winner |
|---|---|---|---|---|---|
| 2026-09-28 | Umassalum | -0.79% | -0.96% | -1.15% | 🏆 Umassalum |
| 2026-09-28 | GrandMastaShake | -2.18% | -2.35% | -1.15% | 🏆 Umassalum |
| 2026-09-21 | GrandMastaShake | +3.40% | +2.73% | +0.41% | 🏆 GrandMastaShake |
| 2026-09-21 | Umassalum | -3.48% | -4.15% | +0.41% | 🏆 GrandMastaShake |
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

**Basis note (2026-08-31):** player alpha uses the Arena SPY basis (Mon open $767.33 -> Fri close $770.19, +0.37%). The Council's return/alpha come from the Tracker's own basis (same SPY window this week; Council -0.04%, alpha -0.41%). GrandMastaShake's CRWD (-3.76%) and FCX (-5.48%) did the damage; Umassalum's SPCX (+5.66%) and GILD (+4.69%) carried his book despite DDOG's -8.74%. Umassalum wins the week outright; the Council beats GrandMastaShake but loses to Umassalum.

**Basis note (2026-08-24):** player alpha uses the Arena SPY basis (Mon open $764.78 -> Fri close $769.35, +0.60%). The Council's return/alpha come from the Tracker's own basis (SPY +0.43% that week; Council +0.05%, alpha -0.38%). Note: the close run re-fetched entry bars, so locked Monday opens were refreshed at close (MRK $149.12 -> $150.72). First Council week win.

**Basis note (2026-08-17):** player alpha uses the Arena SPY basis (Mon open $776.18 -> Fri close $765.72, -1.35%). The Council's return/alpha come from the Tracker's own basis (SPY -1.29% that week; Council -3.24%, alpha -1.95%). Both books are Monday-entry -> Friday-close.

**Basis note (2026-08-10):** player alpha uses the Arena SPY basis (Mon open $772.60 -> Fri close $776.34, +0.48%). The Council sat the week out (ENGINE ABORT -- sanity gate; see `reports/2026-08-10-report.md`) and is scored at 0.00% cash; the Tracker's SPY basis that week was +0.43%, so Council alpha logs as -0.43% for the week. The Arena Council average now spans three weeks (-1.52%, -1.03%, 0.00%).

**Basis note (2026-08-03):** player alpha uses the Arena SPY basis (Mon open $749.44 -> Fri close $773.26, +3.18%). The Council's return/alpha come from the Tracker's own basis (SPY +2.72% that week; Council -1.03%, alpha -3.75%). Both books are Monday-entry -> Friday-close.

**Basis note (2026-07-27):** player alpha uses the Arena SPY basis (Mon open 744.91 -> Fri close 747.03, +0.28%). The Council's return/alpha come from the Tracker's own basis (SPY +0.71% that week). Both books are Monday-entry -> Friday-close.

**Basis note (2026-09-14, closed 2026-09-21):** player alpha uses the Arena SPY basis (Mon open $757.12 -> Fri close $761.69, +0.60%, dividend-adjusted -- SPY went ex-div 9/18). GrandMastaShake -0.16% (XOM -3.06%, CBOE -4.27% did the damage; TSM +4.77% and DDOG +2.18% carried), alpha -0.76%. The Council's +0.23% / alpha +0.57% is on the Tracker's own basis (Fri 2026-09-11 close -> Fri 2026-09-18 close, SPY -0.34%), so the head-to-head carries the basis caveat below; on a same-window Mon-close basis the Council book was -0.14% (shadow-book.md), which still beats -0.16% by 2bp. **Second Council week win.** The close run re-fetched the settled Monday bars: every open passed low <= open <= high, so the closed yaml uses validated Monday opens in place of the ~09:42 ET live prices recorded at lock (locked-basis result -0.90% vs SPY +0.35%; both are recorded in arena/2026-09-14.yaml).

**Umassalum did NOT enter this week, and the reason is a process failure worth recording.** His entry on the still-open Arena issue #83 (NVDA 30 / MSOS 30 / TMO 20 / GE 20) was posted 2026-09-07 at 07:50 ET — a valid, before-the-lock entry for the **week of 2026-09-07**. That week was Labor Day, no `arena/2026-09-07.yaml` was ever opened, and his picks were never scored or acknowledged. The 2026-09-08 session logged that "neither real player had submitted picks," which was **incorrect** — he had. His entry was not carried forward into 2026-09-14, because booking a week-old submission as if it were this week's would fabricate an entry in his name (the standing rule on this line). He has been asked directly, in the issue thread, to re-enter on the week of 2026-09-21 issue.

**Entry-basis note (2026-09-14):** the provider's Monday daily bar carried a stale Open field (a verbatim copy of Friday 2026-09-11's open) that fell outside the same day's high/low range for 5 of 7 tickers. Those opens were rejected as impossible rows; four of the five entries are recorded at the live Monday price read ~09:42 ET (`live_intraday_open_unavailable`), DDOG at a validated `open`. Exit basis is unchanged (Friday close). The Council's book is on the Tracker's own basis (Friday 2026-09-11 closes) for the same reason — so this week's Council-vs-player comparison carries a wider basis gap than usual and should be read with that caveat.

**The Council was in that week:** ALL 18.3% / PSX 16.7% / HIG 14.8% / DE 10.0% + 40.2% cash (see `reports/2026-09-14-report.md`). No prior Arena week was scored this session: `arena/2026-08-31.yaml` was already closed by the 2026-09-08 run, and no yaml was ever opened for 2026-09-07 or 2026-09-08.

**Basis note (2026-09-21, closed 2026-09-28):** every book -- both players and the Council -- is on the SAME basis for the first time: validated Monday 2026-09-21 opens -> Friday 2026-09-25 close (Arena SPY $766.25 -> $771.35, +0.67%; the Tracker's SPY window is identical). **GrandMastaShake +3.40%, alpha +2.73% -- the best week any player has posted** (DDOG +16.72% and BFLY +17.38% carried; SPCX -3.93% and COIN -4.91% cost). **Umassalum -3.48%, alpha -4.15%** (HQY -7.54%, UPST -6.74%, PGR -4.02% -- the insurer selloff that also took the Council's HIG -5.66%). **The Council +0.41%, alpha -0.26%** (AMD +8.00%; HIG -5.66%; 47.8% cash). GrandMastaShake wins the week and beats the Council head-to-head; the Council beats Umassalum -- his first head-to-head loss (4-1). The close run re-fetched the settled Monday bars: all 14 passed low <= open <= high; four opens moved by cents from the lock-time prices, and both results are recorded in arena/2026-09-21.yaml (locked basis: +3.39% / -3.48%).

**Basis note (2026-09-28, closed 2026-10-05):** all three books are on the same basis: Monday 2026-09-28 opens -> Friday 2026-10-02 close (Arena SPY $768.35 -> $769.64, +0.17%; the Tracker's SPY window is identical). A red week for every book. **Umassalum -0.79%, alpha -0.96%** (BNO +3.77% on a 30% weight carried; VRTX -3.73% and GE -3.70% cost) -- wins the week and beats the Council head-to-head (5-1). **The Council -1.15%, alpha -1.32%** (AAPL -1.96%, META -2.93%, AMD +1.44%; 20.0% cash). **GrandMastaShake -2.18%, alpha -2.35%** (NVDA +1.83% was the only green; MOD -8.66%, JNJ -5.23%, CNK -4.25%, MCS -3.87%, VRTX -3.73%; 25% cash) -- the Council wins that head-to-head (4-4). The close run re-fetched the settled Monday bars; VRTX's open moved 0.43% from the lock-time price ($522.02 -> $524.27), and the locked-basis results (-0.71% / -2.14%) are recorded in arena/2026-09-28.yaml. The order is the same on either basis.

**Open week (2026-10-05):** two players locked in (entry set pinned from #121 by comment timestamps; both comments created and unedited before the 08:50 ET lock) -- **Umassalum** RDVT 20% / NVDA 15% / INSP 25% / CDNA 10% / BTC 30% (BTC = Grayscale Bitcoin Mini Trust ETF, the US-listed ticker), fully invested; **GrandMastaShake** AMAT 20% / NVDA 20% / XOM 20% / GEV 15% / BJRI 10% / GEF 10% / RKLB 5%, fully invested. **The Council is in:** SNPS 21.3% / JCI 17.3% / NDSN 14.8% / AMAT 13.6% / LRCX 13.0% + 20.0% cash (report published after the lock). Entry prices are the validated Monday 2026-10-05 opens, recorded in arena/2026-10-05.yaml by the post-open booking.

*May the best thesis win.* 🏛️