import os
import json

CONFIG_DIR = os.path.expanduser("~/.config/net-scanner")
DEVICES_FILE = os.path.join(CONFIG_DIR, "devices.json")
HISTORY_FILE = os.path.join(CONFIG_DIR, "router_history.json")

def init_db():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(DEVICES_FILE):
        with open(DEVICES_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

def load_devices():
    init_db()
    try:
        with open(DEVICES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_device_name(mac, name):
    init_db()
    devices = load_devices()
    devices[mac.lower()] = name
    try:
        with open(DEVICES_FILE, "w", encoding="utf-8") as f:
            json.dump(devices, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar nome do dispositivo: {e}")

def load_router_history():
    init_db()
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def add_router_restart_log(router_ip, router_mac, timestamp_str):
    init_db()
    history = load_router_history()
    log_entry = {
        "ip": router_ip,
        "mac": router_mac,
        "timestamp": timestamp_str,
        "message": f"Roteador {router_ip} ({router_mac}) reiniciou ou ficou offline."
    }
    history.insert(0, log_entry)  # Add at the beginning
    # Keep last 100 entries
    history = history[:100]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar histórico do roteador: {e}")
