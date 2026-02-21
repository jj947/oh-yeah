window.socket = io({
    transports: ["websocket"]
});

socket.on("global_count", count => {
    const el = document.getElementById("globalCount");
    if (el) el.innerText = count;
});

function goChat() {
    const username = document.getElementById("username").value.trim();
    const emotion = document.getElementById("emotion").value;

    if (!username || !emotion) {
        alert("Remplis tout");
        return;
    }

    window.currentUser = username;

    document.getElementById("menu").classList.add("hidden");
    document.getElementById("chat").classList.remove("hidden");

    socket.emit("join", { username, emotion });
}

function backMenu() {
    location.reload();
}
