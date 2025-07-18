import os
import requests
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD
from ta.volatility import BollingerBands
from datetime import datetime
from telegram import Bot

# Ambiente
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
bot = Bot(token=TOKEN)

COINS = ["BTC", "ETH", "XRP", "ADA", "DOGE", "AVAX", "MATIC", "SOL", "DOT", "LTC", "BCH", "ATOM", "UNI", "APE", "CRV", "ANKR", "LINK", "ETC", "AAVE", "XTZ", "SHIB", "GRT", "EOS", "USDC", "SNX", "XLM", "ALGO", "1INCH", "MANA", "CHZ", "ICP"]
LIMIT = 50


def fetch_data(symbol):
    url = "https://min-api.cryptocompare.com/data/v2/histominute"
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


def aplicar_indicadores(df):
    df["ema50"] = EMAIndicator(df["close"], window=50).ema_indicator()
    df["ema200"] = EMAIndicator(df["close"], window=200).ema_indicator()
    df["rsi"] = RSIIndicator(df["close"]).rsi()
    macd = MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_diff"] = macd.macd_diff()
    boll = BollingerBands(df["close"])
    df["bb_upper"] = boll.bollinger_hband()
    df["bb_lower"] = boll.bollinger_lband()
    df["bb_width"] = df["bb_upper"] - df["bb_lower"]
    return df


def verificar_breakout(df):
    candle = df.iloc[-1]
    return candle["close"] > candle["bb_upper"] and candle["macd_diff"] > 0


def verificar_pullback_rejeitado(df):
    candle = df.iloc[-1]
    anterior = df.iloc[-2]
    return (
        candle["close"] > candle["ema200"] and
        anterior["close"] < anterior["ema200"] and
        candle["rsi"] > 50 and
        candle["macd_diff"] > 0
    )


def enviar_alerta_predictivo(coin, preco, tipo):
    msg = (
        f"🔎 SINAL PREDITIVO: {coin}\n"
        f"💰 Preço atual: {preco:.2f} EUR\n"
        f"📈 Tipo: {tipo}\n"
        f"⚠️ Sinal antecipado baseado em padrão técnico forte."
    )
    bot.send_message(chat_id=CHAT_ID, text=msg)


def main():
    for coin in COINS:
        try:
            df = fetch_data(coin)
            df = aplicar_indicadores(df)
            preco = df["close"].iloc[-1]

            if verificar_breakout(df):
                enviar_alerta_predictivo(coin, preco, "Breakout")

            elif verificar_pullback_rejeitado(df):
                enviar_alerta_predictivo(coin, preco, "Pullback com rejeição")

        except Exception as e:
            print(f"Erro com {coin}: {e}")


if __name__ == "__main__":
    main()
