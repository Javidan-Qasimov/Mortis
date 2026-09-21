/**
 * homis-search-inbox.js
 *
 * User search (typeahead dropdown) and the conversations list / inbox
 * rendering (Instagram-DM style).
 *
 * DEPENDS ON homis-core.js (must be loaded first): uses `myUsername`,
 * `applyAvatar`, `truncate`, `formatTime`.
 *
 * `openChat` (referenced inside the row/result click handlers below) is
 * defined later in homis-chat.js. That's fine even though this file loads
 * before homis-chat.js: the handlers only look up `openChat` at click
 * time, long after every script on the page has finished loading, not at
 * the moment this file itself runs.
 */

// =============================================================================
// User search (typeahead dropdown)
// =============================================================================

let search = document.getElementById("search");
let resultsBox = document.getElementById("results");

/** Flat list of every registered username, used for client-side search. */
let allUsers = Array.from(document.querySelectorAll("#list li")).map(li => li.innerText);

/**
 * Render the search-results dropdown for the given (lowercased) query.
 * Filters `allUsers` client-side (no network request per keystroke, since
 * the full user list was embedded server-side) and excludes the current
 * user from the results.
 * @param {string} value - lowercased search query.
 */
function renderResults(value) {
    resultsBox.innerHTML = "";

    if (value === "") {
        resultsBox.classList.remove("active");
        return;
    }

    let matches = allUsers.filter(u => u.toLowerCase().includes(value) && u !== myUsername);

    if (matches.length === 0) {
        resultsBox.classList.remove("active");
        return;
    }

    matches.forEach(function(username) {
        let row = document.createElement("div");
        row.className = "result-row";

        let avatar = document.createElement("div");
        avatar.className = "avatar";
        avatar.dataset.username = username;
        applyAvatar(avatar, username);

        let name = document.createElement("span");
        name.className = "result-name";
        name.innerText = username;

        row.appendChild(avatar);
        row.appendChild(name);

        // Clicking a result opens a chat with that user and resets the
        // search box back to its empty state.
        row.onclick = function() {
            openChat(username);
            resultsBox.classList.remove("active");
            search.value = "";
        };

        resultsBox.appendChild(row);
    });

    resultsBox.classList.add("active");
}

// Re-filter results on every keystroke.
search.onkeyup = function() {
    let value = search.value.toLowerCase();
    renderResults(value);
};

// Close the dropdown when the user clicks anywhere outside the search
// capsule (standard "click outside to dismiss" pattern).
document.addEventListener("click", function(e) {
    if (!e.target.closest(".search-capsule")) {
        resultsBox.classList.remove("active");
    }
});

// =============================================================================
// Conversations list (Instagram-DM-style inbox)
// =============================================================================

let conversationsListBox = document.getElementById("conversations-list");
let centerBox = document.getElementById("center");

/**
 * In-memory copy of the user's conversation list, seeded from the
 * server-rendered `#conversations-data` JSON blob and kept up to date
 * client-side as new messages are sent/received (see upsertConversation).
 * Shape per entry: { username, last_text, last_from_me, time }.
 */
let conversationsData = JSON.parse(document.getElementById("conversations-data").textContent);

/**
 * Render the full conversations list into #conversations-list.
 *
 * If there are no conversations yet, hides the list and falls back to
 * showing the empty-state headline (#center) instead. Otherwise hides the
 * headline and renders one clickable row per conversation partner,
 * ordered as given in `conversationsData` (kept sorted by recency by
 * upsertConversation).
 */
function renderConversations() {
    if (!conversationsData || conversationsData.length === 0) {
        // No conversations at all -> show the "Are you looking for
        // someone??" empty state instead of an empty list.
        conversationsListBox.hidden = true;
        centerBox.hidden = false;
        return;
    }

    centerBox.hidden = true;
    conversationsListBox.hidden = false;
    conversationsListBox.innerHTML = "";

    conversationsData.forEach(function(conv) {
        let row = document.createElement("div");
        row.className = "conv-row";

        let avatar = document.createElement("div");
        avatar.className = "avatar";
        avatar.dataset.username = conv.username;
        applyAvatar(avatar, conv.username);

        let info = document.createElement("div");
        info.className = "conv-info";

        let name = document.createElement("span");
        name.className = "conv-name";
        name.innerText = conv.username;

        // Prefix the preview with "Sen: " ("You: ") when the last message
        // in this conversation was sent by the current user.
        let preview = document.createElement("span");
        preview.className = "conv-preview";
        let prefix = conv.last_from_me ? "Sen: " : "";
        preview.innerText = prefix + truncate(conv.last_text, 42);

        info.appendChild(name);
        info.appendChild(preview);

        let time = document.createElement("span");
        time.className = "conv-time";
        time.innerText = formatTime(conv.time);

        row.appendChild(avatar);
        row.appendChild(info);
        row.appendChild(time);

        // Clicking anywhere on the row opens the chat for that
        // conversation partner in the main-chat panel.
        row.onclick = function() {
            openChat(conv.username);
        };

        conversationsListBox.appendChild(row);
    });
}

// Initial render on page load, using the server-seeded data.
renderConversations();

/**
 * Insert or update a conversation's "last message" preview and re-render
 * the inbox, keeping it sorted newest-first. Called whenever a message is
 * sent or received, so the inbox stays in sync with the open chat without
 * needing a full page reload.
 * @param {string} username - the conversation partner's username.
 * @param {string} text - the new last message's text.
 * @param {boolean} fromMe - true if the current user sent this message.
 * @param {number} [time] - Unix timestamp (seconds) of the message; falls
 *   back to the current client time if not provided.
 */
function upsertConversation(username, text, fromMe, time) {
    let ts = time || (Date.now() / 1000);
    let existing = conversationsData.find(c => c.username === username);

    if (existing) {
        existing.last_text = text;
        existing.last_from_me = fromMe;
        existing.time = ts;
    } else {
        conversationsData.push({
            username: username,
            last_text: text,
            last_from_me: fromMe,
            time: ts
        });
    }

    conversationsData.sort((a, b) => b.time - a.time);
    renderConversations();
}