from threading import Event, Lock, Thread

from pagefinder import config
from pagefinder.service import PagefinderService
from pagefinder.utils import utc_now


class BackgroundSyncJob:
    def __init__(self, service: PagefinderService) -> None:
        self.service = service
        self._thread: Thread | None = None
        self._stop_event = Event()
        self._start_lock = Lock()

    def should_run(self) -> bool:
        return config.SOURCE_MODE == "confluence" and config.BACKGROUND_SYNC_ENABLED

    def start(self) -> None:
        if not self.should_run():
            return
        with self._start_lock:
            if self._thread and self._thread.is_alive():
                return
            self._thread = Thread(target=self._run_loop, name="pagefinder-background-sync", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _run_loop(self) -> None:
        while not self._stop_event.wait(config.BACKGROUND_SYNC_INTERVAL_SECONDS):
            try:
                synced_pages = self.service.sync_pages(force=False)
                if synced_pages:
                    print(
                        f"[{utc_now()}] Background sync refreshed {len(synced_pages)} page(s): "
                        + ", ".join(page["page_id"] for page in synced_pages)
                    )
            except Exception as error:
                print(f"[{utc_now()}] Background sync failed: {self.service.format_source_error(error)}")
