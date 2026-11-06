# history/renderer.py
"""
HTML rendering helpers for the analysis history views.

The dashboard uses HTMX: every public function returns an HTML
fragment that is injected into the '#preview-container' element of
the main page. All display text is in English.
"""

import html
import os
import time
from typing import Optional

from analyze.models import AnalysisReport, ChartInfo, ReportSection, ReportType
from analyze.report_renderer import render_report_to_html
from history.models import HistoryRecord

# htmx target shared by every button rendered from this module
_PREVIEW_TARGET = "#preview-container"

# Maximum length of the prompt preview shown in the history list
_PROMPT_PREVIEW_LENGTH = 180


def _escape(value: object) -> str:
    """HTML-escape any value for safe insertion into the page."""
    return html.escape(str(value if value is not None else ""))


def _shorten(text: str, limit: int) -> str:
    """Collapse whitespace and truncate long text with an ellipsis."""
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _chart_url(chart_path: Optional[str]) -> Optional[str]:
    """Build a browser URL for a stored chart snapshot, if the file exists."""
    if not chart_path:
        return None
    normalized = chart_path.replace("\\", "/").lstrip("/")
    if not os.path.exists(normalized):
        return None
    return "/" + normalized


def _chart_block(
    chart_path: Optional[str],
    caption: str = "AI-Generated Visualization",
) -> str:
    """Render a chart card for a history detail view."""
    url = _chart_url(chart_path)
    if not url:
        return ""

    cache_buster = int(time.time())
    return f"""
    <div class="bg-white p-4 rounded-xl border border-gray-100 shadow-sm flex flex-col items-center mb-6">
        <h3 class="text-sm font-semibold text-gray-700 mb-3 w-full text-left">
            📈 {_escape(caption)}
        </h3>
        <img src="{url}?t={cache_buster}"
             alt="AI Generated Chart"
             class="max-h-96 rounded-lg shadow-sm border border-gray-200" />
    </div>
    """


def _type_badge(record: HistoryRecord) -> str:
    """Render a colored badge describing the record type."""
    if record.is_structured():
        report_type = ReportType.from_string(record.report_type or "comprehensive")
        label = f"{report_type.icon()} {report_type.display_name()}"
        classes = "bg-blue-50 text-blue-700 border-blue-100"
    else:
        label = "⚡ Quick Analysis"
        classes = "bg-amber-50 text-amber-700 border-amber-100"

    return (
        f'<span class="text-[11px] font-medium px-2 py-0.5 rounded-full border '
        f'{classes}">{_escape(label)}</span>'
    )


def _record_card(record: HistoryRecord) -> str:
    """Render a single record card for the history list."""
    title = _escape(record.title or "Untitled Analysis")
    prompt = _escape(_shorten(record.prompt, _PROMPT_PREVIEW_LENGTH))
    dataset = _escape(record.dataset_name or "active_dataset.xlsx")
    created = _escape(record.created_at)

    return f"""
    <div class="bg-white p-4 rounded-xl border border-gray-100 shadow-sm">
        <div class="flex flex-wrap items-start justify-between gap-3">
            <div class="min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                    <span>{record.icon()}</span>
                    <span class="font-semibold text-sm text-gray-900 break-words">{title}</span>
                    {_type_badge(record)}
                </div>
                <p class="text-xs text-gray-500 mt-1">
                    🕒 {created} · 📁 {dataset}
                </p>
                <p class="text-sm text-gray-600 mt-2 break-words">{prompt}</p>
            </div>
            <div class="flex items-center gap-2 flex-shrink-0">
                <button hx-get="/history/{record.id}"
                        hx-target="{_PREVIEW_TARGET}"
                        class="text-xs bg-blue-600 hover:bg-blue-700 text-white font-medium px-3 py-1.5 rounded-lg transition">
                    👁 View
                </button>
                <button hx-post="/history/{record.id}/delete"
                        hx-target="{_PREVIEW_TARGET}"
                        hx-confirm="Delete this history record?"
                        class="text-xs bg-white hover:bg-red-50 text-red-600 font-medium px-3 py-1.5 rounded-lg border border-red-200 transition">
                    🗑 Delete
                </button>
            </div>
        </div>
    </div>
    """


def render_history_empty() -> str:
    """Render the empty-state view shown when no history exists."""
    return f"""
    <div class="bg-white p-10 rounded-xl border border-gray-100 shadow-sm text-center">
        <p class="text-4xl mb-3">🕘</p>
        <h2 class="text-lg font-semibold text-gray-900">No History Yet</h2>
        <p class="text-sm text-gray-500 mt-1">
            Run a quick analysis or generate a structured report, and the result
            will be saved here automatically.
        </p>
        <a href="/" class="inline-block mt-4 text-xs bg-gray-800 hover:bg-gray-900 text-white font-medium px-4 py-2 rounded-lg transition">
            ← Back to Dashboard
        </a>
    </div>
    """


