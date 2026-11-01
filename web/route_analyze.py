# web/route_analyze.py
"""
API routes for dataset analysis and report generation.

Endpoints:
  POST /analyze            — Original endpoint: calls DeepSeek API and returns HTML report.
  POST /analyze/report     — New structured endpoint: generates a typed report (executive
                             summary, detailed, statistical, data quality, or comprehensive).
  GET  /analyze/report/types — Returns available report types as an HTML <select> element.
  POST /export-report      — Exports AI text report into the file_export folder.
                             Supports 'md', 'html', 'json', 'txt' formats and
                             auto-generates a unique timestamped file per export.
  GET  /download-report/{file_name} — Downloads the exported report file.

All display text and comments are in English.
"""

import os
import time
from datetime import datetime
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse

from AI.api_call import analyze_data_with_deepseek
from analyze import (
    ReportType,
    ReportGenerator,
    render_report_to_html,
)
from file_export.export_handler import ReportExporter

router = APIRouter()

# Initialize the report exporter targeting the 'file_export' folder
exporter = ReportExporter(output_dir="file_export")

# ─────────────────────────────────────────────────────────────────────
# Dataset path constant
# ─────────────────────────────────────────────────────────────────────
ACTIVE_DATASET_PATH = "uploads/active_dataset.xlsx"


def _dataset_exists() -> bool:
    """Check whether the user has uploaded an active dataset."""
    return os.path.exists(ACTIVE_DATASET_PATH)


def _missing_dataset_response() -> str:
    """Return a standardised warning when no dataset is available."""
    return """
    <div class="bg-amber-50 border border-amber-200 text-amber-700 p-4 rounded-xl text-sm">
        <strong>Dataset Missing:</strong> Please upload a dataset file first before running AI analysis.
    </div>
    """


# ─────────────────────────────────────────────────────────────────────
# Original /analyze endpoint (backward-compatible)
# ─────────────────────────────────────────────────────────────────────

@router.post("/analyze", response_class=HTMLResponse)
async def analyze_dataset(prompt: str = Form(...)):
    """
    Original analysis endpoint.

    Calls DeepSeek API with the uploaded dataset and user prompt,
    returning an HTML fragment containing the generated chart (if any)
    and the AI's markdown-formatted analysis report.

    This endpoint is kept for backward compatibility with the existing
    dashboard form. For structured / typed reports, use POST /analyze/report.
    """
    if not _dataset_exists():
        return _missing_dataset_response()

    text_report, chart_image_path = analyze_data_with_deepseek(
        ACTIVE_DATASET_PATH, ".xlsx", prompt
    )

    html_parts = ['<div class="space-y-4">']

    # --- Chart (if generated) ---
    static_chart = os.path.join("static", "output_chart.png")
    if os.path.exists(static_chart):
        ts = int(time.time())
        html_parts.append(f"""
        <div class="bg-white p-4 rounded-xl border border-gray-100 shadow-sm flex flex-col items-center">
            <h3 class="text-sm font-semibold text-gray-700 mb-3 w-full text-left">
                📈 AI-Generated Chart
            </h3>
            <img src="/static/output_chart.png?t={ts}"
                 alt="AI Generated Chart"
                 class="max-h-96 rounded-lg shadow-sm border border-gray-200" />
        </div>
        """)

    # --- Text report ---
    formatted = text_report.replace("\n", "<br>")
    html_parts.append(f"""
    <div class="bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
        <h3 class="text-sm font-semibold text-gray-700 mb-2">📝 AI Analysis Report</h3>
        <div class="text-sm text-gray-700 leading-relaxed font-sans">
            {formatted}
        </div>
    </div>
    """)

    html_parts.append("</div>")
    return "\n".join(html_parts)


# ─────────────────────────────────────────────────────────────────────
# New: structured report generation
# ─────────────────────────────────────────────────────────────────────

