// Pagefinder Confluence content script.
// Injects a floating chat button + panel into a Shadow DOM so the page's styles
// (and Confluence's strict CSP) don't interfere with ours, and ours don't leak out.

(function () {
  if (window.__pagefinderInjected) return;
  window.__pagefinderInjected = true;

  // ---------------------------------------------------------------------------
  // Styles — ported from the standalone light-mode UI (teal accent, white
  // bubbles, mint conversation area). System font stack on purpose: loading
  // Google Fonts from the page context would be blocked by Confluence CSP.
  // ---------------------------------------------------------------------------
  const CSS = `
    :host {
      --panel: #ffffff;
      --messages-bg: #e6f4f6;
      --surface: #ffffff;
      --border: rgba(15, 64, 72, 0.12);
      --text: #103a40;
      --muted: #5a868c;
      --accent: #13b5c4;
      --accent-hover: #0e9fae;
      --ink-on-accent: #ffffff;
      --font: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      all: initial;
    }
    * { box-sizing: border-box; }

    .launcher {
      position: fixed;
      right: 22px;
      bottom: 22px;
      width: 56px;
      height: 56px;
      border-radius: 16px;
      border: 0;
      cursor: pointer;
      background: linear-gradient(150deg, #2ad4e0 0%, #13b5c4 52%, #0c93a2 100%);
      color: #fff;
      display: grid;
      place-items: center;
      box-shadow: 0 12px 30px rgba(12, 147, 162, 0.42);
      z-index: 2147483647;
      transition: transform 140ms ease, box-shadow 140ms ease;
    }
    .launcher:hover { transform: translateY(-2px); box-shadow: 0 16px 38px rgba(12, 147, 162, 0.5); }
    .launcher svg { width: 26px; height: 26px; }

    .panel {
      position: fixed;
      right: 22px;
      bottom: 90px;
      width: 390px;
      max-width: calc(100vw - 32px);
      height: 580px;
      max-height: calc(100vh - 120px);
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 18px;
      box-shadow: 0 24px 70px rgba(8, 40, 45, 0.32);
      display: none;
      grid-template-rows: auto minmax(0, 1fr) auto;
      overflow: hidden;
      z-index: 2147483647;
      font-family: var(--font);
      color: var(--text);
      font-size: 14px;
    }
    .panel.open { display: grid; }

    .pf-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 18px;
      border-bottom: 1px solid var(--border);
    }
    .pf-title { display: flex; align-items: center; gap: 10px; }
    .pf-badge {
      width: 34px; height: 34px; border-radius: 10px;
      background: linear-gradient(150deg, #2ad4e0, #13b5c4 55%, #0c93a2);
      color: #fff; display: grid; place-items: center; font-weight: 700; font-size: 1.05rem;
    }
    .pf-title h1 { margin: 0; font-size: 1rem; font-weight: 700; letter-spacing: -0.01em; }
    .pf-title p { margin: 1px 0 0; font-size: 0.74rem; color: var(--muted); }
    .pf-close {
      border: 0; background: transparent; color: var(--muted); cursor: pointer;
      width: 30px; height: 30px; border-radius: 8px; font-size: 20px; line-height: 1;
    }
    .pf-close:hover { background: var(--messages-bg); color: var(--text); }

    .pf-messages {
      overflow-y: auto;
      padding: 18px;
      background: var(--messages-bg);
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .pf-messages::-webkit-scrollbar { width: 9px; }
    .pf-messages::-webkit-scrollbar-thumb {
      background: rgba(15, 64, 72, 0.18); border-radius: 999px;
      border: 3px solid transparent; background-clip: padding-box;
    }

    .pf-msg { max-width: 80%; display: flex; flex-direction: column; gap: 5px; }
    .pf-msg.user { align-self: flex-end; }
    .pf-msg.assistant { align-self: flex-start; }
    .pf-label {
      font-size: 0.66rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.1em; color: var(--muted); padding: 0 4px;
    }
    .pf-msg.user .pf-label { text-align: right; }

    .pf-bubble {
      border-radius: 16px; padding: 11px 14px; line-height: 1.55;
      white-space: pre-wrap; word-break: break-word;
    }
    .pf-msg.user .pf-bubble {
      background: var(--accent); color: var(--ink-on-accent);
      border-bottom-right-radius: 5px;
    }
    .pf-msg.assistant .pf-bubble {
      background: var(--surface); border: 1px solid var(--border);
      border-bottom-left-radius: 5px;
      box-shadow: 0 4px 14px rgba(15, 64, 72, 0.08);
    }

    .pf-bubble.md { white-space: normal; }
    .pf-bubble.md > :first-child { margin-top: 0; }
    .pf-bubble.md > :last-child { margin-bottom: 0; }
    .pf-bubble.md p { margin: 0 0 8px; }
    .pf-bubble.md ul, .pf-bubble.md ol { margin: 6px 0 8px; padding-left: 20px; }
    .pf-bubble.md li { margin: 2px 0; }
    .pf-bubble.md strong { color: #0c2c28; font-weight: 700; }
    .pf-bubble.md a { color: var(--accent); text-decoration: underline; word-break: break-all; }
    .pf-bubble.md code {
      background: rgba(15, 64, 72, 0.08); color: #0c8a96;
      padding: 1px 5px; border-radius: 5px;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.85em;
    }
    .pf-bubble.md pre {
      background: #f1f8f9; border: 1px solid var(--border);
      padding: 10px 12px; border-radius: 10px; overflow-x: auto; margin: 6px 0;
    }
    .pf-bubble.md pre code { background: transparent; padding: 0; }
    .pf-bubble.md table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 0.88em; display: block; overflow-x: auto; }
    .pf-bubble.md th, .pf-bubble.md td { border: 1px solid var(--border); padding: 5px 9px; text-align: left; vertical-align: top; }
    .pf-bubble.md th { background: var(--messages-bg); font-weight: 600; }

    .pf-bubble:has(.pf-dot-typing) { display: inline-flex; align-items: center; align-self: flex-start; min-height: 1.2em; }
    .pf-dot-typing { display: inline-flex; align-items: center; gap: 5px; }
    .pf-dot-typing span {
      width: 7px; height: 7px; border-radius: 50%; background: var(--muted);
      animation: pfbounce 1.3s infinite ease-in-out both;
    }
    .pf-dot-typing span:nth-child(2) { animation-delay: 0.16s; }
    .pf-dot-typing span:nth-child(3) { animation-delay: 0.32s; }
    @keyframes pfbounce {
      0%, 70%, 100% { transform: translateY(0); opacity: 0.35; }
      35% { transform: translateY(-5px); opacity: 1; }
    }

    .pf-suggest { background: var(--messages-bg); }
    .pf-suggest-toggle {
      width: 100%; display: flex; align-items: center; justify-content: space-between;
      padding: 9px 18px; border: 0; background: transparent; cursor: pointer;
      color: var(--muted); font-family: var(--font); font-weight: 700;
      font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em;
    }
    .pf-suggest-toggle .chev { transition: transform 160ms ease; }
    .pf-suggest.collapsed .pf-suggest-toggle .chev { transform: rotate(-90deg); }
    .pf-chips {
      display: flex; flex-wrap: wrap; gap: 8px;
      padding: 0 18px 12px; max-height: 160px; overflow-y: auto;
      transition: max-height 180ms ease, padding 180ms ease, opacity 140ms ease;
    }
    .pf-suggest.collapsed .pf-chips {
      max-height: 0; padding-top: 0; padding-bottom: 0; opacity: 0;
      overflow: hidden; pointer-events: none;
    }
    .pf-chip {
      border: 1px solid var(--border); background: var(--surface); color: var(--text);
      border-radius: 999px; padding: 7px 12px; font-size: 0.8rem; font-weight: 600;
      cursor: pointer; font-family: var(--font);
    }
    .pf-chip:hover { border-color: var(--accent); color: var(--accent); }

    .pf-composer-wrap { padding: 14px; border-top: 1px solid var(--border); background: var(--panel); }
    .pf-composer {
      border: 1px solid var(--border); background: var(--messages-bg);
      border-radius: 12px; padding: 10px 12px; display: grid; gap: 10px;
      transition: border-color 140ms ease;
    }
    .pf-composer:focus-within { border-color: var(--accent); }
    .pf-input {
      width: 100%; resize: none; border: 0; outline: 0; background: transparent;
      color: var(--text); font-family: var(--font); font-size: 0.92rem; line-height: 1.5;
      min-height: 40px; max-height: 120px;
    }
    .pf-input::placeholder { color: #93b1b4; }
    .pf-actions { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
    .pf-status { font-size: 0.78rem; color: var(--muted); }
    .pf-send {
      border: 0; background: var(--accent); color: var(--ink-on-accent);
      padding: 9px 18px; border-radius: 10px; font-weight: 700; font-size: 0.85rem;
      cursor: pointer; font-family: var(--font);
    }
    .pf-send:hover:not(:disabled) { background: var(--accent-hover); }
    .pf-send:disabled { opacity: 0.5; cursor: not-allowed; }
    .pf-send.pf-stop { background: #64748b; }
    .pf-send.pf-stop:hover { background: #515e72; }
  `;

  // ---------------------------------------------------------------------------
  // Markdown rendering — ported from the standalone UI (ui.py).
  // ---------------------------------------------------------------------------
  function escapeHtml(value) {
    return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function renderInline(text) {
    const codes = [];
    text = text.replace(/`([^`]+)`/g, function (_, code) {
      codes.push(code);
      return "{{{CODE" + (codes.length - 1) + "}}}";
    });
    text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, function (_, label, url) {
      return '<a href="' + url.replace(/"/g, "%22") + '" target="_blank" rel="noopener">' + label + "</a>";
    });
    text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    text = text.replace(/__([^_]+)__/g, "<strong>$1</strong>");
    text = text.replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
    text = text.replace(/(^|[\s(])(https?:\/\/[^\s<)]+)/g, function (_, pre, url) {
      return pre + '<a href="' + url.replace(/"/g, "%22") + '" target="_blank" rel="noopener">' + url + "</a>";
    });
    text = text.replace(/\{\{\{CODE(\d+)\}\}\}/g, function (_, index) {
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
      if (para.length) { html += "<p>" + renderInline(para.join("<br>")) + "</p>"; para = []; }
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

  // ---------------------------------------------------------------------------
  // Identity (user/session id) — required headers since memory is enabled.
  // ---------------------------------------------------------------------------
  function uuid() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
      const r = (Math.random() * 16) | 0;
      return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
    });
  }
  function ensureIdentity() {
    let userId = localStorage.getItem("pagefinder-user-id");
    let sessionId = localStorage.getItem("pagefinder-session-id");
    if (!userId) { userId = "ext-user-" + uuid().slice(0, 12); localStorage.setItem("pagefinder-user-id", userId); }
    if (!sessionId) { sessionId = "ext-session-" + uuid().slice(0, 12); localStorage.setItem("pagefinder-session-id", sessionId); }
    return { userId, sessionId };
  }

  // ---------------------------------------------------------------------------
  // pageId — prefer the page's own meta tag; fall back to the URL. Re-read on
  // SPA navigation (Confluence is a SPA; the content script loads only once).
  // ---------------------------------------------------------------------------
  function getPageId() {
    // URL first: it updates on SPA navigation. The ajs-page-id meta tag is set on
    // the initial server render and goes stale after client-side page changes, so
    // it's only a fallback (e.g. short links without a numeric id in the path).
    const m = location.pathname.match(/\/pages\/(\d+)/);
    if (m) return m[1];
    const meta = document.querySelector('meta[name="ajs-page-id"]');
    if (meta && meta.content && /^\d+$/.test(meta.content)) return meta.content;
    return null;
  }

  // ---------------------------------------------------------------------------
  // Build the UI inside a Shadow DOM.
  // ---------------------------------------------------------------------------
  const host = document.createElement("div");
  host.id = "pagefinder-root";
  document.documentElement.appendChild(host);
  const root = host.attachShadow({ mode: "open" });

  const style = document.createElement("style");
  style.textContent = CSS;
  root.appendChild(style);

  const launcher = document.createElement("button");
  launcher.className = "launcher";
  launcher.title = "Pagefinder";
  launcher.innerHTML =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>';
  root.appendChild(launcher);

  const panel = document.createElement("div");
  panel.className = "panel";
  panel.innerHTML = `
    <div class="pf-header">
      <div class="pf-title">
        <div class="pf-badge">P</div>
        <div>
          <h1>Pagefinder</h1>
          <p>Hỏi đáp tài liệu Confluence</p>
        </div>
      </div>
      <button class="pf-close" aria-label="Đóng">×</button>
    </div>
    <div class="pf-messages"></div>
    <div class="pf-suggest collapsed">
      <button class="pf-suggest-toggle" type="button">
        <span>Gợi ý</span>
        <svg class="chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
      </button>
      <div class="pf-chips"></div>
    </div>
    <div class="pf-composer-wrap">
      <div class="pf-composer">
        <textarea class="pf-input" placeholder="Message Pagefinder..."></textarea>
        <div class="pf-actions">
          <div class="pf-status">Ready</div>
          <button class="pf-send">Send</button>
        </div>
      </div>
    </div>
  `;
  root.appendChild(panel);

  const messagesEl = panel.querySelector(".pf-messages");
  const suggestEl = panel.querySelector(".pf-suggest");
  const suggestToggleEl = panel.querySelector(".pf-suggest-toggle");
  const chipsEl = panel.querySelector(".pf-chips");
  const inputEl = panel.querySelector(".pf-input");
  const sendEl = panel.querySelector(".pf-send");
  const statusEl = panel.querySelector(".pf-status");
  const closeEl = panel.querySelector(".pf-close");

  function addMessage(role, text, isMarkdown) {
    const wrap = document.createElement("div");
    wrap.className = "pf-msg " + role;
    const label = document.createElement("div");
    label.className = "pf-label";
    label.textContent = role === "user" ? "You" : "Pagefinder";
    const bubble = document.createElement("div");
    bubble.className = "pf-bubble";
    if (isMarkdown) { bubble.classList.add("md"); bubble.innerHTML = renderMarkdown(text); }
    else { bubble.textContent = text; }
    wrap.appendChild(label);
    wrap.appendChild(bubble);
    messagesEl.appendChild(wrap);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return bubble;
  }

  let busy = false;
  let pendingReqId = null;
  let pendingBubble = null;

  function setBusy(b) {
    busy = b;
    inputEl.disabled = b;
    // Keep the button clickable while busy so it can cancel.
    sendEl.textContent = b ? "Stop" : "Send";
    sendEl.classList.toggle("pf-stop", b);
    statusEl.textContent = b ? "Thinking" : "Ready";
  }

  function cancelPending() {
    if (!pendingReqId) return;
    chrome.runtime.sendMessage({ type: "pagefinder:abort", id: pendingReqId });
    if (pendingBubble) (pendingBubble.closest(".pf-msg") || pendingBubble).remove();
    pendingReqId = null;
    pendingBubble = null;
    setBusy(false);
    inputEl.focus();
  }

  async function send(message, displayLabel) {
    const trimmed = (message || "").trim();
    if (!trimmed || busy) return;
    const id = ensureIdentity();
    // Show a clean label (e.g. "Tóm tắt trang này") while still sending the
    // pageId-tagged message that the agent's page shortcut needs.
    addMessage("user", displayLabel || trimmed, false);
    inputEl.value = "";
    inputEl.style.height = "40px";
    setBusy(true);

    const reqId = "r" + Date.now() + Math.random().toString(16).slice(2, 8);
    pendingReqId = reqId;
    const bubble = addMessage("assistant", "", false);
    bubble.innerHTML = '<span class="pf-dot-typing"><span></span><span></span><span></span></span>';
    pendingBubble = bubble;

    chrome.runtime.sendMessage(
      { type: "pagefinder:invoke", id: reqId, message: trimmed, userId: id.userId, sessionId: id.sessionId },
      function (resp) {
        if (pendingReqId !== reqId) return; // cancelled or superseded
        pendingReqId = null;
        pendingBubble = null;
        if (chrome.runtime.lastError) {
          bubble.textContent = "Extension connection error: " + chrome.runtime.lastError.message;
        } else if (resp && resp.aborted) {
          (bubble.closest(".pf-msg") || bubble).remove();
        } else if (!resp || !resp.ok) {
          bubble.textContent = (resp && resp.error) || "No response received.";
        } else {
          bubble.classList.add("md");
          // Strip the agent's no-diacritics "Tom tat noi dung page <id>:" prefix line.
          const cleaned = (resp.response || "(empty)").replace(/^\s*Tom tat noi dung page \d+:\s*/i, "");
          bubble.innerHTML = renderMarkdown(cleaned);
        }
        messagesEl.scrollTop = messagesEl.scrollHeight;
        setBusy(false);
        inputEl.focus();
      }
    );
  }

  // Quick-action chips. "Tóm tắt trang này" embeds the current pageId so the
  // agent's page shortcut targets the page being viewed.
  function renderChips() {
    chipsEl.innerHTML = "";
    const chips = [
      { label: "Tóm tắt trang này", summarize: true },
      { label: "Có gì mới cập nhật?", text: "Có document nào vừa được update không?" },
      { label: "Ghi chú của tôi", text: "Liệt kê các ghi chú tôi đã lưu" },
    ];
    for (const c of chips) {
      const b = document.createElement("button");
      b.className = "pf-chip";
      b.textContent = c.label;
      b.addEventListener("click", function () {
        if (c.summarize) {
          // Resolve the pageId at click time so it always reflects the page
          // currently open (not whatever it was when the chips were rendered).
          const pid = getPageId();
          if (!pid) {
            addMessage("assistant", "Couldn't detect the current page (possibly a short link). Open a page with a URL like .../pages/<id>/...", false);
            return;
          }
          send("Tóm tắt trang này (page " + pid + ")", "Tóm tắt trang này");
        } else {
          send(c.text, c.label);
        }
      });
      chipsEl.appendChild(b);
    }
  }

  // Events
  launcher.addEventListener("click", function () {
    panel.classList.toggle("open");
    if (panel.classList.contains("open")) { renderChips(); inputEl.focus(); }
  });
  closeEl.addEventListener("click", function () { panel.classList.remove("open"); });
  suggestToggleEl.addEventListener("click", function () { suggestEl.classList.toggle("collapsed"); });
  sendEl.addEventListener("click", function () {
    if (busy) { cancelPending(); return; }
    send(inputEl.value);
  });
  inputEl.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(inputEl.value); }
  });
  inputEl.addEventListener("input", function () {
    inputEl.style.height = "40px";
    inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + "px";
  });

  // Seed greeting
  addMessage("assistant", "Xin chào 👋 Mình là Pagefinder. Hỏi mình về tài liệu Confluence, hoặc bấm \"Tóm tắt trang này\".", false);

  // SPA navigation: refresh chips (pageId) when the route changes client-side.
  let lastPath = location.pathname;
  function onRouteMaybeChanged() {
    if (location.pathname !== lastPath) {
      lastPath = location.pathname;
      if (panel.classList.contains("open")) renderChips();
    }
  }
  const _push = history.pushState;
  history.pushState = function () { _push.apply(this, arguments); onRouteMaybeChanged(); };
  const _replace = history.replaceState;
  history.replaceState = function () { _replace.apply(this, arguments); onRouteMaybeChanged(); };
  window.addEventListener("popstate", onRouteMaybeChanged);
})();
