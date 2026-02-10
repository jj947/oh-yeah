from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

# --------------------
# STOCKAGE GLOBAL
# --------------------
waiting_users = {}        # emotion -> [sid, sid, ...]
pairs = {}                # sid -> sid
usernames = {}            # sid -> pseudo
emotions = {}             # sid -> emotion
connected_users = set()   # tous les sid connectés


# --------------------
# ROUTE
# --------------------
@app.route("/")
def index():
    return render_template("index.html")


# --------------------
# UTILS
# --------------------
def emit_counters():
    emotion_counts = {}
    for emo, users in waiting_users.items():
        emotion_counts[emo] = len(users)

    emit("update_counters", {
        "global": len(connected_users),
        "emotions": emotion_counts
    }, broadcast=True)


# --------------------
# SOCKET EVENTS
# --------------------
@socketio.on("connect")
def handle_connect():
    connected_users.add(request.sid)
    emit_counters()


@socketio.on("join")
def handle_join(data):
    sid = request.sid
    username = data["username"]
    emotion = data["emotion"]

    usernames[sid] = username
    emotions[sid] = emotion

    if emotion not in waiting_users:
        waiting_users[emotion] = []

    # Si quelqu’un attend déjà
    if waiting_users[emotion]:
        partner_sid = waiting_users[emotion].pop(0)

        pairs[sid] = partner_sid
        pairs[partner_sid] = sid

        emit("status", "🎉 Partenaire trouvé !", to=sid)
        emit("status", "🎉 Partenaire trouvé !", to=partner_sid)
    else:
        waiting_users[emotion].append(sid)
        emit("status", "⏳ En attente d’un partenaire...", to=sid)

    emit_counters()


@socketio.on("message")
def handle_message(data):
    sid = request.sid
    msg = data["message"]

    if sid in pairs:
        partner_sid = pairs[sid]
        emit("message", {
            "from": usernames[sid],
            "message": msg
        }, to=partner_sid)


@socketio.on("leave_chat")
def handle_leave_chat():
    sid = request.sid

    if sid in pairs:
        partner_sid = pairs.pop(sid)
        pairs.pop(partner_sid, None)

        emit("status", "⚠️ Votre partenaire a quitté.", to=partner_sid)

        emo = emotions.get(partner_sid)
        if emo:
            waiting_users.setdefault(emo, []).append(partner_sid)

    emit_counters()


@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    connected_users.discard(sid)

    # Retirer de l’attente
    for emo in list(waiting_users.keys()):
        if sid in waiting_users[emo]:
            waiting_users[emo].remove(sid)

    # Gérer les paires
    if sid in pairs:
        partner_sid = pairs.pop(sid)
        pairs.pop(partner_sid, None)

        emit("status", "⚠️ Votre partenaire a quitté.", to=partner_sid)

        emo = emotions.get(partner_sid)
        if emo:
            waiting_users.setdefault(emo, []).append(partner_sid)

    usernames.pop(sid, None)
    emotions.pop(sid, None)

    emit_counters()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
