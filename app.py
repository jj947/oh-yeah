from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

# ------------------------
# STOCKAGE GLOBAL
# ------------------------
waiting_users = {}      # emotion -> [sid]
pairs = {}              # sid -> partner_sid
usernames = {}          # sid -> pseudo
emotions = {}           # sid -> emotion
connected_users = set()


# ------------------------
# ROUTE
# ------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ------------------------
# COUNTERS
# ------------------------
def emit_counters():
    emotion_counts = {emo: len(users) for emo, users in waiting_users.items()}
    socketio.emit("update_counters", {
        "global": len(connected_users),
        "emotions": emotion_counts
    })


# ------------------------
# SOCKET EVENTS
# ------------------------
@socketio.on("connect")
def connect():
    connected_users.add(request.sid)
    emit_counters()


@socketio.on("join")
def join(data):
    sid = request.sid
    username = data["username"]
    emotion = data["emotion"]

    usernames[sid] = username
    emotions[sid] = emotion
    waiting_users.setdefault(emotion, [])

    if waiting_users[emotion]:
        partner = waiting_users[emotion].pop(0)

        pairs[sid] = partner
        pairs[partner] = sid

        emit("status", "🎉 Partenaire trouvé !", to=sid)
        emit("status", "🎉 Partenaire trouvé !", to=partner)
    else:
        waiting_users[emotion].append(sid)
        emit("status", "⏳ En attente d’un partenaire...", to=sid)

    emit_counters()


@socketio.on("message")
def message(data):
    sid = request.sid
    msg = data["message"]

    if sid not in pairs:
        return

    partner = pairs[sid]

    # Message pour le partenaire
    emit("message", {
        "from": usernames[sid],
        "message": msg,
        "self": False
    }, to=partner)

    # Message pour soi-même
    emit("message", {
        "from": "Moi",
        "message": msg,
        "self": True
    }, to=sid)


@socketio.on("leave_chat")
def leave():
    sid = request.sid

    if sid in pairs:
        partner = pairs.pop(sid)
        pairs.pop(partner, None)

        emit("status", "⚠️ Votre partenaire a quitté.", to=partner)

        emo = emotions.get(partner)
        if emo:
            waiting_users.setdefault(emo, []).append(partner)

    emit_counters()


@socketio.on("disconnect")
def disconnect():
    sid = request.sid
    connected_users.discard(sid)

    for emo in waiting_users:
        if sid in waiting_users[emo]:
            waiting_users[emo].remove(sid)

    if sid in pairs:
        partner = pairs.pop(sid)
        pairs.pop(partner, None)
        emit("status", "⚠️ Votre partenaire a quitté.", to=partner)

    usernames.pop(sid, None)
    emotions.pop(sid, None)

    emit_counters()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
