import socket
import threading

# Structure des salons : { "triste": [[client1, client2], [client3, client4]], ... }
salons = {"triste": [], "en_colere": [], "stressé": [], "heureux": []}

client_info = {}  # map client -> salon attribué

def gerer_client(client_socket):
    try:
        # Recevoir l'émotion choisie au début
        emotion = client_socket.recv(1024).decode()
        
        # Chercher un salon avec moins de 2 personnes
        placed = False
        for salon in salons[emotion]:
            if len(salon) < 2:
                salon.append(client_socket)
                client_info[client_socket] = salon
                placed = True
                break
        if not placed:
            # Crée un nouveau salon pour cette émotion
            new_salon = [client_socket]
            salons[emotion].append(new_salon)
            client_info[client_socket] = new_salon

        while True:
            message = client_socket.recv(1024)
            if not message:
                break
            # Envoyer le message aux autres membres du salon
            salon = client_info[client_socket]
            for c in salon:
                if c != client_socket:
                    c.send(message)
    except:
        pass
    finally:
        # Supprimer le client du salon
        if client_socket in client_info:
            salon = client_info[client_socket]
            if client_socket in salon:
                salon.remove(client_socket)
        client_socket.close()

serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serveur.bind(("0.0.0.0", 12345))
serveur.listen()
print("Serveur démarré sur 0.0.0.0:12345")

while True:
    client_socket, addr = serveur.accept()
    threading.Thread(target=gerer_client, args=(client_socket,), daemon=True).start()