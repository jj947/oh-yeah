from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

waiting_users = {}    # emotion -> [sid, sid]
pairs = {}            # sid -> sid
usernames = {}        # sid -> pseudo
emotions = {}         # sid -> emotion

connected_users = 0


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("connect")
def handle_connect():
    global connected_users
    connected_users += 1
    emit("counter", connected_users, broadcast=True)


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
    if sid in pairs:
        partner = pairs[sid]
        emit("message", {
            "from": usernames[sid],
            "message": data["message"]
        }, to=partner)


@socketio.on("disconnect")
def handle_disconnect():
    global connected_users
    sid = request.sid
    connected_users -= 1
    emit("counter", connected_users, broadcast=True)

    # Retirer de l'attente
    for emotion in list(waiting_users):
        if sid in waiting_users[emotion]:
            waiting_users[emotion].remove(sid)

    # Gérer la déconnexion en discussion
    if sid in pairs:
        partner = pairs.pop(sid)
        pairs.pop(partner, None)

        emit(
            "status",
            "⚠️ Votre partenaire a quitté. En attente d’un nouveau partenaire...",
            to=partner
        )

        emo = emotions.get(partner)
        if emo:
            if emo not in waiting_users:
                waiting_users[emo] = []
            waiting_users[emo].append(partner)

    usernames.pop(sid, None)
    emotions.pop(sid, None)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
