from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import uuid

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

waiting_user = None
rooms = {}

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("join")
def join(data):
    global waiting_user

    sid = data["sid"]
    pseudo = data["pseudo"]
    emotion = data["emotion"]

    if waiting_user is None:
        waiting_user = {
            "sid": sid,
            "pseudo": pseudo,
            "emotion": emotion
        }
        emit("waiting")
    else:
        room_id = str(uuid.uuid4())

        rooms[room_id] = {
            "users": [waiting_user["sid"], sid],
            "emotion": waiting_user["emotion"]
        }

        emit("joined", {
            "room": room_id,
            "emotion": rooms[room_id]["emotion"]
        }, to=waiting_user["sid"])

        emit("joined", {
            "room": room_id,
            "emotion": rooms[room_id]["emotion"]
        }, to=sid)

        waiting_user = None

@socketio.on("message")
def message(data):
    room = data["room"]
    emit("message", data, to=rooms[room]["users"])

@socketio.on("disconnect")
def disconnect():
    global waiting_user

    sid = None
    for room_id, room in list(rooms.items()):
        if request.sid in room["users"]:
            room["users"].remove(request.sid)
            del rooms[room_id]
            break

    if waiting_user and waiting_user["sid"] == request.sid:
        waiting_user = None

if __name__ == "__main__":
    socketio.run(app)
