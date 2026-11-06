# history/recorder.py
"""
Helpers that turn analysis results into persisted history records.

Two entry points are provided:
  - record_quick_analysis(...)    — for the original /analyze route.
  - record_structured_report(...) — for the /analyze/report route.

Both helpers snapshot the generated chart (when present) into a
per-record file so later analyses cannot overwrite it. Failures are
logged and swallowed: recording history must never break the main
analysis flow.

All comments and display text are in English.
"""

import os
import shutil
import uuid
from datetime import datetime
from typing import Optional

from history.models import (
    ENTRY_QUICK_ANALYSIS,
    ENTRY_STRUCTURED_REPORT,
    HistoryRecord,
)
from history.store import HISTORY_CHART_DIR, history_store

# Maximum length of an auto-generated history title
_MAX_TITLE_LENGTH = 90


def _new_record_id() -> str:
    """Build a sortable, unique record identifier."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{stamp}_{uuid.uuid4().hex[:6]}"


def _now() -> str:
    """Return the current time in a human-readable format."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _snapshot_chart(source_path: Optional[str], record_id: str) -> Optional[str]:
    """
    Copy the generated chart into the history folder.

    The live analysis writes to a fixed path (static/output_chart.png),
    so a copy is required to keep the chart visible in history after
    the next run overwrites the original.

    Returns:
        The relative forward-slash path of the snapshot, or None.
    """
    if not source_path or not os.path.exists(source_path):
        return None

    extension = os.path.splitext(source_path)[1] or ".png"
    target_name = f"chart_{record_id}{extension}"
    target_path = os.path.join(HISTORY_CHART_DIR, target_name)

    try:
        os.makedirs(HISTORY_CHART_DIR, exist_ok=True)
        shutil.copyfile(source_path, target_path)
    except OSError as exc:
        print(f"[history] Failed to copy chart snapshot: {exc}")
        return None

    # Store a browser-friendly path (forward slashes, no leading slash)
    return f"{HISTORY_CHART_DIR}/{target_name}"


def _quick_title(prompt: str) -> str:
    """Derive a short title from the user's prompt."""
    compact = " ".join((prompt or "").split())
    if not compact:
        return "Quick Analysis"
    if len(compact) > _MAX_TITLE_LENGTH:
        compact = compact[: _MAX_TITLE_LENGTH - 3].rstrip() + "..."
    return compact


def record_quick_analysis(
    prompt: str,
    text_report: str,
    chart_path: Optional[str] = None,
    dataset_name: str = "active_dataset.xlsx",
) -> Optional[HistoryRecord]:
    """
    Persist the result of a quick analysis.

    Args:
        prompt:       The user's analysis query.
        text_report:  The raw markdown text returned by the AI.
        chart_path:   Path to the live chart image, if one was generated.
        dataset_name: Original name of the analysed dataset.

    Returns:
        The stored HistoryRecord, or None if recording failed.
    """
    try:
        record_id = _new_record_id()
        record = HistoryRecord(
            id=record_id,
            created_at=_now(),
            entry_type=ENTRY_QUICK_ANALYSIS,
            title=_quick_title(prompt),
            prompt=(prompt or "").strip(),
            dataset_name=dataset_name or "active_dataset.xlsx",
            raw_text=text_report or "",
            chart_path=_snapshot_chart(chart_path, record_id),
        )
        return history_store.add(record)
    except Exception as exc:  # noqa: BLE001 - history must never break analysis
        print(f"[history] Failed to record quick analysis: {exc}")
        return None


def record_structured_report(
    prompt: str,
    report,
    dataset_name: str = "active_dataset.xlsx",
) -> Optional[HistoryRecord]:
    """
    Persist the result of a structured report generation.

    Args:
        prompt:       The user's analysis query.
        report:       The AnalysisReport object produced by ReportGenerator.
        dataset_name: Original name of the analysed dataset.

    Returns:
        The stored HistoryRecord, or None if recording failed.
    """
    try:
        record_id = _new_record_id()

        # Serialize report sections into plain dictionaries for JSON storage
        sections = [
            {"title": section.title, "content": section.content, "level": section.level}
            for section in getattr(report, "sections", [])
        ]

        chart_source = None
        chart = getattr(report, "chart", None)
        if chart is not None:
            chart_source = chart.path

        report_type = getattr(report, "report_type", None)
        report_type_value = getattr(report_type, "value", "comprehensive")

        record = HistoryRecord(
            id=record_id,
            created_at=_now(),
            entry_type=ENTRY_STRUCTURED_REPORT,
            title=getattr(report, "title", "") or "Analysis Report",
            prompt=(prompt or "").strip(),
            dataset_name=dataset_name or "active_dataset.xlsx",
            report_type=report_type_value or "comprehensive",
            raw_text=getattr(report, "raw_text", "") or "",
            summary=getattr(report, "summary", "") or "",
            key_insights=list(getattr(report, "key_insights", []) or []),
            recommendations=list(getattr(report, "recommendations", []) or []),
            sections=sections,
            chart_path=_snapshot_chart(chart_source, record_id),
        )
        return history_store.add(record)
    except Exception as exc:  # noqa: BLE001 - history must never break analysis
        print(f"[history] Failed to record structured report: {exc}")
        return None
