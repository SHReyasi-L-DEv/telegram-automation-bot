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

def send_all_charts():
    for name, symbol in MARKETS.items():
        filename = f"{name}.png"
        chart = generate_chart(symbol, filename)
        if chart:
            bot.send_photo(CHANNEL_ID, photo=open(chart, "rb"))


send_all_charts()



def generate_chart(symbol, filename):
    end = datetime.now()
    start = end - timedelta(days=7)

    data = yf.download(symbol, start=start, end=end, interval="1h")

    # --- FIX: skip empty or invalid data ---
    if data is None or data.empty:
        print(f"⚠ Skipping {symbol} - No data received.")
        return None

    # Drop rows with NaN values
    data = data.dropna()

    if data.empty:
        print(f"⚠ Skipping {symbol} - Data contains only NaN.")
        return None
    # --------------------------

    # Now safe to plot
    mpf.plot(data, type='candle', style='yahoo',
             title=symbol,
             volume=True,
             savefig=filename)

def generate_chart(symbol, filename):
    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=7)
