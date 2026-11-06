# history/store.py
"""
JSON-file-backed persistence for analysis history records.

Records are stored newest-first in a single JSON file so they survive
server restarts. The store is thread-safe and prunes the oldest entries
(and their chart snapshots) once the configured limit is exceeded.

All comments and display text are in English.
"""

import json
import os
import threading
from typing import Optional

from history.models import HistoryRecord

# Directory where per-record chart snapshots are stored.
# It lives under 'static', so the files are served by the existing
# '/static' mount in the FastAPI application.
HISTORY_CHART_DIR = "static/history_charts"

# Default location of the JSON history file (inside the history package)
DEFAULT_STORAGE_PATH = "history/data/history.json"

# Maximum number of records kept on disk
DEFAULT_MAX_RECORDS = 100


def _remove_chart(path: Optional[str]) -> None:
    """
    Delete a chart snapshot file.

    Only files that live inside the history chart directory are removed
    as a safety measure, so a malformed record can never delete other
    application files.
    """
    if not path:
        return

    normalized = path.replace("\\", "/").lstrip("/")
    chart_root = HISTORY_CHART_DIR.replace("\\", "/")
    if not normalized.startswith(chart_root + "/"):
        return

    try:
        if os.path.exists(normalized):
            os.remove(normalized)
    except OSError as exc:
        print(f"[history] Failed to remove chart snapshot: {exc}")


class HistoryStore:
    """
    Thread-safe persistence layer for analysis history records.

    Usage:
        store = HistoryStore()
        store.add(record)
        records = store.all()
        store.delete(record.id)
    """

    def __init__(
        self,
        storage_path: str = DEFAULT_STORAGE_PATH,
        max_records: int = DEFAULT_MAX_RECORDS,
    ):
        self.storage_path = storage_path
        self.max_records = max_records
        self._lock = threading.Lock()

        # Ensure the data and chart directories exist
        os.makedirs(os.path.dirname(storage_path) or ".", exist_ok=True)
        os.makedirs(HISTORY_CHART_DIR, exist_ok=True)

        self._records = self._load()

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    def _load(self) -> list[HistoryRecord]:
        """Read records from disk, skipping malformed entries."""
        if not os.path.exists(self.storage_path):
            return []

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[history] Failed to load history file: {exc}")
            return []

        if not isinstance(data, list):
            return []

        records: list[HistoryRecord] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                records.append(HistoryRecord.from_dict(item))
            except TypeError as exc:
                print(f"[history] Skipping malformed record: {exc}")
        return records

    def _save(self) -> None:
        """Write all records to disk atomically."""
        payload = [record.to_dict() for record in self._records]
        temp_path = self.storage_path + ".tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, self.storage_path)
        except OSError as exc:
            print(f"[history] Failed to save history file: {exc}")

    def _prune(self) -> None:
        """Drop the oldest records once the limit is exceeded."""
        while len(self._records) > self.max_records:
            removed = self._records.pop()
            _remove_chart(removed.chart_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, record: HistoryRecord) -> HistoryRecord:
        """Prepend a record (newest first), prune, and persist."""
        with self._lock:
            self._records.insert(0, record)
            self._prune()
            self._save()
        return record

    def all(self) -> list[HistoryRecord]:
        """Return a snapshot list of all records, newest first."""
        with self._lock:
            return list(self._records)

    def get(self, record_id: str) -> Optional[HistoryRecord]:
        """Return a single record by id, or None when not found."""
        with self._lock:
            for record in self._records:
                if record.id == record_id:
                    return record
        return None

    def delete(self, record_id: str) -> bool:
        """Delete a record and its chart snapshot. Returns True on success."""
        with self._lock:
            for index, record in enumerate(self._records):
                if record.id == record_id:
                    self._records.pop(index)
                    _remove_chart(record.chart_path)
                    self._save()
                    return True
        return False

    def clear(self) -> int:
        """Delete every record and chart snapshot. Returns the removed count."""
        with self._lock:
            count = len(self._records)
            for record in self._records:
                _remove_chart(record.chart_path)
            self._records = []
            self._save()
            return count

    def count(self) -> int:
        """Return the number of stored records."""
        with self._lock:
            return len(self._records)


# Shared default store used by the web routes
history_store = HistoryStore()