def render_history_list(records: list[HistoryRecord]) -> str:
    """Render the full history list, newest first."""
    if not records:
        return render_history_empty()

    cards = "".join(_record_card(record) for record in records)
    count = len(records)
    label = "record" if count == 1 else "records"

    return f"""
    <div class="space-y-4">
        <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
                <a href="/" class="text-xs text-blue-600 hover:text-blue-800">
                    ← Back to Dashboard
                </a>
                <h2 class="text-lg font-bold text-gray-900 mt-1">🕘 Analysis History</h2>
                <p class="text-xs text-gray-500">{count} saved {label}</p>
            </div>
            <div class="flex items-center gap-2">
                <button hx-get="/history"
                        hx-target="{_PREVIEW_TARGET}"
                        class="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium px-3 py-1.5 rounded-lg border border-gray-300 transition">
                    🔄 Refresh
                </button>
                <button hx-post="/history/clear"
                        hx-target="{_PREVIEW_TARGET}"
                        hx-confirm="Delete all history records? This action cannot be undone."
                        class="text-xs bg-white hover:bg-red-50 text-red-600 font-medium px-3 py-1.5 rounded-lg border border-red-200 transition">
                    🗑 Clear All
                </button>
            </div>
        </div>
        <div class="space-y-3">{cards}</div>
    </div>
    """


def _quick_analysis_body(record: HistoryRecord) -> str:
    """Render the stored raw text (and chart) of a quick analysis."""
    chart = _chart_block(record.chart_path)
    formatted = _escape(record.raw_text).replace("\n", "<br>")

    return f"""
    <div class="space-y-4">
        {chart}
        <div class="bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
            <h3 class="text-sm font-semibold text-gray-700 mb-2">📝 AI Analysis Report</h3>
            <div class="text-sm text-gray-700 leading-relaxed font-sans">{formatted}</div>
        </div>
    </div>
    """


def _structured_report_body(record: HistoryRecord) -> str:
    """Rebuild an AnalysisReport from storage and render it to HTML."""
    sections: list[ReportSection] = []

    for raw in record.sections or []:
        if not isinstance(raw, dict):
            continue
        try:
            level = int(raw.get("level", 2))
        except (TypeError, ValueError):
            level = 2
        sections.append(
            ReportSection(
                title=str(raw.get("title", "")),
                content=str(raw.get("content", "")),
                level=level,
            )
        )

    chart = None
    if record.chart_path:
        chart = ChartInfo(path=record.chart_path, caption="AI-Generated Visualization")

    report = AnalysisReport(
        title=record.title or "Analysis Report",
        report_type=ReportType.from_string(record.report_type or "comprehensive"),
        sections=sections,
        chart=chart,
        summary=record.summary or "",
        key_insights=list(record.key_insights or []),
        recommendations=list(record.recommendations or []),
        raw_text=record.raw_text or "",
    )
    return render_report_to_html(report)


def render_history_detail(record: HistoryRecord) -> str:
    """Render the detail view for a single history record."""
    if record.is_structured():
        type_note = " · " + ReportType.from_string(
            record.report_type or "comprehensive"
        ).display_name()
        body = _structured_report_body(record)
    else:
        type_note = ""
        body = _quick_analysis_body(record)

    return f"""
    <div class="space-y-4">
        <div class="flex flex-wrap items-start justify-between gap-3">
            <div class="min-w-0">
                <button hx-get="/history"
                        hx-target="{_PREVIEW_TARGET}"
                        class="text-xs text-blue-600 hover:text-blue-800">
                    ← Back to History
                </button>
                <h2 class="text-lg font-bold text-gray-900 mt-1 break-words">
                    {_escape(record.title)}
                </h2>
                <p class="text-xs text-gray-500 mt-0.5">
                    {record.icon()} {_escape(record.display_type())}{_escape(type_note)}
                    · 🕒 {_escape(record.created_at)}
                    · 📁 {_escape(record.dataset_name)}
                </p>
                <p class="text-sm text-gray-600 mt-2 break-words">
                    <span class="font-medium">Prompt:</span> {_escape(record.prompt)}
                </p>
            </div>
            <button hx-post="/history/{record.id}/delete"
                    hx-target="{_PREVIEW_TARGET}"
                    hx-confirm="Delete this history record?"
                    class="text-xs bg-white hover:bg-red-50 text-red-600 font-medium px-3 py-1.5 rounded-lg border border-red-200 transition flex-shrink-0">
                🗑 Delete
            </button>
        </div>
        <div class="border-t border-gray-200 pt-4">{body}</div>
    </div>
    """


def render_history_error(message: str) -> str:
    """Render an error card when a record cannot be displayed."""
    return f"""
    <div class="bg-amber-50 border border-amber-200 text-amber-800 p-6 rounded-xl">
        <h3 class="font-semibold text-lg mb-1">⚠️ History Record Unavailable</h3>
        <p class="text-sm">{_escape(message)}</p>
        <button hx-get="/history"
                hx-target="{_PREVIEW_TARGET}"
                class="mt-3 text-xs bg-gray-800 hover:bg-gray-900 text-white font-medium px-3 py-1.5 rounded-lg transition">
            ← Back to History
        </button>
    </div>
    """
