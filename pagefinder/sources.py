from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit

import requests

from pagefinder.utils import utc_now


@dataclass
class PageSnapshot:
    page_id: str
    title: str
    version: int
    url: str
    body: str
    body_format: str
    fetched_at: str


@dataclass
class PageMeta:
    """Lightweight page metadata for change detection — no body fetched."""

    page_id: str
    title: str
    version: int


class ConfluenceClient:
    def __init__(self, base_url: str, email: str, api_token: str) -> None:
        self.base_url = self._normalize_base_url(base_url)
        self.session = requests.Session()
        self.session.auth = (email, api_token)
        self.session.headers.update({"Accept": "application/json"})

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        parsed = urlsplit(base_url.strip())
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("CONFLUENCE_BASE_URL must be a valid absolute URL")

        path = parsed.path.rstrip("/")
        if "/wiki" in path:
            wiki_path = path[: path.index("/wiki") + len("/wiki")]
        else:
            wiki_path = "/wiki"
        return f"{parsed.scheme}://{parsed.netloc}{wiki_path}"

    def list_page_ids(self, space_keys: list[str]) -> list[str]:
        """Discover every page id in the given Confluence space keys (paginated)."""
        page_ids: list[str] = []
        seen: set[str] = set()
        for space_key in space_keys:
            start, limit = 0, 100
            while True:
                response = self.session.get(
                    f"{self.base_url}/rest/api/space/{space_key}/content/page",
                    params={"limit": limit, "start": start},
                    timeout=30,
                )
                response.raise_for_status()
                results = response.json().get("results", [])
                for page in results:
                    page_id = str(page.get("id", "")).strip()
                    if page_id and page_id not in seen:
                        seen.add(page_id)
                        page_ids.append(page_id)
                if len(results) < limit:
                    break
                start += limit
        return page_ids

    @staticmethod
    def _resolve_version(raw_version: dict) -> int:
        """Derive a change-detection version from the Confluence version object.

        Confluence "live docs" freeze ``version.number`` at 1 across every edit, so it
        cannot signal content changes. ``version.when`` (the last-edit timestamp) DOES
        change on each edit for both live docs and classic pages, so we use its epoch
        seconds as the version. Comparison is equality-only (``needs_reindex``), so a
        timestamp works as well as an incrementing counter. Falls back to
        ``version.number`` when the timestamp is missing or unparseable.
        """
        version_number = int(raw_version.get("number", 1) or 1)
        version_when = raw_version.get("when")
        if version_when:
            try:
                edited_at = datetime.fromisoformat(str(version_when).replace("Z", "+00:00"))
                return int(edited_at.timestamp())
            except ValueError:
                return version_number
        return version_number

    def fetch_page_meta(self, page_id: str) -> PageMeta:
        """Fetch only the version/title (no body) for cheap change detection."""
        response = self.session.get(
            f"{self.base_url}/rest/api/content/{page_id}",
            params={"expand": "version"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        version = self._resolve_version(payload.get("version", {}) or {})
        return PageMeta(
            page_id=str(payload["id"]),
            title=payload["title"],
            version=version,
        )

    def fetch_page(self, page_id: str) -> PageSnapshot:
        response = self.session.get(
            f"{self.base_url}/rest/api/content/{page_id}",
            params={"expand": "body.storage,version,space,_links"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        version = self._resolve_version(payload.get("version", {}) or {})
        space_key = payload.get("space", {}).get("key", "")
        webui = payload.get("_links", {}).get("webui")
        url = f"{self.base_url}{webui}" if webui else f"{self.base_url}/spaces/{space_key}/pages/{page_id}"
        return PageSnapshot(
            page_id=str(payload["id"]),
            title=payload["title"],
            version=version,
            url=url,
            body=payload["body"]["storage"]["value"],
            body_format="html",
            fetched_at=utc_now(),
        )
