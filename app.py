from flask import Flask, request
from flask_socketio import SocketIO
from collections import defaultdict

app = Flask(__name__)
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet"
)

# emotion -> liste de socket ids (max 2)
rooms = defaultdict(list)
# socket id -> emotion
client_emotion = {}


@app.route("/")
def home():
    return "Serveur en ligne"


@socketio.on("join")
def handle_join(data):
    emotion = data["emotion"]
    sid = request.sid

    rooms[emotion].append(sid)
    client_emotion[sid] = emotion

    join_room(emotion)

    if len(rooms[emotion]) == 1:
        emit("status", "🕒 En attente d’une personne avec la même émotion...")
    elif len(rooms[emotion]) == 2:
        emit("status", "💬 Match trouvé !", room=emotion)
    else:
        emit("status", "❌ Salon plein")
        leave_room(emotion)


@socketio.on("message")
def handle_message(msg):
    sid = request.sid
    emotion = client_emotion.get(sid)

    if not emotion or len(rooms[emotion]) < 2:
        return

    emit("message", msg, room=emotion, include_self=False)


@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    emotion = client_emotion.get(sid)

    if emotion and sid in rooms[emotion]:
        rooms[emotion].remove(sid)
        if not rooms[emotion]:
            del rooms[emotion]

    client_emotion.pop(sid, None)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)


