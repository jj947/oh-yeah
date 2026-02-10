from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

waiting = {}        # emotion -> sid
pairs = {}          # sid -> sid
connected = set()   # sids connectés


@app.route("/")
def index():
    return render_template("index.html")


def update_global_counter():
    socketio.emit("global_count", len(connected))


@socketio.on("connect")
def on_connect():
    connected.add(request.sid)
    update_global_counter()


@socketio.on("join")
def on_join(data):
    sid = request.sid
    emotion = data["emotion"]

    emit("enter_chat", to=sid)

    if emotion in waiting:
        partner = waiting.pop(emotion)

        pairs[sid] = partner
        pairs[partner] = sid

        emit("status", "🎉 Partenaire trouvé !", to=sid)
        emit("status", "🎉 Partenaire trouvé !", to=partner)
    else:
        waiting[emotion] = sid
        emit("status", "⏳ En attente d’un partenaire...", to=sid)


@socketio.on("send_message")
def on_message(data):
    sid = request.sid
    msg = data["message"]

    if sid not in pairs:
        return

    partner = pairs[sid]

    emit("message", {"text": msg, "self": True}, to=sid)
    emit("message", {"text": msg, "self": False}, to=partner)


@socketio.on("leave")
def on_leave():
    sid = request.sid

    # Était en attente
    for emo in list(waiting):
        if waiting[emo] == sid:
            waiting.pop(emo)
            break

    # Était en chat
    if sid in pairs:
        partner = pairs.pop(sid)
        pairs.pop(partner, None)

        emit("status", "⚠️ Votre partenaire a quitté.", to=partner)

    emit("return_menu", to=sid)


@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    connected.discard(sid)

    for emo in list(waiting):
        if waiting[emo] == sid:
            waiting.pop(emo)

    if sid in pairs:
        partner = pairs.pop(sid)
        pairs.pop(partner, None)
        emit("status", "⚠️ Votre partenaire a quitté.", to=partner)

    update_global_counter()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
