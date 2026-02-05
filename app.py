import socket
import threading
from collections import defaultdict

HOST = "0.0.0.0"
PORT = 5000

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

print("Serveur lancé...")

# emotion -> liste de sockets (max 2)
rooms = defaultdict(list)

# socket -> emotion
client_emotion = {}


def handle_client(client_socket):
    try:
        # 1) recevoir l'émotion
        emotion = client_socket.recv(1024).decode().strip()
        client_emotion[client_socket] = emotion

        # 2) rejoindre ou créer un salon
        rooms[emotion].append(client_socket)

        if len(rooms[emotion]) == 1:
            client_socket.send(
                "🕒 En attente d’une personne avec la même émotion...\n".encode()
            )
        elif len(rooms[emotion]) == 2:
            for c in rooms[emotion]:
                c.send("💬 Match trouvé ! Vous pouvez discuter.\n".encode())
        else:
            client_socket.send("❌ Salon plein.\n".encode())
            client_socket.close()
            return

        # 3) chat
        while True:
            message = client_socket.recv(1024).decode()
            if not message:
                break

            # envoyer uniquement à l'autre personne
            for c in rooms[emotion]:
                if c != client_socket:
                    c.send(message.encode())

    except:
        pass
    finally:
        # 4) nettoyage
        emotion = client_emotion.get(client_socket)
        if emotion and client_socket in rooms[emotion]:
            rooms[emotion].remove(client_socket)
            if len(rooms[emotion]) == 0:
                del rooms[emotion]

        client_emotion.pop(client_socket, None)
        client_socket.close()
        print("Client déconnecté")


while True:
    client_socket, addr = server.accept()
    print(f"Connexion de {addr}")
    threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()
