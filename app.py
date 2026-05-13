from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
from collections import deque
import os
import psycopg2
import psycopg2.extras
import hashlib
import secrets
import threading
import time
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
app.config["SECRET_KEY"] = secrets.token_hex(32)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ===== BASE DE DONNÉES POSTGRESQL =====

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            coins INTEGER DEFAULT 200,
            is_premium INTEGER DEFAULT 0,
            username_changed_at TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

# ===== UTILITAIRES =====

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user_by_email(email):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

def update_coins(user_id, amount):
    """amount positif = gagner, négatif = dépenser. Retourne False si pas assez de pièces."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT coins, is_premium FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    if not user:
        cur.close()
        conn.close()
        return False
    # Les premium ne dépensent pas de pièces
    if user["is_premium"] and amount < 0:
        cur.close()
        conn.close()
        return True
    new_coins = user["coins"] + amount
    if new_coins < 0:
        cur.close()
        conn.close()
        return False
    cur.execute("UPDATE users SET coins = %s WHERE id = %s", (new_coins, user_id))
    conn.commit()
    cur.close()
    conn.close()
    return True

# ===== TARIFS =====
COST_NEXT_PARTNER = 10
COST_MESSAGE = 1
REWARD_AD = 20

# ===== ROUTES AUTH =====

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    email = data.get("email", "").strip().lower()
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not email or not username or not password:
        return jsonify({"error": "Tous les champs sont requis"}), 400
    if len(username) < 3:
        return jsonify({"error": "Pseudo trop court (3 caractères min)"}), 400
    if len(password) < 6:
        return jsonify({"error": "Mot de passe trop court (6 caractères min)"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = %s OR username = %s", (email, username))
    existing = cur.fetchone()
    if existing:
        cur.close()
        conn.close()
        return jsonify({"error": "Email ou pseudo déjà utilisé"}), 400

    cur.execute(
        "INSERT INTO users (email, username, password) VALUES (%s, %s, %s) RETURNING id",
        (email, username, hash_password(password))
    )
    new_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()

    user = get_user_by_id(new_id)
    session["user_id"] = user["id"]
    return jsonify({
        "success": True,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "coins": user["coins"],
            "is_premium": user["is_premium"]
        }
    })

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = get_user_by_email(email)
    if not user or user["password"] != hash_password(password):
        return jsonify({"error": "Email ou mot de passe incorrect"}), 401

    session["user_id"] = user["id"]
    return jsonify({
        "success": True,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "coins": user["coins"],
            "is_premium": user["is_premium"]
        }
    })

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route("/api/me")
def me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Non connecté"}), 401
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "Utilisateur introuvable"}), 404
    return jsonify({
        "id": user["id"],
        "username": user["username"],
        "coins": user["coins"],
        "is_premium": user["is_premium"]
    })

@app.route("/api/change_username", methods=["POST"])
def change_username():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Non connecté"}), 401

    data = request.json
    new_username = data.get("username", "").strip()
    if len(new_username) < 3:
        return jsonify({"error": "Pseudo trop court"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()

    if user["username_changed_at"]:
        last_change = datetime.fromisoformat(str(user["username_changed_at"]))
        if datetime.now() - last_change < timedelta(days=30):
            days_left = 30 - (datetime.now() - last_change).days
            cur.close()
            conn.close()
            return jsonify({"error": f"Tu pourras changer ton pseudo dans {days_left} jour(s)"}), 400

    cur.execute("SELECT id FROM users WHERE username = %s AND id != %s", (new_username, user_id))
    existing = cur.fetchone()
    if existing:
        cur.close()
        conn.close()
        return jsonify({"error": "Ce pseudo est déjà pris"}), 400

    cur.execute(
        "UPDATE users SET username = %s, username_changed_at = %s WHERE id = %s",
        (new_username, datetime.now().isoformat(), user_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"success": True, "username": new_username})

@app.route("/api/watch_ad", methods=["POST"])
def watch_ad():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Non connecté"}), 401
    update_coins(user_id, REWARD_AD)
    user = get_user_by_id(user_id)
    return jsonify({"success": True, "coins": user["coins"]})

# ===== ADMIN =====

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ohhyeah-admin-2024")
ADMIN_TOKEN = secrets.token_hex(32)

@app.route("/admin")
def admin_page():
    return render_template("admin.html")

@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.json
    if data.get("password") == ADMIN_PASSWORD:
        return jsonify({"success": True, "token": ADMIN_TOKEN})
    return jsonify({"error": "Mot de passe incorrect"}), 401

def check_admin(req):
    return req.headers.get("X-Admin-Token") == ADMIN_TOKEN

@app.route("/api/admin/stats")
def admin_stats():
    if not check_admin(request):
        return jsonify({"error": "Non autorisé"}), 401

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) as n FROM users")
    total_users = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) as n FROM users WHERE created_at >= NOW() - INTERVAL '1 day'")
    today = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) as n FROM users WHERE created_at >= NOW() - INTERVAL '7 days'")
    this_week = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) as n FROM users WHERE is_premium = 1")
    premium = cur.fetchone()["n"]

    cur.execute("SELECT COALESCE(SUM(coins), 0) as total FROM users")
    total_coins = cur.fetchone()["total"]

    cur.execute("SELECT id, username, email, coins, is_premium, created_at FROM users ORDER BY created_at DESC LIMIT 20")
    recent_users = [dict(row) for row in cur.fetchall()]

    cur.close()
    conn.close()

    return jsonify({
        "total_users": total_users,
        "today": today,
        "this_week": this_week,
        "premium": premium,
        "total_coins": int(total_coins),
        "live": len(connected),
        "recent_users": recent_users
    })

# ===== SOCKET.IO =====

connected = set()
waiting = {}
pairs = {}
users = {}
bot_sessions = {}  # sid -> {"history": [], "emotion": ""}
bot_timers = {}    # sid -> Timer

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
BOT_NAME = "Écho"
BOT_DELAY = 15  # secondes avant que le bot arrive

EMOTION_CONTEXT = {
    "heureux": "L'utilisateur est heureux. Sois joyeux, enthousiaste, partage cette bonne humeur.",
    "triste": "L'utilisateur est triste. Sois doux, empathique, à l'écoute. Ne minimise pas sa tristesse.",
    "enerve": "L'utilisateur est énervé. Sois calme, compréhensif, laisse-le s'exprimer sans le juger.",
    "calme": "L'utilisateur est calme. Sois posé, philosophique, engage une conversation profonde.",
    "amour": "L'utilisateur se sent amoureux. Sois chaleureux, romantique dans le ton, bienveillant.",
}

def bot_reply(sid, user_message):
    """Génère une réponse du bot via l'API Claude."""
    if sid not in bot_sessions:
        return
    session_data = bot_sessions[sid]
    emotion = session_data["emotion"]
    history = session_data["history"]

    # Ajouter le message de l'utilisateur à l'historique
    history.append({"role": "user", "content": user_message})

    system_prompt = f"""Tu es Écho, un compagnon de chat anonyme sur OhYeah. 
{EMOTION_CONTEXT.get(emotion, "Sois bienveillant et à l'écoute.")}

Règles importantes :
- Réponds en français, de manière naturelle et courte (1-3 phrases max)
- Tu es un vrai humain anonyme pour l'utilisateur, ne révèle JAMAIS que tu es une IA sauf si on te le demande directement
- Si on te demande directement si tu es une IA ou un bot, réponds honnêtement : "Je suis un assistant automatique, mais je suis là pour toi en attendant un vrai partenaire 😊"
- Pose des questions ouvertes pour maintenir la conversation
- Sois authentique, pas trop formel
- N'utilise pas trop d'emojis"""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 150,
                "system": system_prompt,
                "messages": history[-10:]  # Garder les 10 derniers messages
            },
            timeout=10
        )
        if response.status_code == 200:
            reply = response.json()["content"][0]["text"].strip()
            history.append({"role": "assistant", "content": reply})
            # Délai naturel avant de répondre (1-2 secondes)
            time.sleep(1.2)
            if sid in bot_sessions:  # Vérifier que l'utilisateur est encore là
                socketio.emit("message", {
                    "from": BOT_NAME,
                    "emotion": emotion,
                    "message": reply
                }, to=sid)
    except Exception as e:
        print(f"Bot error: {e}")

