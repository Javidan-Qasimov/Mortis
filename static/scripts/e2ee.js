/*
 * Browser-side E2EE prototype.
 *
 * The server receives an identity public key and AES-GCM ciphertext only.
 * Private keys remain in this browser's local storage. This is deliberately
 * not a Signal Protocol implementation: it has no X3DH/PQXDH, prekeys,
 * Double Ratchet, multi-device support, or audited secure key storage.
 */

const E2EE_VERSION = 1;
const E2EE_PRIVATE_KEY_PREFIX = "homis_e2ee_private_";
const E2EE_PUBLIC_KEY_PREFIX = "homis_e2ee_public_";
const textEncoder = new TextEncoder();
const textDecoder = new TextDecoder();

function bytesToBase64(bytes) {
    let binary = "";
    for (const byte of new Uint8Array(bytes)) binary += String.fromCharCode(byte);
    return btoa(binary);
}

function base64ToBytes(value) {
    const binary = atob(value);
    return Uint8Array.from(binary, char => char.charCodeAt(0));
}

function csrfToken() {
    return document.querySelector('meta[name="csrf-token"]').content;
}

async function createIdentity() {
    const keyPair = await crypto.subtle.generateKey(
        { name: "ECDH", namedCurve: "P-256" }, true, ["deriveKey"]
    );
    const publicKey = await crypto.subtle.exportKey("jwk", keyPair.publicKey);
    const privateKey = await crypto.subtle.exportKey("jwk", keyPair.privateKey);
    localStorage.setItem(E2EE_PRIVATE_KEY_PREFIX + myUsername, JSON.stringify(privateKey));
    localStorage.setItem(E2EE_PUBLIC_KEY_PREFIX + myUsername, JSON.stringify(publicKey));
    return { publicKey, privateKey };
}

async function getIdentity() {
    const savedPrivate = localStorage.getItem(E2EE_PRIVATE_KEY_PREFIX + myUsername);
    const savedPublic = localStorage.getItem(E2EE_PUBLIC_KEY_PREFIX + myUsername);
    if (!savedPrivate || !savedPublic) return createIdentity();
    return { publicKey: JSON.parse(savedPublic), privateKey: JSON.parse(savedPrivate) };
}

async function registerIdentity() {
    const identity = await getIdentity();
    const response = await fetch("/keys/me", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
        body: JSON.stringify({ public_key: identity.publicKey }),
    });
    if (!response.ok && response.status !== 204) {
        throw new Error("This browser identity does not match the registered identity key.");
    }
}

async function getPeerPublicKey(username) {
    const response = await fetch(`/keys/${encodeURIComponent(username)}`);
    if (response.status === 404) {
        throw new Error("This user has not opened encrypted chat yet. Ask them to log in once first.");
    }
    if (!response.ok) throw new Error("Recipient encryption key could not be retrieved.");
    const body = await response.json();
    return crypto.subtle.importKey(
        "jwk", body.public_key, { name: "ECDH", namedCurve: "P-256" }, false, []
    );
}

async function conversationKey(peerUsername) {
    const identity = await getIdentity();
    const privateKey = await crypto.subtle.importKey(
        "jwk", identity.privateKey, { name: "ECDH", namedCurve: "P-256" }, false, ["deriveKey"]
    );
    return crypto.subtle.deriveKey(
        { name: "ECDH", public: await getPeerPublicKey(peerUsername) },
        privateKey,
        { name: "AES-GCM", length: 256 },
        false,
        ["encrypt", "decrypt"]
    );
}

async function encryptMessage(peerUsername, plaintext) {
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const encrypted = await crypto.subtle.encrypt(
        { name: "AES-GCM", iv, additionalData: textEncoder.encode(`${myUsername}:${peerUsername}`) },
        await conversationKey(peerUsername),
        textEncoder.encode(plaintext)
    );
    return { v: E2EE_VERSION, iv: bytesToBase64(iv), ciphertext: bytesToBase64(encrypted) };
}

async function decryptMessage(peerUsername, envelope, sender) {
    if (!envelope || envelope.v !== E2EE_VERSION) throw new Error("Unsupported encrypted message.");
    const plaintext = await crypto.subtle.decrypt(
        {
            name: "AES-GCM",
            iv: base64ToBytes(envelope.iv),
            additionalData: textEncoder.encode(`${sender}:${sender === myUsername ? peerUsername : myUsername}`),
        },
        await conversationKey(peerUsername),
        base64ToBytes(envelope.ciphertext)
    );
    return textDecoder.decode(plaintext);
}

const encryptionReady = registerIdentity().catch(error => {
    console.error("E2EE initialization failed:", error);
    alert(`Encrypted messaging could not be initialized: ${error.message}`);
    throw error;
});
