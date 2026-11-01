# analyze/models.py
"""
Data models for structured report generation.

Defines the ReportType enum and dataclasses used throughout
the report generation pipeline. All display text is in English.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ReportType(str, Enum):
    """
    Types of AI-generated analysis reports available.

    Each type produces a differently structured report tailored
    to a specific analytical need (executive overview, deep dive,
    statistical analysis, data quality check, or all-in-one).
    """
    EXECUTIVE_SUMMARY = "executive_summary"
    DETAILED_ANALYSIS = "detailed_analysis"
    STATISTICAL_REPORT = "statistical_report"
    DATA_QUALITY = "data_quality"
    COMPREHENSIVE = "comprehensive"

    @classmethod
    def from_string(cls, value: str) -> "ReportType":
        """Convert a string to a ReportType, defaulting to COMPREHENSIVE on mismatch."""
        for member in cls:
            if member.value == value:
                return member
        return cls.COMPREHENSIVE

    def display_name(self) -> str:
        """Return a human-readable display name for the report type."""
        names = {
            "executive_summary": "Executive Summary",
            "detailed_analysis": "Detailed Analysis",
            "statistical_report": "Statistical Report",
            "data_quality": "Data Quality Assessment",
            "comprehensive": "Comprehensive Report",
        }
        return names.get(self.value, "Comprehensive Report")

    def icon(self) -> str:
        """Return an emoji icon representing the report type."""
        icons = {
            "executive_summary": "\U0001f4cb",
            "detailed_analysis": "\U0001f4ca",
            "statistical_report": "\U0001f4c8",
            "data_quality": "✅",
            "comprehensive": "\U0001f4d1",
        }
        return icons.get(self.value, "\U0001f4c4")

    def description(self) -> str:
        """Return a one-line description of what this report type offers."""
        descriptions = {
            "executive_summary": "A brief high-level overview with the most important findings and recommendations.",
            "detailed_analysis": "An in-depth exploration of the dataset with sectioned analysis and insights.",
            "statistical_report": "A statistics-focused report covering distributions, correlations, and key metrics.",
            "data_quality": "An assessment of data completeness, consistency, and potential quality issues.",
            "comprehensive": "A full-spectrum report combining summary, analysis, statistics, quality, and recommendations.",
        }
        return descriptions.get(self.value, "A comprehensive analysis report.")


@dataclass
class ReportSection:
    """
    A single section within an analysis report.

    Attributes:
        title:   Section heading text.
        content: Section body content (markdown-formatted text).
        level:   Heading level (1 for #, 2 for ##, etc.).
    """
    title: str
    content: str
    level: int = 2


@dataclass
class ChartInfo:
    """
    Information about a chart generated as part of the report.

    Attributes:
        path:    Filesystem path to the saved chart image (None if generation failed).
        caption: Descriptive caption for the chart.
    """
    path: Optional[str] = None
    caption: str = ""


@dataclass
class AnalysisReport:
    """
    A complete structured analysis report.

    This is the primary output object produced by the ReportGenerator.
    It contains all sections, metadata, chart references, extracted
    insights, and recommendations in a structured format ready for rendering.

    Attributes:
        title:          Report title.
        report_type:    The type of report generated.
        sections:       Ordered list of report sections.
        chart:          Optional chart information (path + caption).
        summary:        One-paragraph executive summary extracted from the content.
        key_insights:   Bullet-point list of key findings extracted from the content.
        recommendations: Bullet-point list of recommendations extracted from the content.
        raw_text:       The original raw markdown text returned by the AI.
    """
    title: str
    report_type: ReportType = ReportType.COMPREHENSIVE
    sections: list[ReportSection] = field(default_factory=list)
    chart: Optional[ChartInfo] = None
    summary: str = ""
    key_insights: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    raw_text: str = ""
