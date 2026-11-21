#!/usr/bin/env python3
"""The forward ledger of the trend-strength book (Pass 63).

Two paper books, rules frozen on 2026-11-21 from Passes 59 to 62, kept
week by week on prices nobody has seen:

- "cap of three": ten slots; the screen ranked by stock trend strength; no
  more than three names from one sector; sold on a weekly close 20% under
  its high; no new buys while SPY is under its 40-week average.
- "cap of three, pause of eight weeks": the same, and after three sales in
  a row at a loss no new buys for eight weeks.

Each run settles last week's orders at Monday's open, marks the books at
Friday's close, and writes the orders for next Monday. Running it twice in
a week changes nothing. A missed week is caught up in order.

    python lab/forward_book.py            # settle, mark, decide; writes the ledger and BOOK.md
    python lab/forward_book.py plan       # print what it would do; write nothing

The ledger is append-only: past rows are never rewritten.
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

LAB = Path(__file__).resolve().parent
LEDGER = LAB / "book_ledger.json"
PAGE = LAB / "BOOK.md"
START = "2026-11-20"                  # the first Friday decided on
SLOTS = 10
CAP = 3
OFF_HIGH = 0.20
LOSSES = 3
SLIP = 0.001                          # a side, the large-cap rate of Pass 43
START_EQUITY = 100.0
FETCH_TOP = 800                       # names fetched, by the list's own market value
MEMBERS = 500
BOOKS = {"cap of three": None, "cap of three, pause of eight weeks": 8}
SAME = {"Finance": "Financials", "Technology": "Information Technology", "Basic Materials": "Materials",
        "Telecommunications": "Communication Services", "": "Unlabelled", "Miscellaneous": "Unlabelled"}


# ---------------------------------------------------------------- the book (pure; plain dicts and lists)

def new_book(pause):
    return {"pause_weeks": pause, "cash": START_EQUITY, "positions": {}, "pending": None, "losing_streak": 0,
            "paused_until": None, "trades": [], "history": []}


def equity(book):
    return book["cash"] + sum(p["shares"] * p["last_close"] for p in book["positions"].values())


def settle(book, opens, monday):
    """Carry out the pending orders at Monday's open: sales first, then the
    cash on hand shared equally among the empty slots."""
    pend = book["pending"]
    if not pend:
        return
    for t in pend["sells"]:
        p = book["positions"].pop(t, None)
        if p is None:
            continue
        px = opens.get(t) or p["last_close"]
        got = p["shares"] * px * (1.0 - SLIP)
        book["cash"] += got
        book["trades"].append({"date": monday, "side": "sell", "ticker": t, "price": round(px, 4), "shares": p["shares"],
                               "proceeds": round(got, 4), "cost": round(p["cost"], 4), "bought": p["bought"],
                               "open_missing": t not in opens})
    buys = [b for b in pend["buys"] if opens.get(b["ticker"])]
    free = SLOTS - len(book["positions"])
    if buys and free > 0:
        per = book["cash"] / free
        for b in buys[:free]:
            px = opens[b["ticker"]]
            shares = per * (1.0 - SLIP) / px
            book["cash"] -= per
            book["positions"][b["ticker"]] = {"shares": shares, "cost": per, "bought": monday, "sector": b["sector"],
                                              "high": max(b["high"], px), "last_close": px, "missing": 0}
            book["trades"].append({"date": monday, "side": "buy", "ticker": b["ticker"], "price": round(px, 4),
                                   "shares": shares, "cost": round(per, 4)})
    book["pending"] = None


def mark(book, closes, friday, spy_close):
    """Friday's close: new highs, the book's value, one history row."""
    for t, p in book["positions"].items():
        c = closes.get(t)
        if c:
            p["last_close"], p["missing"] = c, 0
            p["high"] = max(p["high"], c)
        else:
            p["missing"] += 1
    book["history"].append({"friday": friday, "equity": round(equity(book), 4), "cash": round(book["cash"], 4),
                            "names": len(book["positions"]), "spy_close": spy_close})


def decide(book, friday, monday, ranked, cold):
    """The orders for Monday. `ranked` is the screen, best first, as
    (ticker, sector, 52-week high close) rows."""
    sells = []
    for t, p in book["positions"].items():
        if p["missing"] >= 2 or p["last_close"] / p["high"] - 1.0 <= -OFF_HIGH:
            sells.append(t)
            lost = p["shares"] * p["last_close"] < p["cost"]
            book["losing_streak"] = book["losing_streak"] + 1 if lost else 0
            if book["pause_weeks"] and book["losing_streak"] >= LOSSES:
                book["paused_until"] = (date.fromisoformat(friday) + timedelta(weeks=book["pause_weeks"])).isoformat()
                book["losing_streak"] = 0
    kept = {t: p for t, p in book["positions"].items() if t not in sells}
    free = SLOTS - len(kept)
    paused = bool(book["paused_until"] and friday <= book["paused_until"])
    buys, why = [], None
    if free <= 0:
        why = "full"
    elif cold:
        why = "cold market"
    elif paused:
        why = f"paused until {book['paused_until']}"
    else:
        count = {}
        for p in kept.values():
            count[p["sector"]] = count.get(p["sector"], 0) + 1
        for t, sec, high in ranked:
            if len(buys) >= free:
                break
            if t in book["positions"] or count.get(sec, 0) >= CAP:
                continue
            buys.append({"ticker": t, "sector": sec, "high": high})
            count[sec] = count.get(sec, 0) + 1
    book["pending"] = {"decided_on": friday, "enter_open_of": monday, "sells": sells, "buys": buys, "no_buys_because": why}


def step(ledger, week):
    """One completed week for every book. `week` carries friday, monday (the
    Monday after it), opens and closes of that week, spy_close, cold, ranked."""
    if ledger["weeks"] and week["friday"] <= ledger["weeks"][-1]["friday"]:
        return False
    for name, pause in BOOKS.items():
        book = ledger["books"].setdefault(name, new_book(pause))
        settle(book, week["opens"], week["week_monday"])
        mark(book, week["closes"], week["friday"], week["spy_close"])
        decide(book, week["friday"], week["monday"], week["ranked"], week["cold"])
    ledger["weeks"].append({"friday": week["friday"], "cold": week["cold"], "names_on_screen": len(week["ranked"]),
                            "top_ten": [r[0] for r in week["ranked"][:10]]})
    return True


def summary(book):
    h = book["history"]
    if not h:
        return None
    eq = [r["equity"] for r in h]
    peak, dd = eq[0], 0.0
    for v in eq:
        peak = max(peak, v)
        dd = min(dd, v / peak - 1.0)
    spy0 = h[0]["spy_close"]
    return {"weeks": len(h), "since": h[0]["friday"], "to": h[-1]["friday"], "equity": eq[-1],
            "return": eq[-1] / START_EQUITY - 1.0, "spy_return": h[-1]["spy_close"] / spy0 - 1.0 if spy0 else None,
            "largest_drawdown": dd, "names": h[-1]["names"], "cash_share": h[-1]["cash"] / eq[-1]}


# ---------------------------------------------------------------- the data (pandas, numpy and Yahoo live here)

def last_friday(today):
    """The latest Friday whose week is over: this week's on a Saturday or
    Sunday, last week's on any weekday (a Friday run does not count the day
    it is run on)."""
    wd = today.weekday()
    return today - timedelta(days=wd - 4) if wd >= 5 else today - timedelta(days=wd + 3)


def weeks_since(after, today):
    """Facts for every completed Friday after `after` (an ISO date or None), oldest first."""
    import pickle
    import time
    import numpy as np
    import pandas as pd
    sys.path.insert(0, str(LAB))
    import engine_lab as lab
    import pass41_owner_channel as p41
    import pass43_channel_by_size as p43
    import pass48_screen_book as p48
    import pass52_ten_good_channels as p52
    p41.MIN_AGE = 8
    final = last_friday(today)
    uni = sorted(p43.read_universe(p43.universe_file()), key=lambda r: -float(r["cap_m"]))[:FETCH_TOP]
    info = {r["ticker"]: r for r in uni}
    cache = lab.CACHE / f"weekly_book_{today.isoformat()}_{len(uni)}.pkl"
    if cache.exists():
        with open(cache, "rb") as fh:
            frames = pickle.load(fh)
    else:
        import yfinance as yf
        names, frames = [r["ticker"] for r in uni] + ["SPY"], {}
        start = today - timedelta(days=4 * 366)
        start = (start - timedelta(days=start.weekday())).isoformat()      # a Monday, so Yahoo keys each bar on its Monday
        for i in range(0, len(names), 100):
            chunk = names[i:i + 100]
            df = None
            for attempt in range(3):
                try:
                    df = yf.download([t.replace(".", "-") for t in chunk], start=start, interval="1wk", auto_adjust=True,
                                     progress=False, group_by="ticker", threads=True)
                    break
                except Exception as e:                              # noqa: BLE001
                    print("retry", i, repr(e)[:80])
                    time.sleep(5 + 5 * attempt)
            if df is None:
                continue
            for t in chunk:
                y = t.replace(".", "-")
                if y in df.columns.get_level_values(0):
                    sub = df[y].dropna(how="all")
                    if len(sub) > 30:
                        frames[t] = sub[["Open", "High", "Low", "Close", "Volume"]].astype("float64")
            time.sleep(1.0)
        lab.CACHE.mkdir(parents=True, exist_ok=True)
        for old in lab.CACHE.glob("weekly_book_*.pkl"):
            old.unlink()
        with open(cache, "wb") as fh:
            pickle.dump(frames, fh)
    off = [t for t, f in frames.items() if len(f) and f.index[-1].weekday() != 0]
    if off:
        raise SystemExit(f"weekly bars not keyed on Mondays for {len(off)} names (e.g. {off[:3]}); not guessing which week they belong to")
    idx = pd.DatetimeIndex([d for d in frames["SPY"].index if d.weekday() == 0 and (d + pd.Timedelta(days=4)).date() <= final])
    names = sorted(t for t in frames if t in info)

    def mat(col):
        return np.column_stack([frames[t][col].reindex(idx).to_numpy(dtype=float) for t in names])
    Ow, Hw, Lw, Cw, Vw = mat("Open"), mat("High"), mat("Low"), mat("Close"), mat("Volume")
    nW, n = Cw.shape
    fridays = [(d + pd.Timedelta(days=4)).date().isoformat() for d in idx]
    spy_c = frames["SPY"]["Close"].reindex(idx).ffill().to_numpy(dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        lC = np.log(Cw)
        dv = Cw * Vw
        wr = np.diff(lC, axis=0)
    todo = [w for w in range(nW) if fridays[w] >= START and (after is None or fridays[w] > after)]
    if not todo:
        return []
    T = p52.quality_table(Cw, Hw, Lw)
    sector = [SAME.get(info[t]["sector"], info[t]["sector"]) for t in names]
    cap_now = np.array([float(info[t]["cap_m"]) for t in names])
    ref_px = np.full(n, np.nan)
    for j, t in enumerate(names):
        good = np.flatnonzero(~np.isnan(Cw[:, j]))
        if len(good):
            upto = [w for w in good if fridays[w] <= info[t]["cap_date"]]
            ref_px[j] = Cw[upto[-1] if upto else good[0], j]
    out = []
    for w in todo:
        with np.errstate(invalid="ignore", divide="ignore"):
            med_dv = np.nanmedian(dv[max(0, w - 51):w + 1], axis=0)
            hi52 = np.nanmax(Cw[max(0, w - 51):w + 1], axis=0)
            win = wr[max(0, w - 104):w]
            swing = np.where((~np.isnan(win)).sum(axis=0) >= 40, np.nanstd(win, axis=0), np.nan)
            size = cap_now * Cw[w] / ref_px
            near = (lC[w] - np.log(hi52)) / swing >= -p48.SWINGS_MAX
            back = [Cw[w] / Cw[w - k] - 1.0 for k in (4, 13, 26, 52)]
        ok = np.flatnonzero(~np.isnan(size))
        member = np.zeros(n, dtype=bool)
        member[ok[np.argsort(-size[ok])][:MEMBERS]] = True
        tradeable = (np.nan_to_num(med_dv) >= p43.DV_MIN) & (np.nan_to_num(swing) >= p48.SWING_MIN)
        channel = (~np.isnan(T["lower"][w]) & (np.nan_to_num(T["slope"][w], nan=-1.0) >= p48.FLOOR)
                   & (np.nan_to_num(T["r2"][w], nan=0.0) >= p48.R2_MIN))
        js = np.flatnonzero(member & tradeable & channel & np.nan_to_num(near, nan=0.0).astype(bool))
        if len(js) > 1:
            tr = sum(p52.ranks(np.nan_to_num(b[js], nan=-9.0)) for b in back) / 4.0
            js = js[np.argsort(-tr, kind="stable")]
        friday = fridays[w]
        out.append({"friday": friday, "week_monday": idx[w].date().isoformat(),
                    "monday": (date.fromisoformat(friday) + timedelta(days=3)).isoformat(),
                    "opens": {names[j]: float(Ow[w, j]) for j in range(n) if Ow[w, j] == Ow[w, j]},
                    "closes": {names[j]: float(Cw[w, j]) for j in range(n) if Cw[w, j] == Cw[w, j]},
                    "spy_close": float(spy_c[w]),
                    "cold": bool(w >= 39 and spy_c[w] < spy_c[w - 39:w + 1].mean()),
                    "ranked": [(names[j], sector[j], float(hi52[j])) for j in js]})
    return out


def write_page(ledger):
    L = ["# The trend-strength book, forward", "",
         "Two paper books under rules frozen on 2026-11-21 (lab Pass 63). Lab only: not the Council's picks and not advice.",
         "Orders are written on Friday's close and filled at Monday's open; 0.10% a side is charged.", ""]
    L += ["| Book | Weeks | Value (from 100) | Return | SPY over the same weeks | Largest drawdown | Names | Cash |", "|---|---|---|---|---|---|---|---|"]
    for name, book in ledger["books"].items():
        s_ = summary(book)
        if s_:
            L.append(f"| {name} | {s_['weeks']} | {s_['equity']:.2f} | {100 * s_['return']:+.1f}% | {100 * s_['spy_return']:+.1f}% | "
                     f"{100 * s_['largest_drawdown']:.1f}% | {s_['names']} | {100 * s_['cash_share']:.0f}% |")
    for name, book in ledger["books"].items():
        L += ["", f"## {name}", ""]
        if book["positions"]:
            L += ["| Holding | Sector | Bought | Last close | High | Under its high |", "|---|---|---|---|---|---|"]
            for t, p in sorted(book["positions"].items()):
                L.append(f"| {t} | {p['sector']} | {p['bought']} | {p['last_close']:.2f} | {p['high']:.2f} | {100 * (p['last_close'] / p['high'] - 1):.1f}% |")
        else:
            L.append("No holdings yet.")
        pend = book["pending"]
        if pend:
            L += ["", f"Orders for the open of {pend['enter_open_of']} (decided on {pend['decided_on']}): "
                  f"sell {', '.join(pend['sells']) or 'nothing'}; buy {', '.join(b['ticker'] for b in pend['buys']) or 'nothing'}"
                  + (f" ({pend['no_buys_because']})" if pend["no_buys_because"] and not pend["buys"] else "") + "."]
    if ledger["weeks"]:
        last = ledger["weeks"][-1]
        L += ["", f"Week ending {last['friday']}: {last['names_on_screen']} names on the screen; market {'cold' if last['cold'] else 'not cold'}; "
              f"highest trend strength: {', '.join(last['top_ten'])}.", ""]
    with open(PAGE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")


def main(argv):
    plan = len(argv) > 1 and argv[1] == "plan"
    if LEDGER.exists():
        with open(LEDGER, encoding="utf-8") as fh:
            ledger = json.load(fh)
    else:
        ledger = {"schema": "book-ledger/v1", "started": START, "rules": "lab/README.md, Pass 63", "books": {}, "weeks": []}
    after = ledger["weeks"][-1]["friday"] if ledger["weeks"] else None
    done = 0
    for week in weeks_since(after, date.today()):
        done += step(ledger, week)
    for name, book in ledger["books"].items():
        pend, s_ = book["pending"], summary(book)
        print(f"{name}: value {s_['equity']:.2f} after {s_['weeks']} week(s), {s_['names']} names; "
              f"for {pend['enter_open_of']} sell {pend['sells'] or 'nothing'}, buy {[b['ticker'] for b in pend['buys']] or 'nothing'}"
              + (f" ({pend['no_buys_because']})" if pend["no_buys_because"] else ""))
    print(f"{done} new week(s)" + (" (plan only, nothing written)" if plan else ""))
    if not plan and done:
        with open(LEDGER, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(ledger, fh, indent=1)
            fh.write("\n")
        write_page(ledger)


if __name__ == "__main__":
    main(sys.argv)
