import os
import requests
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD
from datetime import datetime
from telegram import Bot
import json

# Configurações de ambiente
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
bot = Bot(token=TOKEN)

# Lista de moedas da Neteller (com base nas imagens que enviaste)
COINS = ["BTC", "ETH", "XRP", "ADA", "DOGE", "AVAX", "MATIC", "SOL", "DOT", "LTC", "BCH", "ATOM", "UNI", "APE", "CRV", "ANKR", "LINK", "ETC", "AAVE", "XTZ", "SHIB", "GRT", "EOS", "USDC", "SNX", "XLM", "ALGO", "1INCH", "MANA", "CHZ", "ICP"]
LIMIT = 50
SIGNALS_LOG = "signals_log.json"

def carregar_sinais():
    if os.path.exists(SIGNALS_LOG):
        with open(SIGNALS_LOG, "r") as f:
            return json.load(f)
    return []

def guardar_sinal(sinal):
    sinais = carregar_sinais()
    sinais.append(sinal)
    with open(SIGNALS_LOG, "w") as f:
        json.dump(sinais, f)

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

def analisar_indicadores(df):
    df["ema"] = EMAIndicator(close=df["close"], window=14).ema_indicator()
    df["rsi"] = RSIIndicator(close=df["close"], window=14).rsi()
    macd = MACD(close=df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_diff"] = macd.macd_diff()
    df["ema20"] = EMAIndicator(close=df["close"], window=20).ema_indicator()
    df["ema50"] = EMAIndicator(close=df["close"], window=50).ema_indicator()
    df["ema200"] = EMAIndicator(close=df["close"], window=200).ema_indicator()
    df["vol_ma"] = df["volumefrom"].rolling(window=20).mean()
    df["volatilidade"] = df["high"] - df["low"]
    df["candle_alta"] = df["close"] > df["open"]
    return df

def verificar_sinal(df):
    ult = df.iloc[-1]
    prev = df.iloc[-2]
    condicoes = [
        ult["rsi"] < 30,
        ult["macd_diff"] > 0,
        ult["close"] > ult["ema"],
        ult["ema20"] > ult["ema50"] > ult["ema200"],
        ult["volumefrom"] > ult["vol_ma"],
        ult["candle_alta"] and ult["close"] > prev["high"]  # Breakout técnico
    ]
    return all(condicoes)

def enviar_alerta(moeda, preco, df):
    ult = df.iloc[-1]
    vol = df["volatilidade"].rolling(window=20).mean().iloc[-1]
    tp = preco + vol
    sl = preco - vol
    mensagem = (
        f"✨ COMPRA antecipada: {moeda}\n"
        f"💵 Preço: {preco:.2f} EUR\n"
        f"🎯 Alvo venda: {tp:.2f} EUR\n"
        f"⛔ Stop Loss: {sl:.2f} EUR"
    )
    bot.send_message(chat_id=CHAT_ID, text=mensagem)
    guardar_sinal({"moeda": moeda, "preco": preco, "alvo": tp, "sl": sl, "hora": str(datetime.now())})

def enviar_resumo():
    sinais = carregar_sinais()
    if not sinais:
        bot.send_message(chat_id=CHAT_ID, text="Resumo semanal: Nenhum sinal gerado esta semana.")
        return
    texto = "✅ Resumo semanal:\n"
    for sinal in sinais[-20:]:
        texto += (f"{sinal['moeda']}: entrada a {sinal['preco']:.2f} | alvo: {sinal['alvo']:.2f} | SL: {sinal['sl']:.2f}\n")
    bot.send_message(chat_id=CHAT_ID, text=texto)

def main():
    print("[INÍCIO] A iniciar análise de oportunidades...")
    houve_alertas = False
    for coin in COINS:
        try:
            print(f"[ANÁLISE] {coin}")
            df = fetch_data(coin)
            df = analisar_indicadores(df)
            if verificar_sinal(df):
                enviar_alerta(coin, df["close"].iloc[-1], df)
                houve_alertas = True
        except Exception as e:
            print(f"[ERRO] com {coin}: {e}")

    if not houve_alertas:
        print("[INFO] Nenhum alerta gerado neste ciclo.")

    try:
        print("[FIM] Análise concluída.")
        bot.send_message(chat_id=CHAT_ID, text="✅ Análise concluída.")
    except Exception as e:
        print(f"[ERRO] ao enviar mensagem final: {e}")

    if datetime.now().weekday() == 6 and datetime.now().hour >= 22:
        enviar_resumo()

if __name__ == "__main__":
    main()
