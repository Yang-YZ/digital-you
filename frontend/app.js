const $ = (sel) => document.querySelector(sel);

const personaView = $("#persona-view");
const chatLog = $("#chat-log");
const chatHistory = []; // {role, content}

async function loadPersona() {
  try {
    const res = await fetch("/api/persona");
    if (res.status === 404) {
      personaView.textContent = "No persona generated yet.";
      return;
    }
    if (!res.ok) throw new Error(await res.text());
    personaView.textContent = await res.text();
  } catch (err) {
    personaView.textContent = `Error: ${err.message}`;
  }
}

$("#reload-persona").addEventListener("click", loadPersona);

$("#gen-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const fd = new FormData(form);
  const payload = {
    imap_host: fd.get("imap_host"),
    imap_port: Number(fd.get("imap_port")),
    username: fd.get("username"),
    password: fd.get("password"),
    mailboxes: String(fd.get("mailboxes"))
      .split(",")
      .map((m) => m.trim())
      .filter(Boolean),
    per_mailbox_limit: Number(fd.get("per_mailbox_limit")),
    model: fd.get("model"),
    user_hint: fd.get("user_hint") || null,
  };

  const status = $("#gen-status");
  const btn = $("#gen-btn");
  btn.disabled = true;
  status.textContent = "Fetching emails & generating persona...";

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed");
    status.textContent = `Done. Analyzed ${data.email_count} emails.`;
    personaView.textContent = data.persona_md;
  } catch (err) {
    status.textContent = `Error: ${err.message}`;
  } finally {
    btn.disabled = false;
  }
});

function addMsg(role, content) {
  const div = document.createElement("div");
  div.className = `msg ${role === "user" ? "user" : "bot"}`;
  div.textContent = content;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

$("#chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = $("#chat-input");
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  addMsg("user", message);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history: chatHistory }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed");
    addMsg("bot", data.reply);
    chatHistory.push({ role: "user", content: message });
    chatHistory.push({ role: "assistant", content: data.reply });
  } catch (err) {
    addMsg("bot", `[error] ${err.message}`);
  }
});

loadPersona();
