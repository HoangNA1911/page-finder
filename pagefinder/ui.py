from starlette.responses import HTMLResponse


CHATBOT_UI_HTML = r"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Pagefinder</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap"
      rel="stylesheet"
    />
    <style>
      :root {
        color-scheme: light;
        --bg: #d0e9ec;
        --panel: #ffffff;
        --panel-strong: #ffffff;
        --surface: #ffffff;
        --messages-bg: #e6f4f6;
        --border: rgba(15, 64, 72, 0.10);
        --border-strong: rgba(15, 64, 72, 0.18);
        --text: #103a40;
        --muted: #5a868c;
        --accent: #13b5c4;
        --accent-hover: #0e9fae;
        --accent-soft: rgba(19, 181, 196, 0.14);
        --accent-line: rgba(19, 181, 196, 0.35);
        --ink-on-accent: #ffffff;
        --shadow: 0 10px 30px rgba(15, 64, 72, 0.10);
        --assistant: #ffffff;
        --font-display: "Space Grotesk", "Inter", ui-sans-serif, system-ui, sans-serif;
        --font-body: "Inter", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        --font-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
        --sidebar-w: 320px;
      }

      /* Dark = neutral charcoal-slate (no teal tint on surfaces); teal is ACCENT only. */
      [data-theme="dark"] {
        color-scheme: dark;
        --bg: #161922;
        --panel: #222732;
        --panel-strong: #222732;
        --surface: #2c323e;
        --messages-bg: #1b1f29;
        --border: rgba(255, 255, 255, 0.10);
        --border-strong: rgba(255, 255, 255, 0.18);
        --text: #e9ebef;
        --muted: #a3a9b4;
        --accent: #2ec6d4;
        --accent-hover: #45d4e1;
        --accent-soft: rgba(46, 198, 212, 0.16);
        --accent-line: rgba(46, 198, 212, 0.38);
        --ink-on-accent: #06292e;
        --shadow: 0 14px 40px rgba(0, 0, 0, 0.5);
      }

      /* Assistant bubble is a dark card → markdown inside uses light text. */
      [data-theme="dark"] .bubble.md strong { color: #f1fbfb; }
      [data-theme="dark"] .bubble.md code {
        background: rgba(255, 255, 255, 0.09);
        color: #7ee6f1;
      }
      [data-theme="dark"] .bubble.md pre { background: #161922; }
      [data-theme="dark"] .messages::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.16);
      }
      [data-theme="dark"] .messages::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 255, 255, 0.28);
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        min-height: 100vh;
        font-family: var(--font-body);
        font-size: 15.5px;
        color: var(--text);
        background: var(--bg);
      }

      /* Antialiasing makes light strokes on a light background look too thin;
         keep the fuller default rendering in light mode, antialias only in dark. */
      [data-theme="dark"] body {
        -webkit-font-smoothing: antialiased;
      }

      .sidebar,
      .chat {
        box-shadow: var(--shadow);
      }

      .shell {
        display: grid;
        grid-template-columns: var(--sidebar-w) 8px minmax(0, 1fr);
        gap: 6px;
        height: 100vh;
        padding: 20px;
        overflow: hidden;
      }

      .sidebar,
      .chat {
        border: 1px solid var(--border);
        background: var(--panel);
      }

      .sidebar {
        border-radius: 16px;
        padding: 24px;
        display: flex;
        flex-direction: column;
        gap: 20px;
      }

      .brand {
        display: flex;
        flex-direction: column;
        gap: 12px;
      }

      .brand-badge {
        width: 48px;
        height: 48px;
        border-radius: 15px;
        display: grid;
        place-items: center;
        background: linear-gradient(150deg, #2ad4e0 0%, #13b5c4 52%, #0c93a2 100%);
        color: #ffffff;
        font-family: var(--font-display);
        font-weight: 700;
        font-size: 1.5rem;
        line-height: 1;
        text-shadow: 0 1px 2px rgba(7, 60, 54, 0.35);
        box-shadow:
          0 10px 22px rgba(18, 130, 118, 0.4),
          inset 0 1px 0 rgba(255, 255, 255, 0.55),
          inset 0 0 0 1px rgba(255, 255, 255, 0.12);
      }

      .brand h1 {
        margin: 0 0 7px;
        font-family: var(--font-display);
        font-size: 1.55rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        line-height: 1.05;
        color: var(--text);
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
        background: var(--messages-bg);
        color: var(--text);
        border-radius: 8px;
        padding: 9px 14px;
        font-size: 0.85rem;
        font-weight: 600;
        cursor: pointer;
        transition: border-color 140ms ease, color 140ms ease, background 140ms ease;
      }

      .pill:hover {
        border-color: var(--accent);
        color: var(--accent);
        background: var(--accent-soft);
      }

      .meta-block {
        padding: 16px;
        border-radius: 12px;
        background: var(--messages-bg);
        border: 1px solid var(--border);
      }

      .cap-list {
        list-style: none;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 11px;
      }
      .cap-list li {
        display: flex;
        gap: 9px;
        align-items: flex-start;
        font-size: 0.86rem;
        line-height: 1.4;
        color: var(--text);
      }
      .cap-list li span {
        flex: none;
        font-size: 1rem;
        line-height: 1.3;
      }

      .sidebar-foot {
        margin-top: auto;
        font-size: 0.78rem;
        opacity: 0.85;
      }

      .hint {
        text-transform: uppercase;
        letter-spacing: 0.14em;
        font-size: 0.7rem;
        font-weight: 600;
        margin-bottom: 12px !important;
        color: var(--muted);
      }

      .chat {
        border-radius: 16px;
        display: grid;
        grid-template-rows: auto minmax(0, 1fr) auto;
        overflow: hidden;
      }

      .chat-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 22px 28px 20px;
        border-bottom: 1px solid var(--border);
        background: transparent;
      }

      .chat-header h2 {
        margin: 0 0 4px;
        font-family: var(--font-display);
        font-size: 1.25rem;
        font-weight: 600;
        letter-spacing: -0.015em;
      }

      .chat-header .meta {
        font-size: 0.92rem;
      }

      .messages {
        overflow-y: auto;
        padding: 24px 28px;
        display: flex;
        flex-direction: column;
        gap: 16px;
        background: var(--messages-bg);
      }

      .message {
        max-width: min(680px, 80%);
        display: flex;
        flex-direction: column;
        gap: 6px;
        animation: rise 280ms cubic-bezier(0.22, 1, 0.36, 1) both;
      }

      @keyframes rise {
        from { opacity: 0; transform: translateY(10px); }
        to   { opacity: 1; transform: translateY(0); }
      }

      .message.user {
        align-self: flex-end;
      }

      .message.assistant {
        align-self: flex-start;
      }

      .message-label {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--muted);
        padding: 0 6px;
      }

      .message.user .message-label {
        text-align: right;
      }

      .bubble {
        border-radius: 16px;
        padding: 11px 15px;
        line-height: 1.6;
        white-space: pre-wrap;
        word-break: break-word;
      }

      .message.user .bubble {
        background: var(--accent);
        color: var(--ink-on-accent);
        border-bottom-right-radius: 6px;
        box-shadow: 0 4px 14px rgba(19, 181, 196, 0.28);
      }

      .message.assistant .bubble {
        background: var(--surface);
        border: 1px solid var(--border);
        border-bottom-left-radius: 6px;
        box-shadow: 0 4px 14px rgba(15, 64, 72, 0.08);
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
        font-family: var(--font-display);
        font-weight: 600;
        letter-spacing: -0.01em;
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

      .bubble.md strong { color: #0c2c28; font-weight: 600; }

      .bubble.md table {
        border-collapse: collapse;
        width: 100%;
        margin: 8px 0;
        font-size: 0.9em;
        display: block;
        overflow-x: auto;
      }
      .bubble.md th,
      .bubble.md td {
        border: 1px solid var(--border);
        padding: 6px 10px;
        text-align: left;
        vertical-align: top;
      }
      .bubble.md th { background: var(--messages-bg); font-weight: 600; }

      .bubble.md a {
        color: var(--accent);
        text-decoration: underline;
        text-underline-offset: 2px;
        word-break: break-all;
      }

      .bubble.md code {
        background: rgba(15, 64, 72, 0.08);
        color: #0c8a96;
        padding: 1px 6px;
        border-radius: 5px;
        font-family: var(--font-mono);
        font-size: 0.84em;
      }

      .bubble.md pre {
        background: #f1f8f7;
        border: 1px solid var(--border);
        padding: 12px 14px;
        border-radius: 10px;
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
        padding: 18px 28px;
        border-top: 1px solid var(--border);
        background: transparent;
      }

      .composer {
        border: 1px solid var(--border);
        background: var(--messages-bg);
        border-radius: 12px;
        padding: 14px 16px;
        display: grid;
        gap: 12px;
        transition: border-color 160ms ease;
      }

      .composer:focus-within {
        border-color: var(--accent);
      }

      textarea {
        width: 100%;
        resize: none;
        min-height: 46px;
        max-height: 200px;
        border: 0;
        outline: 0;
        background: transparent;
        color: var(--text);
        font-family: var(--font-body);
        font-size: 0.97rem;
        line-height: 1.55;
      }

      textarea::placeholder {
        color: #93ada8;
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
        background: var(--accent);
        color: var(--ink-on-accent);
        padding: 10px 22px;
        border-radius: 12px;
        font-family: var(--font-display);
        font-size: 0.9rem;
        font-weight: 600;
        cursor: pointer;
        transition: background 140ms ease;
      }

      .send:hover:not(:disabled) {
        background: var(--accent-hover);
      }

      .send:disabled {
        cursor: not-allowed;
        opacity: 0.4;
      }

      .send.stop {
        background: #64748b;
        color: #fff;
      }
      .send.stop:hover { background: #515e72; }

      .messages::-webkit-scrollbar {
        width: 10px;
      }

      .messages::-webkit-scrollbar-thumb {
        background: rgba(15, 64, 72, 0.18);
        border-radius: 999px;
        border: 3px solid transparent;
        background-clip: padding-box;
      }

      .messages::-webkit-scrollbar-thumb:hover {
        background: rgba(15, 64, 72, 0.30);
        background-clip: padding-box;
      }

      .typing::after {
        content: "...";
        display: inline-block;
        width: 1.4em;
        text-align: left;
        white-space: nowrap;
        overflow: hidden;
        vertical-align: bottom;
        animation: dots 1.2s steps(1, end) infinite;
      }

      @keyframes dots {
        0%   { content: "."; }
        33%  { content: ".."; }
        66%  { content: "..."; }
      }

      .bubble.loading {
        display: inline-flex;
        align-items: center;
        align-self: flex-start;
        min-height: 1.2em;
      }
      .dot-typing {
        display: inline-flex;
        align-items: center;
        gap: 5px;
      }
      .dot-typing span {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--muted);
        animation: dotbounce 1.3s infinite ease-in-out both;
      }
      .dot-typing span:nth-child(2) { animation-delay: 0.16s; }
      .dot-typing span:nth-child(3) { animation-delay: 0.32s; }
      @keyframes dotbounce {
        0%, 70%, 100% { transform: translateY(0); opacity: 0.35; }
        35% { transform: translateY(-5px); opacity: 1; }
      }

      .resizer {
        align-self: stretch;
        position: relative;
        width: 8px;
        cursor: col-resize;
        background: transparent;
        touch-action: none;
      }

      .resizer::before {
        content: "";
        position: absolute;
        top: 0;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 2px;
        border-radius: 999px;
        background: var(--border-strong);
        transition: background 140ms ease, width 140ms ease;
      }

      .resizer:hover::before,
      .resizer.dragging::before {
        width: 3px;
        background: var(--accent);
      }

      .header-actions {
        display: flex;
        align-items: center;
        gap: 10px;
      }

      .icon-btn {
        display: grid;
        place-items: center;
        width: 38px;
        height: 38px;
        padding: 0;
        border: 1px solid var(--border);
        background: var(--messages-bg);
        color: var(--text);
        border-radius: 10px;
        cursor: pointer;
        transition: border-color 140ms ease, color 140ms ease, background 140ms ease;
      }

      .icon-btn:hover {
        border-color: var(--accent);
        color: var(--accent);
        background: var(--accent-soft);
      }

      .icon-btn svg {
        width: 18px;
        height: 18px;
      }

      .icon-btn .moon { display: none; }
      [data-theme="dark"] .icon-btn .sun { display: none; }
      [data-theme="dark"] .icon-btn .moon { display: block; }

      @media (max-width: 960px) {
        .shell {
          grid-template-columns: 1fr;
          padding: 14px;
          height: auto;
          overflow: visible;
        }

        .resizer { display: none; }

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
          <div class="brand-badge" aria-label="Pagefinder">P</div>
          <div>
            <h1>Pagefinder</h1>
            <p class="meta">Trợ lý hỏi đáp tài liệu Confluence</p>
          </div>
        </div>

        <div class="meta-block">
          <p class="hint">Gợi ý</p>
          <div class="pill-grid">
            <button class="pill" data-prompt="Liệt kê tất cả tài liệu hiện có">Tất cả tài liệu</button>
            <button class="pill" data-prompt="Tóm tắt tài liệu hiện có">Tóm tắt tài liệu</button>
            <button class="pill" data-prompt="Có document nào vừa được update không?">Kiểm tra update</button>
            <button class="pill" data-prompt="Liệt kê các ghi chú tôi đã lưu">Ghi chú của tôi</button>
          </div>
        </div>

        <div class="meta-block">
          <p class="hint">Mình giúp được gì</p>
          <ul class="cap-list">
            <li><span>🔍</span> Tìm kiếm trong tài liệu đã index</li>
            <li><span>📄</span> Tóm gọn nhanh một trang dài</li>
            <li><span>🔔</span> Cho biết tài liệu nào vừa cập nhật</li>
            <li><span>📝</span> Lưu &amp; xem lại ghi chú cá nhân</li>
          </ul>
        </div>

        <p class="meta sidebar-foot">Gõ câu hỏi bên phải, hoặc bấm một gợi ý để bắt đầu.</p>

      </aside>

      <div class="resizer" id="resizer" role="separator" aria-orientation="vertical" aria-label="Resize sidebar"></div>

      <main class="chat">
        <div class="chat-header">
          <div>
            <h2>Chat with your docs</h2>
            <p class="meta">Ask about indexed Confluence pages, updates, notes, or summaries</p>
          </div>
          <div class="header-actions">
            <button class="icon-btn" id="theme-toggle" type="button" aria-label="Đổi giao diện sáng/tối" title="Sáng / Tối">
              <svg class="sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="4" />
                <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
              </svg>
              <svg class="moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              </svg>
            </button>
            <button class="pill" id="reset-session">New chat</button>
          </div>
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
        if (sessionMetaEl) sessionMetaEl.textContent = userId + " / " + sessionId;
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
        function isTableSep(s) {
          return s.indexOf("|") !== -1 && /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(s);
        }
        function splitRow(s) {
          let t = s.trim();
          if (t.charAt(0) === "|") t = t.slice(1);
          if (t.charAt(t.length - 1) === "|") t = t.slice(0, -1);
          return t.split("|").map(function (c) { return c.trim(); });
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
          if (line.indexOf("|") !== -1 && i + 1 < lines.length && isTableSep(lines[i + 1])) {
            flushPara(); closeList();
            let t = "<table><thead><tr>";
            for (const c of splitRow(line)) t += "<th>" + renderInline(c) + "</th>";
            t += "</tr></thead><tbody>";
            i += 2;
            while (i < lines.length && lines[i].indexOf("|") !== -1 && !/^\s*$/.test(lines[i])) {
              t += "<tr>";
              for (const c of splitRow(lines[i])) t += "<td>" + renderInline(c) + "</td>";
              t += "</tr>";
              i++;
            }
            i--;
            html += t + "</tbody></table>";
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

      let pendingController = null;
      const sentHistory = [];
      let histPos = -1; // -1 = not navigating history

      function setPromptValue(value) {
        promptEl.value = value;
        promptEl.style.height = "46px";
        promptEl.style.height = Math.min(promptEl.scrollHeight, 200) + "px";
        const end = value.length;
        promptEl.setSelectionRange(end, end);
      }

      function setBusy(isBusy) {
        promptEl.disabled = isBusy;
        // Keep the button clickable while busy so it can cancel the request.
        sendEl.disabled = false;
        sendEl.textContent = isBusy ? "Stop" : "Send";
        sendEl.classList.toggle("stop", isBusy);
        statusEl.textContent = isBusy ? "Thinking" : "Ready";
        statusEl.classList.toggle("typing", isBusy);
      }

      function cancelPending() {
        if (pendingController) pendingController.abort();
      }

      async function sendPrompt(message) {
        const trimmed = message.trim();
        if (!trimmed) return;

        const identity = ensureIdentity();
        addMessage("user", trimmed);
        if (sentHistory[sentHistory.length - 1] !== trimmed) sentHistory.push(trimmed);
        histPos = -1;
        promptEl.value = "";
        promptEl.style.height = "46px";
        setBusy(true);

        const bubble = addMessage("assistant", "");
        bubble.classList.add("loading");
        bubble.innerHTML = '<span class="dot-typing"><span></span><span></span><span></span></span>';

        const controller = new AbortController();
        pendingController = controller;
        try {
          const response = await fetch("/invocations", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-GreenNode-AgentBase-User-Id": identity.userId,
              "X-GreenNode-AgentBase-Session-Id": identity.sessionId,
            },
            body: JSON.stringify({ message: trimmed }),
            signal: controller.signal,
          });
          const payload = await response.json();
          bubble.classList.remove("loading");
          bubble.innerHTML = renderMarkdown(payload.response || payload.error || "No response returned.");
        } catch (error) {
          if (error.name === "AbortError") {
            (bubble.closest(".message") || bubble).remove();
          } else {
            bubble.classList.remove("loading");
            bubble.textContent = "Could not reach /invocations. Check that the runtime is running and the API is accessible.";
          }
        } finally {
          if (pendingController === controller) pendingController = null;
          setBusy(false);
          promptEl.focus();
        }
      }

      function seedMessages() {
        addMessage("assistant", "Xin chào. Tôi là Pagefinder. Hãy hỏi tôi về tài liệu Confluence, yêu cầu tóm tắt, kiểm tra cập nhật, hoặc tìm đúng page bạn cần.");
      }

      formEl.addEventListener("submit", function(event) {
        event.preventDefault();
        if (pendingController) { cancelPending(); return; }
        sendPrompt(promptEl.value);
      });

      promptEl.addEventListener("keydown", function(event) {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          formEl.requestSubmit();
          return;
        }
        // ↑ on an empty/navigating composer recalls previous sent messages (shell-style).
        if (event.key === "ArrowUp") {
          if (histPos === -1) {
            if (promptEl.value !== "" || sentHistory.length === 0) return;
            histPos = sentHistory.length - 1;
          } else if (histPos > 0) {
            histPos--;
          } else {
            return;
          }
          event.preventDefault();
          setPromptValue(sentHistory[histPos]);
        } else if (event.key === "ArrowDown") {
          if (histPos === -1) return;
          event.preventDefault();
          if (histPos < sentHistory.length - 1) {
            histPos++;
            setPromptValue(sentHistory[histPos]);
          } else {
            histPos = -1;
            setPromptValue("");
          }
        }
      });

      promptEl.addEventListener("input", function() {
        histPos = -1;
        promptEl.style.height = "46px";
        promptEl.style.height = Math.min(promptEl.scrollHeight, 200) + "px";
      });

      resetEl.addEventListener("click", newSession);

      document.querySelectorAll("[data-prompt]").forEach(function(button) {
        button.addEventListener("click", function() {
          promptEl.value = button.dataset.prompt;
          promptEl.focus();
        });
      });

      // --- Theme (light / dark) ---
      const rootEl = document.documentElement;
      const themeToggleEl = document.getElementById("theme-toggle");
      function applyTheme(theme) {
        if (theme === "dark") {
          rootEl.setAttribute("data-theme", "dark");
        } else {
          rootEl.removeAttribute("data-theme");
        }
      }
      let currentTheme = localStorage.getItem("pagefinder-theme") || "light";
      applyTheme(currentTheme);
      themeToggleEl.addEventListener("click", function() {
        currentTheme = rootEl.getAttribute("data-theme") === "dark" ? "light" : "dark";
        applyTheme(currentTheme);
        localStorage.setItem("pagefinder-theme", currentTheme);
      });

      // --- Resizable sidebar ---
      const shellEl = document.querySelector(".shell");
      const resizerEl = document.getElementById("resizer");
      const savedSidebarW = localStorage.getItem("pagefinder-sidebar-w");
      if (savedSidebarW) shellEl.style.setProperty("--sidebar-w", savedSidebarW);
      let dragging = false;
      let dragStartX = 0;
      let dragStartW = 0;
      function clampSidebar(px) {
        return Math.max(220, Math.min(620, px));
      }
      resizerEl.addEventListener("pointerdown", function(event) {
        dragging = true;
        dragStartX = event.clientX;
        dragStartW = parseInt(getComputedStyle(shellEl).getPropertyValue("--sidebar-w"), 10) || 280;
        resizerEl.classList.add("dragging");
        resizerEl.setPointerCapture(event.pointerId);
        document.body.style.userSelect = "none";
      });
      resizerEl.addEventListener("pointermove", function(event) {
        if (!dragging) return;
        const width = clampSidebar(dragStartW + (event.clientX - dragStartX));
        shellEl.style.setProperty("--sidebar-w", width + "px");
      });
      function endResize() {
        if (!dragging) return;
        dragging = false;
        resizerEl.classList.remove("dragging");
        document.body.style.userSelect = "";
        localStorage.setItem("pagefinder-sidebar-w", getComputedStyle(shellEl).getPropertyValue("--sidebar-w").trim());
      }
      resizerEl.addEventListener("pointerup", endResize);
      resizerEl.addEventListener("pointercancel", endResize);
      resizerEl.addEventListener("dblclick", function() {
        shellEl.style.setProperty("--sidebar-w", "320px");
        localStorage.setItem("pagefinder-sidebar-w", "320px");
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
