const socket = io({
    transports: ["websocket"],
    upgrade: false
});
const statusEl = document.getElementById("status");
const messages = document.getElementById("messages");

socket.on("message", (data) => {
    const div = document.createElement("div");
    div.classList.add("message");

    if (data.from === username) {
        div.classList.add("me");
    }

    div.innerHTML = `<strong>${data.from}</strong> : ${data.message}`;
    messages.appendChild(div);

    messages.scrollTop = messages.scrollHeight;
});

socket.on("status", (msg) => {
    statusEl.innerText = msg;

    if (msg.includes("En attente")) {
        statusEl.className = "status waiting";
    } else if (msg.includes("Partenaire trouvé")) {
        statusEl.className = "status found";
    } else if (msg.includes("quitté")) {
        statusEl.className = "status left";
    } else {
        statusEl.className = "status";
    }
});

function sendMessage() {
    const input = document.getElementById("messageInput");
    const msg = input.value.trim();

    if (msg === "") return;

    socket.emit("message", { message: msg });

    input.value = "";
}

socket.on("receive_message", data => {
    const div = document.createElement("div");
    div.textContent = `${data.from} : ${data.message}`;
    document.getElementById("messages").appendChild(div);

    const messages = document.getElementById("messages");
    messages.scrollTop = messages.scrollHeight;
});
