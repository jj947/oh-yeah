from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

# ---- ÉTATS ----
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


# ---- UTILS ----
def send_counters():
    counts = {}
    total = 0
    for emo, lst in waiting.items():
        counts[emo] = len(lst)
        total += len(lst)

    emit("emotion_counts", counts, broadcast=True)
    emit("global_count", total, broadcast=True)


# ---- SOCKETS ----
@socketio.on("connect")
def connect():
    send_counters()


@socketio.on("join")
def join(data):
    sid = request.sid
    username = data["username"]
    emotion = data["emotion"]

    usernames[sid] = username
    emotions[sid] = emotion

    # quelqu’un attend déjà ?
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
def send_message(data):
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
def leave():
    disconnect()


@socketio.on("disconnect")
def disconnect():
    sid = request.sid

    # enlever de l’attente
    for emo in waiting:
        if sid in waiting[emo]:
            waiting[emo].remove(sid)

    # prévenir le partenaire
    if sid in pairs:
        partner = pairs.pop(sid)
        pairs.pop(partner, None)

        emit("status", "⚠️ Votre partenaire a quitté.", to=partner)

        # remettre partenaire en attente
        emo = emotions.get(partner)
        if emo:
            waiting[emo].append(partner)
            emit("status", "⏳ En attente d’un partenaire...", to=partner)

    usernames.pop(sid, None)
    emotions.pop(sid, None)

    send_counters()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
