document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("chat-form");
    const input = document.getElementById("message-input");
    const chatWindow = document.getElementById("chat-window");

    let sessionId = "session_" + Date.now();

    function renderMessage(message, senderClass) {
        const messageDiv = document.createElement("div");
        messageDiv.className = `message ${senderClass}`;
        messageDiv.textContent = message;
        chatWindow.appendChild(messageDiv);
        chatWindow.scrollTop = chatWindow.scrollHeight;
        return messageDiv;
    }

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const message = input.value.trim();
        if (!message) return;

        renderMessage(message, "user");
        input.value = "";

        const typingIndicator = renderMessage("...", "bot");

        try {
            const response = await fetch("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: message, session_id: sessionId }),
            });

            chatWindow.removeChild(typingIndicator);

            if (!response.ok) throw new Error(`Błąd serwera: ${response.statusText}`);

            const data = await response.json();
            renderMessage(data.response, "bot");
            sessionId = data.session_id;

        } catch (error) {
            console.error("Błąd fetch:", error);
            if (typingIndicator.parentNode) chatWindow.removeChild(typingIndicator);
            renderMessage("Przepraszam, wystąpił błąd komunikacji.", "bot-error");
        }
    });
});
