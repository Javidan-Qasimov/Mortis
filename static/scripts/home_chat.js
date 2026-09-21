/**
 * homis-chat.js
 *
 * Real-time 1-to-1 chat panel, powered by Socket.IO, rendered inline
 * WhatsApp-style next to the sidebar.
 *
 * DEPENDS ON (must be loaded first, in this order):
 *   homis-core.js         - myUsername, applyAvatar, getColorFor, formatTime
 *   homis-search-inbox.js - centerBox, renderConversations, upsertConversation
 */

let socket = io();

/** Username of the person the chat panel is currently open with, or null. */
let currentChatWith = null;

let chatPanel = document.getElementById("chat-panel");
let chatWithName = document.getElementById("chat-with-name");
let chatHeaderAvatar = document.getElementById("chat-header-avatar");
let chatMessages = document.getElementById("chat-messages");
let chatInput = document.getElementById("chat-input");
let chatSend = document.getElementById("chat-send");
let chatClose = document.getElementById("chat-close");
let chatBack = document.getElementById("chat-back");

/**
 * Open the chat panel for a given conversation partner, WhatsApp-style:
 * the sidebar (search + conversation list) stays put on the left, and the
 * chat itself fills the main-chat column on the right, replacing the
 * empty-state headline.
 *
 * Resets the message thread, asks the server (via the "join" Socket.IO
 * event) to join the shared room for this pair of users and send back the
 * conversation's message history (handled in the "history" listener
 * below).
 * @param {string} username - the conversation partner to chat with.
 */
function openChat(username) {
    currentChatWith = username;
    chatWithName.innerText = username;

    chatHeaderAvatar.dataset.username = username;
    applyAvatar(chatHeaderAvatar, username);

    chatMessages.innerHTML = "";
    centerBox.hidden = true;
    chatPanel.hidden = false;

    // On narrow/mobile widths, the chat slides in full-screen on top of
    // the sidebar (see the @media block in homis.css); this class is what
    // that CSS hooks into. It's a no-op on desktop widths.
    document.body.classList.add("chat-open");

    socket.emit("join", { with: username });

    // Focus the input right after opening so the user can start typing
    // immediately; the small delay avoids focusing before the panel is
    // actually visible/rendered.
    setTimeout(() => chatInput.focus(), 50);
}

/**
 * Close the currently open chat and return to the sidebar: either the
 * conversation list (if there are conversations) or the empty-state
 * headline (if there aren't) - whichever is actually correct, re-derived
 * via renderConversations() rather than blindly forced.
 */
function closeChat() {
    chatPanel.hidden = true;
    currentChatWith = null;
    document.body.classList.remove("chat-open");
    renderConversations();
}

/**
 * Append a single chat bubble to the message thread and scroll it into
 * view. Bubbles are styled "mine" (sent by the current user, always gray)
 * or "theirs" (sent by the other participant, colored per-user to match
 * their avatar) via CSS classes + an inline background (see homis.css).
 * Each bubble also shows the message's timestamp.
 * @param {{from: string, text: string, time?: number}} msg
 */
function appendMessage(msg, plaintext) {
    let isMine = msg.from === myUsername;

    let row = document.createElement("div");
    row.className = "chat-msg " + (isMine ? "mine" : "theirs");

    if (!isMine) {
        row.style.backgroundColor = getColorFor(msg.from);
    }

    let textSpan = document.createElement("span");
    textSpan.className = "msg-text";
    textSpan.innerText = plaintext;
    row.appendChild(textSpan);

    let timeSpan = document.createElement("span");
    timeSpan.className = "msg-time";
    timeSpan.innerText = formatTime(msg.time);
    row.appendChild(timeSpan);

    chatMessages.appendChild(row);
    chatMessages.scrollTop = chatMessages.scrollHeight; // auto-scroll to the newest message
}

// Server response to "join": full message history for the room just
// joined. Replaces whatever was in the thread (should be empty, since
// openChat() already cleared it).
socket.on("history", async function(data) {
    chatMessages.innerHTML = "";
    for (const msg of data.messages) {
        const peer = msg.from === myUsername ? currentChatWith : msg.from;
        try {
            appendMessage(msg, await decryptMessage(peer, msg.envelope, msg.from));
        } catch {
            appendMessage(msg, "[Unable to decrypt this message]");
        }
    }
});

// Fired whenever a message is broadcast to a room this socket has joined
// (i.e. any message sent or received in an active/joined conversation).
socket.on("receive_message", async function(msg) {
    // Only render it into the thread if it belongs to the conversation
    // that's currently open (covers messages the current user just sent,
    // since the sender is also a member of the room).
    const other = msg.from === myUsername ? currentChatWith : msg.from;
    if (!other) return;
    let plaintext;
    try {
        plaintext = await decryptMessage(other, msg.envelope, msg.from);
    } catch {
        plaintext = "[Unable to decrypt this message]";
    }
    if (currentChatWith && (msg.from === currentChatWith || msg.from === myUsername)) {
        appendMessage(msg, plaintext);
    }

    // Keep the inbox preview in sync regardless of which chat is open:
    // figure out who the "other" party in this message is, then update
    // (or create) that conversation's preview row.
    if (other) {
        upsertConversation(other, plaintext, msg.from === myUsername, msg.time);
    }
});

/**
 * Send whatever is currently typed in the chat input to the currently
 * open conversation partner, then clear the input. No-ops if the input is
 * empty/whitespace-only or no chat is open.
 */
async function sendCurrentMessage() {
    let text = chatInput.value.trim();
    if (!text || !currentChatWith) return;
    if (text.length > 2000) {
        alert("Messages are limited to 2,000 characters.");
        return;
    }

    try {
        await encryptionReady;
        const envelope = await encryptMessage(currentChatWith, text);
        socket.emit("send_message", { to: currentChatWith, envelope: envelope });
    } catch (error) {
        console.error("Message encryption failed:", error);
        alert(`Message could not be encrypted: ${error.message}`);
        return;
    }
    chatInput.value = "";
}

chatSend.onclick = sendCurrentMessage;

// Allow sending with the Enter key, not just the send button.
chatInput.addEventListener("keyup", function(e) {
    if (e.key === "Enter") {
        sendCurrentMessage();
    }
});

// × button (desktop and mobile) and ‹ back button (mobile only, see
// homis.css) both just close the chat and go back to the sidebar/
// empty-state.
chatClose.onclick = closeChat;
chatBack.onclick = closeChat;
