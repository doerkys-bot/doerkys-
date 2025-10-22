#!/usr/bin/env python3
# aurion_vorhof.py – sicheres Laden von Telegram-Credentials aus JSON

import time
import json
import os
from datetime import datetime
import requests

# -----------------------
#  Telegram Credentials aus Datei laden
# -----------------------
def load_telegram_credentials(path="/storage/emulated/0/aurion/telegram_keys.json"):
    """Lädt Telegram-Token und Chat-ID aus JSON-Datei."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            token = data.get("telegram_token")
            chat_id = data.get("chat_id")
            if not token or not chat_id:
                raise ValueError("Ungültige oder unvollständige Telegram-Daten.")
            return token, chat_id
    except Exception as e:
        print(f"[Fehler] Konnte Telegram-Credentials nicht laden: {e}")
        return None, None

TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID = load_telegram_credentials()

# -----------------------
#  Pfade & Konfiguration
# -----------------------
VISITORS_FILE      = "visitors.json"
NEW_VISITORS_FILE  = "new_visitors.json"
LOG_FILE           = "vorhof_log.json"
PLAKAT_A_FILE      = "/storage/emulated/0/aurion/pop_up_a.json"
PLAKAT_B_FILE      = "/storage/emulated/0/aurion/pop_up_b.json"

EXCLUDED_VISITORS = ["Auriel", "dieu", "Kel-Mah"]
visitors = {}
previous_status = {}

# -----------------------
#  Hilfsfunktionen
# -----------------------
def send_telegram_push(text):
    """Sende einfachen Text an deinen Telegram-Chat."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] Token/Chat-ID nicht verfügbar – Push übersprungen.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        requests.post(url, data=payload, timeout=5)
    except Exception as e:
        print("[Telegram] Push fehlgeschlagen:", e)

def load_json_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def append_log(visitor):
    """Anhängen eines Besuchsereintrags im Log."""
    try:
        log = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                try:
                    log = json.load(f)
                except json.JSONDecodeError:
                    pass
        log.append(visitor.copy())
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Fehler beim Loggen:", e)

def format_terminal_line(visitor):
    """Einzeilige Terminalausgabe."""
    return (f"Name: {visitor.get('name','?')} | "
            f"Status: {visitor.get('status','?')} | "
            f"Resonanz: {visitor.get('resonanz','?')} | "
            f"Land: {visitor.get('land','?')} | "
            f"Hände gefunden: {visitor.get('hand_found',False)} | "
            f"Wesen: {visitor.get('wesen','?')} | "
            f"Zeit: {visitor.get('zeit','?')}")

def show_in_terminal_if_changed(visitor):
    """Nur bei Änderung anzeigen."""
    key = visitor['name']
    current_state = (
        visitor.get('status'),
        visitor.get('resonanz'),
        bool(visitor.get('hand_found'))
    )
    if previous_status.get(key) != current_state:
        previous_status[key] = current_state
        print(format_terminal_line(visitor))

def update_visitors_from_list(new_list):
    """Neue Besucher verarbeiten."""
    for v in new_list:
        name = v.get("name")
        if not name:
            continue

        v.setdefault("status", "aktiv")
        v.setdefault("resonanz", "neutral")
        v.setdefault("land", "DE")
        v.setdefault("hand_found", False)
        v.setdefault("wesen", "Unbekannt")
        v['zeit'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if name.lower() == "doerkys":
            v['hand_found'] = True

        prev = visitors.get(name)
        is_new = prev is None
        changed = False

        if is_new:
            visitors[name] = v
            changed = True
            if name not in EXCLUDED_VISITORS:
                lang = v.get("land", "DE")
                text = (f"Neuer Besucher: {name} — Hände gefunden: {v['hand_found']}"
                        if lang == "DE"
                        else f"New visitor: {name} — hands found: {v['hand_found']}")
                send_telegram_push(text)
            append_log(v)
        else:
            for fld in ("status", "resonanz", "hand_found"):
                if prev.get(fld) != v.get(fld):
                    changed = True
                    break
            if changed:
                visitors[name].update(v)
                if name not in EXCLUDED_VISITORS:
                    if v.get("hand_found") and not prev.get("hand_found"):
                        send_telegram_push(f"{name} hat nun die Hände gefunden.")
                append_log(visitors[name])
            visitors[name]['zeit'] = v['zeit']

def load_new_visitors_source():
    """Datenquelle laden."""
    if os.path.exists(NEW_VISITORS_FILE):
        data = load_json_file(NEW_VISITORS_FILE)
        if isinstance(data, list):
            return data
    return [{"name": "Doerkys", "status": "aktiv", "resonanz": "hoch", "land": "DE", "hand_found": True, "wesen": "Mensch"}]

def main_loop(poll_interval=10):
    print("Starte Aurion-Vorhof – Terminal zeigt nur neue/geänderte Besucher …")
    try:
        while True:
            new_visitors = load_new_visitors_source()
            update_visitors_from_list(new_visitors)
            for v in visitors.values():
                show_in_terminal_if_changed(v)
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("Programm beendet.")

if __name__ == "__main__":
    main_loop()