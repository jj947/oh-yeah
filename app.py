import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")
users = {}
rooms = {
    "triste": [],
    "content": [],
    "colere": [],
    "stresse": []
}


@socketio.on("join")
def handle_join(data):
    pseudo = data["pseudo"]
    emotion = data["emotion"]
    sid = request.sid

    # Cherche un salon dispo (moins de 2 personnes)
    for salon in rooms[emotion]:
        if len(salon) < 2:
            salon.append(sid)
            users[sid] = {
                "pseudo": pseudo,
                "emotion": emotion,
                "salon": salon
            }
            emit("message", f"🟢 {pseudo} a rejoint la discussion", room=sid)
            return

    # Aucun salon dispo → en créer un nouveau
    new_salon = [sid]
    rooms[emotion].append(new_salon)

    users[sid] = {
        "pseudo": pseudo,
        "emotion": emotion,
        "salon": new_salon
    }

    emit("message", f"⏳ En attente d’un partenaire...", room=sid)


@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("message")
def handle_message(data):
    user = users.get(request.sid)
    if not user:
        return

    pseudo = user["pseudo"]
    emotion = user["emotion"]
    salon = user["salon"]
    text = data["text"]

    for sid in salon:
        emit(
            "message",
            f"[{pseudo} | {emotion}] {text}",
            room=sid
        )

@socketio.on("disconnect")
def handle_disconnect():
    user = users.get(request.sid)
    if not user:
        return

    pseudo = user["pseudo"]
    emotion = user["emotion"]
    salon = user["salon"]

    if request.sid in salon:
        salon.remove(request.sid)

    for sid in salon:
        emit("message", f"🔴 {pseudo} a quitté la discussion", room=sid)

    # Supprimer salon vide
    if len(salon) == 0:
        rooms[emotion].remove(salon)

    del users[request.sid]

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)



