# 182-ticker universe (ported from constants.ts / data/ticker_ledger.ts)

AVAILABLE_TICKERS = [
    # Tech & Comm Services
    "AAPL", "ACN", "ADBE", "ADSK", "AKAM", "AMAT", "AMD", "ANET", "APH", "AVGO",
    "CDNS", "CRM", "CSCO", "EA", "FTNT", "GOOG", "GOOGL", "HPE", "INTC", "INTU",
    "IONQ", "KLAC", "LRCX", "META", "MSFT", "MSI", "MU", "NFLX", "NOW", "NTLA",
    "NVDA", "NXPI", "ORCL", "PANW", "QBTS", "QCOM", "QUBT", "RBLX", "RGTI", "ROKU",
    "SIDU", "SMCI", "SNPS", "SYM", "TEL", "TER", "VSAT", "ZS",
    # Consumer & Retail
    "ABNB", "AMZN", "AZO", "CMG", "COST", "DPZ", "HD", "HLT", "KDP", "KMB", "KO",
    "LOW", "MAR", "MCD", "MDLZ", "MNST", "MO", "NKE", "ORLY", "PEP", "PG", "ROST",
    "SBUX", "SJM", "TGT", "TPR", "TSLA", "WMT", "YUM",
    # Financials
    "AFL", "AIG", "AJG", "ALL", "AMP", "AON", "APO", "AXP", "BAC", "BK", "BLK",
    "BX", "C", "CB", "CME", "COIN", "CPAY", "GS", "HIG", "JKHY", "JPM", "KEY",
    "KKR", "MA", "MCO", "MMC", "MS", "PAYX", "PGR", "PRU", "PYPL", "SPGI", "TROW",
    "TRV", "UPST", "V", "WFC", "WRB",
    # Healthcare
    "ABBV", "AMGN", "BAX", "BDX", "BFLY", "BIIB", "BMY", "BSX", "CI", "CVS",
    "DHR", "DXCM", "ELV", "EW", "GEHC", "GILD", "HCA", "HUM", "IDXX", "ILMN",
    "IQV", "ISRG", "JNJ", "KVUE", "LLY", "MCK", "MDT", "MRK", "MRNA", "PFE",
    "REGN", "SOLV", "SYK", "TMO", "UNH", "VEEV", "VRTX", "ZTS",
    # Industrials & Aerospace
    "AXON", "BA", "CARR", "CAT", "CPRT", "CSX", "CTAS", "DE", "EMR", "ETN",
    "FAST", "FDX", "GD", "GE", "GEV", "GWW", "HON", "ITW", "JCI", "LMT", "MMM",
    "NDSN", "NOC", "NSC", "ODFL", "OTIS", "PCAR", "PH", "PNR", "PWR", "ROP",
    "RSG", "RTX", "TDG", "TXT", "UNP", "UPS", "URI", "VMI", "WM", "XYL",
    # Energy & Materials
    "APD", "BKR", "CVX", "DD", "DOW", "ECL", "EOG", "FCX", "HAL", "HES", "KMI",
    "LIN", "LYB", "MPC", "NEM", "NUE", "OKE", "OXY", "PPG", "PSX", "SHW", "SLB",
    "VLO", "WMB", "XOM",
    # Real Estate
    "AMT", "ARE", "AVB", "BXP", "CBRE", "CCI", "COLD", "COR", "CPT", "DLR",
    "EQIX", "EQR", "ESS", "EXR", "FRT", "GLPI", "HST", "INVH", "IRM", "KIM",
    "MAA", "O", "PEAK", "PLD", "PSA", "REG", "SBAC", "SPG", "UDR", "VICI",
    "VTR", "WELL", "WY",
    # Utilities
    "AEP", "AES", "ATO", "AWK", "CMS", "CNP", "D", "DUK", "ED", "EIX", "ES",
    "ETR", "EVRG", "EXC", "FE", "LNT", "NEE", "NI", "NRG", "PEG", "PPL", "SO",
    "SRE", "WEC", "XEL",
]

STOCK_UNIVERSE = sorted(AVAILABLE_TICKERS)

# 44 tickers added to the committed weekly panel on 2026-08-26 (BACKFILL_44,
# repo-side merge with per-series provenance). The DATA FEED must keep them:
# equity_universe() includes this set so the Saturday builder's full-file
# rewrite never silently drops them (the exact failure mode of the 8/26
# incident, this time through the "normal" path). The ENGINES do not scan
# these -- they stay on STOCK_UNIVERSE so Monday fetch time is unchanged.
BACKFILL_44_TICKERS = [
    "ALB", "BKNG", "BLFS", "CALM", "CCJ", "CEG", "COP", "CRSP", "CRWD", "CVNA",
    "DDOG", "DIS", "FIVE", "FIZZ", "FSLR", "HIMS", "IMAX", "INOD", "LNG", "LYV",
    "MLM", "MOD", "MP", "MTCH", "OKLO", "ORA", "PLTR", "PM", "RDDT", "RKLB",
    "SCHW", "SM", "SOFI", "SOUN", "SPCX", "SPOT", "SSD", "STZ", "TMUS", "TSM",
    "TTWO", "ULTA", "UMH", "VST",
]

