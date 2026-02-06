import socketio

sio = socketio.Client(transports=["websocket"])

@sio.event
def connect():
    print("✅ Connecté au serveur")

@sio.on("status")
def status(msg):
    print(msg)

@sio.on("message")
def message(msg):
    print("💬", msg)

emotion = input("Emotion : ")

sio.connect(
    "https://oh-yeah-1.onrender.com",
    socketio_path="socket.io"
)

sio.emit("join", {"emotion": emotion})

while True:
    msg = input()
    sio.send(msg)
