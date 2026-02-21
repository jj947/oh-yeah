from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

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
    global_count -= 1
    emit("global_count", global_count, broadcast=True)

    for emotion in waiting:
        if sid in waiting[emotion]:
            waiting[emotion].remove(sid)

    if sid in pairs:
        partner = pairs[sid]

        pairs.pop(partner, None)
        pairs.pop(sid, None)

        emit("status", "⚠️ Votre partenaire a quitté. En attente...", to=partner)

        if partner in users:
            emotion = users[partner]["emotion"]
            waiting[emotion].append(partner)

    users.pop(sid, None)


@socketio.on("join")
def join(data):
    sid = request.sid
    users[sid] = data
    emotion = data["emotion"]

    queue = waiting[emotion]

    if queue:
        partner = queue.pop(0)
        pairs[sid] = partner
        pairs[partner] = sid

        emit("status", "🎉 Partenaire trouvé !", to=sid)
        emit("status", "🎉 Partenaire trouvé !", to=partner)
    else:
        queue.append(sid)
        emit("status", "⏳ En attente d’un partenaire...", to=sid)


@socketio.on("message")
def message(data):
    sid = request.sid

    if sid not in pairs:
        return

    partner = pairs[sid]

    payload = {
        "from": users[sid]["username"],
        "message": data["message"]
    }

    emit("message", payload, to=partner)
    emit("message", payload, to=sid)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
