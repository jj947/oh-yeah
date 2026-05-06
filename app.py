from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import os
import eventlet
eventlet.monkey_patch()
app = Flask(__name__)
app.config["SECRET_KEY"] = "secret-key"

socketio = SocketIO(app, cors_allowed_origins="*")

# ===== DONNÉES =====
waiting = {}          # emotion -> [sid, sid, ...]
pairs = {}            # sid -> partner_sid
usernames = {}        # sid -> pseudo
emotions = {}         # sid -> emotion
connected_users = set()


# ===== ROUTE WEB =====
@app.route("/")
def index():
    return render_template("index.html")


# ===== SOCKET EVENTS =====
@socketio.on("connect")
def handle_connect():
    connected_users.add(request.sid)
    emit("count", len(connected_users), broadcast=True)


@socketio.on("join")
def handle_join(data):
    sid = request.sid
    username = data.get("username")
    emotion = data.get("emotion")

    usernames[sid] = username
    emotions[sid] = emotion

    # créer la file d’attente si absente
    if emotion not in waiting:
        waiting[emotion] = []

    # s'il y a déjà quelqu’un qui attend
    if len(waiting[emotion]) > 0:
        partner_sid = waiting[emotion].pop(0)

        pairs[sid] = partner_sid
        pairs[partner_sid] = sid

        emit("status", "🎉 Partenaire trouvé !", to=sid)
        emit("status", "🎉 Partenaire trouvé !", to=partner_sid)
    else:
        waiting[emotion].append(sid)
        emit("status", "⏳ En attente d’un partenaire...", to=sid)


@socketio.on("message")
def handle_message(data):
    sid = request.sid
    msg = data.get("message")

    if sid in pairs:
        partner_sid = pairs[sid]
        emit(
            "message",
            {
                "from": usernames.get(sid, "Anonyme"),
                "message": msg
            },
            to=partner_sid
        )


@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid

    connected_users.discard(sid)
    emit("count", len(connected_users), broadcast=True)

    # enlever des listes d’attente
    for emotion in waiting:
        if sid in waiting[emotion]:
            waiting[emotion].remove(sid)

    # gérer la déconnexion en discussion
    if sid in pairs:
        partner_sid = pairs.pop(sid)

        if partner_sid in pairs:
            pairs.pop(partner_sid)

            emit(
                "status",
                "⚠️ Votre partenaire a quitté. En attente d’un nouveau partenaire...",
                to=partner_sid
            )

            # remettre le partenaire en attente
            emotion = emotions.get(partner_sid)
            if emotion:
                if emotion not in waiting:
                    waiting[emotion] = []
                waiting[emotion].append(partner_sid)

    usernames.pop(sid, None)
    emotions.pop(sid, None)


# ===== LANCEMENT =====


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
