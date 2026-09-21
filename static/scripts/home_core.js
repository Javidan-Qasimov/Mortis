/**
 * homis-core.js
 *
 * Shared, dependency-free utilities used by every other Homis script:
 *   - the logged-in user's username (read once from the DOM)
 *   - avatar colors (random-but-stable per username)
 *   - avatar photos (locally-stored profile pictures)
 *   - small formatting helpers (truncate, formatTime)
 *
 * LOAD ORDER: this file must be loaded FIRST, before homis-profile.js,
 * homis-search-inbox.js, and homis-chat.js - they all rely on the
 * top-level variables and functions declared here (see home.html).
 *
 * NOTE: these are plain <script> tags, not ES modules. Top-level
 * `let`/`const`/`function` declarations in one <script> tag remain
 * visible to every <script> tag loaded after it on the same page (they
 * share one global scope) - so no imports/exports are needed, just a
 * correct load order.
 */

// =============================================================================
// Server-rendered data (read out of the DOM once on load)
// =============================================================================

/** Username of the currently logged-in user. */
let myUsername = document.body.dataset.username;

// =============================================================================
// Avatar colors
// A random-but-stable color is assigned to each username the first time
// it's seen, then cached, so the same user always gets the same avatar
// color across renders (search results, inbox rows, chat header).
// =============================================================================

let avatarColors = {};

/**
 * Generate a random pastel-ish HSL color string for a new avatar.
 * @returns {string} an `hsl(...)` CSS color.
 */
function randomColor() {
    let hue = Math.floor(Math.random() * 360);
    return `hsl(${hue}, 65%, 50%)`;
}

/**
 * Get the cached avatar color for a username, generating and storing one
 * the first time it's requested.
 * @param {string} username
 * @returns {string} an `hsl(...)` CSS color.
 */
function getColorFor(username) {
    if (!avatarColors[username]) {
        avatarColors[username] = randomColor();
    }
    return avatarColors[username];
}

// =============================================================================
// Avatar photos
// A user can set a custom profile photo (see homis-profile.js). Since
// there's no backend endpoint for uploads, photos are stored locally in
// this browser (localStorage, keyed per-username) as a base64 data URL
// and re-applied on every page load. Any avatar in the app (topbar,
// profile panel, search results, inbox, chat header) will show the photo
// instead of the colored-initial fallback once one is set for that
// username.
// =============================================================================

const AVATAR_PHOTO_PREFIX = "homis_avatar_photo_";

/**
 * Look up a locally-stored profile photo for a username, if any.
 * @param {string} username
 * @returns {string|null} a base64 data URL, or null if none is set.
 */
function getPhotoFor(username) {
    return localStorage.getItem(AVATAR_PHOTO_PREFIX + username);
}

/**
 * Save a profile photo (as a base64 data URL) for a username.
 * @param {string} username
 * @param {string} dataUrl
 */
function setPhotoFor(username, dataUrl) {
    localStorage.setItem(AVATAR_PHOTO_PREFIX + username, dataUrl);
}

/**
 * Apply the correct visual to an avatar element: a custom photo if one is
 * set for this username, otherwise the usual colored-circle-with-initial
 * fallback. Centralizes the "photo vs. initial" branching so every avatar
 * in the app (topbar, profile panel, search results, inbox, chat header)
 * stays in sync.
 * @param {HTMLElement} el - the avatar element to update.
 * @param {string} username
 */
function applyAvatar(el, username) {
    let photo = getPhotoFor(username);

    if (photo) {
        el.style.backgroundImage = `url("${photo}")`;
        el.style.backgroundColor = "";
        el.classList.add("has-photo");
        // Clear only the fallback initial text node, not child elements
        // like the camera badge (relevant for #profile-panel-avatar).
        el.childNodes.forEach(node => {
            if (node.nodeType === Node.TEXT_NODE) node.textContent = "";
        });
    } else {
        el.style.backgroundImage = "";
        el.style.backgroundColor = getColorFor(username);
        el.classList.remove("has-photo");
        el.childNodes.forEach(node => {
            if (node.nodeType === Node.TEXT_NODE) node.textContent = "";
        });
        el.appendChild(document.createTextNode(username.charAt(0).toUpperCase()));
    }
}

// =============================================================================
// Formatting helpers
// =============================================================================

/**
 * Truncate a string to `max` characters, appending an ellipsis if it was
 * cut short. Used to keep inbox preview lines to a single visual line.
 * @param {string} text
 * @param {number} max
 * @returns {string}
 */
function truncate(text, max) {
    if (text.length <= max) return text;
    return text.slice(0, max) + "…";
}

/**
 * Format a Unix timestamp (seconds) into a short, human-readable time
 * string, used both inside the chat window (per-bubble) and in the inbox
 * list (per-conversation last-message time).
 * @param {number} unixSeconds
 * @returns {string} e.g. "14:32", or "" if no timestamp is available.
 */
function formatTime(unixSeconds) {
    if (!unixSeconds) return "";
    let d = new Date(unixSeconds * 1000);
    let hours = String(d.getHours()).padStart(2, "0");
    let minutes = String(d.getMinutes()).padStart(2, "0");
    return `${hours}:${minutes}`;
}