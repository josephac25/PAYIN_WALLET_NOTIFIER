import os
import requests
from time import sleep, time
from dotenv import load_dotenv
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_GROUP_ID = os.getenv("TELEGRAM_GROUP_ID")  # ID del grupo

# Debug crítico - Verificar que se cargó la variable
print(f"🔍 DEBUG: TELEGRAM_GROUP_ID cargado = '{TELEGRAM_GROUP_ID}'")
print(f"🔍 DEBUG: ¿Es None? {TELEGRAM_GROUP_ID is None}")
print(f"🔍 DEBUG: ¿Es vacío? {TELEGRAM_GROUP_ID == ''}")

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
THRESHOLD_USDT = float(os.getenv("THRESHOLD_USDT"))

# Contrato USDT en Polygon Mainnet (ahora configurable)
USDT_CONTRACT = os.getenv("USDT_CONTRACT", "0xc2132D05D31c914a87C6611C10748AEb04B58e8F")

POLYGONSCAN_URL = "https://api.etherscan.io/v2/api"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Tracking de offset para mensajes
last_update_id = 0


def get_usdt_balance():
    """Devuelve USDT balance en Polygon."""
    params = {
        "chainid": "137",  # Polygon Mainnet
        "module": "account",
        "action": "tokenbalance",
        "contractaddress": USDT_CONTRACT,
        "address": WALLET_ADDRESS,
        "tag": "latest",
        "apikey": ETHERSCAN_API_KEY
    }

    try:
        response = requests.get(POLYGONSCAN_URL, params=params, timeout=10)
        res = response.json()
        
        if res.get("status") != "1":
            print(f"❌ Error obteniendo balance:")
            print(f"   Message: {res.get('message')}")
            print(f"   Result: {res.get('result')}")
            return None

        raw = int(res["result"])
        balance = raw / 1_000_000  # USDT tiene 6 decimales
        return balance
    except Exception as e:
        print(f"❌ Excepción al consultar balance: {e}")
        return None


def send_message(text, chat_id=None):
    """Envía mensaje a Telegram."""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    
    # Si no se especifica chat_id, enviar a ambos (personal y grupo)
    if chat_id is None:
        chat_ids = [TELEGRAM_CHAT_ID]
        if TELEGRAM_GROUP_ID:
            chat_ids.append(TELEGRAM_GROUP_ID)
        print(f"📤 Enviando mensaje automático a: {chat_ids}")  # Debug
    else:
        chat_ids = [chat_id]
        print(f"📤 Respondiendo comando a: {chat_id}")  # Debug
    
    # Enviar a cada chat
    for cid in chat_ids:
        try:
            requests.post(url, json={"chat_id": cid, "text": text}, timeout=10)
            print(f"✅ Mensaje enviado a {cid}")  # Debug
        except Exception as e:
            print(f"❌ Error enviando mensaje a {cid}: {e}")


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


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Servidor HTTP simple para que Render detecte que el servicio está corriendo."""
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot is running!')
    
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
    
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot is running!')
    
    def log_message(self, format, *args):
        # Silenciar logs del servidor HTTP
        pass


def start_health_server():
    """Inicia servidor HTTP en el puerto que Render espera."""
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"🌐 Servidor HTTP corriendo en puerto {port}")
    server.serve_forever()


def main_loop():
    print("🤖 Bot corriendo y monitoreando USDT en Polygon…")
    print(f"📍 Wallet: {WALLET_ADDRESS}")
    print(f"💎 Contrato USDT: {USDT_CONTRACT}")
    print(f"⚠️  Umbral: {THRESHOLD_USDT} USDT")
    print(f"💬 Chat personal: {TELEGRAM_CHAT_ID}")
    print(f"👥 Grupo: {TELEGRAM_GROUP_ID if TELEGRAM_GROUP_ID else 'No configurado'}\n")

    last_summary = 0
    last_balance_check = 0
    processed_commands = set()  # Para evitar duplicados

    while True:
        now = time()
        
        # Revisar comandos (cada 2 segundos)
        update = check_for_commands()
        if update:
            text, chat_id = update
            command_id = f"{chat_id}_{text}_{last_update_id}"

            if text and text.startswith("/balance") and command_id not in processed_commands:
                processed_commands.add(command_id)
                balance = get_usdt_balance()
                if balance is None:
                    send_message("⚠️ No pude obtener el balance", chat_id)
                else:
                    send_message(f"💰 Balance actual: {balance:.2f} USDT", chat_id)
                
                # Limpiar set si crece mucho
                if len(processed_commands) > 20:
                    processed_commands.clear()

        # Monitoreo automático (cada 60 segundos)
        if now - last_balance_check >= 60:
            balance = get_usdt_balance()

            if balance is not None:
                print(f"💰 Balance: {balance:.2f} USDT")

                # Alerta si baja del umbral
                if balance < THRESHOLD_USDT:
                    send_message(
                        f"⚠️ ALERTA: El balance cayó a {balance:.2f} USDT "
                        f"(umbral = {THRESHOLD_USDT} USDT)"
                    )

                # Resumen cada 15 minutos
                if now - last_summary >= 60 * 60:
                    send_message(f"⏱ Balance actual: {balance:.2f} USDT")
                    last_summary = now
            
            last_balance_check = now

        sleep(2)


if __name__ == "__main__":
    # Iniciar servidor HTTP en un thread separado (para Render)
    health_thread = Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # Iniciar el bot
    main_loop()
