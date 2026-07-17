#!/usr/bin/env python3
"""
Sector Correlation Heatmap Generator
Fetches 30-day price history for all sector ETFs, computes a correlation matrix,
and generates a PNG heatmap saved to assets/ with a dated filename.
"""

import os
import sys
from datetime import datetime, timedelta

# --- Configuration ---
SECTORS = {
    "SPY": "S&P 500",
    "XLK": "Technology",
    "SMH": "Semiconductors",
    "XLY": "Consumer Discretionary",
    "XLI": "Industrials",
    "XLB": "Materials",
    "XLC": "Communication Services",
    "XLF": "Financials",
    "XLV": "Healthcare",
    "XLU": "Utilities",
    "XLRE": "Real Estate",
    "XLE": "Energy",
    "XLP": "Consumer Staples",
}

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
PERIOD_DAYS = 30


def fetch_close_prices(ticker: str, days: int = PERIOD_DAYS):
    """Fetch daily close prices for the last N days using yfinance."""
    import yfinance as yf

    end = datetime.now()
    start = end - timedelta(days=days + 5)  # buffer for weekends/holidays
    df = yf.download(ticker, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), progress=False)
    if df.empty:
        return None
    # yfinance returns MultiIndex columns in recent versions
    if isinstance(df.columns, pd.MultiIndex):
        closes = df["Close"][ticker]
    else:
        closes = df["Close"]
    return closes.dropna()


def generate_heatmap(correlation_matrix, labels, output_path):
    """Generate and save a seaborn heatmap."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    plt.figure(figsize=(14, 12))
    mask = np.triu(np.ones_like(correlation_matrix, dtype=bool), k=1)
    cmap = sns.diverging_palette(250, 15, s=75, l=40, n=9, center="light", as_cmap=True)

    sns.heatmap(
        correlation_matrix,
        mask=mask,
        annot=True,
        fmt=".2f",
        cmap=cmap,
        vmin=-1,
        vmax=1,
        center=0,
        square=True,
        linewidths=0.5,
        cbar_kws={"shrink": 0.75, "label": "Correlation"},
        xticklabels=labels,
        yticklabels=labels,
        annot_kws={"size": 9},
    )

    plt.title(
        f"Sector ETF Correlation Matrix ({PERIOD_DAYS}-Day Rolling)\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} ET",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )
    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.yticks(rotation=0, fontsize=9)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    return output_path


def main():
    global pd, np
    import pandas as pd
    import numpy as np

    os.makedirs(ASSETS_DIR, exist_ok=True)

    print(f"Fetching {PERIOD_DAYS}-day price data for {len(SECTORS)} tickers...")
    price_data = {}
    for ticker in SECTORS:
        prices = fetch_close_prices(ticker)
        if prices is not None and len(prices) >= PERIOD_DAYS // 2:
            price_data[ticker] = prices
        else:
            print(f"  Warning: insufficient data for {ticker}")

    if len(price_data) < 3:
        print("ERROR: Not enough data to compute correlation matrix.")
        sys.exit(1)

    # Align and compute returns
    df = pd.DataFrame(price_data)
    df = df.dropna()
    returns = df.pct_change().dropna()

    # Use last PERIOD_DAYS of returns
    if len(returns) > PERIOD_DAYS:
        returns = returns.iloc[-PERIOD_DAYS:]

    corr = returns.corr()

    # Order: SPY first, then sectors alphabetically by ticker
    ordered = ["SPY"] + sorted([t for t in corr.columns if t != "SPY"])
    corr = corr.reindex(index=ordered, columns=ordered)

    labels = [f"{t}\n({SECTORS[t]})" for t in ordered]

    date_stamp = datetime.now().strftime("%Y-%m-%d")
    filename = f"correlation-heatmap-{date_stamp}.png"
    output_path = os.path.join(ASSETS_DIR, filename)

    generate_heatmap(corr.values, labels, output_path)
    print(f"Saved heatmap to: {output_path}")

    # Also print the markdown reference for easy copy-paste
    print(f"\nMarkdown reference:")
    print(f"![Sector Correlation Heatmap — {date_stamp}](../assets/{filename})")

    return output_path


if __name__ == "__main__":
    main()
