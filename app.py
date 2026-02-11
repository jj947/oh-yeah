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
def handle_disconnect():
    sid = request.sid

    # --- 1. Retirer du compteur global (si tu l’as) ---
    connected_users.discard(sid)
    socketio.emit("global_count", len(connected_users))

    # --- 2. S’il était en attente ---
    for emotion, waiting_sid in list(waiting_users.items()):
        if waiting_sid == sid:
            waiting_users.pop(emotion, None)
            return  # rien d’autre à faire

    # --- 3. S’il était en discussion ---
    partner_sid = pairs.pop(sid, None)

    if partner_sid:
        pairs.pop(partner_sid, None)

        # prévenir le partenaire SEULEMENT s’il est encore connecté
        if partner_sid in usernames:
            emit(
                "status",
                "⚠️ Votre partenaire a quitté. En attente d’un nouveau partenaire...",
                to=partner_sid
            )

            # le remettre en attente
            emotion = emotions.get(partner_sid)
            if emotion:
                waiting_users[emotion] = partner_sid

    # --- 4. Nettoyage ---
    usernames.pop(sid, None)
    emotions.pop(sid, None)



if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)



