# 321-ticker universe: the original 277 plus the 44 Seven Orbs names that were
# absent. Expanded 2026-08-25 so the price feed is a superset of both the
# sector-focus watchlist and everything Arena and the portfolio touch.
# A price feed costs one call per name; it must never be narrower than the
# positions being scored against it.

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
    # --- Seven Orbs watchlist additions (2026-08-25) ---
    "ALB", "BKNG", "BLFS", "CALM", "CCJ", "CEG", "COP", "CRSP", "CRWD", "CVNA",
    "DDOG", "DIS", "FIVE", "FIZZ", "FSLR", "HIMS", "IMAX", "INOD", "LNG", "LYV",
    "MLM", "MOD", "MP", "MTCH", "OKLO", "ORA", "PLTR", "PM", "RDDT", "RKLB",
    "SCHW", "SM", "SOFI", "SOUN", "SPCX", "SPOT", "SSD", "STZ", "TMUS", "TSM",
    "TTWO", "ULTA", "UMH", "VST",
]

STOCK_UNIVERSE = sorted(AVAILABLE_TICKERS)


# ---------------------------------------------------------------------------
# Sector-focus set
# ---------------------------------------------------------------------------
# The 110-name Seven Orbs watchlist: 11 GICS sectors x 10 names, equal-weighted
# into sector baskets for breadth, relative momentum and volume confirmation.
# This is the ANALYSIS universe. STOCK_UNIVERSE above is the PRICE FEED, and is
# deliberately wider -- dropping to 110 would strip coverage from 22 names that
# Arena and the portfolio actively hold (C, MRK and SIDU among them).
#
# Authoritative copy lives in the sector-regime-heatmap repo at
# config/watchlist_110.csv. Keep them in sync; scripts/check_focus_sync.py
# in that repo compares the two.
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
assert len(FOCUS_TICKERS) == 110, "sector focus set must hold exactly 110 names"
assert set(FOCUS_TICKERS) <= set(STOCK_UNIVERSE), "focus set must be a subset of the price feed"


# Engine configuration constants (ported from constants.ts ENGINE_CONFIG)
ENGINE_CONFIG = {
    "max_position_size": 0.30,
    "min_position_size": 0.10,
    "consensus_alpha": 0.3,
    "big_win_threshold": 0.03,
    "big_loss_threshold": -0.03,
}
