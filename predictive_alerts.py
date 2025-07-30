import os
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from ta.trend import MACD
from datetime import datetime
from telegram import Bot
import io

# Configurações
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
bot = Bot(token=TOKEN)

COINS = ["BTC", "ETH", "XRP", "ADA", "DOGE", "AVAX", "MATIC", "SOL", "DOT", "LTC", "BCH", "ATOM", "UNI", "APE", "CRV", "ANKR", "LINK", "ETC", "AAVE", "XTZ", "SHIB", "GRT", "EOS", "USDC", "SNX", "XLM", "ALGO", "1INCH", "MANA", "CHZ", "ICP"]
LIMIT = 50

def fetch_data(symbol):
    url = "https://min-api.cryptocompare.com/data/v2/histominute"
    params = {"fsym": symbol, "tsym": "EUR", "limit": LIMIT, "api_key": API_KEY}
    r = requests.get(url, params=params)
    data = r.json()
    if data.get("Response") != "Success":
        raise Exception(f"Erro CryptoCompare: {data}")
    df = pd.DataFrame(data["Data"]["Data"])
    df["datetime"] = pd.to_datetime(df["time"], unit="s")
    df.set_index("datetime", inplace=True)
    return df

def aplicar_indicadores(df):
    df["ema20"] = EMAIndicator(df["close"], window=20).ema_indicator()
    df["ema50"] = EMAIndicator(df["close"], window=50).ema_indicator()
    df["ema200"] = EMAIndicator(df["close"], window=200, fillna=True).ema_indicator()
    df["rsi"] = RSIIndicator(df["close"]).rsi()
    macd = MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_diff"] = macd.macd_diff()
    boll = BollingerBands(df["close"])
    df["bb_high"] = boll.bollinger_hband()
    df["bb_low"] = boll.bollinger_lband()
    df["bb_width"] = df["bb_high"] - df["bb_low"]
    return df

def breakout_setup(df):
    return df["close"].iloc[-1] > df["bb_high"].iloc[-1] and df["close"].iloc[-2] < df["bb_high"].iloc[-2]

def pullback_setup(df):
    return df["close"].iloc[-1] > df["ema20"].iloc[-1] and df["close"].iloc[-2] < df["ema20"].iloc[-2]

def ema_trend(df):
    return df["close"].iloc[-1] > df["ema200"].iloc[-1]

def reteste_rejeitado(df):
    return (
        df["close"].iloc[-1] > df["ema200"].iloc[-1] and
        df["close"].iloc[-2] < df["ema200"].iloc[-2] and
        df["macd_diff"].iloc[-1] > 0 and
        df["rsi"].iloc[-1] > 50
    )

def divergencia_macd_rsi(df):
    return (
        df["close"].iloc[-1] > df["close"].iloc[-2] and
        df["rsi"].iloc[-1] < df["rsi"].iloc[-2] and
        df["macd_diff"].iloc[-1] < df["macd_diff"].iloc[-2]
    )

def golden_cross(df):
    return df["ema20"].iloc[-2] < df["ema50"].iloc[-2] and df["ema20"].iloc[-1] > df["ema50"].iloc[-1]

def inside_bar_breakout(df):
    return (
        df["high"].iloc[-2] > df["high"].iloc[-1] and
        df["low"].iloc[-2] < df["low"].iloc[-1] and
        df["close"].iloc[-1] > df["high"].iloc[-2]
    )

def gerar_grafico(df, coin):
    plt.figure(figsize=(10, 4))
    plt.plot(df.index, df["close"], label="Close", linewidth=1.5)
    plt.plot(df.index, df["ema20"], label="EMA20", linestyle="--")
    plt.plot(df.index, df["ema200"], label="EMA200", linestyle="--")
    plt.title(f"{coin} - Análise Técnica")
    plt.legend()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf

def enviar_alerta(coin, preco, tp1, tp2, sl, grafico):
    mensagem = (
        f"🚨 ALERTA PREDITIVO\n"
        f"Moeda: {coin}\n"
        f"Preço atual: {preco:.4f}€\n"
        f"🎯 Take-Profit: {tp1:.4f}€ / {tp2:.4f}€\n"
        f"🛑 Stop-Loss: {sl:.4f}€\n"
        f"💰 Investimento: 1€"
    )
    bot.send_photo(chat_id=CHAT_ID, photo=grafico, caption=mensagem)

def analisar_moeda(coin):
    df = fetch_data(coin)
    df = aplicar_indicadores(df)
    preco = df["close"].iloc[-1]

    condicoes_validas = sum([
        breakout_setup(df),
        pullback_setup(df),
        reteste_rejeitado(df),
        divergencia_macd_rsi(df),
        golden_cross(df),
        inside_bar_breakout(df)
    ])

    tendencia_ok = df["close"].iloc[-1] > 0.98 * df["ema200"].iloc[-1]
    rsi_ok = df["rsi"].iloc[-1] > 48  # antes era 50
    setups_ok = condicoes_validas >= 1  # antes era 2

    if tendencia_ok and setups_ok and rsi_ok:
        tp1 = preco * 1.15
        tp2 = preco * 1.30
        sl = preco * 0.90
        grafico = gerar_grafico(df, coin)
        enviar_alerta(coin, preco, tp1, tp2, sl, grafico)


def main():
    mensagem_inicio = "\u23f0 A iniciar análise de oportunidades (preditivas)..."
    print(f"[INÍCIO] {mensagem_inicio}")
    bot.send_message(chat_id=CHAT_ID, text=mensagem_inicio)

    for coin in COINS:
        try:
            analisar_moeda(coin)
        except Exception as e:
            print(f"Erro com {coin}: {e}")

    try:
        print("[FIM] Análise concluída (preditiva).")
        bot.send_message(chat_id=CHAT_ID, text="✅ Análise preditiva concluída.")
    except Exception as e:
        print(f"[ERRO] ao enviar mensagem final: {e}")

if __name__ == "__main__":
    main()
