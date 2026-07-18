#!/usr/bin/env python3
"""
Sector Correlation Heatmap Generator (Compact PIL Version)
Fetches 30-day price history for all sector ETFs, computes a correlation matrix,
and generates a compact PNG heatmap saved to assets/ with a dated filename.
"""

import os
import sys
from datetime import datetime, timedelta

# --- Configuration ---
SECTORS = {
    "SPY": "S&P 500",
    "XLK": "Tech",
    "SMH": "Semis",
    "XLY": "Cons Disc",
    "XLI": "Industrials",
    "XLB": "Materials",
    "XLC": "Comm Svcs",
    "XLF": "Financials",
    "XLV": "Healthcare",
    "XLU": "Utilities",
    "XLRE": "Real Estate",
    "XLE": "Energy",
    "XLP": "Cons Staples",
}

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
PERIOD_DAYS = 30


def fetch_close_prices(ticker: str, days: int = PERIOD_DAYS):
    """Fetch daily close prices for the last N days using yfinance."""
    import yfinance as yf

    end = datetime.now()
    start = end - timedelta(days=days + 5)
    df = yf.download(ticker, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), progress=False)
    if df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        closes = df["Close"][ticker]
    else:
        closes = df["Close"]
    return closes.dropna()


def corr_to_color(val: float) -> tuple:
    """Map correlation (-1 to 1) to RGB color. Blue = negative, White = 0, Red = positive."""
    if val >= 0:
        r = 255
        g = int(255 * (1 - val))
        b = int(255 * (1 - val))
    else:
        r = int(255 * (1 + val))
        g = int(255 * (1 + val))
        b = 255
    return (r, g, b)


def generate_heatmap_pil(corr_matrix, labels, output_path):
    """Generate a compact heatmap using PIL."""
    from PIL import Image, ImageDraw, ImageFont

    n = len(labels)
    cell_size = 42
    label_width = 90
    label_height = 70
    margin = 10

    img_width = label_width + n * cell_size + margin
    img_height = label_height + n * cell_size + margin + 30

    img = Image.new("RGB", (img_width, img_height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 10)
        small_font = ImageFont.truetype("arial.ttf", 8)
    except OSError:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    title = f"Sector Correlation ({PERIOD_DAYS}D) — {datetime.now().strftime('%Y-%m-%d')}"
    draw.text((margin, 5), title, fill=(0, 0, 0), font=font)

    for i in range(n):
        for j in range(n):
            if j > i:
                continue
            val = corr_matrix[i][j]
            color = corr_to_color(val)
            x = label_width + j * cell_size
            y = label_height + i * cell_size
            draw.rectangle([x, y, x + cell_size - 1, y + cell_size - 1], fill=color, outline=(200, 200, 200))
            text = f"{val:.2f}"
            bbox = draw.textbbox((0, 0), text, font=small_font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            tx = x + (cell_size - tw) // 2
            ty = y + (cell_size - th) // 2
            brightness = (color[0] * 299 + color[1] * 587 + color[2] * 114) / 1000
            text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)
            draw.text((tx, ty), text, fill=text_color, font=small_font)

    for i, label in enumerate(labels):
        y = label_height + i * cell_size + cell_size // 2
        draw.text((margin, y - 5), label, fill=(0, 0, 0), font=small_font)
        x = label_width + i * cell_size + cell_size // 2
        txt_img = Image.new("RGBA", (60, 12), (255, 255, 255, 0))
        txt_draw = ImageDraw.Draw(txt_img)
        txt_draw.text((0, 0), label, fill=(0, 0, 0), font=small_font)
        txt_img = txt_img.rotate(45, expand=True)
        img.paste(txt_img, (x - 10, margin), txt_img)

    img.save(output_path, optimize=True)
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

    df = pd.DataFrame(price_data)
    df = df.dropna()
    returns = df.pct_change().dropna()
    if len(returns) > PERIOD_DAYS:
        returns = returns.iloc[-PERIOD_DAYS:]
    corr = returns.corr()

    ordered = ["SPY"] + sorted([t for t in corr.columns if t != "SPY"])
    corr = corr.reindex(index=ordered, columns=ordered)
    labels = ordered

    date_stamp = datetime.now().strftime("%Y-%m-%d")
    filename = f"correlation-heatmap-{date_stamp}.png"
    output_path = os.path.join(ASSETS_DIR, filename)

    generate_heatmap_pil(corr.values, labels, output_path)
    print(f"Saved heatmap to: {output_path}")
    print(f"\nMarkdown reference:")
    print(f"![Sector Correlation Heatmap — {date_stamp}](../assets/{filename})")

    return output_path


if __name__ == "__main__":
    main()
