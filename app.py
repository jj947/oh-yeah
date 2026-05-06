from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from collections import deque

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

connected = set()
waiting = {}
pairs = {}
users = {}


@app.route("/")
def home():
    return render_template("index.html")


# ===== CONNECT =====
@socketio.on("connect")
def connect():
    sid = request.sid
    connected.add(sid)
    emit("count", len(connected), broadcast=True)


# ===== JOIN =====
@socketio.on("join")
def join(data):
    sid = request.sid

    username = data.get("username")
    emotion = data.get("emotion")

    users[sid] = {"username": username, "emotion": emotion}

    if emotion not in waiting:
        waiting[emotion] = deque()

    # 🔥 CLEAN : éviter doublons / ghosts
    waiting[emotion] = deque([s for s in waiting[emotion] if s in connected and s not in pairs])

    # MATCH
    if waiting[emotion]:
        partner = waiting[emotion].popleft()

        # sécurité double match
        if partner in pairs:
            waiting[emotion].append(partner)
            waiting[emotion].appendleft(sid)
            return

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

    if sid not in pairs:
        return

    partner = pairs[sid]

    emit("message", {
        "from": users[sid]["username"],
        "message": data["message"]
    }, to=partner)


# ===== DISCONNECT =====
@socketio.on("disconnect")
def disconnect():
    sid = request.sid

    connected.discard(sid)

    # remove waiting
    for emo in list(waiting.keys()):
        waiting[emo] = deque([s for s in waiting[emo] if s != sid])

    # handle pair
    if sid in pairs:
        partner = pairs.pop(sid, None)

        if partner:
            pairs.pop(partner, None)

            emit("status", "le partenaire a quitté la discussion", to=partner)

            emo = users.get(partner, {}).get("emotion")
            if emo:
                waiting.setdefault(emo, deque())
                waiting[emo].append(partner)

    users.pop(sid, None)

    emit("count", len(connected), broadcast=True)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
