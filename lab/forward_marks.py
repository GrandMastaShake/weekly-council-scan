#!/usr/bin/env python3
"""Pass 44 -- the owner's marks, forward: the scorer.

Reads lab/owner_marks.json (append-only; this script never writes it) and
scores every mark as registered in lab/README.md, Pass 44:

- A mark is entered at the open of the first session on or after its
  `enter_open_of` date.
- At 4, 13 and 26 weeks (the close 20, 65 and 130 sessions after that open,
  counting the entry session as the first): the name's return, SPY's over the
  same sessions, and the name's place, 0 to 100, among the returns of every
  name in its size tier of lab/universe_all_*.csv (Pass 43's tiers, by rank
  on the entry day). Adjusted prices, so dividends are in; no costs.
- `potential` should place above 50 on average and `broken` below 50; `ideal`
  is reported and not judged; a `withdrawn` row removes the same ticker's mark
  for the same entry session; a row flagged `duplicate_of_earlier_row` is not
  scored twice.
- Nothing is concluded from fewer than 40 marks of one call with a 13-week
  score.
- The mechanical shadow: for a mark carrying a `shadow` line, the first weekly
  close under that line extended at its slope. A record, not part of the score.

    python lab/forward_marks.py          # score, rewrite lab/MARKS.md and lab/results/owner_marks.json
    python lab/forward_marks.py plan     # no prices: what is in the ledger and when each score falls due
"""
from __future__ import annotations

import json
import math
import pickle
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass43_channel_by_size as p43  # noqa: E402

LEDGER = lab.LAB / "owner_marks.json"
PAGE = lab.LAB / "MARKS.md"
DATA = lab.RESULTS / "owner_marks.json"
HORIZONS = {"4w": 20, "13w": 65, "26w": 130}
JUDGED = {"potential": "above", "broken": "below"}
MIN_MARKS = 40
PRICES_FROM = "2026-09-14"
TIER_NAMES = [t[0] for t in p43.TIERS]
TIER_EDGES = [t[2] for t in p43.TIERS]


def live_marks(marks):
    """The rows that are scored: not withdrawn, not a repeat, a call we know."""
    withdrawn = {(m["ticker"], m["enter_open_of"]) for m in marks if m["call"] == "withdrawn"}
    out, seen = [], set()
    for m in marks:
        key = (m["ticker"], m["enter_open_of"], m["call"])
        if m["call"] not in ("potential", "broken", "ideal") or m.get("duplicate_of_earlier_row"):
            continue
        if (m["ticker"], m["enter_open_of"]) in withdrawn or key in seen:
            continue
        seen.add(key)
        out.append(m)
    return out


def place(value, peers):
    """Where `value` sits among `peers`, 0 to 100: the share of peers below it,
    ties counted as half."""
    peers = [p for p in peers if p == p]
    if value != value or not peers:
        return None
    below = sum(1 for p in peers if p < value)
    ties = sum(1 for p in peers if p == value)
    return 100.0 * (below + 0.5 * ties) / len(peers)


def tiers_on(day_idx, sessions, close, universe):
    """Tier of every universe name on a session: rank by cap scaled from its cap date."""
    sizes = {}
    for t, row in universe.items():
        if t not in close:
            continue
        col = close[t]
        ref_i = max([i for i, d in enumerate(sessions) if d <= row["cap_date"]] or [0])
        ref = _last_valid(col, ref_i)
        now = _last_valid(col, day_idx)
        if ref and now:
            sizes[t] = float(row["cap_m"]) * now / ref
    order = sorted(sizes, key=lambda t: -sizes[t])
    tier = {}
    for rank, t in enumerate(order):
        tier[t] = next((k for k, edge in enumerate(TIER_EDGES) if rank < edge), len(TIER_EDGES) - 1)
    return tier, sizes, order


def _last_valid(col, i):
    for k in range(i, max(-1, i - 10), -1):
        v = col[k]
        if v == v:
            return float(v)
    return None


