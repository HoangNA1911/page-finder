from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests

from pagefinder.utils import title_from_markdown, utc_now


@dataclass
class PageSnapshot:
    page_id: str
    title: str
    version: int
    url: str
    body: str
    body_format: str
    fetched_at: str


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

    def fetch_page(self, page_id: str) -> PageSnapshot:
        response = self.session.get(
            f"{self.base_url}/rest/api/content/{page_id}",
            params={"expand": "body.storage,version,space,_links"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        version = int(payload["version"]["number"])
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


class MarkdownClient:
    def __init__(self, docs_dir: Path) -> None:
        self.docs_dir = docs_dir

    def iter_pages(self) -> list[PageSnapshot]:
        snapshots: list[PageSnapshot] = []
        for path in sorted(self.docs_dir.glob("*.md")):
            stat = path.stat()
            snapshots.append(
                PageSnapshot(
                    page_id=path.stem,
                    title=title_from_markdown(path),
                    version=int(stat.st_mtime),
                    url=f"file://{path.resolve()}",
                    body=path.read_text(encoding="utf-8"),
                    body_format="markdown",
                    fetched_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                )
            )
        return snapshots
