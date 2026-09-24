# daily_screen.py - the Butterfly Net: a daily channel + MACD + overhead screen.
# Python 3 standard library only. ASCII output (Windows safe).
# Usage:  python daily_screen.py            (the report for the next session)
#         python daily_screen.py --force    (run even in the session, or over an existing report)
#         python daily_screen.py --date YYYY-MM-DD   (stamp a re-run by hand)
# Output (in ./reports):  screen_YYYY-MM-DD.csv, screen_YYYY-MM-DD.html, latest.html,
#                         first_seen.json (tracks which names are NEW each day),
#                         runs.json (when each report ran and whose closes it used)
#
# The owner's screener (2026-09-23), named the Butterfly Net on 2026-09-24. It
# runs weekday evenings after the US close, for the next session: the report
# dated D is the list for session D, built on closes through the session
# before it. Run before the open, it is the list for that day's session; it
# refuses to run while the session is open (the listing's volume is partial,
# and the day's bar is not a close), and it drops any bar that has not closed.
# .github/workflows/daily-screen.yml runs it and commits screen/reports/, so
# every report is a point-in-time record the Testing Room can score later.
#
# Guards, none of which change the owner's rules: the run fails loudly when the
# universe comes back small or prices cover less than half of it (an empty
# report must never be committed as a quiet day); a report that already
# exists is not redone; a throttled price batch is retried in halves.
import json, math, os, sys, time, datetime, statistics, urllib.request

NAME = "The Butterfly Net"
UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
MIN_UNIVERSE       = 1000           # a full-volume listing gives ~1800; fewer means the volume is partial
MIN_PRICE_COVERAGE = 0.5            # fail the run below this share of the universe with prices

# ---------------- rules (edit here) ----------------
CAP_MIN, CAP_MAX = 300e6, 10e9      # small and mid caps
PRICE_MIN        = 3.0
DOLLAR_VOL_MIN   = 5e6              # traded per day
# Tier A/B (clean):  channel >= 20%/yr, z -2.2..-0.3, 8-30% off 120d high, MACD cross <= 5d or turning
# Tier C (almost):   under $50, channel >= 10%/yr, z -2.5..+0.3, 5-35% off high, cross <= 3d or within 0.35%
# Overhead ("clean air", Alex's rule): overhead days <= 12%, <= 25% to 2y high, <= 1 ceiling, 25d base <= 18%
MAX_EXIT_DIST = 20.0                # drop names whose exit (40d low) is further than this, in %
EXCLUDE = {"XHR", "CXW", "CDP"}     # hand-maintained: REITs the listing data mislabels, or names you never want

# ---------------- the clock (US Eastern, no tz database needed) ----------------
def eastern(utc):
    """US Eastern wall time for a UTC datetime: EDT from the second Sunday of March
    (2:00 local) to the first Sunday of November (2:00 local), EST otherwise."""
    u = utc.replace(tzinfo=None)
    def sunday(month, n):
        d = datetime.datetime(u.year, month, 1)
        return d + datetime.timedelta(days=(6 - d.weekday()) % 7, weeks=n - 1)
    dst = sunday(3, 2) + datetime.timedelta(hours=7) <= u < sunday(11, 1) + datetime.timedelta(hours=6)
    return u - datetime.timedelta(hours=4 if dst else 5)

def in_session(et):
    return et.weekday() < 5 and (9, 30) <= (et.hour, et.minute) < (16, 0)

def next_weekday(d):
    d += datetime.timedelta(days=1)
    while d.weekday() >= 5:
        d += datetime.timedelta(days=1)
    return d

def session_for(et):
    """The session a run at US Eastern time et is for: today's before the open, the next weekday's after it."""
    return et.date() if (et.weekday() < 5 and (et.hour, et.minute) < (9, 30)) else next_weekday(et.date())

def get(url, tries=3):
    for i in range(tries):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40))
        except Exception:
            time.sleep(2 + 2 * i)
    return None

def ema(x, n):
    k = 2 / (n + 1); e = [x[0]]
    for v in x[1:]: e.append(v * k + e[-1] * (1 - k))
    return e

def reg_z(y):
    n = len(y); mx = (n - 1) / 2; my = sum(y) / n
    b = sum((i - mx) * (v - my) for i, v in enumerate(y)) / sum((i - mx) ** 2 for i in range(n))
    r = [v - (my + b * (i - mx)) for i, v in enumerate(y)]
    sd = (sum(t * t for t in r) / (n - 2)) ** 0.5
    return b, (r[-1] / sd if sd else 0.0)

