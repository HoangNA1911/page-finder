// Background service worker.
// Reason: the agent endpoint sends no CORS headers, so a fetch from the page/content
// script would be blocked. A fetch from the worker (with host_permissions for the
// endpoint) is exempt from CORS and the page CSP. Content script talks to it via
// chrome.runtime.sendMessage.

const ENDPOINT =
  "https://endpoint-a469d99f-1eda-4c3a-8453-6beeb52a7bf1.agentbase-runtime.aiplatform.vngcloud.vn";

// Active requests keyed by id, so the content script can cancel an in-flight call.
const controllers = {};

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === "pagefinder:abort") {
    const controller = controllers[msg.id];
    if (controller) controller.abort();
    return false;
  }
  if (!msg || msg.type !== "pagefinder:invoke") return false;

  const controller = new AbortController();
  controllers[msg.id] = controller;

  (async () => {
    try {
      const res = await fetch(ENDPOINT + "/invocations", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          // Memory is enabled on the runtime → these two headers are mandatory.
          "X-GreenNode-AgentBase-User-Id": msg.userId,
          "X-GreenNode-AgentBase-Session-Id": msg.sessionId,
        },
        body: JSON.stringify({ message: msg.message }),
        signal: controller.signal,
      });

      // The endpoint always returns HTTP 200 and signals failure in the JSON body.
      const data = await res.json().catch(() => null);
      if (!data) {
        sendResponse({ ok: false, error: "Invalid response from server." });
        return;
      }
      if (data.status === "error") {
        sendResponse({ ok: false, error: data.error || "The agent returned an error." });
        return;
      }
      sendResponse({ ok: true, response: data.response || "" });
    } catch (err) {
      if (err && err.name === "AbortError") {
        sendResponse({ ok: false, aborted: true });
      } else {
        sendResponse({ ok: false, error: "Couldn't reach the agent: " + (err && err.message ? err.message : String(err)) });
      }
    } finally {
      delete controllers[msg.id];
    }
  })();

  // Keep the message channel open for the async sendResponse.
  return true;
});
