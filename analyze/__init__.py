# analyze/__init__.py
"""
Auto Data Viz - AI Report Generation Module

This package provides structured, AI-powered report generation
for datasets. It supports multiple report types including
executive summaries, detailed analysis, statistical reports,
data quality assessments, and comprehensive reports.

All comments and display content are in English.

Exported API:
    ReportType       - Enum of available report types.
    ReportSection    - Dataclass representing a report section.
    ChartInfo        - Dataclass representing a generated chart.
    AnalysisReport   - Dataclass for a complete structured report.
    ReportGenerator  - Class for generating reports.
    generate_report  - Convenience function (module-level).
    render_report_to_html   - Convert a report to HTML.
    render_report_to_markdown - Convert a report to Markdown.
"""

from analyze.models import ReportType, ReportSection, ChartInfo, AnalysisReport
from analyze.report_generator import ReportGenerator, generate_report
from analyze.report_renderer import render_report_to_html, render_report_to_markdown

__all__ = [
    "ReportType",
    "ReportSection",
    "ChartInfo",
    "AnalysisReport",
    "ReportGenerator",
    "generate_report",
    "render_report_to_html",
    "render_report_to_markdown",
]