def universe():
    d = get("https://api.nasdaq.com/api/screener/stocks?tableonly=true&download=true")
    rows = (d or {}).get("data", {}).get("rows", []) or []
    U = {}
    for r in rows:
        s = r.get("symbol", "")
        if not s or any(ch in s for ch in "^/ "): continue
        try:
            mc = float(r.get("marketCap") or 0)
            px = float(str(r.get("lastsale", "0")).replace("$", "").replace(",", ""))
            vol = float(r.get("volume") or 0)
        except ValueError:
            continue
        if CAP_MIN <= mc <= CAP_MAX and px >= PRICE_MIN and px * vol >= DOLLAR_VOL_MIN:
            U[s] = dict(mc=mc, sector=r.get("sector", "") or "", industry=r.get("industry", "") or "")
    return U

def _spark(batch, now_et):
    """{symbol: (closes, date of the last close)}; a bar for a session still open is dropped."""
    d = get("https://query1.finance.yahoo.com/v7/finance/spark?symbols=" + ",".join(batch) + "&range=2y&interval=1d")
    out = {}
    for x in ((d or {}).get("spark", {}) or {}).get("result", []) or []:
        try:
            r = x["response"][0]
            bars = [(eastern(datetime.datetime.fromtimestamp(t, datetime.timezone.utc)).date(), v)
                    for t, v in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]) if v]
            if bars and bars[-1][0] == now_et.date() and (now_et.hour, now_et.minute) < (16, 0):
                bars = bars[:-1]
            if len(bars) >= 260: out[x["symbol"]] = ([v for _, v in bars], bars[-1][0])
        except Exception:
            pass
    return out

def prices(symbols, now_et):
    out = {}
    for i in range(0, len(symbols), 20):
        b = symbols[i:i + 20]
        got = _spark(b, now_et)
        if not got:                     # a throttled batch: wait, then ask again in halves
            time.sleep(5)
            for half in (b[:10], b[10:]):
                if half: got.update(_spark(half, now_et)); time.sleep(0.5)
        out.update(got)
        time.sleep(0.25)
    return out

def analyze(c):
    p = c[-1]
    s50 = sum(c[-50:]) / 50; s200 = sum(c[-200:]) / 200; s200p = sum(c[-220:-20]) / 200
    b, z = reg_z([math.log(v) for v in c[-120:]]); chan = (math.exp(b * 252) - 1) * 100
    dd = (p / max(c[-120:]) - 1) * 100
    lo40 = min(c[-41:-1])
    m = [a - b2 for a, b2 in zip(ema(c, 12), ema(c, 26))]; sg = ema(m, 9); h = [a - b2 for a, b2 in zip(m, sg)]
    cross = next((k for k in range(1, 6) if h[-k] > 0 and h[-k - 1] <= 0), None)
    gap = abs(h[-1]) / p * 100
    turning = h[-1] < 0 and h[-1] > h[-2] > h[-3]
    hi2 = max(c); over = sum(1 for v in c[:-1] if v > p) / len(c) * 100
    w = 10; sw = sorted(c[i] for i in range(w, len(c) - w) if c[i] == max(c[i - w:i + w + 1]) and c[i] > p * 1.02)
    ceil = []
    for v in sw:
        if not ceil or v > ceil[-1] * 1.03: ceil.append(v)
    base = (max(c[-25:]) / min(c[-25:]) - 1) * 100
    r = [c[i] / c[i - 1] - 1 for i in range(1, len(c))]
    contract = statistics.pstdev(r[-15:]) / (statistics.pstdev(r[-60:]) or 1)
    return dict(px=p, up=(p > s200 and s200 > s200p), s50ok=s50 > s200, s50near=s50 > 0.97 * s200,
                above50=p > s50, chan=chan, z=z, dd=dd, lo40=lo40, fresh_low=p < lo40,
                cross=cross, gap=gap, turning=turning, to_hi=(hi2 / p - 1) * 100, over=over,
                ceil=len(ceil), base=base, contract=contract)

