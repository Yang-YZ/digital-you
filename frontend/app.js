/* Digital You — Frontend Application Logic */

const API_BASE = "";  // Same-origin requests
let sessionId = null;
let conversationHistory = [];

// ---------------------------------------------------------------------------
// Authentication
// ---------------------------------------------------------------------------

async function startLogin() {
    try {
        const res = await fetch(`${API_BASE}/auth/login`);
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || "Login failed");
        }
        // Open Google OAuth in the same window
        window.location.href = data.auth_url;
    } catch (err) {
        alert("Failed to start login: " + err.message);
        console.error(err);
    }
}

async function handleCallback() {
    const params = new URLSearchParams(window.location.search);

    // Handle auth error from server-side callback
    const authError = params.get("auth_error");
    if (authError) {
        alert("Authentication failed: " + authError);
        window.history.replaceState({}, document.title, "/");
        return true;
    }

    // Handle successful server-side callback redirect (session_id in URL)
    const urlSessionId = params.get("session_id");
    const urlEmail = params.get("email");
    if (urlSessionId && urlEmail) {
        sessionId = urlSessionId;
        localStorage.setItem("session_id", sessionId);
        localStorage.setItem("user_email", urlEmail);

        // Clean URL
        window.history.replaceState({}, document.title, "/");
        showLoggedInState(urlEmail);
        return true;
    }

    return false;
}

function showLoggedInState(email) {
    document.getElementById("login-section").innerHTML = `
        <p>✅ Connected as <strong>${escapeHtml(email)}</strong></p>
    `;
    document.getElementById("profile-section").classList.remove("hidden");
    document.getElementById("interaction-section").classList.remove("hidden");
}

// ---------------------------------------------------------------------------
// Profile Building
// ---------------------------------------------------------------------------

async function buildProfile() {
    if (!sessionId) { alert("Please log in first."); return; }

    document.getElementById("profile-loading").classList.remove("hidden");
    document.getElementById("profile-content").classList.add("hidden");

    try {
        const res = await fetch(`${API_BASE}/profile/build?session_id=${sessionId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ max_emails: 500 }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to build profile");
        }

        const data = await res.json();
        renderProfile(data.profile);
    } catch (err) {
        alert(`Error: ${err.message}`);
        console.error(err);
    } finally {
        document.getElementById("profile-loading").classList.add("hidden");
    }
}

function renderProfile(profile) {
    document.getElementById("profile-summary").textContent = profile.summary || "—";
    document.getElementById("profile-style").textContent = profile.communication_style || "—";
    document.getElementById("profile-tone").textContent = profile.writing_tone || "—";

    renderTags("profile-traits", profile.personality_traits);
    renderTags("profile-hobbies", profile.hobbies);
    renderTags("profile-interests", profile.interests);
    renderTags("profile-purchases", profile.purchase_categories);
    renderTags("profile-topics", profile.frequently_discussed_topics);

    document.getElementById("profile-content").classList.remove("hidden");
}

function renderTags(elementId, items) {
    const container = document.getElementById(elementId);
    container.innerHTML = "";
    if (!items || items.length === 0) {
        container.innerHTML = "<span class='tag'>—</span>";
        return;
    }
    items.forEach(item => {
        const span = document.createElement("span");
        span.className = "tag";
        span.textContent = item;
        container.appendChild(span);
    });
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

async function sendChat() {
    const input = document.getElementById("chat-input");
    const message = input.value.trim();
    if (!message || !sessionId) return;

    input.value = "";
    appendChatMessage("user", message);

    try {
        const res = await fetch(`${API_BASE}/chat?session_id=${sessionId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: message,
                conversation_history: conversationHistory,
            }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Chat failed");
        }

        const data = await res.json();
        appendChatMessage("assistant", data.response);
    } catch (err) {
        appendChatMessage("assistant", `Error: ${err.message}`);
    }
}

function appendChatMessage(role, content) {
    conversationHistory.push({ role, content });

    const container = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.className = `message ${role}`;
    div.innerHTML = `<p>${escapeHtml(content)}</p>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

// ---------------------------------------------------------------------------
// Email Reply
// ---------------------------------------------------------------------------

async function generateReply() {
    if (!sessionId) { alert("Please log in first."); return; }

    const sender = document.getElementById("email-sender").value.trim();
    const subject = document.getElementById("email-subject").value.trim();
    const body = document.getElementById("email-body").value.trim();
    const context = document.getElementById("email-context").value.trim();

    if (!subject && !body) {
        alert("Please provide at least a subject or email body.");
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/email/reply?session_id=${sessionId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                original_email_subject: subject,
                original_email_body: body,
                sender_name: sender,
                additional_context: context,
            }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to generate reply");
        }

        const data = await res.json();
        document.getElementById("email-reply-text").textContent = data.reply;
        document.getElementById("email-reply-result").classList.remove("hidden");
    } catch (err) {
        alert(`Error: ${err.message}`);
    }
}

function copyReply() {
    const text = document.getElementById("email-reply-text").textContent;
    navigator.clipboard.writeText(text).then(() => {
        alert("Reply copied to clipboard!");
    }).catch(() => {
        alert("Failed to copy. Please select and copy the text manually.");
    });
}

// ---------------------------------------------------------------------------
// Tab Switching
// ---------------------------------------------------------------------------

function switchTab(tabName) {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));

    if (tabName === "chat") {
        document.querySelector(".tabs .tab:first-child").classList.add("active");
        document.getElementById("chat-tab").classList.add("active");
    } else {
        document.querySelector(".tabs .tab:last-child").classList.add("active");
        document.getElementById("email-tab").classList.add("active");
    }
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

// ---------------------------------------------------------------------------
// Initialization
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", async () => {
    // Check for OAuth callback
    const handled = await handleCallback();
    if (handled) return;

    // Check for existing session and validate it
    const savedSession = localStorage.getItem("session_id");
    const savedEmail = localStorage.getItem("user_email");
    if (savedSession && savedEmail) {
        try {
            const res = await fetch(`${API_BASE}/profile?session_id=${encodeURIComponent(savedSession)}`);
            if (res.status === 401) {
                // Session expired — clear stored data
                localStorage.removeItem("session_id");
                localStorage.removeItem("user_email");
            } else {
                sessionId = savedSession;
                showLoggedInState(savedEmail);
            }
        } catch {
            // Server unreachable — still show logged-in state optimistically
            sessionId = savedSession;
            showLoggedInState(savedEmail);
        }
    }
});