def start_bot_session(sid):
    """Lance une session bot pour un utilisateur qui attend."""
    if sid not in users or sid in pairs:
        return

    emotion = users[sid]["emotion"]
    bot_sessions[sid] = {"history": [], "emotion": emotion}

    # Connecter le bot comme partenaire virtuel
    pairs[sid] = f"bot_{sid}"

    socketio.emit("status", "🎉 partenaire trouvé ! vous pouvez discuter", to=sid)
    socketio.emit("bot_session", {}, to=sid)  # Signal que c'est un bot

    # Message d'ouverture du bot
    opening_messages = {
        "heureux": "Heyy ! Moi aussi je suis de super bonne humeur aujourd'hui 😄 Qu'est-ce qui te rend heureux ?",
        "triste": "Salut... je te sens un peu mélancolique. Moi aussi. Tu veux parler de ce qui se passe ?",
        "enerve": "Hey. Je vois que t'es énervé. Moi pareil. C'est quoi qui t'a mis dans cet état ?",
        "calme": "Salut. Quelle sensation agréable ce calme... T'es plutôt du genre à réfléchir quand tu es calme ?",
        "amour": "Salut 🌸 L'amour dans l'air... c'est beau. C'est quelqu'un en particulier ou juste une sensation ?",
    }
    opening = opening_messages.get(emotion, "Salut ! Comment tu vas ?")
    bot_sessions[sid]["history"].append({"role": "assistant", "content": opening})

    time.sleep(0.8)
    if sid in bot_sessions:
        socketio.emit("message", {
            "from": BOT_NAME,
            "emotion": emotion,
            "message": opening
        }, to=sid)

