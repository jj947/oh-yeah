from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

# ---------------- ÉTAT ----------------
waiting = {
    "heureux": [],
    "triste": [],
    "enerve": [],
    "calme": [],
    "amour": []
}

pairs = {}          # sid -> sid
usernames = {}      # sid -> pseudo
emotions = {}       # sid -> emotion


@app.route("/")
def index():
    return render_template("index.html")


# ---------------- UTILS ----------------
def send_counters():
    emotion_counts = {}
    total = 0

    for emo, lst in waiting.items():
        emotion_counts[emo] = len(lst)
        total += len(lst)

    socketio.emit("emotion_counts", emotion_counts)
    socketio.emit("global_count", total)


# ---------------- SOCKETS ----------------
@socketio.on("connect")
def handle_connect():
    send_counters()


@socketio.on("join")
def handle_join(data):
    sid = request.sid
    username = data["username"]
    emotion = data["emotion"]

    usernames[sid] = username
    emotions[sid] = emotion

    if waiting[emotion]:
        partner = waiting[emotion].pop(0)

        pairs[sid] = partner
        pairs[partner] = sid

        emit("status", "🎉 Partenaire trouvé !", to=sid)
        emit("status", "🎉 Partenaire trouvé !", to=partner)
    else:
        waiting[emotion].append(sid)
        emit("status", "⏳ En attente d’un partenaire...", to=sid)

    send_counters()


@socketio.on("send_message")
def handle_message(data):
    sid = request.sid
    if sid not in pairs:
        return

    partner = pairs[sid]

    emit("message", {
        "from": usernames[sid],
        "message": data["message"]
    }, to=partner)

    emit("message", {
        "from": "Moi",
        "message": data["message"]
    }, to=sid)


@socketio.on("leave")
def handle_leave():
    handle_disconnect()


@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid

    # retirer de l’attente
    for emo in waiting:
        if sid in waiting[emo]:
            waiting[emo].remove(sid)

    # gérer la discussion
    if sid in pairs:
        partner = pairs.pop(sid)
        pairs.pop(partner, None)

        emit("status", "⚠️ Votre partenaire a quitté.", to=partner)

        emo = emotions.get(partner)
        if emo:
            waiting[emo].append(partner)
            emit("status", "⏳ En attente d’un partenaire...", to=partner)

    usernames.pop(sid, None)
    emotions.pop(sid, None)

    send_counters()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
