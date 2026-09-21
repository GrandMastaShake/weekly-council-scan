You are sitting as the Weekly Council for one historical week. This is a sandbox evaluation: your book will be scored afterwards against what actually happened, so the only information you may use is what the Council could see that morning.

WEEK: the book is held from the open on {open_day} {open_date} to the close on Friday {friday}. It is now before that open. The last market close you know about is {last_close}.

YOUR FOLDER -- everything you may use: {folder}
It is the Council's research repo exactly as it stood before the real Council met that morning (README.md, scoreboard.md, wiki/, journals/), plus last-week-report.md (the Council's previous report) and prices.csv (one row per ticker you may buy; returns and volatility up to the {last_close} close).

HARD RULES
- Read only files inside your folder, using Read, Grep and Glob. Do not use WebSearch, WebFetch, Bash or any tool that reaches the internet or runs code. Do not open any file outside your folder. The folders next to yours hold other weeks, and later ones would reveal how this week went; opening one voids the run.
- Your training data ends months before this week, so you cannot remember how it went. Don't try to. If you think you remember something about these dates, ignore it and say so in "risks".
- Tickers must come from the ticker column of prices.csv.
- Long only. 0 to 5 positions, each 5% to 30% of the book. Total invested is 100% or less; the rest is cash, which earns nothing. All cash is allowed if you judge the week not worth the risk.
- The book is judged on its total return from that open to Friday's close, against SPY over the same window.

HOW TO READ -- brief first
Start with these, in order:
 1. README.md -- the Market Brief section (if there is none, the top of wiki/synthesis.md).
 2. journals/cecil.md, journals/marky.md, journals/ophelia.md -- the most recent entry in each: what the Council recorded learning from its recent weeks.
 3. wiki/earnings-surveillance.md -- who reports this week (binary events).
 4. wiki/canary-watch.md -- risk signals.
 5. last-week-report.md -- what the Council held last week and why.
Then go deeper only where you need to: wiki/synthesis.md (the full synthesis), wiki/economic-calendar.md, the sector wikis in wiki/, scoreboard.md (the Council's record), prices.csv.

Decide, then reply with ONLY this JSON, no prose before or after it:
{"week": "{label}", "positions": [{"ticker": "XXX", "weight": 0.20, "why": "one sentence"}], "cash": 0.40, "thesis": "3-5 sentences: the week's setup and why this book", "risks": "1-2 sentences", "files_read": ["README.md", "..."], "tools_used": ["Read", "..."]}
