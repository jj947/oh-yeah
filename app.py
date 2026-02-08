from flask import Flask, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

# -------------------------
# ÉTAT GLOBAL
# -------------------------

users = {}  # sid -> {pseudo, emotion, partner}

waiting = {
    "triste": [],
    "content": [],
    "colere": [],
    "stresse": []
}

# -------------------------
# MATCHING
# -------------------------

def try_match(emotion):
    while len(waiting[emotion]) >= 2:
        a = waiting[emotion].pop(0)
        b = waiting[emotion].pop(0)

        users[a]["partner"] = b
        users[b]["partner"] = a

        emit("message", "🟢 Partenaire trouvé !", room=a)
        emit("message", "🟢 Partenaire trouvé !", room=b)

# -------------------------
# CONNEXION
# -------------------------

@socketio.on("join")
def join(data):
    sid = request.sid
    pseudo = data["pseudo"]
    emotion = data["emotion"]

    users[sid] = {
        "pseudo": pseudo,
        "emotion": emotion,
        "partner": None
    }

    waiting[emotion].append(sid)
    emit("message", "⏳ En attente d’un partenaire...", room=sid)

    try_match(emotion)

# -------------------------
# MESSAGE
# -------------------------

@socketio.on("message")
def handle_message(data):
    sid = request.sid
    user = users.get(sid)

    if not user:
        return

    text = data["text"]
    pseudo = user["pseudo"]
    emotion = user["emotion"]
    partner = user["partner"]

    msg = f"[{pseudo} | {emotion}] {text}"

    # afficher chez soi
    emit("message", msg, room=sid)

    # envoyer au partenaire
    if partner:
        emit("message", msg, room=partner)

# -------------------------
# DÉCONNEXION
# -------------------------

@socketio.on("disconnect")
def disconnect():
    sid = request.sid
    user = users.get(sid)

    if not user:
        return

    emotion = user["emotion"]
    partner = user["partner"]

    # retirer de la file d'attente si besoin
    if sid in waiting[emotion]:
        waiting[emotion].remove(sid)

    # gérer le partenaire
    if partner and partner in users:
        users[partner]["partner"] = None
        waiting[emotion].append(partner)

        emit(
            "message",
            "🔴 Ton partenaire a quitté. En attente d’un nouveau...",
            room=partner
        )

        try_match(emotion)

    del users[sid]

# -------------------------
# LANCEMENT
# -------------------------

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10000)
