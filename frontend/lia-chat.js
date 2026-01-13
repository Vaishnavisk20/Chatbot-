/* ================= CONFIG ================= */

// Default to dev if config isn't loaded for some reason
const CONFIG = window.LIA_CONFIG || { ENV: 'dev', BASE_URLS: { 'dev': 'http://localhost:8000' } };
const BASE_URL = CONFIG.BASE_URLS[CONFIG.ENV];

console.log("🔌 LIA Chat connected to:", BASE_URL);

/* ================= DOM ELEMENTS ================= */

const chatWindow = document.getElementById("lia-chat-window");
const msgContainer = document.getElementById("lia-messages");
const inputField = document.getElementById("lia-input");
const typing = document.getElementById("lia-typing");
const iconChat = document.getElementById("lia-icon-chat");
const iconClose = document.getElementById("lia-icon-close");
const sendBtn = document.getElementById("lia-send-btn");

let chatSessionId = null;
let pollTimeout = null;

// Initialize
startNewChat(false);

/* ================= UI FUNCTIONS ================= */

function toggleChat() {
    const isClosed = chatWindow.style.display === "none" || chatWindow.style.display === "";
    
    if (isClosed) {
        chatWindow.style.display = "flex";
        iconChat.style.display = "none";
        iconClose.style.display = "block";
        setTimeout(() => inputField.focus(), 100);
        msgContainer.scrollTop = msgContainer.scrollHeight;
        restartPolling();
    } else {
        chatWindow.style.display = "none";
        iconChat.style.display = "block";
        iconClose.style.display = "none";
        if(pollTimeout) clearTimeout(pollTimeout);
    }
}

function startNewChat(clearUI = true) {
    // Generate new Session ID
    chatSessionId = "sess_" + Date.now() + "_" + Math.random().toString(36).substr(2, 5);
    localStorage.setItem("lia_session_id", chatSessionId);
    console.log("🆕 New Session:", chatSessionId);

    if (clearUI) {
        msgContainer.innerHTML = `
            <div class="lia-message bot">
                Hello! 👋 I'm Lia.<br>
                Please enter your <b>10-digit mobile number</b> registered with eMudhra to verify your identity and continue. ✨
            </div>`;
        inputField.disabled = false;
        inputField.focus();
    }
    
    restartPolling();
}

/* ================= FORMATTING ================= */

function formatMessage(text) {
    if (!text) return "";
    let formatted = text;

    // Bold (**text**)
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, "<b>$1</b>");

    // Links [Text](URL)
    formatted = formatted.replace(
        /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
        '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
    );

    // Newlines
    formatted = formatted.replace(/\n/g, "<br>");

    return formatted;
}

function addMessage(text, sender) {
    if (!text) return;
    const div = document.createElement("div");
    div.className = `lia-message ${sender}`;
    div.innerHTML = formatMessage(text);
    msgContainer.appendChild(div);
    msgContainer.scrollTop = msgContainer.scrollHeight;
}

/* ================= MESSAGING ================= */

async function sendMessage() {
    const text = inputField.value.trim();
    if (!text) return;

    addMessage(text, "user");
    inputField.value = "";
    
    // Disable input while processing
    inputField.disabled = true;
    sendBtn.disabled = true;
    typing.style.display = "block";
    msgContainer.scrollTop = msgContainer.scrollHeight;

    try {
        const res = await fetch(`${BASE_URL}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: chatSessionId, message: text })
        });

        const data = await res.json();
        typing.style.display = "none";

        if (data.response) {
            addMessage(data.response, "bot");
        }
    } catch (error) {
        console.error("Chat Error:", error);
        typing.style.display = "none";
        addMessage("⚠️ Connection error. Please check your network.", "bot");
    } finally {
        inputField.disabled = false;
        sendBtn.disabled = false;
        inputField.focus();
    }
}

/* ================= POLLING (ROBUST) ================= */

function restartPolling() {
    if (pollTimeout) clearTimeout(pollTimeout);
    pollLoop();
}

async function pollLoop() {
    // Stop polling if chat is closed to save resources
    if (chatWindow.style.display !== "flex") return;

    try {
        // Add timestamp to prevent browser caching
        const url = `${BASE_URL}/chat/poll?session_id=${chatSessionId}&_t=${Date.now()}`;
        const res = await fetch(url);
        
        if (res.ok) {
            const data = await res.json();
            if (data.messages && data.messages.length > 0) {
                console.log("📩 Incoming Agent Messages:", data.messages);
                data.messages.forEach(m => addMessage(m, "bot"));
            }
        }
    } catch (e) {
        // Silent failure is okay for polling, just retry
    } finally {
        // Always schedule next poll
        pollTimeout = setTimeout(pollLoop, 3000);
    }
}

/* ================= EVENTS ================= */

inputField.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMessage();
});

if (sendBtn) {
    sendBtn.addEventListener("click", sendMessage);
}

/* ================= NEW CONVERSATION MODAL ================= */

function showNewConversationModal() {
    const modal = document.getElementById("lia-new-chat-modal");
    if (modal) {
        modal.style.display = "flex";
    }
}

function closeNewConversationModal() {
    const modal = document.getElementById("lia-new-chat-modal");
    if (modal) {
        modal.style.display = "none";
    }
}

function confirmNewConversation() {
    closeNewConversationModal();
    startNewChat(true);
}

/* ================= LIKE/DISLIKE FUNCTIONS ================= */

function likeMessage(button) {
    // Toggle like state
    const svg = button.querySelector('svg');
    if (button.classList.contains('liked')) {
        button.classList.remove('liked');
        svg.style.fill = 'none';
    } else {
        button.classList.add('liked');
        svg.style.fill = 'currentColor';
        // Remove dislike if present
        const dislikeBtn = button.parentElement.querySelector('button:last-child');
        if (dislikeBtn && dislikeBtn.classList.contains('disliked')) {
            dislikeBtn.classList.remove('disliked');
            dislikeBtn.querySelector('svg').style.fill = 'none';
        }
    }
}

function dislikeMessage(button) {
    // Toggle dislike state
    const svg = button.querySelector('svg');
    if (button.classList.contains('disliked')) {
        button.classList.remove('disliked');
        svg.style.fill = 'none';
    } else {
        button.classList.add('disliked');
        svg.style.fill = 'currentColor';
        // Remove like if present
        const likeBtn = button.parentElement.querySelector('button:first-child');
        if (likeBtn && likeBtn.classList.contains('liked')) {
            likeBtn.classList.remove('liked');
            likeBtn.querySelector('svg').style.fill = 'none';
        }
    }
}