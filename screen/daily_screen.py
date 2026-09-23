# daily_screen.py - one-shot daily channel + MACD + overhead screen.
# Python 3 standard library only. ASCII output (Windows safe).
# Usage:  python daily_screen.py            (skips weekends automatically)
#         python daily_screen.py --force    (run on any day)
# Output (in ./reports):  screen_YYYY-MM-DD.csv, screen_YYYY-MM-DD.html,
#                         first_seen.json (tracks which names are NEW each day)
#
# The owner's screener (2026-09-23), run weekdays by .github/workflows/daily-screen.yml
# and committed to screen/reports/, so every day's hits are a point-in-time record
# the Testing Room can score later. Three changes from the owner's original, all
# guards: the run fails loudly when the universe comes back small (mid-session
# the listing's volume is partial and the dollar-volume filter keeps ~400 names
# instead of ~1800) or when the price fetch covers less than half of it (an
# empty report must never be committed as a quiet day); the HTML declares
# utf-8; a --date override lets a missed day be re-run by hand. --force skips
# the weekend and universe checks for a smoke test, never for the record.
import json, math, os, sys, time, datetime, statistics, urllib.request

UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
MIN_UNIVERSE       = 1000           # a pre-open run lists ~1800; fewer means the listing's volume is partial
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

def _spark(batch):
    d = get("https://query1.finance.yahoo.com/v7/finance/spark?symbols=" + ",".join(batch) + "&range=2y&interval=1d")
    out = {}
    for x in ((d or {}).get("spark", {}) or {}).get("result", []) or []:
        try:
            c = [v for v in x["response"][0]["indicators"]["quote"][0]["close"] if v]
            if len(c) >= 260: out[x["symbol"]] = c
        except Exception:
            pass
    return out

def prices(symbols):
    out = {}
    for i in range(0, len(symbols), 20):
        b = symbols[i:i + 20]
        got = _spark(b)
        if not got:                     # a throttled batch: wait, then ask again in halves
            time.sleep(5)
            for half in (b[:10], b[10:]):
                if half: got.update(_spark(half)); time.sleep(0.5)
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

def main():
    today = datetime.date.today()
    for i, arg in enumerate(sys.argv):
        if arg == "--date" and i + 1 < len(sys.argv):
            today = datetime.date.fromisoformat(sys.argv[i + 1])       # the stamp for a re-run by hand
    if today.weekday() >= 5 and "--force" not in sys.argv:
        print("Weekend - nothing to do."); return
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    U = universe()
    if not U:
        print("ERROR: universe download failed."); sys.exit(1)
    if len(U) < MIN_UNIVERSE and "--force" not in sys.argv:
        # Mid-session the listing's volume is the forming day's, and the dollar-volume
        # filter keeps a few hundred names instead of ~1800. Run before the open.
        print("ERROR: universe has %d names (under %d): the listing's volume looks partial; run before the open."
              % (len(U), MIN_UNIVERSE)); sys.exit(1)
    P = prices(sorted(U))
    if len(P) < MIN_PRICE_COVERAGE * len(U):
        print("ERROR: prices for only %d of %d names; not writing a report." % (len(P), len(U))); sys.exit(1)
    rows = []
    for t, c in P.items():
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
        fs.setdefault(r["ticker"], today.isoformat())
    json.dump(fs, open(fs_path, "w", encoding="utf-8"), indent=0)
    stamp = today.isoformat()
    cols = ["tier", "new", "ticker", "price", "cap_b", "macd", "exit_40d_low", "exit_dist", "to_2y_high",
            "overhead", "ceilings", "base_25d", "above_50d", "chan_pct_yr", "z", "off_hi", "sector", "industry", "flags"]
    with open(os.path.join(OUT, "screen_%s.csv" % stamp), "w", newline="", encoding="utf-8") as f:
        f.write(",".join(cols) + "\n")
        for r in rows: f.write(",".join('"%s"' % str(r[c]).replace('"', "'") for c in cols) + "\n")
    desc = {"A": "Tier A - clean setup AND clean air above (Alex's rule)",
            "B": "Tier B - clean setup, but overhead in the way",
            "C": "Tier C - almost: under $50, just crossed or about to"}
    html = ["<html><head><meta charset='utf-8'><title>Screen %s</title><style>"
            "body{font-family:Calibri,Arial;margin:24px;color:#222}h1{color:#1F3864}h2{color:#1F3864;margin-top:28px}"
            "table{border-collapse:collapse;font-size:13px}td,th{border:1px solid #ccc;padding:4px 7px;text-align:right}"
            "th{background:#D9E2F3}td.l{text-align:left}.new{color:#1E7A1E;font-weight:bold}</style></head><body>" % stamp,
            "<h1>Daily Channel Screen - %s</h1><p>%d names screened in %d seconds. %d hits. Rate-sensitive names excluded. "
            "Prices are the prior close. Chart-only reads: check catalysts and the daily chart before acting. "
            "Educational, not advice.</p>" % (stamp, len(P), time.time() - t0, len(rows))]
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
    open(os.path.join(OUT, "screen_%s.html" % stamp), "w", encoding="utf-8", errors="replace").write("\n".join(html))
    print("Done: %d screened, %d hits (A=%d B=%d C=%d) -> %s" % (len(P), len(rows),
          sum(r["tier"] == "A" for r in rows), sum(r["tier"] == "B" for r in rows),
          sum(r["tier"] == "C" for r in rows), OUT))

if __name__ == "__main__":
    main()
