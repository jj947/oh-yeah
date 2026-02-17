function goChat() {
    const username = document.getElementById("username").value.trim();
    const emotion = document.getElementById("emotion").value;

    if (!username || !emotion) {
        alert("Pseudo et émotion obligatoires");
        return;
    }

    socket.emit("join", {
        username: username,
        emotion: emotion
    });

    // afficher l'interface chat
    document.body.classList.remove("menu-page");
    document.body.classList.add("chat-page");
}
