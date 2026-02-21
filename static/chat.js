const messages = document.getElementById("messages");
const statusEl = document.getElementById("status");

socket.on("status", msg => {
    statusEl.innerText = msg;

    if (msg.includes("Partenaire trouvé")) {
        statusEl.className = "status found";
    } else {
        statusEl.className = "status";
    }
});

socket.on("message", data => {
    const div = document.createElement("div");
    div.classList.add("message");

    if (data.from === window.currentUser) {
        div.innerHTML = `<strong>Moi</strong> : ${data.message}`;
    } else {
        div.innerHTML = `<strong>${data.from}</strong> : ${data.message}`;
    }

    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
});

function sendMessage() {
    const input = document.getElementById("messageInput");
    const msg = input.value.trim();
    if (!msg) return;

    socket.emit("message", { message: msg });
    input.value = "";
}
