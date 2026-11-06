# history/__init__.py
"""
Auto Data Viz - Analysis History Module

Persists every analysis and structured report so users can review
previous results from the dashboard. Records are stored as JSON on
disk together with chart snapshots.

Exported API:
    HistoryRecord             - Dataclass representing one history entry.
    HistoryStore              - JSON-backed persistence layer.
    history_store             - Shared default store instance.
    record_quick_analysis     - Persist a quick-analysis result.
    record_structured_report  - Persist a structured report result.

All comments and display text are in English.
"""

from history.models import HistoryRecord
from history.recorder import record_quick_analysis, record_structured_report
from history.store import HistoryStore, history_store

__all__ = [
    "HistoryRecord",
    "HistoryStore",
    "history_store",
    "record_quick_analysis",
    "record_structured_report",
]
