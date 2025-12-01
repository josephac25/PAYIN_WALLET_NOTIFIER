import os
import requests
from time import sleep, time
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")  # Funciona para Polygon también
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
THRESHOLD_USDT = float(os.getenv("THRESHOLD_USDT"))

# ⚠️ Contrato USDT CORRECTO en Polygon Mainnet
USDT_CONTRACT = "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"

POLYGONSCAN_URL = "https://api.polygonscan.com/api"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Tracking de offset para mensajes
last_update_id = 0


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

    try:
        res = requests.get(POLYGONSCAN_URL, params=params, timeout=10).json()
        
        if res.get("status") != "1":
            print("❌ Error obteniendo balance:", res)
            return None

        raw = int(res["result"])
        return raw / 1_000_000  # USDT tiene 6 decimales
    except Exception as e:
        print(f"❌ Excepción al consultar balance: {e}")
        return None


def send_message(text, chat_id=None):
    """Envía mensaje a Telegram."""
    if chat_id is None:
        chat_id = TELEGRAM_CHAT_ID

    url = f"{TELEGRAM_API_URL}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as e:
        print(f"❌ Error enviando mensaje: {e}")


def check_for_commands():
    """Lee mensajes que le envían al bot."""
    global last_update_id
    
    url = f"{TELEGRAM_API_URL}/getUpdates"
    params = {"offset": last_update_id + 1, "timeout": 5}
    
    try:
        res = requests.get(url, params=params, timeout=10).json()
    except Exception as e:
        print(f"❌ Error consultando updates: {e}")
        return None

    if "result" not in res or not res["result"]:
        return None

    updates = res["result"]
    last = updates[-1]
    last_update_id = last["update_id"]
    
    message = last.get("message", {})
    text = message.get("text")
    chat_id = message.get("chat", {}).get("id")

    return text, chat_id


def main_loop():
    print("🤖 Bot corriendo y monitoreando USDT en Polygon…")
    print(f"📍 Wallet: {WALLET_ADDRESS}")
    print(f"💎 Contrato USDT: {USDT_CONTRACT}")
    print(f"⚠️  Umbral: {THRESHOLD_USDT} USDT\n")

    last_summary = 0

    while True:
        # Revisar si enviaron /balance
        update = check_for_commands()
        if update:
            text, chat_id = update

            if text and text.startswith("/balance"):
                balance = get_usdt_balance()
                if balance is None:
                    send_message("⚠️ No pude obtener el balance", chat_id)
                else:
                    send_message(f"💰 Balance actual: {balance:.2f} USDT", chat_id)

        # Monitoreo automático
        balance = get_usdt_balance()
        now = time()

        if balance is not None:
            print(f"💰 Balance: {balance:.2f} USDT")

            # Alerta si baja del umbral
            if balance < THRESHOLD_USDT:
                send_message(
                    f"⚠️ ALERTA: El balance cayó a {balance:.2f} USDT "
                    f"(umbral = {THRESHOLD_USDT} USDT)"
                )

            # Resumen cada 15 minutos
            if now - last_summary >= 15 * 60:
                send_message(f"⏱ Balance actual: {balance:.2f} USDT")
                last_summary = now

        sleep(60)


if __name__ == "__main__":
    main_loop()
