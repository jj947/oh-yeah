import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")
users = {}
waiting = {
    "triste": None,
    "content": None,
    "colere": None,
    "stresse": None
}


@socketio.on("join")
def handle_join(data):
    pseudo = data["pseudo"]
    emotion = data["emotion"]
    sid = request.sid

    # Personne n’attend → il attend
    if waiting[emotion] is None:
        waiting[emotion] = sid
        users[sid] = {
            "pseudo": pseudo,
            "emotion": emotion,
            "partner": None
        }
        emit("message", "⏳ En attente d’un partenaire...", room=sid)
        return

    # Quelqu’un attend → on les connecte
    partner_sid = waiting[emotion]
    waiting[emotion] = None

    users[sid] = {
        "pseudo": pseudo,
        "emotion": emotion,
        "partner": partner_sid
    }

    users[partner_sid]["partner"] = sid

    emit("message", "🟢 Partenaire trouvé !", room=sid)
    emit("message", "🟢 Partenaire trouvé !", room=partner_sid)


@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("message")
def handle_message(data):
    user = users.get(request.sid)
    if not user:
        return

    partner = user["partner"]
    if not partner:
        emit("message", "⏳ Toujours en attente d’un partenaire...", room=request.sid)
        return

    pseudo = user["pseudo"]
    emotion = user["emotion"]
    text = data["text"]

    emit(
        "message",
        f"[{pseudo} | {emotion}] {text}",
        room=partner
    )

@socketio.on("disconnect")
def handle_disconnect():
    user = users.get(request.sid)
    if not user:
        return

    emotion = user["emotion"]
    partner = user["partner"]
    pseudo = user["pseudo"]

    # Si la personne attendait
    if waiting[emotion] == request.sid:
        waiting[emotion] = None

    # Si elle avait un partenaire
    if partner and partner in users:
        users[partner]["partner"] = None
        emit("message", "🔴 Ton partenaire a quitté. En attente d’un nouveau...", room=partner)
        waiting[emotion] = partner

    del users[request.sid]

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)




