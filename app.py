from flask import Flask, render_template
from flask_socketio import SocketIO, join_room, leave_room, emit
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

# salons : { "triste": [room1, room2, ...] }
salons = {
    "triste": [],
    "heureux": [],
    "stressé": [],
    "en_colere": []
}

users = {}  # sid -> room

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("join")
def handle_join(data):
    emotion = data["emotion"]
    pseudo = data["pseudo"]

    # chercher une room avec moins de 2 personnes
    for room in salons[emotion]:
        if room["count"] < 2:
            room["count"] += 1
            join_room(room["name"])
            users[data["sid"]] = room["name"]
            emit("status", f"{pseudo} a rejoint le chat", room=room["name"])
            return

    # sinon créer une nouvelle room
    room_name = f"{emotion}_{len(salons[emotion])}"
    salons[emotion].append({"name": room_name, "count": 1})
    join_room(room_name)
    users[data["sid"]] = room_name
    emit("status", f"{pseudo} a rejoint le chat", room=room_name)

@socketio.on("message")
def handle_message(data):
    room = users.get(data["sid"])
    emit("message", data["message"], room=room)

@socketio.on("disconnect")
def handle_disconnect():
    room = users.get(request.sid)
    leave_room(room)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)