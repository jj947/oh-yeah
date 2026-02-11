from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

waiting = {}        # emotion -> [sid, sid, ...]
pairs = {}          # sid -> partner_sid
connected_users = set()

@socketio.on("connect")
def handle_connect():
    connected_users.add(request.sid)
    socketio.emit("global_count", len(connected_users))

@app.route("/")
def index():
    return render_template("index.html")


def broadcast_count():
    socketio.emit("count", len(users))


@socketio.on("join")
def join(data):
    sid = request.sid
    username = data["username"]
    emotion = data["emotion"]

    users[sid] = {"username": username, "emotion": emotion}
    broadcast_count()

    waiting.setdefault(emotion, [])

    if waiting[emotion]:
        partner = waiting[emotion].pop(0)

        pairs[sid] = partner
        pairs[partner] = sid

        emit("status", "🎉 Partenaire trouvé", to=sid)
        emit("status", "🎉 Partenaire trouvé", to=partner)

    else:
        waiting[emotion].append(sid)
        emit("status", "⏳ En attente d’un partenaire...", to=sid)


@socketio.on("send_message")
def send_message(data):
    sid = request.sid
    message = data["message"]

    if sid not in pairs:
        return

    partner = pairs[sid]

    emit("message", {
        "from": users[sid]["username"],
        "text": message,
        "self": False
    }, to=partner)

    emit("message", {
        "from": users[sid]["username"],
        "text": message,
        "self": True
    }, to=sid)


@socketio.on("leave")
def leave():
    disconnect()


@socketio.on("disconnect")
def disconnect():
    sid = request.sid
    connected_users.discard(sid)
    socketio.emit("global_count", len(connected_users))
    if sid not in users:
        return

    emotion = users[sid]["emotion"]

    if sid in waiting.get(emotion, []):
        waiting[emotion].remove(sid)

    if sid in pairs:
        partner = pairs.pop(sid)
        pairs.pop(partner, None)

        emit("status", "⚠️ Votre partenaire a quitté", to=partner)

        waiting.setdefault(users[partner]["emotion"], []).append(partner)
        emit("status", "⏳ En attente d’un partenaire...", to=partner)

    users.pop(sid, None)
    broadcast_count()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)


