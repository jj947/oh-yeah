function sendMessage() {
    const input = document.getElementById("messageInput");
    const msg = input.value.trim();
    if (!msg) return;

    socket.emit("send_message", { message: msg });
    input.value = "";
}

socket.on("receive_message", data => {
    const div = document.createElement("div");
    div.textContent = `${data.from} : ${data.message}`;
    document.getElementById("messages").appendChild(div);

    const messages = document.getElementById("messages");
    messages.scrollTop = messages.scrollHeight;
});
