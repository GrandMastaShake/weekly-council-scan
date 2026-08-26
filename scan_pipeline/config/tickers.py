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

# Engine configuration constants (ported from constants.ts ENGINE_CONFIG)
ENGINE_CONFIG = {
    "max_position_size": 0.30,
    "min_position_size": 0.10,
    "consensus_alpha": 0.3,
    "big_win_threshold": 0.03,
    "big_loss_threshold": -0.03,
}
