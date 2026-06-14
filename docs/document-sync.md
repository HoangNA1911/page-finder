# Document Sync and Update Tracking

## Purpose

Pagefinder keeps a local index of source documents so it can answer faster and detect updates.

## Sync Logic

- Each source document is indexed into semantic chunks grouped by heading.
- The index stores a version value for each document.
- When a source version changes, Pagefinder rebuilds the chunks for that document only.

## Update Detection

- For Markdown test documents, the version is derived from file modification time.
- For Confluence pages, the version comes from the page metadata.
- The `check_document_updates` tool reports documents that changed since the last index.

## Notes and Reading History

- Personal notes are stored separately from the RAG corpus.
- Reading history records which document a user opened and the related focus query.
- This separation avoids polluting retrieval results with private notes.

## Rollout Plan

- Start with 1-2 Markdown files for testing.
- Replace Markdown input with Confluence pages after shared-account access is ready.
