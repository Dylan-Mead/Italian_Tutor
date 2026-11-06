(() => {
  const messagesEl = document.getElementById("messages");
  const formEl = document.getElementById("chat-form");
  const inputEl = document.getElementById("chat-input");
  const sendBtn = document.getElementById("send-btn");
  const saveBtn = document.getElementById("save-btn");
  const resetBtn = document.getElementById("reset-btn");
  const warningEl = document.getElementById("warning");
  const sidebarToggle = document.getElementById("sidebar-toggle");
  const sidebar = document.getElementById("sidebar");

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function appendMessage(role, text) {
    const div = document.createElement("div");
    div.className = `message ${role}`;
    div.textContent = text;
    messagesEl.appendChild(div);
    scrollToBottom();
    return div;
  }

  function showWarning(text) {
    warningEl.textContent = text;
    warningEl.classList.remove("hidden");
  }

  function clearWarning() {
    warningEl.classList.add("hidden");
    warningEl.textContent = "";
  }

  function setBusy(busy) {
    sendBtn.disabled = busy;
    saveBtn.disabled = busy;
    resetBtn.disabled = busy;
    inputEl.disabled = busy;
  }

  function renderPills(container, items, extraClass) {
    container.innerHTML = "";
    (items || []).forEach((item) => {
      const span = document.createElement("span");
      span.className = extraClass ? `pill ${extraClass}` : "pill";
      span.textContent = item;
      container.appendChild(span);
    });
  }

  function renderMemory(mem) {
    document.getElementById("mem-level").textContent = mem.proficiency_level || "Unknown";
    renderPills(document.getElementById("mem-learned"), mem.learned_vocabulary);
    renderPills(document.getElementById("mem-struggled"), mem.struggled_vocabulary, "struggle");
    renderPills(document.getElementById("mem-concepts"), mem.grammar_concepts_mastered);
    document.getElementById("mem-notes").textContent = mem.session_notes || "";
  }

  async function refreshMemory() {
    try {
      const res = await fetch("/api/memory");
      if (res.ok) {
        renderMemory(await res.json());
      }
    } catch (err) {
      // Non-fatal: the sidebar just won't refresh this round.
      console.error("Failed to refresh memory", err);
    }
  }

  async function sendMessage(text) {
    clearWarning();
    appendMessage("user", text);
    setBusy(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });

      const contentType = res.headers.get("Content-Type") || "";

      if (contentType.includes("application/json")) {
        const data = await res.json();
        if (data.blocked) {
          showWarning(`⚠️ Message blocked by the prompt firewall (verdict: ${data.verdict}). Please rephrase and try again.`);
        } else if (data.error) {
          showWarning(`⚠️ ${data.error}`);
        }
        return;
      }

      if (!res.ok || !res.body) {
        showWarning("⚠️ Something went wrong talking to Paolo. Please try again.");
        return;
      }

      const bubble = appendMessage("assistant", "");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        bubble.textContent += decoder.decode(value, { stream: true });
        scrollToBottom();
      }

      refreshMemory();
    } catch (err) {
      console.error(err);
      showWarning("⚠️ Lost connection to the server. Please try again.");
    } finally {
      setBusy(false);
      inputEl.focus();
    }
  }

  formEl.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = inputEl.value.trim();
    if (!text) return;
    inputEl.value = "";
    inputEl.style.height = "auto";
    sendMessage(text);
  });

  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      formEl.requestSubmit();
    }
  });

  inputEl.addEventListener("input", () => {
    inputEl.style.height = "auto";
    inputEl.style.height = `${Math.min(inputEl.scrollHeight, 128)}px`;
  });

  saveBtn.addEventListener("click", async () => {
    clearWarning();
    setBusy(true);
    try {
      const res = await fetch("/api/save", { method: "POST" });
      if (res.ok) {
        renderMemory(await res.json());
        appendMessage("assistant", "✅ Progress saved.");
      } else {
        showWarning("⚠️ Failed to save progress.");
      }
    } catch (err) {
      console.error(err);
      showWarning("⚠️ Failed to save progress.");
    } finally {
      setBusy(false);
    }
  });

  resetBtn.addEventListener("click", async () => {
    clearWarning();
    setBusy(true);
    try {
      const res = await fetch("/api/reset", { method: "POST" });
      if (res.ok) {
        const mem = await res.json();
        renderMemory(mem);
        messagesEl.innerHTML = "";
        appendMessage("assistant", `Ciao di nuovo! Ricominciamo. (Level: ${mem.proficiency_level})`);
      } else {
        showWarning("⚠️ Failed to start a new conversation.");
      }
    } catch (err) {
      console.error(err);
      showWarning("⚠️ Failed to start a new conversation.");
    } finally {
      setBusy(false);
    }
  });

  sidebarToggle.addEventListener("click", () => {
    sidebar.classList.toggle("open");
  });

  refreshMemory();
  scrollToBottom();
  inputEl.focus();
})();
