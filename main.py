import os
import requests
from time import sleep, time
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
USDT_CONTRACT = os.getenv("USDT_CONTRACT")
THRESHOLD_USDT = float(os.getenv("THRESHOLD_USDT"))

ETHERSCAN_URL = "https://api.etherscan.io/v2/api"

def get_usdt_balance():
    """Devuelve balance USDT en Polygon."""
    params = {
        "chainid": 137,
        "module": "account",
        "action": "tokenbalance",
        "address": WALLET_ADDRESS,
        "contractaddress": USDT_CONTRACT,
        "apikey": ETHERSCAN_API_KEY
    }

    res = requests.get(ETHERSCAN_URL, params=params).json()

    if res.get("status") != "1":
        print("Error obteniendo balance:", res)
        return None

    raw_balance = int(res["result"])
    balance = raw_balance / 1_000_000
    return balance


def send_message(text):
    """Envía mensaje a Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    requests.post(url, json=payload)


def main_loop():
    print("Bot iniciado… monitoreando USDT…")
    
    last_summary_time = 0  # última vez que se envió el reporte de 15 min
    
    while True:
        balance = get_usdt_balance()
        now = time()

        if balance is None:
            sleep(60)
            continue

        print(f"Balance actual: {balance} USDT")

        # 1) ALERTA INMEDIATA SI < 20,000
        if balance < THRESHOLD_USDT:
            send_message(
                f"⚠️ ALERTA: El balance cayó a {balance} USDT "
                f"(umbral = {THRESHOLD_USDT} USDT)"
            )

        # 2) RESUMEN CADA 15 MINUTOS
        if now - last_summary_time >= 15 * 60:
            send_message(f"⏱ Balance actual: {balance} USDT")
            last_summary_time = now

        sleep(60)  # revisa cada minuto


if __name__ == "__main__":
    main_loop()