import time
import anthropic
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import pytz

# =========================================================
# CONFIGURATION
# =========================================================

ANTHROPIC_API_KEY = "your-anthropic-api-key-here"
TELEGRAM_BOT_TOKEN = "your-telegram-bot-token-here"
TELEGRAM_CHAT_ID = "your-telegram-chat-id-here"

TICKER = "AAPL"
INTERVAL = "5m"
CHECK_EVERY_SECONDS = 300  # check once every 5 minutes

dubai_tz = pytz.timezone("Asia/Dubai")

# =========================================================
# TELEGRAM HELPER
# =========================================================

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10)
        if r.status_code != 200:
            print("Telegram error:", r.text)
    except Exception as e:
        print("Telegram send failed:", e)

# =========================================================
# DATA FETCHING
# =========================================================

def fetch_data(ticker: str, interval: str) -> pd.DataFrame:
    try:
        df = yf.download(ticker, period="2d", interval=interval,
                         auto_adjust=False, progress=False)
    except Exception as e:
        print("Data fetch error:", e)
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    return df

# =========================================================
# INDICATOR CALCULATIONS
# =========================================================

def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    return 100 - (100 / (1 + rs))

def compute_macd(close: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd - signal_line  # histogram only

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    close = pd.to_numeric(df["Close"], errors="coerce")
    df["ema9"]     = close.ewm(span=9,  adjust=False).mean()
    df["ema21"]    = close.ewm(span=21, adjust=False).mean()
    df["rsi"]      = compute_rsi(close)
    df["macd_hist"] = compute_macd(close)
    return df.dropna()

# =========================================================
# BUILDING THE PROMPT FOR CLAUDE
# =========================================================

def build_prompt(df: pd.DataFrame, ticker: str) -> str:
    latest = df.iloc[-1]
    prev   = df.iloc[-2]

    price       = float(latest["Close"])
    ema9        = float(latest["ema9"])
    ema21       = float(latest["ema21"])
    rsi         = float(latest["rsi"])
    macd_hist   = float(latest["macd_hist"])
    volume      = float(latest["Volume"])

    ema9_prev   = float(prev["ema9"])
    ema21_prev  = float(prev["ema21"])

    # Describe EMA trend
    if ema9 > ema21 and ema9_prev <= ema21_prev:
        ema_status = "EMA9 has just crossed above EMA21 (fresh bullish crossover)"
    elif ema9 < ema21 and ema9_prev >= ema21_prev:
        ema_status = "EMA9 has just crossed below EMA21 (fresh bearish crossover)"
    elif ema9 > ema21:
        ema_status = "EMA9 is above EMA21 (uptrend)"
    else:
        ema_status = "EMA9 is below EMA21 (downtrend)"

    # Describe RSI
    if rsi > 70:
        rsi_status = f"RSI is {rsi:.1f}, which is overbought territory"
    elif rsi < 30:
        rsi_status = f"RSI is {rsi:.1f}, which is oversold territory"
    else:
        rsi_status = f"RSI is {rsi:.1f}, which is in a neutral zone"

    # Describe MACD histogram
    if macd_hist > 0:
        macd_status = f"MACD histogram is positive at {macd_hist:.4f}, suggesting bullish momentum"
    else:
        macd_status = f"MACD histogram is negative at {macd_hist:.4f}, suggesting bearish momentum"

    prompt = f"""You are a professional stock market analyst. You are analyzing {ticker} on the 5-minute timeframe.

Here is the current market snapshot:

- Current price: {price:.2f}
- {ema_status}
- {rsi_status}
- {macd_status}
- Current volume on this candle: {volume:.0f}

Based on this information, your job is to return exactly one of the following three signals:

BUY - if the evidence clearly supports a long entry
SELL - if the evidence clearly supports a short or exit signal
HOLD - if the setup is unclear, mixed, or not yet confirmed

Respond in this exact format:
SIGNAL: [BUY / SELL / HOLD]
REASON: [One clear sentence explaining your decision]

Do not add any extra commentary. Do not hedge. Give a direct answer."""

    return prompt

# =========================================================
# CALLING CLAUDE
# =========================================================

def ask_claude(prompt: str) -> tuple[str, str]:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text.strip()

        signal = "HOLD"
        reason = "No clear reason provided."

        for line in response_text.splitlines():
            if line.startswith("SIGNAL:"):
                raw_signal = line.replace("SIGNAL:", "").strip().upper()
                if "BUY" in raw_signal:
                    signal = "BUY"
                elif "SELL" in raw_signal:
                    signal = "SELL"
                else:
                    signal = "HOLD"
            elif line.startswith("REASON:"):
                reason = line.replace("REASON:", "").strip()

        return signal, reason

    except Exception as e:
        print("Claude API error:", e)
        return "HOLD", "API error, defaulting to HOLD."

# =========================================================
# SIGNAL FORMATTING
# =========================================================

def format_signal_message(ticker: str, signal: str, reason: str,
                           price: float, now: datetime) -> str:
    expiry = now + timedelta(minutes=15)
    return (
        f"AI Signal for {ticker}\n\n"
        f"Decision: {signal}\n"
        f"Price: {price:.2f}\n"
        f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')} Dubai time\n"
        f"Review at: {expiry.strftime('%H:%M:%S')} Dubai time\n\n"
        f"Claude's Reason: {reason}\n\n"
        f"This is for educational purposes only. Not financial advice."
    )

# =========================================================
# MAIN LOOP
# =========================================================

last_candle_time = None

def check_signal():
    global last_candle_time

    now = datetime.now(dubai_tz)
    print(f"\n[{now.strftime('%H:%M:%S')}] Checking {TICKER}...")

    # Fetch and prepare data
    df = fetch_data(TICKER, INTERVAL)
    if df.empty or len(df) < 30:
        print("Not enough data.")
        return

    df = add_indicators(df)
    if df.empty or len(df) < 3:
        print("Not enough data after indicators.")
        return

    # Avoid duplicate checks on the same candle
    current_candle_time = df.index[-1]
    if last_candle_time is not None and current_candle_time <= last_candle_time:
        print("Same candle, skipping.")
        return
    last_candle_time = current_candle_time

    # Build prompt and ask Claude
    prompt = build_prompt(df, TICKER)
    print("Sending data to Claude...")
    signal, reason = ask_claude(prompt)
    print(f"Claude says: {signal} — {reason}")

    # Only send Telegram alert for BUY or SELL
    if signal in ("BUY", "SELL"):
        price = float(df.iloc[-1]["Close"])
        msg = format_signal_message(TICKER, signal, reason, price, now)
        send_telegram(msg)
        print("Alert sent to Telegram.")
    else:
        print("HOLD signal — no alert sent.")


def main():
    print(f"Starting AI Stock Signal Bot for {TICKER}")
    send_telegram(f"AI Stock Signal Bot started for {TICKER}. Monitoring 5-minute candles.")
    while True:
        try:
            check_signal()
        except Exception as e:
            print("Unexpected error:", e)
        time.sleep(CHECK_EVERY_SECONDS)


if __name__ == "__main__":
    main()