import time
from pathlib import Path
from datetime import datetime
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

from config import DEBOUNCE_SECONDS


class NoteChangeHandler(FileSystemEventHandler):
    """
    Handles file system events for markdown files.
    Debounces rapid changes to avoid over-triggering analysis.
    """

    def __init__(self, on_change: Callable[[Path], None]):
        super().__init__()
        self.on_change = on_change
        self.last_event_time: dict[str, float] = {}
        self.debounce_seconds = DEBOUNCE_SECONDS
        self.current_file: Optional[Path] = None

    def set_current_file(self, file_path: Path) -> None:
        """Set the specific file to watch (ignore others)."""
        self.current_file = file_path.resolve()
        print(f"[watcher] Now watching: {self.current_file}")

    def _should_process(self, file_path: Path) -> bool:
        """Check if this file should be processed."""
        # Only process markdown files
        if file_path.suffix.lower() not in (".md", ".markdown"):
            return False

        # If we have a specific file set, only watch that one
        if self.current_file and file_path.resolve() != self.current_file:
            return False

        return True

    def _is_debounced(self, file_path: str) -> bool:
        """Check if we should skip this event due to debouncing."""
        now = time.time()
        last_time = self.last_event_time.get(file_path, 0)

        if now - last_time < self.debounce_seconds:
            return True

        self.last_event_time[file_path] = now
        return False

    def on_modified(self, event: FileModifiedEvent) -> None:
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        if not self._should_process(file_path):
            return

        if self._is_debounced(event.src_path):
            return

        print(f"[watcher] File modified: {file_path.name}")
        self.on_change(file_path)

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        if not self._should_process(file_path):
            return

        print(f"[watcher] File created: {file_path.name}")
        self.on_change(file_path)


class NoteWatcher:
    """
    Watches a directory or file for changes.
    Triggers callbacks when markdown files are modified.
    """

    def __init__(self, watch_path: Path, on_change: Callable[[Path], None]):
        self.watch_path = watch_path.resolve()
        self.on_change = on_change
        self.handler = NoteChangeHandler(on_change)
        self.observer = Observer()

        # Determine if watching a file or directory
        if self.watch_path.is_file():
            self.handler.set_current_file(self.watch_path)
            self.watch_dir = self.watch_path.parent
        else:
            self.watch_dir = self.watch_path

    def set_file(self, file_path: Path) -> None:
        """Switch to watching a specific file."""
        self.handler.set_current_file(file_path)

    def start(self) -> None:
        """Start watching for file changes."""
        self.observer.schedule(self.handler, str(self.watch_dir), recursive=False)
        self.observer.start()
        print(f"[watcher] Started watching: {self.watch_dir}")

    def stop(self) -> None:
        """Stop watching for file changes."""
        self.observer.stop()
        self.observer.join()
        print("[watcher] Stopped")

    def run_forever(self) -> None:
        """Block and watch forever (until interrupted)."""
        self.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[watcher] Interrupted")
        finally:
            self.stop()


# Utility function for testing
def watch_file(file_path: Path, on_change: Callable[[Path], None]) -> NoteWatcher:
    """Convenience function to watch a single file."""
    watcher = NoteWatcher(file_path, on_change)
    return watcher


if __name__ == "__main__":
    # Quick test: watch current directory
    def handle_change(path: Path):
        print(f"  -> Would analyze: {path}")
        print(f"  -> Content preview: {path.read_text()[:100]}...")

    import sys

    watch_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")

    watcher = NoteWatcher(watch_path, handle_change)
    watcher.run_forever()
