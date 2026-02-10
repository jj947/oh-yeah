from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

# ------------------ ÉTAT GLOBAL ------------------

EMOTIONS = ["heureux", "triste", "enerve", "calme", "amour"]

waiting = {e: [] for e in EMOTIONS}   # emotion -> [sid, sid, ...]
pairs = {}                            # sid -> sid
usernames = {}                        # sid -> pseudo
emotions = {}                         # sid -> emotion


# ------------------ ROUTE ------------------

@app.route("/")
def index():
    return render_template("index.html")


# ------------------ OUTILS ------------------

def send_counters():
    emotion_counts = {}
    total = 0

    for emo in EMOTIONS:
        emotion_counts[emo] = len(waiting[emo])
        total += len(waiting[emo])

    socketio.emit("emotion_counts", emotion_counts)
    socketio.emit("global_count", total)


def leave_current_room(sid):
    # Retirer de l'attente
    for emo in EMOTIONS:
        if sid in waiting[emo]:
            waiting[emo].remove(sid)

    # Si en discussion
    if sid in pairs:
        partner = pairs.pop(sid)
        pairs.pop(partner, None)

        emit("status", "⚠️ Votre partenaire a quitté.", to=partner)

        emo = emotions.get(partner)
        if emo:
            waiting[emo].append(partner)
            emit("status", "⏳ En attente d’un partenaire...", to=partner)


# ------------------ SOCKETS ------------------

@socketio.on("connect")
def on_connect():
    send_counters()


@socketio.on("join")
def on_join(data):
    sid = request.sid
    username = data.get("username")
    emotion = data.get("emotion")

    usernames[sid] = username
    emotions[sid] = emotion

    # Si quelqu'un attend déjà
    if waiting[emotion]:
        partner = waiting[emotion].pop(0)

        pairs[sid] = partner
        pairs[partner] = sid

        emit("status", "🎉 Partenaire trouvé !", to=sid)
        emit("status", "🎉 Partenaire trouvé !", to=partner)
    else:
        waiting[emotion].append(sid)
        emit("status", "⏳ En attente d’un partenaire...", to=sid)

    send_counters()


@socketio.on("send_message")
def on_message(data):
    sid = request.sid
    msg = data.get("message", "").strip()

    if not msg:
        return

    # afficher chez soi
    emit("message", {
        "from": "Moi",
        "message": msg
    }, to=sid)

    # envoyer au partenaire
    if sid in pairs:
        partner = pairs[sid]
        emit("message", {
            "from": usernames.get(sid, "Inconnu"),
            "message": msg
        }, to=partner)


@socketio.on("leave")
def on_leave():
    sid = request.sid
    leave_current_room(sid)
    send_counters()


@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    leave_current_room(sid)

    usernames.pop(sid, None)
    emotions.pop(sid, None)

    send_counters()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