def tier_of_outsider(size, sizes, order):
    """A marked name that is not in the universe file takes the tier its size would rank in."""
    rank = sum(1 for t in order if sizes[t] > size)
    return next((k for k, edge in enumerate(TIER_EDGES) if rank < edge), len(TIER_EDGES) - 1)


def score(marks, sessions, opens, close, universe, outsider_caps=None):
    """Every live mark scored against the prices in hand. Pure: no network and
    no pandas. sessions is the list of session dates; opens and close
    map a ticker to a list of prices, one per session (NaN where there is none)."""
    outsider_caps = outsider_caps or {}
    last = len(sessions) - 1
    rows, tier_cache = [], {}
    for m in live_marks(marks):
        t = m["ticker"]
        row = {"ticker": t, "call": m["call"], "marked": m["marked"], "enter_open_of": m["enter_open_of"],
               "last_close_at_mark": m.get("last_close"), "source": m.get("source", "his own pick"), "scores": {}}
        e = next((i for i, d in enumerate(sessions) if d >= m["enter_open_of"]), None)
        if e is None or t not in opens or opens[t][e] != opens[t][e]:
            row["status"] = "not yet entered" if e is None else "no price at entry"
            rows.append(row)
            continue
        px_in = float(opens[t][e])
        if e not in tier_cache:
            tier_cache[e] = tiers_on(max(e - 1, 0), sessions, close, universe)
        tier, sizes, order = tier_cache[e]
        if t in tier:
            k = tier[t]
        elif t in outsider_caps and _last_valid(close[t], max(e - 1, 0)) and _last_valid(close[t], last):
            k = tier_of_outsider(outsider_caps[t] * _last_valid(close[t], max(e - 1, 0)) / _last_valid(close[t], last), sizes, order)
        else:
            k = None
        row.update(entered=sessions[e], entry_open=round(px_in, 4), tier=None if k is None else TIER_NAMES[k], status="open")
        peers = [p for p in tier if tier[p] == k and p != t] if k is not None else []
        spy_in = float(opens["SPY"][e])

        def at(x):
            px = close[t][x]
            if px != px:
                return None
            ret = float(px) / px_in - 1.0
            peer_rets = [float(close[p][x]) / float(opens[p][e]) - 1.0 for p in peers
                         if p in opens and opens[p][e] == opens[p][e] and close[p][x] == close[p][x]]
            return {"through": sessions[x], "return": ret, "spy": float(close["SPY"][x]) / spy_in - 1.0,
                    "place": place(ret, peer_rets), "peers": len(peer_rets)}
        for label, n_sess in HORIZONS.items():
            x = e + n_sess - 1
            row["scores"][label] = at(x) if x <= last else None
        row["to_date"] = at(last)
        if all(row["scores"][h] is not None for h in HORIZONS):
            row["status"] = "closed"
        sh = m.get("shadow")
        if sh and sh.get("lower_line_on_mark_date") and sh.get("slope_year") is not None:
            b = math.log(1.0 + sh["slope_year"]) / 52.0
            mark_day = date.fromisoformat(m["marked"])
            broke = None
            for i in range(e, last + 1):
                d = date.fromisoformat(sessions[i])
                week_end = i == last or date.fromisoformat(sessions[i + 1]).isocalendar()[:2] != d.isocalendar()[:2]
                if not week_end or (i == last and d.weekday() < 4):
                    continue
                line = sh["lower_line_on_mark_date"] * math.exp(b * (d - mark_day).days / 7.0)
                px = close[t][i]
                if px == px and float(px) < line:
                    broke = {"week_ending": sessions[i], "close": float(px), "line": line}
                    break
            row["shadow_break"] = broke
        rows.append(row)
    return rows


def summarise(rows):
    out = {}
    for call in ("potential", "broken", "ideal"):
        out[call] = {"marks": sum(1 for r in rows if r["call"] == call)}
        for h in HORIZONS:
            got = [r["scores"][h] for r in rows if r["call"] == call and r.get("scores", {}).get(h)]
            places = [g["place"] for g in got if g["place"] is not None]
            edge = [g["return"] - g["spy"] for g in got]
            n = len(places)
            mean = sum(places) / n if n else None
            sd = (sum((p - mean) ** 2 for p in places) / (n - 1)) ** 0.5 if n > 1 else None
            out[call][h] = {"scored": len(got), "mean_place": mean,
                            "share_above_50": (sum(1 for p in places if p > 50) / n) if n else None,
                            "t_against_50": ((mean - 50.0) / (sd / n ** 0.5)) if sd else None,
                            "mean_return_over_spy": (sum(edge) / len(edge)) if edge else None}
    return out