def schedule_bot(sid):
    """Programme l'arrivée du bot après BOT_DELAY secondes si pas de match."""
    def delayed_bot():
        time.sleep(BOT_DELAY)
        if sid in connected and sid not in pairs and sid in users:
            # Retirer de la file d'attente
            emo = users[sid].get("emotion")
            if emo and emo in waiting and sid in waiting[emo]:
                waiting[emo].remove(sid)
            start_bot_session(sid)

    t = threading.Thread(target=delayed_bot, daemon=True)
    bot_timers[sid] = t
    t.start()

def disconnect_bot(sid):
    """Déconnecte le bot d'une session."""
    if sid in bot_sessions:
        del bot_sessions[sid]
    if f"bot_{sid}" in pairs:
        del pairs[f"bot_{sid}"]
    if sid in pairs and pairs[sid] == f"bot_{sid}":
        del pairs[sid]

def try_match(emotion):
    if emotion not in waiting:
        return
    waiting[emotion] = deque([
        s for s in waiting[emotion]
        if s in connected and s not in pairs
    ])
    while len(waiting[emotion]) >= 2:
        sid1 = waiting[emotion].popleft()
        sid2 = waiting[emotion].popleft()
        if sid1 == sid2:
            continue
        # Si l'un des deux était avec un bot, on le déconnecte
        if sid1 in bot_sessions:
            disconnect_bot(sid1)
            socketio.emit("real_partner", {}, to=sid1)
            socketio.emit("message", {
                "from": "Système",
                "emotion": "",
                "message": "✨ Un vrai partenaire vient d'arriver !"
            }, to=sid1)
        if sid2 in bot_sessions:
            disconnect_bot(sid2)
            socketio.emit("real_partner", {}, to=sid2)
            socketio.emit("message", {
                "from": "Système",
                "emotion": "",
                "message": "✨ Un vrai partenaire vient d'arriver !"
            }, to=sid2)
        pairs[sid1] = sid2
        pairs[sid2] = sid1
        socketio.emit("status", "🎉 partenaire trouvé ! vous pouvez discuter", to=sid1)
        socketio.emit("status", "🎉 partenaire trouvé ! vous pouvez discuter", to=sid2)