def tier(a):
    if a["fresh_low"] or (a["lo40"] / a["px"] - 1) * 100 < -MAX_EXIT_DIST: return None
    clean = (a["up"] and a["s50ok"] and a["chan"] >= 20 and -2.2 <= a["z"] <= -0.3 and -30 <= a["dd"] <= -8
             and (a["cross"] is not None or (a["turning"] and a["gap"] < 0.6)))
    air = a["over"] <= 12 and a["to_hi"] <= 25 and a["ceil"] <= 1 and a["base"] <= 18
    if clean and air: return "A"
    if clean: return "B"
    almost = (a["px"] < 50 and a["up"] and a["s50near"] and a["chan"] >= 10 and -2.5 <= a["z"] <= 0.3
              and -35 <= a["dd"] <= -5 and ((a["cross"] is not None and a["cross"] <= 3) or (a["turning"] and a["gap"] < 0.35)))
    return "C" if almost else None

def flags(meta):
    s, ind = meta["sector"], meta["industry"].lower()
    f = []
    if "Real Estate" in s or "bank" in ind or "savings institution" in ind or "reit" in ind or "real estate investment" in ind:
        f.append("RATE-SENSITIVE")
    if "biotech" in ind or "pharmaceutical" in ind: f.append("BIOTECH")
    return f

