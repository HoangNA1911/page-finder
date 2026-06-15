from starlette.responses import HTMLResponse


CHATBOT_UI_HTML = r"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Pagefinder Chat</title>
    <style>
      :root {
        color-scheme: dark;
        --bg: #0b1020;
        --panel: rgba(15, 23, 42, 0.78);
        --panel-strong: rgba(15, 23, 42, 0.92);
        --border: rgba(148, 163, 184, 0.18);
        --text: #e5eefb;
        --muted: #94a3b8;
        --accent: #22c55e;
        --accent-soft: rgba(34, 197, 94, 0.14);
        --assistant: rgba(59, 130, 246, 0.12);
        --user: linear-gradient(135deg, #2563eb 0%, #22c55e 100%);
        --shadow: 0 24px 80px rgba(2, 6, 23, 0.45);
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        min-height: 100vh;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: var(--text);
        background:
          radial-gradient(circle at top, rgba(59, 130, 246, 0.22), transparent 28%),
          radial-gradient(circle at right, rgba(34, 197, 94, 0.12), transparent 24%),
          linear-gradient(180deg, #020617 0%, #0f172a 52%, #020617 100%);
      }

      .shell {
        display: grid;
        grid-template-columns: 280px minmax(0, 1fr);
        gap: 20px;
        min-height: 100vh;
        padding: 20px;
      }

      .sidebar,
      .chat {
        border: 1px solid var(--border);
        background: var(--panel);
        backdrop-filter: blur(18px);
        box-shadow: var(--shadow);
      }

      .sidebar {
        border-radius: 28px;
        padding: 22px;
        display: flex;
        flex-direction: column;
        gap: 18px;
      }

      .brand {
        display: flex;
        flex-direction: column;
        gap: 10px;
      }

      .brand-badge {
        width: 42px;
        height: 42px;
        border-radius: 14px;
        display: grid;
        place-items: center;
        background: linear-gradient(135deg, #2563eb, #22c55e);
        font-weight: 700;
      }

      .brand h1 {
        margin: 0;
        font-size: 1.2rem;
      }

      .brand p,
      .meta,
      .hint {
        margin: 0;
        color: var(--muted);
        line-height: 1.5;
      }

      .pill-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
      }

      .pill {
        border: 1px solid var(--border);
        background: rgba(15, 23, 42, 0.55);
        color: var(--text);
        border-radius: 999px;
        padding: 10px 14px;
        cursor: pointer;
        transition: 160ms ease;
      }

      .pill:hover {
        border-color: rgba(96, 165, 250, 0.4);
        transform: translateY(-1px);
      }

      .meta-block {
        padding: 14px;
        border-radius: 18px;
        background: rgba(2, 6, 23, 0.34);
        border: 1px solid rgba(148, 163, 184, 0.12);
      }

      .chat {
        border-radius: 32px;
        display: grid;
        grid-template-rows: auto minmax(0, 1fr) auto;
        overflow: hidden;
      }

      .chat-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 24px 28px 18px;
        border-bottom: 1px solid var(--border);
        background: linear-gradient(180deg, rgba(15, 23, 42, 0.9), rgba(15, 23, 42, 0.68));
      }

      .chat-header h2 {
        margin: 0;
        font-size: 1.05rem;
      }

      .chat-header .meta {
        font-size: 0.92rem;
      }

      .messages {
        overflow-y: auto;
        padding: 28px;
        display: flex;
        flex-direction: column;
        gap: 18px;
      }

      .message {
        max-width: min(760px, 88%);
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .message.user {
        align-self: flex-end;
      }

      .message.assistant {
        align-self: flex-start;
      }

      .message-label {
        font-size: 0.8rem;
        color: var(--muted);
        letter-spacing: 0.02em;
      }

      .bubble {
        border-radius: 24px;
        padding: 16px 18px;
        line-height: 1.6;
        white-space: pre-wrap;
        word-break: break-word;
      }

      .message.user .bubble {
        background: var(--user);
        color: white;
        border-bottom-right-radius: 8px;
      }

      .message.assistant .bubble {
        background: var(--assistant);
        border: 1px solid rgba(96, 165, 250, 0.14);
        border-bottom-left-radius: 8px;
      }

      /* Rendered Markdown inside assistant bubbles */
      .bubble.md {
        white-space: normal;
      }

      .bubble.md > :first-child { margin-top: 0; }
      .bubble.md > :last-child { margin-bottom: 0; }

      .bubble.md p { margin: 0 0 10px; }

      .bubble.md h1,
      .bubble.md h2,
      .bubble.md h3,
      .bubble.md h4 {
        margin: 14px 0 8px;
        line-height: 1.3;
      }

      .bubble.md h1 { font-size: 1.18rem; }
      .bubble.md h2 { font-size: 1.08rem; }
      .bubble.md h3 { font-size: 1rem; }
      .bubble.md h4 { font-size: 0.95rem; }

      .bubble.md ul,
      .bubble.md ol {
        margin: 6px 0 10px;
        padding-left: 22px;
      }

      .bubble.md li { margin: 3px 0; }

      .bubble.md strong { color: #ffffff; }

      .bubble.md a {
        color: #7cc4ff;
        text-decoration: underline;
        word-break: break-all;
      }

      .bubble.md code {
        background: rgba(2, 6, 23, 0.5);
        padding: 1px 6px;
        border-radius: 6px;
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: 0.88em;
      }

      .bubble.md pre {
        background: rgba(2, 6, 23, 0.55);
        border: 1px solid var(--border);
        padding: 12px 14px;
        border-radius: 12px;
        overflow-x: auto;
        margin: 8px 0;
      }

      .bubble.md pre code {
        background: transparent;
        padding: 0;
        font-size: 0.86em;
      }

      .bubble.md blockquote {
        margin: 8px 0;
        padding: 4px 12px;
        border-left: 3px solid var(--accent);
        color: var(--muted);
      }

      .bubble.md hr {
        border: 0;
        border-top: 1px solid var(--border);
        margin: 12px 0;
      }

      .session-line {
        margin-top: auto;
        font-size: 0.76rem;
        opacity: 0.65;
        word-break: break-all;
      }

      .composer-wrap {
        padding: 20px;
        border-top: 1px solid var(--border);
        background: rgba(15, 23, 42, 0.82);
      }

      .composer {
        border: 1px solid var(--border);
        background: var(--panel-strong);
        border-radius: 24px;
        padding: 14px;
        display: grid;
        gap: 12px;
      }

      textarea {
        width: 100%;
        resize: none;
        min-height: 84px;
        max-height: 220px;
        border: 0;
        outline: 0;
        background: transparent;
        color: var(--text);
        font: inherit;
      }

      textarea::placeholder {
        color: #7c8aa5;
      }

      .composer-actions {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
      }

      .status {
        color: var(--muted);
        font-size: 0.9rem;
      }

      .send {
        border: 0;
        background: linear-gradient(135deg, #2563eb 0%, #22c55e 100%);
        color: white;
        padding: 12px 18px;
        border-radius: 14px;
        font: inherit;
        font-weight: 600;
        cursor: pointer;
      }

      .send:disabled {
        cursor: not-allowed;
        opacity: 0.6;
      }

      .typing::after {
        content: "...";
        display: inline-block;
        width: 18px;
        overflow: hidden;
        vertical-align: bottom;
        animation: dots 1.1s steps(4, end) infinite;
      }

      @keyframes dots {
        from { width: 0; }
        to { width: 18px; }
      }

      @media (max-width: 960px) {
        .shell {
          grid-template-columns: 1fr;
          padding: 14px;
        }

        .sidebar {
          order: 2;
          border-radius: 22px;
        }

        .chat {
          min-height: 76vh;
          border-radius: 24px;
        }

        .messages,
        .chat-header {
          padding-left: 18px;
          padding-right: 18px;
        }

        .message {
          max-width: 100%;
        }
      }
    </style>
  </head>
  <body>
    <div class="shell">
      <aside class="sidebar">
        <div class="brand">
          <div class="brand-badge">P</div>
          <div>
            <h1>Pagefinder</h1>
            <p class="meta">Trợ lý hỏi đáp tài liệu Confluence.</p>
          </div>
        </div>

        <div class="meta-block">
          <p class="hint">Gợi ý</p>
          <div class="pill-grid">
            <button class="pill" data-prompt="Tóm tắt tài liệu hiện có">Tóm tắt tài liệu</button>
            <button class="pill" data-prompt="Có document nào vừa được update không?">Kiểm tra update</button>
            <button class="pill" data-prompt="Liệt kê các ghi chú tôi đã lưu">Ghi chú của tôi</button>
          </div>
        </div>

        <p class="meta session-line" id="session-meta"></p>
      </aside>

      <main class="chat">
        <div class="chat-header">
          <div>
            <h2>Chat with your docs</h2>
            <p class="meta">Ask about indexed Confluence pages, updates, notes, or summaries.</p>
          </div>
          <button class="pill" id="reset-session">New chat</button>
        </div>

        <div class="messages" id="messages"></div>

        <div class="composer-wrap">
          <form class="composer" id="chat-form">
            <textarea id="prompt" placeholder="Message Pagefinder..."></textarea>
            <div class="composer-actions">
              <div class="status" id="status">Ready</div>
              <button class="send" id="send" type="submit">Send</button>
            </div>
          </form>
        </div>
      </main>
    </div>

    <script>
      const messagesEl = document.getElementById("messages");
      const formEl = document.getElementById("chat-form");
      const promptEl = document.getElementById("prompt");
      const sendEl = document.getElementById("send");
      const statusEl = document.getElementById("status");
      const sessionMetaEl = document.getElementById("session-meta");
      const resetEl = document.getElementById("reset-session");

      function uuid() {
        return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function(char) {
          const rand = Math.random() * 16 | 0;
          const value = char === "x" ? rand : (rand & 0x3 | 0x8);
          return value.toString(16);
        });
      }

      function ensureIdentity() {
        let userId = localStorage.getItem("pagefinder-user-id");
        let sessionId = localStorage.getItem("pagefinder-session-id");
        if (!userId) {
          userId = "web-user-" + uuid().slice(0, 12);
          localStorage.setItem("pagefinder-user-id", userId);
        }
        if (!sessionId) {
          sessionId = "web-session-" + uuid().slice(0, 12);
          localStorage.setItem("pagefinder-session-id", sessionId);
        }
        sessionMetaEl.textContent = userId + " / " + sessionId;
        return { userId, sessionId };
      }

      function newSession() {
        localStorage.setItem("pagefinder-session-id", "web-session-" + uuid().slice(0, 12));
        messagesEl.innerHTML = "";
        ensureIdentity();
        seedMessages();
      }

      function escapeHtml(value) {
        return value
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;");
      }

      function renderInline(text) {
        // `text` is already HTML-escaped. Protect inline code spans first.
        const codes = [];
        text = text.replace(/`([^`]+)`/g, function(_, code) {
          codes.push(code);
          return "{{{CODE" + (codes.length - 1) + "}}}";
        });
        // Markdown links [label](http...)
        text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, function(_, label, url) {
          return '<a href="' + url.replace(/"/g, "%22") + '" target="_blank" rel="noopener">' + label + "</a>";
        });
        text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
        text = text.replace(/__([^_]+)__/g, "<strong>$1</strong>");
        text = text.replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
        // Auto-link bare URLs that are not already inside an href.
        text = text.replace(/(^|[\s(])(https?:\/\/[^\s<)]+)/g, function(_, pre, url) {
          return pre + '<a href="' + url.replace(/"/g, "%22") + '" target="_blank" rel="noopener">' + url + "</a>";
        });
        text = text.replace(/\{\{\{CODE(\d+)\}\}\}/g, function(_, index) {
          return "<code>" + codes[+index] + "</code>";
        });
        return text;
      }

      function renderMarkdown(src) {
        const lines = escapeHtml((src || "").replace(/\r\n/g, "\n")).split("\n");
        let html = "";
        let listType = null;
        let para = [];

        function flushPara() {
          if (para.length) {
            html += "<p>" + renderInline(para.join("<br>")) + "</p>";
            para = [];
          }
        }
        function closeList() {
          if (listType) { html += "</" + listType + ">"; listType = null; }
        }

        for (let i = 0; i < lines.length; i++) {
          const line = lines[i];
          if (/^\s*```/.test(line)) {
            flushPara(); closeList();
            const code = [];
            i++;
            while (i < lines.length && !/^\s*```/.test(lines[i])) { code.push(lines[i]); i++; }
            html += "<pre><code>" + code.join("\n") + "</code></pre>";
            continue;
          }
          if (/^\s*$/.test(line)) { flushPara(); closeList(); continue; }
          const heading = line.match(/^\s*(#{1,6})\s+(.*)$/);
          if (heading) {
            flushPara(); closeList();
            const level = heading[1].length;
            html += "<h" + level + ">" + renderInline(heading[2].trim()) + "</h" + level + ">";
            continue;
          }
          if (/^\s*([-*_])\1\1+\s*$/.test(line)) { flushPara(); closeList(); html += "<hr>"; continue; }
          const quote = line.match(/^\s*&gt;\s?(.*)$/);
          if (quote) {
            flushPara(); closeList();
            html += "<blockquote>" + renderInline(quote[1]) + "</blockquote>";
            continue;
          }
          const unordered = line.match(/^\s*[-*+]\s+(.*)$/);
          if (unordered) {
            flushPara();
            if (listType !== "ul") { closeList(); html += "<ul>"; listType = "ul"; }
            html += "<li>" + renderInline(unordered[1]) + "</li>";
            continue;
          }
          const ordered = line.match(/^\s*\d+[.)]\s+(.*)$/);
          if (ordered) {
            flushPara();
            if (listType !== "ol") { closeList(); html += "<ol>"; listType = "ol"; }
            html += "<li>" + renderInline(ordered[1]) + "</li>";
            continue;
          }
          closeList();
          para.push(line.trim());
        }
        flushPara(); closeList();
        return html;
      }

      function addMessage(role, text) {
        const wrapper = document.createElement("div");
        wrapper.className = "message " + role;

        const label = document.createElement("div");
        label.className = "message-label";
        label.textContent = role === "user" ? "You" : "Pagefinder";

        const bubble = document.createElement("div");
        bubble.className = "bubble";
        if (role === "assistant") {
          bubble.classList.add("md");
          bubble.innerHTML = renderMarkdown(text);
        } else {
          bubble.textContent = text;
        }

        wrapper.appendChild(label);
        wrapper.appendChild(bubble);
        messagesEl.appendChild(wrapper);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        return bubble;
      }

      function setBusy(isBusy) {
        sendEl.disabled = isBusy;
        promptEl.disabled = isBusy;
        statusEl.textContent = isBusy ? "Thinking" : "Ready";
        statusEl.classList.toggle("typing", isBusy);
      }

      async function sendPrompt(message) {
        const trimmed = message.trim();
        if (!trimmed) return;

        const identity = ensureIdentity();
        addMessage("user", trimmed);
        promptEl.value = "";
        promptEl.style.height = "84px";
        setBusy(true);

        const bubble = addMessage("assistant", "");
        bubble.textContent = "Đang trả lời";
        bubble.classList.add("typing");

        try {
          const response = await fetch("/invocations", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-GreenNode-AgentBase-User-Id": identity.userId,
              "X-GreenNode-AgentBase-Session-Id": identity.sessionId,
            },
            body: JSON.stringify({ message: trimmed }),
          });
          const payload = await response.json();
          bubble.classList.remove("typing");
          bubble.innerHTML = renderMarkdown(payload.response || payload.error || "No response returned.");
        } catch (error) {
          bubble.classList.remove("typing");
          bubble.textContent = "Could not reach /invocations. Check that the runtime is running and the API is accessible.";
        } finally {
          setBusy(false);
          promptEl.focus();
        }
      }

      function seedMessages() {
        addMessage("assistant", "Xin chào. Tôi là Pagefinder. Hãy hỏi tôi về tài liệu Confluence, yêu cầu tóm tắt, kiểm tra cập nhật, hoặc tìm đúng page bạn cần.");
      }

      formEl.addEventListener("submit", function(event) {
        event.preventDefault();
        sendPrompt(promptEl.value);
      });

      promptEl.addEventListener("keydown", function(event) {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          formEl.requestSubmit();
        }
      });

      promptEl.addEventListener("input", function() {
        promptEl.style.height = "84px";
        promptEl.style.height = Math.min(promptEl.scrollHeight, 220) + "px";
      });

      resetEl.addEventListener("click", newSession);

      document.querySelectorAll("[data-prompt]").forEach(function(button) {
        button.addEventListener("click", function() {
          promptEl.value = button.dataset.prompt;
          promptEl.focus();
        });
      });

      ensureIdentity();
      seedMessages();
      promptEl.focus();
    </script>
  </body>
</html>
"""


def render_chatbot_ui() -> str:
    return CHATBOT_UI_HTML


def register_ui_routes(app: object) -> None:
    async def ui_handler(*_args, **_kwargs):
        return HTMLResponse(render_chatbot_ui())

    targets = [app, getattr(app, "app", None)]

    for target in targets:
        if target is None:
            continue

        try:
            existing_paths = {getattr(route, "path", None) for route in getattr(target, "routes", [])}
            if "/" in existing_paths:
                return

            if hasattr(target, "add_route"):
                target.add_route("/", ui_handler, methods=["GET"])
                return
            if hasattr(target, "route"):
                try:
                    target.route("/", methods=["GET"])(ui_handler)
                    return
                except TypeError:
                    target.route("/")(ui_handler)
                    return
            if hasattr(target, "get"):
                target.get("/")(ui_handler)
                return
            if hasattr(target, "add_api_route"):
                target.add_api_route("/", ui_handler, methods=["GET"])
                return
        except Exception:
            continue
