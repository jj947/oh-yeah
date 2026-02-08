from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

MAX_PER_ROOM = 2

waiting_queue = []          # sockets en attente
rooms = {}                  # room_id -> [sid, sid]
user_room = {}              # sid -> room_id
user_pseudo = {}            # sid -> pseudo


@app.route("/")
def index():
    return render_template("index.html")


def try_create_room():
    """Crée un salon si possible"""
    if len(waiting_queue) >= 2:
        sid1 = waiting_queue.pop(0)
        sid2 = waiting_queue.pop(0)

        room_id = str(uuid.uuid4())[:8]
        rooms[room_id] = [sid1, sid2]

        user_room[sid1] = room_id
        user_room[sid2] = room_id

        join_room(room_id, sid=sid1)
        join_room(room_id, sid=sid2)

        socketio.emit("system", "Salon créé, vous êtes connectés 🎉", room=room_id)


@socketio.on("join")
def handle_join(data):
    pseudo = data.get("pseudo", "Anonyme")
    user_pseudo[request.sid] = pseudo

    waiting_queue.append(request.sid)
    emit("system", "En attente d’un autre utilisateur…")

    try_create_room()


@socketio.on("message")
def handle_message(data):
    room_id = user_room.get(request.sid)
    if not room_id:
        return

    emit(
        "message",
        {
            "pseudo": user_pseudo.get(request.sid, "???"),
            "text": data["text"]
        },
        room=room_id
    )


@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid

    # Retirer de la file d’attente
    if sid in waiting_queue:
        waiting_queue.remove(sid)

    # Si dans un salon
    room_id = user_room.get(sid)
    if room_id and room_id in rooms:
        rooms[room_id].remove(sid)

        emit("system", "L’autre utilisateur a quitté le salon ❌", room=room_id)

        # Si salon vide → supprimer
        if not rooms[room_id]:
            del rooms[room_id]
        else:
            # remettre le survivant en attente
            survivor = rooms[room_id][0]
            del rooms[room_id]
            del user_room[survivor]

            waiting_queue.append(survivor)
            emit("system", "Retour en attente d’un nouveau partenaire…", to=survivor)
            try_create_room()

    user_room.pop(sid, None)
    user_pseudo.pop(sid, None)


if __name__ == "__main__":
    socketio.run(app, debug=True)