# ---------------------------------------------------------------------------
# The price feed, and the analysis universe inside it
# ---------------------------------------------------------------------------
# PRICE_FEED_UNIVERSE is what data/weekly and data/daily commit: every name the
# scan fetches. STOCK_UNIVERSE is what the ENGINES scan and is deliberately
# narrower, so Monday fetch time is unchanged; the 44 backfilled names are fed
# and stored but not scanned.
#
# This constant exists because its absence was a live defect. Commit 009f7f6
# added SECTOR_FOCUS_110, FOCUS_TICKERS and two asserts; 7cf7025 deleted all
# four and left AVAILABLE_TICKERS at 277. The assert that broke was
# `FOCUS_TICKERS <= STOCK_UNIVERSE`, which cannot hold at 277 -- only 66 of the
# 110 are in it -- so the block was removed rather than the bound corrected.
# CLAUDE.md went on documenting all of it for two weeks and nothing failed,
# because this repo has no config-drift gate.
#
# The correct bound is the FEED, not the engine set. 277 | 44 = 321, which is
# the number the docs claimed all along.
PRICE_FEED_UNIVERSE = sorted(set(STOCK_UNIVERSE) | set(BACKFILL_44_TICKERS))


# ---------------------------------------------------------------------------
# Sector-focus set
# ---------------------------------------------------------------------------
# The 110-name Seven Orbs watchlist: 11 GICS sectors x 10 names, equal-weighted
# into sector baskets for breadth, relative momentum and volume confirmation.
# This is the ANALYSIS universe. The price feed above is deliberately wider --
# dropping to 110 would strip coverage from 22 names Arena and the portfolio
# actively hold (C, MRK and SIDU among them).
#
# Authoritative copy lives in the sector-regime-heatmap repo at
# config/watchlist_110.csv, cap-descending. Keep them in sync: this copy is a
# transcription and the CSV wins any disagreement.
SECTOR_FOCUS_110 = {
    "Communication Services": ["META", "NFLX", "TMUS", "DIS", "SPOT", "TTWO", "LYV", "RDDT", "MTCH", "IMAX"],
    "Consumer Discretionary": ["AMZN", "TSLA", "HD", "MCD", "BKNG", "ABNB", "CVNA", "NKE", "ULTA", "FIVE"],
    "Consumer Staples": ["WMT", "COST", "KO", "PG", "PM", "PEP", "MDLZ", "STZ", "CALM", "FIZZ"],
    "Energy": ["XOM", "CVX", "COP", "VLO", "WMB", "SLB", "LNG", "CCJ", "FSLR", "SM"],
    "Financials": ["JPM", "V", "MA", "GS", "SCHW", "BLK", "PGR", "COIN", "SOFI", "UPST"],
    "Healthcare": ["LLY", "JNJ", "UNH", "TMO", "VRTX", "ISRG", "REGN", "HIMS", "CRSP", "BLFS"],
    "Industrials": ["SPCX", "CAT", "GE", "DE", "ETN", "LMT", "CSX", "HON", "RKLB", "MOD"],
    "Materials": ["LIN", "NEM", "FCX", "SHW", "ECL", "NUE", "MLM", "ALB", "MP", "SSD"],
    "Real Estate": ["WELL", "PLD", "EQIX", "AMT", "SPG", "PSA", "O", "VICI", "AVB", "UMH"],
    "Technology": ["NVDA", "GOOGL", "TSM", "AMD", "PLTR", "CRWD", "DDOG", "RGTI", "SOUN", "INOD"],
    "Utilities": ["NEE", "CEG", "D", "SRE", "XEL", "VST", "ATO", "AWK", "OKLO", "ORA"],
}

FOCUS_TICKERS = sorted(t for ts in SECTOR_FOCUS_110.values() for t in ts)

assert len(SECTOR_FOCUS_110) == 11, "sector focus set must hold all 11 GICS sectors"
assert len(FOCUS_TICKERS) == 110, "sector focus set must hold exactly 110 names"
assert len(set(FOCUS_TICKERS)) == 110, "sector focus set must not repeat a name"
# Bound against the FEED, not the engine set. This is the assert that was
# wrong before and took the whole block down with it.
assert set(FOCUS_TICKERS) <= set(PRICE_FEED_UNIVERSE), (
    "focus set must be a subset of the price feed; missing: "
    + ", ".join(sorted(set(FOCUS_TICKERS) - set(PRICE_FEED_UNIVERSE))))


# Engine configuration constants (ported from constants.ts ENGINE_CONFIG)
ENGINE_CONFIG = {
    "max_position_size": 0.30,
    "min_position_size": 0.10,
    "consensus_alpha": 0.3,
    "big_win_threshold": 0.03,
    "big_loss_threshold": -0.03,
}
