import os
import requests
from time import sleep, time
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
THRESHOLD_USDT = float(os.getenv("THRESHOLD_USDT"))

# Contrato USDT en Polygon
USDT_CONTRACT = "0x3813e82e6f7098b9583FC0F33a962D02018B6803"

POLYGONSCAN_URL = "https://api.polygonscan.com/api"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def get_usdt_balance():
    """Devuelve USDT balance en Polygon."""
    params = {
        "module": "account",
        "action": "tokenbalance",
        "contractaddress": USDT_CONTRACT,
        "address": WALLET_ADDRESS,
        "tag": "latest",
        "apikey": ETHERSCAN_API_KEY
    }

    res = requests.get(POLYGONSCAN_URL, params=params).json()

    if res.get("status") != "1":
        print("❌ Error obteniendo balance:", res)
        return None

    raw = int(res["result"])
    return raw / 1_000_000  # USDT tiene 6 decimales


def send_message(text, chat_id=None):
    """Envía mensaje a Telegram."""
    if chat_id is None:
        chat_id = TELEGRAM_CHAT_ID

    url = f"{TELEGRAM_API_URL}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})


def check_for_commands():
    """Lee mensajes que le envían al bot."""
    url = f"{TELEGRAM_API_URL}/getUpdates"
    res = requests.get(url).json()

    if "result" not in res:
        return None

    updates = res["result"]
    if not updates:
        return None

    last = updates[-1]  # último mensaje
    message = last.get("message", {})
    text = message.get("text")
    chat_id = message.get("chat", {}).get("id")

    return text, chat_id


def main_loop():
    print("Bot corriendo y monitoreando USDT…")

    last_summary = 0

    while True:
        # Revisar si enviaron /balance
        update = check_for_commands()
        if update:
            text, chat_id = update

            if text == "/balance":
                balance = get_usdt_balance()
                if balance is None:
                    send_message("⚠️ No pude obtener el balance", chat_id)
                else:
                    send_message(f"💰 Balance actual: {balance} USDT", chat_id)

        # Monitoreo automático
        balance = get_usdt_balance()
        now = time()

        if balance is not None:
            print(f"Balance: {balance} USDT")

            # Alerta si baja del umbral
            if balance < THRESHOLD_USDT:
                send_message(
                    f"⚠️ ALERTA: El balance cayó a {balance} USDT "
                    f"(umbral = {THRESHOLD_USDT} USDT)"
                )

            # Resumen cada 15 minutos
            if now - last_summary >= 15 * 60:
                send_message(f"⏱ Balance actual: {balance} USDT")
                last_summary = now

        sleep(60)


if __name__ == "__main__":
    main_loop()
