const socket = io({
  transports: ["websocket"],
  upgrade: false
});

function goChat() {
    const username = document.getElementById("username").value;
    const emotion = document.getElementById("emotion").value;

    if (!username || !emotion) {
        alert("Choisis un pseudo et une émotion");
        return;
    }

    // 🔥 C'EST CE QUI MANQUAIT 🔥
    socket.emit("join", {
        username: username,
        emotion: emotion
    });

    // afficher l’interface chat
    document.body.classList.remove("menu-page");
    document.body.classList.add("chat-page");

    document.getElementById("status").innerText =
        "⏳ En attente d’un partenaire...";
}