@router.post("/analyze/report", response_class=HTMLResponse)
async def generate_structured_report(
    prompt: str = Form(...),
    report_type: str = Form("comprehensive"),
):
    """
    Generate a structured, typed AI analysis report.

    Unlike /analyze which returns raw AI output, this endpoint
    produces a professionally formatted report with parsed sections,
    extracted insights, recommendations, and optional chart — all
    wrapped in a polished HTML layout.

    Args:
        prompt:      The user's analysis query or area of interest.
        report_type: One of the ReportType values (default: comprehensive).

    Returns:
        An HTML fragment with the structured report.
    """
    if not _dataset_exists():
        return _missing_dataset_response()

    # Resolve the report type (default to COMPREHENSIVE on invalid input)
    rtype = ReportType.from_string(report_type)

    try:
        # Generate the structured report
        generator = ReportGenerator()
        report = generator.generate(
            file_path=ACTIVE_DATASET_PATH,
            ext=".xlsx",
            user_prompt=prompt,
            report_type=rtype,
        )

        # Render to HTML
        html = render_report_to_html(report)

        return html

    except Exception as e:
        return f"""
        <div class="bg-red-50 border border-red-200 text-red-700 p-6 rounded-xl">
            <h3 class="font-semibold text-lg mb-2">⚠️ Report Generation Error</h3>
            <p class="text-sm">An unexpected error occurred while generating the report.</p>
            <pre class="mt-2 text-xs bg-red-100 p-3 rounded-lg overflow-x-auto">{str(e)}</pre>
            <p class="text-xs text-red-500 mt-2">Please check the dataset and try again.</p>
        </div>
        """


@router.get("/analyze/report/types", response_class=HTMLResponse)
async def list_report_types():
    """
    Return the available report types as an HTML <select> element.

    This can be used by the frontend to dynamically render a report-type
    dropdown picker.
    """
    options = "".join(
        f"""
        <option value="{rtype.value}"
                data-icon="{rtype.icon()}"
                data-desc="{rtype.description()}"
                {"selected" if rtype == ReportType.COMPREHENSIVE else ""}>
            {rtype.icon()} {rtype.display_name()}
        </option>
        """
        for rtype in ReportType
    )

    return f"""
    <div class="space-y-1">
        <label for="report-type" class="text-xs font-medium text-gray-600">
            Report Type
        </label>
        <select id="report-type" name="report_type"
                class="w-full border border-gray-300 rounded-lg p-2.5 text-sm
                       focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white">
            {options}
        </select>
        <p id="report-type-desc" class="text-xs text-gray-400 mt-1">
            {ReportType.COMPREHENSIVE.description()}
        </p>
    </div>
    """


# ─────────────────────────────────────────────────────────────────────
# Report Export & Download Endpoints
# ─────────────────────────────────────────────────────────────────────

@router.post("/export-report")
async def export_analysis_report(report_data: dict):
    """
    API endpoint to receive AI text report and export it into the file_export folder.

    Every export auto-generates a unique, timestamped file name so previous
    exports are never overwritten.

    Request body:
        content (str):  The report text/content to export.
        format  (str):  'md' (default), 'html', 'json' or 'txt'.
        filename (str, optional): Optional explicit file name (auto-generated otherwise).

    Returns:
        JSON with the status, the relative file path, and the file name.
    """
    try:
        content = report_data.get("content", "No content provided.")
        export_format = report_data.get("format", "md").lower()
        filename = report_data.get("filename")

        if export_format == "html":
            file_path = exporter.save_html_report(content, filename=filename)
        elif export_format == "json":
            payload = {
                "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "content": content,
            }
            file_path = exporter.save_json_report(payload, filename=filename)
        elif export_format == "txt":
            file_path = exporter.save_text_report(content, filename=filename)
        else:
            file_path = exporter.save_markdown_report(content, filename=filename)

        return {
            "status": "success",
            "message": "Report exported and saved to file_export successfully",
            "file_path": f"/{file_path}",
            "file_name": os.path.basename(file_path),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download-report/{file_name}")
async def download_exported_file(file_name: str):
    """
    Download the generated report file directly from the file_export folder.
    """
    # Prevent path traversal — only serve files inside the export directory
    safe_name = os.path.basename(file_name)
    file_path = os.path.join("file_export", safe_name)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=safe_name)
    raise HTTPException(status_code=404, detail="File not found in export directory")