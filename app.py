import socket
import threading
import tkinter as tk

# --- Connexion au serveur ---
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(("mon-serveur.onrender.com", 12345))  # même IP et port que le serveur

# Fonction pour recevoir les messages
def recevoir_messages():
    while True:
        try:
            message = client_socket.recv(1024).decode()
            if message:
                chat_text.config(state="normal")
                chat_text.insert(tk.END, message + "\n")
                chat_text.see(tk.END)
                chat_text.config(state="disabled")
        except:
            break

threading.Thread(target=recevoir_messages, daemon=True).start()

# Fenêtre principale
fenetre = tk.Tk()
fenetre.title("Connexion émotionnelle")
fenetre.geometry("500x500")

# Salle des émotions
salles = {"triste": [], "en_colere": [], "stressé": [], "heureux": []}

# Variables globales
chat_text = None
entry_message = None

# Fonction pour envoyer un message
def envoyer_message():
    msg = entry_message.get().strip()
    if msg == "":
        return
    message = f"{entry.get()} : {msg}"
    client_socket.send(message.encode())
    entry_message.delete(0, tk.END)
    chat_text.config(state="normal")
    chat_text.insert(tk.END, f"{entry.get()} : {msg}\n", "right")
    chat_text.see(tk.END)
    chat_text.config(state="disabled")
    entry_message.delete(0, tk.END)

# Démarrer le chat
def start_chat(pseudo):
    global chat_text, entry_message

    # Désactiver boutons et pseudo
    for btn in buttons:
        btn.config(state="disabled")
    entry.config(state="disabled")
    label_resultat.config(text="Chat commencé ! Tape ton message ci-dessous.")

    # Zone chat
    chat_text = tk.Text(fenetre, height=20, width=60)
    chat_text.pack(pady=10)
    chat_text.tag_configure("right", justify="right", background="#add8e6")
    chat_text.tag_configure("left", justify="left", background="#d3d3d3")
    chat_text.config(state="disabled")

    # Champ pour écrire + bouton
    frame_input = tk.Frame(fenetre)
    frame_input.pack()
    entry_message = tk.Entry(frame_input, width=40)
    entry_message.pack(side="left", padx=5)
    tk.Button(frame_input, text="Envoyer", command=envoyer_message).pack(side="left")

# Choisir émotion
def choisir_emotion(emotion):
    pseudo = entry.get().strip()
    if pseudo == "":
        label_resultat.config(text="⚠️ Mets un pseudo d'abord !")
        return

    # ENVOYER l'émotion au serveur
    client_socket.send(emotion.encode())

    label_resultat.config(text=f"Quelqu’un qui se sent {emotion} a été trouvé 💬")
    start_chat(pseudo)# Interface
tk.Label(fenetre, text="Bienvenue", font=("Arial", 16)).pack(pady=10)
tk.Label(fenetre, text="Choisis ton pseudo :").pack()
entry = tk.Entry(fenetre)
entry.pack(pady=5)

emotions = ["triste", "en_colere", "stressé", "heureux"]
buttons = []
for emo in emotions:
    btn = tk.Button(fenetre, text=emo, width=15, command=lambda e=emo: choisir_emotion(e))
    btn.pack(pady=5)
    buttons.append(btn)

label_resultat = tk.Label(fenetre, text="", font=("Arial", 12))
label_resultat.pack(pady=20)

fenetre.mainloop()