# history/models.py
"""
Data model for analysis history records.

A HistoryRecord stores everything required to display a previous
analysis attempt: metadata, the raw AI response, parsed report
sections (for structured reports), and a snapshot path for the
generated chart (if any).

All comments and display text are in English.
"""

from dataclasses import asdict, dataclass, field, fields
from typing import Any, Optional

# Entry type constants shared across the history package
ENTRY_QUICK_ANALYSIS = "quick_analysis"
ENTRY_STRUCTURED_REPORT = "structured_report"


@dataclass
class HistoryRecord:
    """
    A single saved analysis history entry.

    Attributes:
        id:              Unique record identifier (timestamp + random suffix).
        created_at:      Human-readable creation time.
        entry_type:      'quick_analysis' or 'structured_report'.
        title:           Short display title for the record.
        prompt:          The user's original query.
        dataset_name:    Original name of the dataset used for the analysis.
        report_type:     Structured report type value (empty for quick analyses).
        raw_text:        Raw markdown text returned by the AI.
        summary:         Extracted executive summary (structured reports only).
        key_insights:    Extracted key insights (structured reports only).
        recommendations: Extracted recommendations (structured reports only).
        sections:        Serialized report sections (structured reports only).
        chart_path:      Relative path to the saved chart snapshot, if any.
    """

    id: str = ""
    created_at: str = ""
    entry_type: str = ENTRY_QUICK_ANALYSIS
    title: str = "Untitled Analysis"
    prompt: str = ""
    dataset_name: str = "active_dataset.xlsx"
    report_type: str = ""
    raw_text: str = ""
    summary: str = ""
    key_insights: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    sections: list[dict] = field(default_factory=list)
    chart_path: Optional[str] = None

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Convert the record into a JSON-serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HistoryRecord":
        """
        Rebuild a record from a dictionary, ignoring unknown keys.

        Missing optional keys fall back to the dataclass defaults so
        older or partially corrupted entries still load safely.
        """
        allowed = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in allowed}
        return cls(**filtered)

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def display_type(self) -> str:
        """Return a human-readable label for the entry type."""
        if self.entry_type == ENTRY_STRUCTURED_REPORT:
            return "Structured Report"
        return "Quick Analysis"

    def icon(self) -> str:
        """Return an emoji icon representing the entry type."""
        if self.entry_type == ENTRY_STRUCTURED_REPORT:
            return "\U0001f4d1"
        return "⚡"

    def is_structured(self) -> bool:
        """Return True when this record holds a structured report."""
        return self.entry_type == ENTRY_STRUCTURED_REPORT
