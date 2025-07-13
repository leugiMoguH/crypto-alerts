import os
import requests
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD

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

def analisar_indicadores(df):
    ema = EMAIndicator(close=df["close"], window=14)
    df["ema"] = ema.ema_indicator()

    rsi = RSIIndicator(close=df["close"], window=14)
    df["rsi"] = rsi.rsi()

    macd = MACD(close=df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_diff"] = macd.macd_diff()

    return df

def verificar_sinal(df):
    ult = df.iloc[-1]
    if ult["rsi"] < 30 and ult["macd_diff"] > 0 and ult["close"] > ult["ema"]:
        return True
    return False

def enviar_alerta(moeda, preco):
    mensagem = f"💰 Alerta de compra antecipado para {moeda}!\nPreço atual: {preco:.4f} EUR"
    bot.send_message(chat_id=CHAT_ID, text=mensagem)

def main():
    for coin in COINS:
        try:
            df = fetch_data(coin)
            df = analisar_indicadores(df)
            if verificar_sinal(df):
                enviar_alerta(coin, df["close"].iloc[-1])
        except Exception as e:
            print(f"Erro com {coin}: {e}")

if __name__ == "__main__":
    main()
