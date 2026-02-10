from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

waiting = {}          # emotion -> [sid]
pairs = {}            # sid -> sid
users = {}            # sid -> pseudo
emotions = {}         # sid -> emotion
connected = set()


@app.route("/")
def index():
    return render_template("index.html")


def update_counters():
    emotion_counts = {e: len(waiting[e]) for e in waiting}
    socketio.emit("counters", {
        "global": len(connected),
        "emotions": emotion_counts
    })


@socketio.on("connect")
def connect():
    connected.add(request.sid)
    update_counters()


@socketio.on("join")
def join(data):
    sid = request.sid
    pseudo = data["username"]
    emotion = data["emotion"]

    users[sid] = pseudo
    emotions[sid] = emotion
    waiting.setdefault(emotion, [])

    emit("joined_chat", to=sid)

    if waiting[emotion]:
        partner = waiting[emotion].pop(0)

        pairs[sid] = partner
        pairs[partner] = sid

        emit("status", "🎉 Partenaire trouvé !", to=sid)
        emit("status", "🎉 Partenaire trouvé !", to=partner)
    else:
        waiting[emotion].append(sid)
        emit("status", "⏳ En attente d’un partenaire...", to=sid)

    update_counters()


@socketio.on("send_message")
def send_message(data):
    sid = request.sid
    msg = data["message"]

    if sid not in pairs:
        return

    partner = pairs[sid]

    emit("message", {
        "text": msg,
        "self": True
    }, to=sid)

    emit("message", {
        "text": msg,
        "self": False
    }, to=partner)


@socketio.on("leave")
def leave():
    sid = request.sid

    if sid in pairs:
        partner = pairs.pop(sid)
        pairs.pop(partner, None)

        emit("status", "⚠️ Votre partenaire a quitté.", to=partner)

        emo = emotions.get(partner)
        if emo:
            waiting.setdefault(emo, []).append(partner)

    update_counters()


@socketio.on("disconnect")
def disconnect():
    sid = request.sid
    connected.discard(sid)

    for e in waiting:
        if sid in waiting[e]:
            waiting[e].remove(sid)

    if sid in pairs:
        partner = pairs.pop(sid)
        pairs.pop(partner, None)
        emit("status", "⚠️ Votre partenaire a quitté.", to=partner)

    users.pop(sid, None)
    emotions.pop(sid, None)

    update_counters()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
