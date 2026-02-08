from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

waiting_users = {}   # emotion -> sid
pairs = {}           # sid -> sid
usernames = {}       # sid -> pseudo
emotions = {}        # sid -> emotion


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("join")
def handle_join(data):
    sid = request.sid
    username = data["username"]
    emotion = data["emotion"]

    usernames[sid] = username
    emotions[sid] = emotion

    # Si quelqu’un attend déjà avec la même émotion
    if emotion in waiting_users:
        partner_sid = waiting_users.pop(emotion)

        pairs[sid] = partner_sid
        pairs[partner_sid] = sid

        emit("status", "🎉 Partenaire trouvé !", to=sid)
        emit("status", "🎉 Partenaire trouvé !", to=partner_sid)

    else:
        waiting_users[emotion] = sid
        emit("status", "⏳ En attente d’un partenaire...", to=sid)


@socketio.on("message")
def handle_message(data):
    sid = request.sid
    msg = data["message"]

    if sid in pairs:
        partner_sid = pairs[sid]
        emit("message", {
            "from": usernames[sid],
            "message": msg
        }, to=partner_sid)


@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid

    # S'il attendait
    for emotion, waiting_sid in list(waiting_users.items()):
        if waiting_sid == sid:
            waiting_users.pop(emotion, None)
            return

    # S'il était en discussion
    if sid in pairs:
        partner_sid = pairs.get(sid)

        pairs.pop(sid, None)
        if partner_sid:
            pairs.pop(partner_sid, None)

        try:
            emit(
                "status",
                "⚠️ Votre partenaire a quitté. En attente d’un nouveau partenaire...",
                to=partner_sid
            )
            waiting_users[emotions[partner_sid]] = partner_sid
        except:
            pass


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
