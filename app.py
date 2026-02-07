import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")
users = {}

@socketio.on("join")
def handle_join(data):
    pseudo = data["pseudo"]
    emotion = data["emotion"]

    users[request.sid] = {
        "pseudo": pseudo,
        "emotion": emotion
    }

    emit("message", f"🟢 {pseudo} a rejoint ({emotion})", broadcast=True)

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
    text = data["text"]

    emit(
        "message",
        f"[{pseudo} | {emotion}] {text}",
        broadcast=True
    )

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)