def summary(stamp, through, rows, screened, cols):
    """The run page on GitHub shows this (GITHUB_STEP_SUMMARY): the day's hits, readable."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path: return
    show = ["ticker", "price", "macd", "exit_dist", "overhead", "ceilings", "sector"]
    lines = ["## %s - for the session of %s" % (NAME, stamp), "",
             "Closes through %s. %d names screened, %d hits (A %d, B %d, C %d). NEW = first time on the net." % (
                 through, screened, len(rows), *(sum(r["tier"] == t for r in rows) for t in "ABC")), ""]
    for t, title in (("A", "Tier A - clean setup, clean air"), ("B", "Tier B - clean setup, overhead in the way"),
                     ("C", "Tier C - almost, under $50")):
        sub = [r for r in rows if r["tier"] == t]
        lines += ["### %s (%d)" % (title, len(sub)), ""]
        if not sub: lines += ["None.", ""]; continue
        lines += ["| new | " + " | ".join(show) + " |", "|---" * (len(show) + 1) + "|"]
        lines += ["| %s | %s |" % (r["new"], " | ".join(str(r[c]) for c in show)) for r in sub[:25]]
        lines += [""]
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

def main():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_et = eastern(now_utc)
    force = "--force" in sys.argv
    if in_session(now_et) and not force:
        print("ERROR: the US session is open (%s ET). %s runs after the close for the next session." %
              (now_et.strftime("%H:%M"), NAME)); sys.exit(1)
    stamp = session_for(now_et)
    for i, arg in enumerate(sys.argv):
        if arg == "--date" and i + 1 < len(sys.argv):
            stamp = datetime.date.fromisoformat(sys.argv[i + 1])       # the stamp for a re-run by hand
    stamp = stamp.isoformat()
    os.makedirs(OUT, exist_ok=True)
    if os.path.exists(os.path.join(OUT, "screen_%s.csv" % stamp)) and not force:
        print("The report for %s already exists; nothing to do." % stamp); return
    t0 = time.time()
    U = universe()
    if not U:
        print("ERROR: universe download failed."); sys.exit(1)
    if len(U) < MIN_UNIVERSE and not force:
        print("ERROR: universe has %d names (under %d): the listing's volume looks partial." % (len(U), MIN_UNIVERSE)); sys.exit(1)
    P = prices(sorted(U), now_et)
    if len(P) < MIN_PRICE_COVERAGE * len(U):
        print("ERROR: prices for only %d of %d names; not writing a report." % (len(P), len(U))); sys.exit(1)
    through = statistics.mode(d for _, d in P.values()).isoformat()
    rows = []
    for t, (c, _) in P.items():
        try:
            a = analyze(c)
        except Exception:
            continue
        tr = tier(a)
        if not tr: continue
        fl = flags(U[t])
        if "RATE-SENSITIVE" in fl or t in EXCLUDE: continue
        macd = ("cross %dd" % a["cross"]) if a["cross"] else ("%.2f%% away, rising" % a["gap"])
        rows.append(dict(tier=tr, ticker=t, price=round(a["px"], 2), cap_b=round(U[t]["mc"] / 1e9, 2),
                         sector=U[t]["sector"][:22], industry=U[t]["industry"][:34], macd=macd,
                         chan_pct_yr=round(a["chan"]), z=round(a["z"], 2), off_hi=round(a["dd"], 1),
                         exit_40d_low=round(a["lo40"], 2), exit_dist=round((a["lo40"] / a["px"] - 1) * 100, 1),
                         to_2y_high=round(a["to_hi"], 1), overhead=round(a["over"], 1), ceilings=a["ceil"],
                         base_25d=round(a["base"], 1), above_50d="Y" if a["above50"] else "n",
                         flags=" ".join(fl)))
    rows.sort(key=lambda r: (r["tier"], r["overhead"], r["exit_dist"] * -1))
    # NEW today tracking
    fs_path = os.path.join(OUT, "first_seen.json")
    fs = json.load(open(fs_path, encoding="utf-8")) if os.path.exists(fs_path) else {}
    for r in rows:
        r["new"] = "NEW" if r["ticker"] not in fs else ""
        fs.setdefault(r["ticker"], stamp)
    json.dump(fs, open(fs_path, "w", encoding="utf-8"), indent=0)
    cols = ["tier", "new", "ticker", "price", "cap_b", "macd", "exit_40d_low", "exit_dist", "to_2y_high",
            "overhead", "ceilings", "base_25d", "above_50d", "chan_pct_yr", "z", "off_hi", "sector", "industry", "flags"]
    with open(os.path.join(OUT, "screen_%s.csv" % stamp), "w", newline="", encoding="utf-8") as f:
        f.write(",".join(cols) + "\n")
        for r in rows: f.write(",".join('"%s"' % str(r[c]).replace('"', "'") for c in cols) + "\n")
    desc = {"A": "Tier A - clean setup AND clean air above (Alex's rule)",
            "B": "Tier B - clean setup, but overhead in the way",
            "C": "Tier C - almost: under $50, just crossed or about to"}
    html = ["<html><head><meta charset='utf-8'><title>%s - %s</title><style>"
            "body{font-family:Calibri,Arial;margin:24px;color:#222}h1{color:#1F3864}h2{color:#1F3864;margin-top:28px}"
            "table{border-collapse:collapse;font-size:13px}td,th{border:1px solid #ccc;padding:4px 7px;text-align:right}"
            "th{background:#D9E2F3}td.l{text-align:left}.new{color:#1E7A1E;font-weight:bold}</style></head><body>" % (NAME, stamp),
            "<h1>%s - for the session of %s</h1><p>Closes through %s (run %s ET). %d names screened in %d seconds. "
            "%d hits. Rate-sensitive names excluded. Chart-only reads: check catalysts and the daily chart before "
            "acting. Educational, not advice.</p>" % (NAME, stamp, through, now_et.strftime("%Y-%m-%d %H:%M"),
                                                       len(P), time.time() - t0, len(rows))]
    for tr in "ABC":
        sub = [r for r in rows if r["tier"] == tr]
        html.append("<h2>%s (%d)</h2>" % (desc[tr], len(sub)))
        if not sub: html.append("<p>None today.</p>"); continue
        html.append("<table><tr>" + "".join("<th>%s</th>" % c for c in cols[1:]) + "</tr>")
        for r in sub:
            cells = []
            for c in cols[1:]:
                v = r[c]; cls = " class='l'" if c in ("ticker", "macd", "sector", "industry", "flags", "new") else ""
                if c == "new" and v: cells.append("<td class='l new'>NEW</td>")
                else: cells.append("<td%s>%s</td>" % (cls, v))
            html.append("<tr>" + "".join(cells) + "</tr>")
        html.append("</table>")
    html.append("</body></html>")
    for name in ("screen_%s.html" % stamp, "latest.html"):
        open(os.path.join(OUT, name), "w", encoding="utf-8", errors="replace").write("\n".join(html))
    runs_path = os.path.join(OUT, "runs.json")
    runs = json.load(open(runs_path, encoding="utf-8")) if os.path.exists(runs_path) else []
    hits = {t: sum(r["tier"] == t for r in rows) for t in "ABC"}
    runs.append({"session": stamp, "run_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "run_et": now_et.strftime("%Y-%m-%d %H:%M"), "closes_through": through, "universe": len(U),
                 "screened": len(P), "hits": hits, "forced": force})
    json.dump(runs, open(runs_path, "w", encoding="utf-8"), indent=1)
    summary(stamp, through, rows, len(P), cols)
    print("Done: %s for %s, closes through %s: %d screened, %d hits (A=%d B=%d C=%d) -> %s" % (
        NAME, stamp, through, len(P), len(rows), hits["A"], hits["B"], hits["C"], OUT))

if __name__ == "__main__":
    main()
