from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

waiting_users = {}   # emotion -> sid
pairs = {}           # sid -> sid
usernames = {}       # sid -> pseudo
emotions = {}        # sid -> emotion
connected_users = 0

@socketio.on("connect")
def handle_connect():
    global connected_users
    connected_users += 1
    emit("counter", connected_users, broadcast=True)

@app.route("/")
def index():
    return render_template("index.html")


def connected_count():
    return len(usernames)


def count_waiting():
    counts = {}
    for sid, emotion in emotions.items():
        counts.setdefault(emotion, 0)
    for emotion in waiting_users:
        counts[emotion] += 1
    return counts

@socketio.on("join")
def handle_join(data):
    sid = request.sid
    username = data["username"]
    emotion = data["emotion"]

    usernames[sid] = username
    emotions[sid] = emotion

    if emotion not in waiting_users:
        waiting_users[emotion] = []

    waiting_users[emotion].append(sid)

    # s'il y a au moins 2 personnes, on crée un salon
    if len(waiting_users[emotion]) >= 2:
        sid1 = waiting_users[emotion].pop(0)
        sid2 = waiting_users[emotion].pop(0)

        pairs[sid1] = sid2
        pairs[sid2] = sid1

        emit("status", "🎉 Partenaire trouvé !", to=sid1)
        emit("status", "🎉 Partenaire trouvé !", to=sid2)
    else:
        emit("status", "⏳ En attente d’un partenaire...", to=sid)


@socketio.on("message")
def handle_message(data):
    sid = request.sid
    msg = data.get("message")

    if not msg or sid not in pairs:
        return

    partner_sid = pairs[sid]
    emit("message", {
        "from": usernames[sid],
        "message": msg
    }, to=partner_sid)

@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid

    # retirer de l'attente
    for emotion, waiting_sid in list(waiting_users.items()):
        if waiting_sid == sid:
            waiting_users.pop(emotion, None)

    # gérer une discussion en cours
    if sid in pairs:
        partner_sid = pairs.pop(sid)
        pairs.pop(partner_sid, None)

        emit(
            "status",
            "⚠️ Votre partenaire a quitté. En attente d’un nouveau partenaire...",
            to=partner_sid
        )

        waiting_users[emotions[partner_sid]] = partner_sid

    usernames.pop(sid, None)
    emotions.pop(sid, None)

    emit("waiting_update", count_waiting(), broadcast=True)
    emit("connected_update", connected_count(), broadcast=True)
    global connected_users
    connected_users -= 1
    emit("counter", connected_users, broadcast=True)
    ...

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)

