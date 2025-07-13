import os
import requests
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from telegram import Bot

# Configurações
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
bot = Bot(token=TOKEN)

# Lista de moedas e parâmetros
COINS = ["BTC", "ETH", "XRP", "MATIC", "AVAX", "ADA", "DOGE"]
LIMIT = 50

def fetch_data(symbol):
    url = f"https://min-api.cryptocompare.com/data/v2/histominute"
    params = {
        "fsym": symbol,
        "tsym": "EUR",
        "limit": LIMIT,
        "api_key": API_KEY
    }
    r = requests.get(url, params=params)
    data = r.json()
    if data.get("Response") != "Success":
        raise Exception(f"Erro CryptoCompare: {data}")
    df = pd.DataFrame(data["Data"]["Data"])
    df["datetime"] = pd.to_datetime(df["time"], unit="s")
    df.set_index("datetime", inplace=True)
    return df

def analisar_moeda(symbol):
    try:
        df = fetch_data(symbol)
        df["RSI"] = ta.rsi(df["close"], length=14)
        df["SMA20"] = df["close"].rolling(20).mean()
        df["SMA50"] = df["close"].rolling(50).mean()

        rsi = round(df["RSI"].iloc[-1], 2)
        price = round(df["close"].iloc[-1], 4)

        if rsi > 70:
            return f"🔴 **VENDE 1€ {symbol}** (RSI {rsi})\n💰 Preço: €{price}"
        elif rsi < 30:
            return f"🟢 **COMPRA 1€ {symbol}** (RSI {rsi})\n💰 Preço: €{price}"
        else:
            return None
    except Exception as e:
        return f"⚠️ Erro {symbol}: {str(e)}"

def main():
    bot.send_message(chat_id=CHAT_ID, text="🔍 A analisar oportunidades...")

    for coin in COINS:
        msg = analisar_moeda(coin)
        if msg:
            bot.send_message(chat_id=CHAT_ID, text=msg)

if __name__ == "__main__":
    main()
