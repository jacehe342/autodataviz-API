# file_export/export_handler.py
"""
Report exporter utilities for Auto Data Viz API.

Responsible for persisting AI-generated analysis reports (raw text,
structured AnalysisReport objects, or standalone HTML pages) into the
file_export directory.

Every export automatically generates a unique, timestamped file name,
so no previous export is ever overwritten.

Supported formats:
  - Markdown (.md)      — human-readable text report.
  - HTML (.html)        — standalone HTML page with an embedded chart image.
  - JSON (.json)        — machine-readable structured payload.
  - Plain text (.txt)   — plain-text version of the report.

All comments and display text are in English.
"""

import json
import os
from datetime import datetime
from typing import Any, Optional


def _timestamp() -> str:
    """Return a compact timestamp used to build unique file names."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _to_dict(obj: Any) -> dict:
    """
    Convert a report-like object to a plain dict.

    Handles dataclass instances (recursively) and falls back to the
    object's __dict__ for plain classes, so both real AnalysisReport
    objects and simple stub objects can be serialized.
    """
    import dataclasses
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    return {"value": str(obj)}


class ReportExporter:
    """
    Exporter utility to handle saving AI analysis reports and managing exported files.

    All exports automatically generate unique, timestamped file names.
    """

    def __init__(self, output_dir: str = "file_export"):
        self.output_dir = output_dir
        # Ensure the export directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    # ------------------------------------------------------------------
    # File name generation helpers
    # ------------------------------------------------------------------

    def _generate_file_name(self, stem: str, extension: str) -> str:
        """
        Auto-generate a unique file name inside the export directory.

        Pattern: <stem>_<timestamp>.<extension>
        If the name already exists (e.g. two exports within the same
        second), a numeric suffix is appended to keep every export unique.

        Args:
            stem:      Base name without extension, e.g. 'analysis_report'.
            extension: File extension without a leading dot, e.g. 'md'.

        Returns:
            A unique file name (without the directory part).
        """
        base_name = f"{stem}_{_timestamp()}"
        file_name = f"{base_name}.{extension}"
        counter = 1
        while os.path.exists(os.path.join(self.output_dir, file_name)):
            file_name = f"{base_name}_{counter}.{extension}"
            counter += 1
        return file_name

    def _write_file(self, file_name: str, content: str) -> str:
        """
        Write text content into the export directory.

        Args:
            file_name: Target file name inside the export directory.
            content:   Text content to write (UTF-8).

        Returns:
            The relative path to the written file.
        """
        file_path = os.path.join(self.output_dir, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

    # ------------------------------------------------------------------
    # Raw-content exporters
    # ------------------------------------------------------------------

    def save_markdown_report(self, report_content: str,
                             filename: Optional[str] = None) -> str:
        """
        Save the AI-generated text report as a Markdown file.

        Args:
            report_content: The markdown text returned by the AI.
            filename:       Optional target file name. When omitted, a unique
                            timestamped name is auto-generated.

        Returns:
            The relative path to the saved report file.
        """
        file_name = filename or self._generate_file_name("analysis_report", "md")

        # Add a timestamp header to the exported markdown report
        timestamp_header = f"> Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        return self._write_file(file_name, timestamp_header + report_content)

    def save_html_report(self, report_html: str,
                         chart_filename: str = "../static/output_chart.png",
                         filename: Optional[str] = None) -> str:
        """
        Generate a comprehensive HTML report embedding both the visualization
        chart and the AI analysis text.

        Args:
            report_html:    The HTML fragment (or raw text) of the analysis.
            chart_filename: Relative path to the chart image referenced by
                            the page (default points to static/output_chart.png).
            filename:       Optional target file name. When omitted, a unique
                            timestamped name is auto-generated.

        Returns:
            The relative path to the saved HTML file.
        """
        file_name = filename or self._generate_file_name("report", "html")

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Automated Data Analysis Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; color: #333; }}
                h1 {{ color: #2c3e50; }}
                .chart-container {{ margin: 20px 0; }}
                img {{ max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; }}
                .report-body {{ background: #f9f9f9; padding: 20px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <h1>Automated Data Analysis Report</h1>
            <p><strong>Generated on:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

            <div class="chart-container">
                <h2>Visualization Chart</h2>
                <img src="{chart_filename}" alt="Analysis Chart">
            </div>

            <div class="report-body">
                <h2>AI Insights</h2>
                <div>{report_html}</div>
            </div>
        </body>
        </html>
        """

        return self._write_file(file_name, html_content)

    def save_text_report(self, report_content: str,
                         filename: Optional[str] = None) -> str:
        """
        Save the AI-generated report as a plain text (.txt) file.

        Args:
            report_content: The report text to save.
            filename:       Optional target file name. When omitted, a unique
                            timestamped name is auto-generated.

        Returns:
            The relative path to the saved text file.
        """
        file_name = filename or self._generate_file_name("analysis_report", "txt")
        return self._write_file(file_name, report_content)

    def save_json_report(self, data: dict, filename: Optional[str] = None) -> str:
        """
        Save a dictionary payload as a pretty-printed JSON file.

        Args:
            data:     The structured payload to persist (must be JSON-serializable).
            filename: Optional target file name. When omitted, a unique
                      timestamped name is auto-generated.

        Returns:
            The relative path to the saved JSON file.
        """
        file_name = filename or self._generate_file_name("report_export", "json")
        file_path = os.path.join(self.output_dir, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            # default=str converts any non-serializable object (datetimes,
            # paths, custom classes) to its string form instead of failing
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        return file_path

    # ------------------------------------------------------------------
    # Structured report exporter (AnalysisReport)
    # ------------------------------------------------------------------

    def export_analysis_report(self, report: Any, export_format: str = "md",
                               chart_filename: str = "../static/output_chart.png",
                               filename: Optional[str] = None) -> str:
        """
        Export a structured AnalysisReport object as a file.

        Uses the analyze package renderers so the exported markdown / HTML
        mirrors exactly what is displayed in the dashboard.

        Args:
            report:         The AnalysisReport object to export.
            export_format:  'md', 'html' or 'json'.
            chart_filename: Relative path to the chart image used in HTML exports.
            filename:       Optional target file name. When omitted, a unique
                            timestamped name is auto-generated.

        Returns:
            The relative path to the saved file.

        Raises:
            ValueError: If export_format is not 'md', 'html' or 'json'.
        """
        fmt = export_format.lower().strip(".")

        if fmt == "json":
            payload = {
                "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "report": _to_dict(report),
            }
            return self.save_json_report(payload, filename=filename)

        if fmt == "md":
            # Lazy import keeps this module lightweight for raw-text exports
            from analyze.report_renderer import render_report_to_markdown
            content = render_report_to_markdown(report)
            file_name = filename or self._generate_file_name("analysis_report", "md")
            return self._write_file(file_name, content)

        if fmt == "html":
            from analyze.report_renderer import render_report_to_html
            content = render_report_to_html(report)
            return self.save_html_report(content, chart_filename=chart_filename,
                                         filename=filename)

        raise ValueError(
            f"Unsupported export format '{export_format}'. "
            "Use 'md', 'html' or 'json'."
        )

    # ------------------------------------------------------------------
    # Export directory management
    # ------------------------------------------------------------------

    def list_exported_files(self) -> list[str]:
        """
        List all exported report files in the output directory.

        Returns:
            A list of file names, newest first.
        """
        if not os.path.exists(self.output_dir):
            return []
        files = [
            f for f in os.listdir(self.output_dir)
            if os.path.isfile(os.path.join(self.output_dir, f))
        ]
        # Sort newest first; use the file name as a deterministic tiebreaker
        # for exports created within the same second
        files.sort(
            key=lambda f: (
                os.path.getmtime(os.path.join(self.output_dir, f)),
                f,
            ),
            reverse=True,
        )
        return files
