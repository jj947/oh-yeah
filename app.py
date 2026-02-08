from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# { emotion: [sid1, sid2, sid3...] }
waiting = {}

# { sid: room }
user_room = {}

# { room: [sid1, sid2] }
rooms = {}


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("join")
def join(data):
    emotion = data["emotion"]
    pseudo = data["pseudo"]
    sid = request.sid

    if emotion not in waiting:
        waiting[emotion] = []

    waiting[emotion].append(sid)

    emit("status", "En attente d’un partenaire...", to=sid)

    try_match(emotion)


def try_match(emotion):
    while len(waiting[emotion]) >= 2:
        sid1 = waiting[emotion].pop(0)
        sid2 = waiting[emotion].pop(0)

        room = f"{emotion}_{uuid.uuid4().hex[:6]}"
        rooms[room] = [sid1, sid2]

        user_room[sid1] = room
        user_room[sid2] = room

        join_room(room, sid=sid1)
        join_room(room, sid=sid2)

        emit("connected", to=room)
        emit("status", "🎉 Partenaire trouvé ! Vous pouvez discuter.", to=room)


@socketio.on("message")
def message(msg):
    sid = request.sid
    room = user_room.get(sid)
    if not room:
        return

    emit("message", {
        "pseudo": "Partenaire",
        "message": msg
    }, to=room, include_self=False)


@socketio.on("typing")
def typing(status):
    room = user_room.get(request.sid)
    if room:
        emit("typing", status, to=room, include_self=False)


@socketio.on("disconnect")
def handle_disconnect():
    global waiting_user

    if waiting_user == request.sid:
        waiting_user = None
        return

    for sid, partner in list(pairs.items()):
        if partner == request.sid:
            del pairs[sid]

            socketio.emit(
                "status",
                "⚠️ Votre partenaire a quitté la discussion. Recherche d’un nouveau partenaire...",
                room=sid
            )

            waiting_user = sid
            break

        del rooms[room]