def verdict(summary):
    lines = []
    for call, want in JUDGED.items():
        s = summary[call]["13w"]
        if s["scored"] < MIN_MARKS:
            lines.append(f"`{call}`: too few ({s['scored']} of {MIN_MARKS} marks have a 13-week score).")
        else:
            ok = s["mean_place"] > 50 if want == "above" else s["mean_place"] < 50
            lines.append(f"`{call}`: mean place {s['mean_place']:.0f} over {s['scored']} marks (t against 50: "
                         f"{s['t_against_50']:+.1f}); it should be {want} 50, and it is{'' if ok else ' not'}.")
    return lines


def fetch(tickers, today):
    """Daily adjusted opens and closes since PRICES_FROM, cached for the day in lab/cache."""
    import pandas as pd
    import yfinance as yf
    path = lab.CACHE / f"marks_daily_{PRICES_FROM}_{today}_{len(tickers)}.pkl"
    if path.exists():
        with open(path, "rb") as fh:
            return pickle.load(fh)
    o, c = {}, {}
    for i in range(0, len(tickers), 100):
        chunk = tickers[i:i + 100]
        df = None
        for attempt in range(3):
            try:
                df = yf.download([t.replace(".", "-") for t in chunk], start=PRICES_FROM, auto_adjust=True, progress=False,
                                 group_by="ticker", threads=True)
                break
            except Exception as e:                                  # noqa: BLE001
                print("retry", i, e)
                time.sleep(5 + 5 * attempt)
        if df is None:
            continue
        for t in chunk:
            y = t.replace(".", "-")
            if y in df.columns.get_level_values(0):
                o[t], c[t] = df[y]["Open"], df[y]["Close"]
        print(f"  prices {min(i + 100, len(tickers))}/{len(tickers)}", flush=True)
    opens, close = pd.DataFrame(o), pd.DataFrame(c)
    keep = close["SPY"].notna()
    opens, close = opens[keep], close[keep]
    lab.CACHE.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as fh:
        pickle.dump((opens, close), fh)
    return opens, close


def write_page(rows, summary, generated, through):
    def pct(x):
        return "--" if x is None else f"{100 * x:+.1f}%"

    def cell(s):
        if not s:
            return "--"
        pl = "--" if s["place"] is None else f"{s['place']:.0f}"
        return f"{pct(s['return'])} / {pct(s['spy'])} / {pl}"
    lines = ["# The owner's marks", "",
             "His own chart calls, written down before they trade and scored on prices nobody had seen (Pass 44).",
             "`lab/forward_marks.py` regenerates this page from `lab/owner_marks.json`, which is append-only; edits by hand",
             "to this page are overwritten.", "",
             f"Last run: {generated}. Prices through {through or 'none yet'}.", ""]
    lines += ["**Status.** " + " ".join(verdict(summary)), ""]
    lines += ["| Call | Marks | 4 weeks: scored, mean place | 13 weeks: scored, mean place | 26 weeks: scored, mean place | 13 weeks: mean return over SPY |",
              "|---|---|---|---|---|---|"]
    for call in ("potential", "broken", "ideal"):
        s = summary[call]
        f = lambda h: f"{s[h]['scored']}, {'--' if s[h]['mean_place'] is None else format(s[h]['mean_place'], '.0f')}"  # noqa: E731
        lines.append(f"| {call} | {s['marks']} | {f('4w')} | {f('13w')} | {f('26w')} | {pct(s['13w']['mean_return_over_spy'])} |")
    lines += ["", "Place is where the name's return sits among every name in its size tier over the same days: 0 is the worst,",
              "100 the best, 50 the middle. `potential` should average above 50 and `broken` below it. `ideal` is shown and not",
              f"judged. Nothing is concluded from fewer than {MIN_MARKS} marks of one call with a 13-week score.", ""]
    for call in ("potential", "broken", "ideal"):
        mine = [r for r in rows if r["call"] == call]
        if not mine:
            continue
        lines += [f"## {call} ({len(mine)})", "",
                  "| Ticker | Marked | Entered | Tier | Status | To date: name / SPY / place | 4 weeks | 13 weeks | 26 weeks | Where it came from |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for r in sorted(mine, key=lambda r: (r["marked"], r["ticker"])):
            sc = r.get("scores", {})
            lines.append(f"| {r['ticker']} | {r['marked']} | {r.get('entered', '--')} | {r.get('tier') or '--'} | {r['status']} | "
                         f"{cell(r.get('to_date'))} | {cell(sc.get('4w'))} | {cell(sc.get('13w'))} | {cell(sc.get('26w'))} | {r['source']} |")
        lines.append("")
    shadows = [r for r in rows if "shadow_break" in r]
    if shadows:
        lines += ["## The mechanical shadow", "",
                  "Where a line drawn from his anchor would have sold. A record, not part of the score.", "",
                  "| Ticker | Marked | First weekly close under the line |", "|---|---|---|"]
        for r in shadows:
            b = r["shadow_break"]
            lines.append(f"| {r['ticker']} | {r['marked']} | "
                         + ("not yet" if not b else f"week ending {b['week_ending']}: {b['close']:.2f} against a line at {b['line']:.2f}") + " |")
        lines.append("")
    with open(PAGE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines).rstrip("\n") + "\n")


