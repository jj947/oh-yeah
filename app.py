import os
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from collections import deque

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"

socketio = SocketIO(
    app,
    cors_allowed_origins="*"
)

connected = set()
waiting = {}
pairs = {}
users = {}


@app.route("/")
def home():
    return render_template("index.html")


# ===== CONNECT =====
@socketio.on("connect")
def on_connect():
    sid = request.sid
    connected.add(sid)
    emit("count", len(connected), broadcast=True)


# ===== JOIN =====
@socketio.on("join")
def on_join(data):
    sid = request.sid

    username = data.get("username")
    emotion = data.get("emotion")

    users[sid] = {"username": username, "emotion": emotion}

    if emotion not in waiting:
        waiting[emotion] = deque()

    # remove dead
    waiting[emotion] = deque([s for s in waiting[emotion] if s in connected])

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
def on_message(data):
    sid = request.sid

    if sid not in pairs:
        return

    partner = pairs[sid]

    emit("message", {
        "from": users[sid]["username"],
        "emotion": users[sid]["emotion"],
        "message": data["message"]
    }, to=partner)


# ===== DISCONNECT =====
@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid

    connected.discard(sid)

    # remove waiting
    for emo in list(waiting.keys()):
        if sid in waiting[emo]:
            waiting[emo].remove(sid)

    # handle pair
    if sid in pairs:
        partner = pairs.pop(sid, None)

        if partner:
            pairs.pop(partner, None)

            emit("status", "le partenaire a quitté la discussion", to=partner)

            emo = users.get(partner, {}).get("emotion")
            if emo:
                if emo not in waiting:
                    waiting[emo] = deque()
                waiting[emo].append(partner)

    users.pop(sid, None)

    emit("count", len(connected), broadcast=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
