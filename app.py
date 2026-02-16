from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

# --- états ---
waiting_users = {}     # emotion -> sid
pairs = {}             # sid -> sid
usernames = {}         # sid -> username
emotions = {}          # sid -> emotion
connected_users = 0


@app.route("/chat")
def chat():
    return render_template("chat.html")


@socketio.on("connect")
def handle_connect():
    global connected_users
    connected_users += 1
    socketio.emit("global_count", connected_users)


@socketio.on("join")
def on_join(data):
    sid = request.sid
    username = data["username"]
    emotion = data["emotion"]

    usernames[sid] = username
    emotions[sid] = emotion

    # quelqu’un attend déjà ?
    if emotion in waiting_users:
        partner_sid = waiting_users.pop(emotion)

        pairs[sid] = partner_sid
        pairs[partner_sid] = sid

        emit("status", "🎉 Partenaire trouvé !", to=sid)
        emit("status", "🎉 Partenaire trouvé !", to=partner_sid)
    else:
        waiting_users[emotion] = sid
        emit("status", "⏳ En attente d’un partenaire...", to=sid)


@socketio.on("send_message")
def on_message(data):
    sid = request.sid
    msg = data["message"]

    # envoyer à l’autre
    if sid in pairs:
        partner_sid = pairs[sid]
        emit("message", {
            "from": usernames[sid],
            "message": msg
        }, to=partner_sid)

        # renvoyer à soi-même pour affichage
        emit("message", {
            "from": "me",
            "message": msg
        }, to=sid)


@socketio.on("disconnect")
def handle_disconnect():
    global connected_users
    connected_users -= 1
    socketio.emit("global_count", connected_users)

    # s’il attendait
    for emo, wsid in list(waiting_users.items()):
        if wsid == sid:
            waiting_users.pop(emo)
            break

    # s’il discutait
    partner_sid = pairs.pop(sid, None)
    if partner_sid:
        pairs.pop(partner_sid, None)

        if partner_sid in usernames:
            emit(
                "status",
                "⚠️ Votre partenaire a quitté. En attente d’un nouveau partenaire...",
                to=partner_sid
            )
            emo = emotions.get(partner_sid)
            if emo:
                waiting_users[emo] = partner_sid

    usernames.pop(sid, None)
    emotions.pop(sid, None)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)


