from flask import Flask, render_template
from flask_socketio import SocketIO, join_room, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("join")
def on_join(data):
    emotion = data["emotion"]
    join_room(emotion)
    emit("message", {"message": f"Quelqu’un a rejoint : {emotion}"}, room=emotion)

@socketio.on("message")
def handle_message(data):
    emit("message", data, broadcast=True)

if __name__ == "__main__":
    socketio.run(app)
