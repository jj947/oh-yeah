from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

waiting = {
    "heureux": [],
    "triste": [],
    "enerve": [],
    "calme": [],
    "amour": []
}

pairs = {}
users = {}

global_count = 0


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("connect")
def on_connect():
    global global_count
    global_count += 1
    emit("global_count", global_count, broadcast=True)

@socketio.on("message")
def handle_message(data):
    sid = request.sid

    if sid in pairs:
        partner_sid = pairs[sid]

        emit("message", {
            "from": usernames[sid],
            "message": data["message"]
        }, to=partner_sid)

        # 👇 renvoi à soi-même (TRÈS IMPORTANT)
        emit("message", {
            "from": usernames[sid],
            "message": data["message"]
        }, to=sid)

@socketio.on("disconnect")
def on_disconnect():
    global global_count
    sid = request.sid

    global_count -= 1
    emit("global_count", global_count, broadcast=True)

    # Enlever de toutes les files d'attente
    for emotion in waiting:
        if sid in waiting[emotion]:
            waiting[emotion].remove(sid)

    # Si la personne était en discussion
    if sid in pairs:
        partner = pairs[sid]

        # Nettoyage des paires
        pairs.pop(sid, None)
        pairs.pop(partner, None)

        # Prévenir le partenaire
        emit("status", "⚠️ Votre partenaire a quitté. En attente d’un nouveau partenaire...", to=partner)

        # 🔥 REMETTRE le partenaire en attente
        partner_emotion = users[partner]["emotion"]
        waiting[partner_emotion].append(partner)

    # Nettoyage utilisateur
    users.pop(sid, None)


@socketio.on("join")
def on_join(data):
    sid = request.sid
    users[sid] = data

    emotion = data["emotion"]
    queue = waiting[emotion]

    if queue:
        partner = queue.pop(0)
        pairs[sid] = partner
        pairs[partner] = sid

        emit("status", "🎉 Partenaire trouvé !", to=sid)
        emit("status", "🎉 Partenaire trouvé !", to=partner)
    else:
        queue.append(sid)
        emit("status", "⏳ En attente d’un partenaire...", to=sid)


@socketio.on("send_message")
def on_message(data):
    sid = request.sid

    if sid not in pairs:
        return

    partner = pairs[sid]
    emit("receive_message", {
        "from": users[sid]["username"],
        "message": data["message"]
    }, to=partner)

    # afficher aussi côté envoyeur
    emit("receive_message", {
        "from": "Moi",
        "message": data["message"]
    }, to=sid)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)


