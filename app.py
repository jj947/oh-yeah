from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from collections import deque
import os

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
def index():
    return render_template("index.html")


# ===== CONNECT =====
@socketio.on("connect")
def connect():
    sid = request.sid

    connected.add(sid)

    print("CONNECT:", sid)

    socketio.emit("count", len(connected))


# ===== JOIN =====
@socketio.on("join")
def join(data):
    sid = request.sid

    username = data["username"]
    emotion = data["emotion"]

    users[sid] = {
        "username": username,
        "emotion": emotion
    }

    print("JOIN:", username, emotion, sid)

    if emotion not in waiting:
        waiting[emotion] = deque()

    # enlever users morts
    waiting[emotion] = deque([
        s for s in waiting[emotion]
        if s in connected and s not in pairs
    ])

    # MATCH
    if len(waiting[emotion]) > 0:

        partner = waiting[emotion].popleft()

        if partner == sid:
            waiting[emotion].append(sid)
            return

        pairs[sid] = partner
        pairs[partner] = sid

        socketio.emit(
            "status",
            "🎉 partenaire trouvé ! vous pouvez discuter",
            to=sid
        )

        socketio.emit(
            "status",
            "🎉 partenaire trouvé ! vous pouvez discuter",
            to=partner
        )

        print("MATCH:", sid, partner)

    else:
        waiting[emotion].append(sid)

        socketio.emit(
            "status",
            "⏳ en attente d'un partenaire",
            to=sid
        )


# ===== MESSAGE =====
@socketio.on("message")
def message(data):
    sid = request.sid

    if sid not in pairs:
        return

    partner = pairs[sid]

    socketio.emit(
        "message",
        {
            "from": users[sid]["username"],
            "emotion": users[sid]["emotion"],
            "message": data["message"]
        },
        to=partner
    )


# ===== DISCONNECT =====
@socketio.on("disconnect")
def disconnect():
    sid = request.sid

    print("DISCONNECT:", sid)

    connected.discard(sid)

    # remove waiting
    for emo in waiting:
        if sid in waiting[emo]:
            waiting[emo].remove(sid)

    # remove pair
    if sid in pairs:

        partner = pairs.pop(sid)

        if partner in pairs:
            pairs.pop(partner)

            socketio.emit(
                "status",
                "⚠️ le partenaire a quitté la discussion",
                to=partner
            )

            emo = users[partner]["emotion"]

            if emo not in waiting:
                waiting[emo] = deque()

            waiting[emo].append(partner)

    users.pop(sid, None)

    socketio.emit("count", len(connected))


# ===== RUN =====
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=False,
        allow_unsafe_werkzeug=True
    )
