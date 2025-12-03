# bot.py - Safe, GitHub-Actions-friendly version
import os
import time
import traceback
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import telegram
from datetime import datetime, timedelta

# --- Config (read from GitHub Secrets) ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Quick token check
if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN secret is not set. Add it under Repo -> Settings -> Secrets -> Actions.")
    raise SystemExit(1)

if not CHANNEL_ID:
    print("ERROR: CHANNEL_ID secret is not set. Add it under Repo -> Settings -> Secrets -> Actions.")
    raise SystemExit(1)

# Create bot safely
try:
    bot = telegram.Bot(token=BOT_TOKEN)
    # optional quick call to get_me to validate the token (comment out if you prefer)
    _ = bot.get_me()
except Exception as e:
    print("ERROR: Failed to create Telegram bot (invalid token or network issue):", e)
    raise SystemExit(1)

# Markets to post (Yahoo tickers)
MARKETS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "GOLD": "XAUUSD=X",
    "BITCOIN": "BTC-USD",
    "ETHEREUM": "ETH-USD",
}

# Chart generation function (robust)
def generate_chart(symbol: str, filename: str, lookback_days: int = 7):
    end = datetime.utcnow()
    start = end - timedelta(days=lookback_days)

    try:
        data = yf.download(symbol, start=start, end=end, interval="1h", progress=False, auto_adjust=True)
    except Exception as e:
        print(f"⚠ Exception when downloading {symbol}: {e}")
        return None

    if data is None or data.empty:
        print(f"⚠ No data for {symbol} (empty dataframe). Skipping.")
        return None

    # Ensure numeric columns
    numeric_cols = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    for col in numeric_cols:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    # Drop rows with NaNs
    data = data.dropna()
    if data.empty:
        print(f"⚠ After cleaning, no valid rows for {symbol}. Skipping.")
        return None

    # mpf expects the index to be DatetimeIndex and numeric columns present
    try:
        mpf.plot(
            data,
            type="candle",
            style="yahoo",
            volume=True,
            title=f"{symbol} — 1H",
            savefig=filename  # mplfinance accepts this form
        )
        print(f"✔ Chart saved: {filename}")
        return filename
    except Exception as e:
        print(f"❌ Failed to create chart image for {symbol}: {e}")
        traceback.print_exc()
        return None


def send_all_charts():
    for name, symbol in MARKETS.items():
        filename = f"{name}.png"
        try:
            chart_file = generate_chart(symbol, filename)
            if not chart_file:
                # skip if no chart produced
                continue

            # send photo to channel
            try:
                with open(chart_file, "rb") as photo:
                    bot.send_photo(chat_id=CHANNEL_ID, photo=photo, caption=f"{name} — 1H chart 📈")
                print(f"✔ Posted {name} to channel {CHANNEL_ID}")
            except Exception as te:
                print(f"❌ Failed to send {name} to Telegram: {te}")
                traceback.print_exc()
            finally:
                # small polite pause to avoid burst sending
                time.sleep(1)
        except Exception as e:
            print(f"Unexpected error while processing {name} ({symbol}): {e}")
            traceback.print_exc()


if __name__ == "__main__":
    print("Starting chart generation run:", datetime.utcnow().isoformat(), "UTC")
    send_all_charts()
    print("Run complete.")
