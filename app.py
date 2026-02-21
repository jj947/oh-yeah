from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading"
)

waiting = {
    "heureux": [],
    "triste": [],
    "enerve": [],
    "calme": [],
    "amour": []
}

pairs = {}
users = {}
global_count = 0


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("connect")
def connect():
    global global_count
    global_count += 1
    emit("global_count", global_count, broadcast=True)


@socketio.on("disconnect")
def disconnect():
    global global_count
    sid = request.sid

    global_count = max(0, global_count - 1)
    emit("global_count", global_count, broadcast=True)

    # enlever des files d'attente
    for emotion in waiting:
        if sid in waiting[emotion]:
            waiting[emotion].remove(sid)

    # gérer la discussion
    if sid in pairs:
        partner = pairs.get(sid)

        pairs.pop(sid, None)
        pairs.pop(partner, None)

        if partner and partner in users:
            emit("status", "⚠️ Votre partenaire a quitté. En attente...", to=partner)

            emotion = users[partner].get("emotion")
            if emotion in waiting:
                waiting[emotion].append(partner)

    users.pop(sid, None)


@socketio.on("join")
def join(data):
    sid = request.sid

    username = data.get("username")
    emotion = data.get("emotion")

    if not username or not emotion:
        return

    users[sid] = {
        "username": username,
        "emotion": emotion
    }

    queue = waiting.get(emotion)

    if queue and len(queue) > 0:
        partner = queue.pop(0)

        pairs[sid] = partner
        pairs[partner] = sid

        emit("status", "🎉 Partenaire trouvé !", to=sid)
        emit("status", "🎉 Partenaire trouvé !", to=partner)
    else:
        waiting[emotion].append(sid)
        emit("status", "⏳ En attente d’un partenaire...", to=sid)


@socketio.on("message")
def message(data):
    sid = request.sid

    if sid not in pairs:
        return

    if sid not in users:
        return

    msg = data.get("message")
    if not msg:
        return

    partner = pairs.get(sid)
    username = users[sid].get("username", "Inconnu")

    payload = {
        "from": username,
        "message": msg
    }

    emit("message", payload, to=partner)
    emit("message", payload, to=sid)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