def main(argv):
    with open(LEDGER, encoding="utf-8") as fh:
        marks = json.load(fh)["marks"]
    live = live_marks(marks)
    now = datetime.now()
    today = now.date().isoformat()
    if len(argv) > 1 and argv[1] == "plan":
        print(f"{len(marks)} rows in the ledger, {len(live)} scored")
        for call in ("potential", "broken", "ideal"):
            print(f"  {call}: {sum(1 for m in live if m['call'] == call)}")
        for e in sorted({m["enter_open_of"] for m in live}):
            d = date.fromisoformat(e)
            due = ", ".join(f"{h} about {(d + timedelta(days=7 * int(h[:-1]) - 3)).isoformat()}" for h in HORIZONS)
            print(f"  entered {e}: {sum(1 for m in live if m['enter_open_of'] == e)} marks; scores due {due}")
        return 0
    universe = {r["ticker"]: r for r in p43.read_universe(p43.universe_file())}
    if not any(m["enter_open_of"] <= today for m in live):
        rows = [{"ticker": m["ticker"], "call": m["call"], "marked": m["marked"], "enter_open_of": m["enter_open_of"],
                 "status": "not yet entered", "source": m.get("source", "his own pick"), "scores": {}} for m in live]
        opens = close = None
        through = None
    else:
        tickers = sorted(set(universe) | {m["ticker"] for m in live} | {"SPY"})
        opens, close = fetch(tickers, today)
        outsiders = {m["ticker"] for m in live if m["ticker"] not in universe}
        caps = {}
        if outsiders:
            import yfinance as yf
            for t in sorted(outsiders):
                try:
                    caps[t] = float(yf.Ticker(t.replace(".", "-")).fast_info["market_cap"]) / 1e6
                except Exception:                                   # noqa: BLE001
                    pass
        sessions = [d.date().isoformat() for d in close.index]
        as_lists = lambda df: {t: [float(v) for v in df[t].to_numpy()] for t in df.columns}  # noqa: E731
        rows = score(marks, sessions, as_lists(opens), as_lists(close), universe, caps)
        through = sessions[-1]
    summary = summarise(rows)
    generated = now.strftime("%Y-%m-%d %H:%M")
    write_page(rows, summary, generated, through)
    with open(DATA, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"generated": generated, "prices_through": through, "summary": summary, "rows": rows}, fh, indent=1)
        fh.write("\n")
    for line in verdict(summary):
        print(line)
    print(f"{len(rows)} marks; wrote {PAGE.name} and {DATA.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
