# Pagefinder for Confluence — Browser Extension

A floating chat button on every Confluence Cloud page that lets you ask the deployed
Pagefinder agent about your docs. It shares the same `/invocations` backend as the
standalone chat — **no agent code is touched**.

## Highlights
- **No build step** (vanilla MV3 + Shadow DOM) — load it unpacked and it just runs.
- UI matches the standalone light theme (teal accent, white bubbles, mint conversation area).
- Rendered inside a **Shadow DOM**, so the extension's CSS never clashes with Confluence (and vice versa).
- Network goes through a **background service worker** to bypass Confluence's CORS & CSP
  (the agent endpoint sends no CORS headers).
- Detects the current `pageId` from the page (`<meta name="ajs-page-id">`, with URL fallback),
  so the **"Tóm tắt trang này" / Summarize this page** chip targets the page you're reading.
- Generates and stores a `user-id` / `session-id` (required because the agent has memory enabled).

## Install (once per machine)
1. Open `chrome://extensions`
2. Enable **Developer mode** (top-right)
3. Click **Load unpacked** and select the `confluence-extension/` folder

## Usage
1. Open a Confluence page (`https://<site>.atlassian.net/wiki/...`)
2. Click the teal chat button in the bottom-right corner to open the panel
3. Type a question, or use the **Summarize this page** suggestion chip

## Project structure
```
confluence-extension/
  manifest.json   # MV3: host_permissions for the endpoint, content script for *.atlassian.net/wiki/*
  background.js   # service worker: fetch /invocations (bypasses CORS/CSP), attaches the two session headers
  content.js      # injects the Shadow-DOM UI, renders markdown, resolves pageId (URL + meta + SPA), calls the worker
  README.md
```

## Configuration
- **Endpoint**: `host_permissions` in `manifest.json` uses a wildcard
  (`https://*.agentbase-runtime.aiplatform.vngcloud.vn/*`), so it already covers any
  runtime endpoint on that domain. To point at a different runtime you only need to
  change `ENDPOINT` in `background.js`, then reload the extension.
  - A normal redeploy (new image/version) keeps the same endpoint URL — nothing to change.
  - The URL only changes if you create a new runtime, delete & recreate it, or switch
    network mode (PUBLIC ↔ VPC). In that case update `ENDPOINT` in `background.js`.
- Page scope: `content_scripts.matches` in `manifest.json` (defaults to `*://*.atlassian.net/wiki/*`).

## Current limitations (agent-side logic — to be improved separately, not the extension)
- "Summarize this page" currently returns raw content (the agent short-circuits before the LLM, so it isn't a true summary yet).
- Only pages within the indexed scope (`CONFLUENCE_SPACE_KEYS`) can be answered; pages outside it report as unavailable.
- A free-text question containing a 4+ digit number can be misread by the agent as a pageId.

## Technical notes
- Because it's loaded unpacked, each demo machine performs the 3 install steps above (typical for extension dev mode).
- The MV3 service worker may sleep, but normal requests take only a few seconds, so it's not an issue
  (per-query auto-sync is turned off on the runtime).
- `pageId` resolution prefers the URL (`/pages/<id>/`) because the `ajs-page-id` meta tag goes stale
  after client-side (SPA) navigation; the meta tag is only a fallback.
