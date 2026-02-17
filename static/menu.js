const socket = io();

socket.on("global_count", count => {
    document.getElementById("globalCount").innerText = count;
});

function goChat() {
    const username = document.getElementById("username").value;
    const emotion = document.getElementById("emotion").value;

    if (!username || !emotion) return alert("Remplis tout");

    document.getElementById("menu").classList.add("hidden");
    document.getElementById("chat").classList.remove("hidden");

    socket.emit("join", { username, emotion });
}

function backMenu() {
    location.reload();
}

socket.on("status", msg => {
    document.getElementById("status").innerText = msg;
});
