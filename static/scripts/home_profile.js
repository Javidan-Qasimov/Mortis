/**
 * homis-profile.js
 *
 * Profile panel (left-side drawer, opened via the topbar avatar) and the
 * profile-photo upload flow.
 *
 * DEPENDS ON homis-core.js (must be loaded first): uses `myUsername` and
 * `applyAvatar`, `getPhotoFor`/`setPhotoFor` indirectly via applyAvatar.
 */

let profileAvatar = document.getElementById("profile-avatar");
let profileOverlay = document.getElementById("profile-overlay");
let profilePanelAvatar = document.getElementById("profile-panel-avatar");
let profilePanelUsername = document.getElementById("profile-panel-username");
let profileClose = document.getElementById("profile-close");
let avatarUpload = document.getElementById("avatar-upload");

// Fill in the logged-in user's own avatar (topbar + inside the panel).
applyAvatar(profileAvatar, myUsername);

function openProfilePanel() {
    applyAvatar(profilePanelAvatar, myUsername);
    profilePanelUsername.innerText = myUsername;
    profileOverlay.hidden = false;
}

function closeProfilePanel() {
    profileOverlay.hidden = true;
}

profileAvatar.onclick = openProfilePanel;
profileClose.onclick = closeProfilePanel;

// Close when clicking the dimmed backdrop, same pattern as the chat modal.
profileOverlay.addEventListener("click", function(e) {
    if (e.target === profileOverlay) {
        closeProfilePanel();
    }
});

/**
 * Clicking the big avatar inside the profile panel opens the native file
 * picker (the actual <input type="file"> stays hidden the whole time).
 */
profilePanelAvatar.onclick = function() {
    avatarUpload.click();
};

/**
 * Once the user picks an image file, read it as a base64 data URL,
 * persist it locally for this username, and immediately refresh every
 * avatar on screen so the change is visible without a reload.
 */
avatarUpload.addEventListener("change", function() {
    let file = avatarUpload.files[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
        alert("Lütfen bir görsel dosyası seçin.");
        avatarUpload.value = "";
        return;
    }

    let reader = new FileReader();
    reader.onload = function(e) {
        setPhotoFor(myUsername, e.target.result);
        applyAvatar(profileAvatar, myUsername);
        applyAvatar(profilePanelAvatar, myUsername);
        // In case the current user's own avatar also appears elsewhere
        // on screen (e.g. inbox rows, if they ever show up there).
        document.querySelectorAll('.avatar, .conv-row .avatar').forEach(el => {
            if (el.dataset.username === myUsername) applyAvatar(el, myUsername);
        });
    };
    reader.readAsDataURL(file);

    // Reset so selecting the same file again still fires "change".
    avatarUpload.value = "";
});