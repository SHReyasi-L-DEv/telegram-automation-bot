import yfinance as yf
import mplfinance as mpf
import telegram
import datetime
from datetime import timedelta
import os
import pandas as pd

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = telegram.Bot(token=BOT_TOKEN)

# ---- Markets you want to send screenshots for ----
MARKETS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "GOLD": "XAUUSD=X",
    "BITCOIN": "BTC-USD",
    "ETHEREUM": "ETH-USD"
}

def generate_chart(symbol, filename):
    end = datetime.now()
    start = end - timedelta(days=7)

    data = yf.download(symbol, start=start, end=end, interval="1h")

    # If empty data — skip
    if data is None or data.empty:
        print(f"⚠ No data for {symbol}. Skipping.")
        return None

    # Force all numeric columns to float
    numeric_cols = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    for col in numeric_cols:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    # Drop all rows with NaN after cleaning
    data = data.dropna()

    # If still empty — skip
    if data.empty:
        print(f"⚠ Cleaned data empty for {symbol}. Skipping.")
        return None

    # Plot safely
    try:
        mpf.plot(
            data,
            type="candle",
            style="yahoo",
            volume=True,
            title=symbol,
            savefig=filename
        )
        return filename
    except Exception as e:
        print(f"❌ Chart generation failed for {symbol}: {e}")
        return None

def send_all_charts():
    for name, symbol in MARKETS.items():
        filename = f"{name}.png"
        chart = generate_chart(symbol, filename)
        if chart:
            bot.send_photo(CHANNEL_ID, photo=open(chart, "rb"))


send_all_charts()
