function goChat() {
    const username = document.getElementById("username").value;
    const emotion = document.getElementById("emotion").value;

    if (!username || !emotion) {
        alert("Complète tout !");
        return;
    }

    localStorage.setItem("username", username);
    localStorage.setItem("emotion", emotion);

    window.location.href = "/chat";
}