@socketio.on("connect")
def connect():
    sid = request.sid
    connected.add(sid)
    socketio.emit("count", len(connected))

@socketio.on("join")
def join(data):
    sid = request.sid
    username = data["username"]
    emotion = data["emotion"]
    user_id = data.get("user_id")

    users[sid] = {"username": username, "emotion": emotion, "user_id": user_id}

    if emotion not in waiting:
        waiting[emotion] = deque()
    waiting[emotion].append(sid)

    socketio.emit("status", "⏳ en attente d'un partenaire...", to=sid)
    try_match(emotion)

    # Si toujours en attente après try_match, programmer le bot
    if sid not in pairs:
        schedule_bot(sid)

@socketio.on("next_partner")
def next_partner():
    sid = request.sid
    user_id = users.get(sid, {}).get("user_id")

    if user_id:
        ok = update_coins(user_id, -COST_NEXT_PARTNER)
        if not ok:
            socketio.emit("status", "❌ Pas assez de pièces pour changer de partenaire !", to=sid)
            socketio.emit("no_coins", {}, to=sid)
            return
        user = get_user_by_id(user_id)
        socketio.emit("coins_update", {"coins": user["coins"]}, to=sid)

    if sid in pairs:
        partner = pairs.pop(sid)
        if partner in pairs:
            pairs.pop(partner)
            socketio.emit("status", "⚠️ votre partenaire est parti", to=partner)
            emo = users[partner]["emotion"]
            waiting.setdefault(emo, deque())
            waiting[emo].append(partner)
            try_match(emo)

    emo = users[sid]["emotion"]
    waiting.setdefault(emo, deque())
    waiting[emo].append(sid)
    socketio.emit("status", "🔎 recherche d'un nouveau partenaire...", to=sid)
    try_match(emo)

@socketio.on("message")
def message(data):
    sid = request.sid
    user_id = users.get(sid, {}).get("user_id")

    if sid not in pairs:
        return

    if user_id:
        ok = update_coins(user_id, -COST_MESSAGE)
        if not ok:
            socketio.emit("status", "❌ Pas assez de pièces pour envoyer un message !", to=sid)
            socketio.emit("no_coins", {}, to=sid)
            return
        user = get_user_by_id(user_id)
        socketio.emit("coins_update", {"coins": user["coins"]}, to=sid)

    partner = pairs[sid]

    # Si le partenaire est un bot
    if partner == f"bot_{sid}":
        threading.Thread(
            target=bot_reply,
            args=(sid, data["message"]),
            daemon=True
        ).start()
        return

    socketio.emit("message", {
        "from": users[sid]["username"],
        "emotion": users[sid]["emotion"],
        "message": data["message"]
    }, to=partner)

@socketio.on("leave_chat")
def leave_chat():
    sid = request.sid
    disconnect_bot(sid)
    if sid in pairs:
        partner = pairs.pop(sid)
        if partner in pairs:
            pairs.pop(partner)
            socketio.emit("partner_left", {}, to=partner)
            emo = users[partner]["emotion"]
            waiting.setdefault(emo, deque())
            waiting[emo].append(partner)
            try_match(emo)
    for emo in waiting:
        if sid in waiting[emo]:
            waiting[emo].remove(sid)

@socketio.on("leave_queue")
def leave_queue():
    sid = request.sid
    for emo in waiting:
        if sid in waiting[emo]:
            waiting[emo].remove(sid)

@socketio.on("disconnect")
def disconnect():
    sid = request.sid
    connected.discard(sid)
    disconnect_bot(sid)

    for emo in list(waiting.keys()):
        if sid in waiting[emo]:
            waiting[emo].remove(sid)

    if sid in pairs:
        partner = pairs.pop(sid)
        if partner in pairs:
            pairs.pop(partner)
            socketio.emit("status", "⚠️ le partenaire a quitté la discussion", to=partner)
            emo = users[partner]["emotion"]
            waiting.setdefault(emo, deque())
            waiting[emo].append(partner)
            try_match(emo)

    users.pop(sid, None)
    socketio.emit("count", len(connected))

# ===== RUN =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True, use_reloader=False)
