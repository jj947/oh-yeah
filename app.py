from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet"
)

# --- états ---
waiting_users = {
    "heureux": [],
    "triste": [],
    "enerve": [],
    "calme": [],
    "amour": []
}
pairs = {}             # sid -> sid
usernames = {}         # sid -> username
emotions = {}          # sid -> emotion
connected_users = 0

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat")
def chat():
    return render_template("chat.html")


@socketio.on("connect")
def handle_connect():
    global connected_users
    connected_users += 1
    socketio.emit("global_count", connected_users)


@socketio.on("join")
def handle_join(data):
    sid = request.sid
    username = data["username"]
    emotion = data["emotion"]

    usernames[sid] = username
    emotions[sid] = emotion

    # ✅ créer la file si elle n'existe pas
    if emotion not in waiting_users:
        waiting_users[emotion] = []

    queue = waiting_users[emotion]

    # ✅ retirer les SID morts éventuels
    queue[:] = [s for s in queue if s != sid]

    if len(queue) > 0:
        partner_sid = queue.pop(0)

        pairs[sid] = partner_sid
        pairs[partner_sid] = sid

        emit("status", "🎉 Partenaire trouvé !", to=sid)
        emit("status", "🎉 Partenaire trouvé !", to=partner_sid)

        print(f"MATCH: {sid} <-> {partner_sid} ({emotion})")

    else:
        queue.append(sid)
        emit("status", "⏳ En attente d’un partenaire...", to=sid)

        print(f"WAIT: {sid} ({emotion})")


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

@socketio.on("message")
def handle_message(data):
    sid = request.sid
    msg = data["message"]

    if sid in pairs:
        partner_sid = pairs[sid]

        payload = {
            "from": usernames[sid],
            "message": msg
        }

        # pour l'autre
        emit("message", payload, to=partner_sid)
        # pour soi
        emit("message", payload, to=sid)


@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    print("DISCONNECT:", sid)

    # enlever des files d'attente
    for emotion, queue in waiting_users.items():
        if sid in queue:
            queue.remove(sid)

    # si en discussion
    if sid in pairs:
        partner = pairs.pop(sid)
        pairs.pop(partner, None)

        emit(
            "status",
            "⚠️ Votre partenaire a quitté. En attente d’un nouveau partenaire...",
            to=partner
        )

        # remettre le partenaire en attente
        waiting_users[emotions[partner]].append(partner)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)







