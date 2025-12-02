import yfinance as yf
import mplfinance as mpf
import telegram
import datetime
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

def chart = generate_chart(symbol, name):
    if chart:
    send_photo(chart)
    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=2)

    data = yf.download(symbol, start=start, end=end, interval="1h")

    if data.empty:
        return None

    file_path = f"{name}.png"

    mpf.plot(
        data,
        type="candle",
        style="charles",
        title=f"{name} – 1H Chart",
        savefig=file_path
    )

    return file_path


def send_all_charts():
    for name, symbol in MARKETS.items():
        file = generate_chart(symbol, name)

        if file:
            bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=open(file, "rb"),
                caption=f"{name} Latest Chart 📊"
            )

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

    return filename

