import os
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from collections import deque

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

connected_users = set()
waiting = {}
pairs = {}
user_data = {}


@app.route("/")
def index():
    return render_template("index.html")


# ===== CONNECT =====
@socketio.on("connect")
def connect():
    sid = request.sid
    connected_users.add(sid)
    emit("count", len(connected_users), broadcast=True)


# ===== JOIN =====
@socketio.on("join")
def join(data):
    sid = request.sid

    username = data.get("username")
    emotion = data.get("emotion")

    user_data[sid] = {"username": username, "emotion": emotion}

    if emotion not in waiting:
        waiting[emotion] = deque()

    # 🔥 CLEAN DEAD SIDS (important)
    waiting[emotion] = deque([s for s in waiting[emotion] if s in connected_users])

    # MATCH
    if waiting[emotion]:
        partner = waiting[emotion].popleft()

        pairs[sid] = partner
        pairs[partner] = sid

        emit("status", "🎉 partenaire trouvé ! vous pouvez discuter", to=sid)
        emit("status", "🎉 partenaire trouvé ! vous pouvez discuter", to=partner)

    else:
        waiting[emotion].append(sid)
        emit("status", "⏳ en attente d'un partenaire", to=sid)


# ===== MESSAGE =====
@socketio.on("message")
def message(data):
    sid = request.sid

    if sid in pairs:
        partner = pairs[sid]

        emit("message", {
            "from": user_data[sid]["username"],
            "message": data["message"]
        }, to=partner)


# ===== DISCONNECT =====
@socketio.on("disconnect")
def disconnect():
    sid = request.sid

    connected_users.discard(sid)

    # remove from waiting
    for emo in list(waiting.keys()):
        if sid in waiting[emo]:
            waiting[emo].remove(sid)

    # handle pair break
    if sid in pairs:
        partner = pairs.pop(sid, None)

        if partner:
            pairs.pop(partner, None)

            emit("status", "le partenaire a quitté la discussion", to=partner)

            emo = user_data.get(partner, {}).get("emotion")
            if emo:
                if emo not in waiting:
                    waiting[emo] = deque()
                waiting[emo].append(partner)

    user_data.pop(sid, None)

    emit("count", len(connected_users), broadcast=True)


# ===== RUN =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
