# analyze/report_renderer.py
"""
HTML renderer for structured AnalysisReport objects.

Converts an AnalysisReport into a polished HTML fragment styled with
Tailwind CSS, matching the existing dashboard design language.

Supports:
  - Report header with type icon and title.
  - Summary callout box.
  - Key-insights highlight card.
  - Section-by-section body with proper heading hierarchy.
  - Chart image display.
  - Recommendations callout box.
  - Basic markdown-to-HTML conversion (bold, italic, code, links, lists).
"""

import re
from typing import Optional

from analyze.models import AnalysisReport, ReportSection


# ---------------------------------------------------------------------------
# Markdown → HTML helpers
# ---------------------------------------------------------------------------

def _md_to_html(text: str) -> str:
    """
    Convert common markdown inline formatting to HTML.

    Handles: **bold**, *italic*, `inline code`, [links](url),
    bullet lists, numbered lists, and paragraphs.
    """
    if not text:
        return ""

    # Escape HTML entities first to prevent injection
    text = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    # Restore entities inside code blocks
    lines = text.split("\n")
    result_lines: list[str] = []
    in_code_block = False

    for line in lines:
        stripped = line.strip()

        # Code block fences — handled upstream, but just in case
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            result_lines.append(f"<pre class=\"bg-gray-100 p-3 rounded-lg overflow-x-auto text-xs\">{line}</pre>")
            continue

        # --- Bullet list items ---
        bullet_match = re.match(r"^[-*+]\s+(.+)$", stripped)
        if bullet_match:
            content = _inline_md(bullet_match.group(1))
            result_lines.append(f"<li class=\"ml-4 list-disc text-gray-700\">{content}</li>")
            continue

        # --- Numbered list items ---
        num_match = re.match(r"^(\d+)[.)]\s+(.+)$", stripped)
        if num_match:
            content = _inline_md(num_match.group(2))
            result_lines.append(f"<li class=\"ml-4 list-decimal text-gray-700\">{content}</li>")
            continue

        # --- Table rows ---
        if "|" in stripped and stripped.startswith("|"):
            result_lines.append(_table_row_to_html(stripped, lines, lines.index(line)))
            continue

        # --- Horizontal rule ---
        if re.match(r"^---+\s*$", stripped) or re.match(r"^\*\*\*+\s*$", stripped):
            result_lines.append("<hr class=\"my-4 border-gray-200\" />")
            continue

        # --- Regular paragraph ---
        if stripped:
            content = _inline_md(stripped)
            result_lines.append(f"<p class=\"text-sm text-gray-700 leading-relaxed mb-2\">{content}</p>")
        else:
            # Empty line → paragraph break
            result_lines.append("")

    html = "\n".join(result_lines)

    # Wrap consecutive <li> elements in <ul> / <ol>
    html = _wrap_list_items(html)

    return html


def _inline_md(text: str) -> str:
    """Process inline markdown: bold, italic, code, links."""
    # Inline code: `code`
    text = re.sub(r"`([^`]+)`", r"<code class=\"bg-gray-100 px-1.5 py-0.5 rounded text-xs font-mono text-pink-600\">\1</code>", text)

    # Bold: **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong class=\"font-semibold text-gray-900\">\1</strong>", text)

    # Italic: *text* (but not inside words, and not already consumed)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em class=\"italic text-gray-700\">\1</em>", text)

    # Links: [text](url)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r"<a href=\"\1\" class=\"text-blue-600 underline hover:text-blue-800\" target=\"_blank\" rel=\"noopener\">\1</a>",
        text,
    )

    return text


def _table_row_to_html(line: str, all_lines: list[str], idx: int) -> str:
    """
    Convert a markdown table row to an HTML table row.
    Expects lines like: | col1 | col2 | col3 |
    """
    cells = [c.strip() for c in line.split("|") if c.strip()]
    if not cells:
        return ""

    # Check if this is a separator row (|---|---|---|)
    if all(re.match(r"^[-:]+$", c) for c in cells):
        return ""

    tag = "th" if idx == 1 or (idx > 0 and re.match(r"^[-| ]+$", all_lines[idx - 1].strip())) else "td"
    # Actually, the first row is typically the header
    # And the second row is the separator (|---|---|)
    # So if we're at index 0 or there's a separator before us, we're a header row
    is_header = False
    if idx == 0:
        is_header = True
    elif idx >= 2:
        # Check if the previous row is a separator
        prev = all_lines[idx - 1].strip()
        if prev.startswith("|") and all(re.match(r"^[-:| ]+$", c.strip()) for c in prev.split("|") if c.strip()):
            is_header = True

    tag = "th" if is_header else "td"
    cell_html = "".join(
        f"<{tag} class=\"border border-gray-300 px-3 py-2 text-sm {'font-semibold bg-gray-50' if tag == 'th' else 'text-gray-700'}\">"
        f"{_inline_md(c)}</{tag}>"
        for c in cells
    )
    return f"<tr class=\"border-b border-gray-200\">{cell_html}</tr>"


def _wrap_list_items(html: str) -> str:
    """
    Wrap consecutive <li> elements in <ul> or <ol> tags.

    Detects list-disc → <ul>, list-decimal → <ol>.
    """
    # Wrap unordered lists
    html = re.sub(
        r"(<li class=\"ml-4 list-disc[^>]*>.*?</li>\s*)+",
        lambda m: f"<ul class=\"list-disc pl-5 mb-3 space-y-1\">{m.group(0)}</ul>",
        html,
    )
    # Wrap ordered lists
    html = re.sub(
        r"(<li class=\"ml-4 list-decimal[^>]*>.*?</li>\s*)+",
        lambda m: f"<ol class=\"list-decimal pl-5 mb-3 space-y-1\">{m.group(0)}</ol>",
        html,
    )
    return html


# ---------------------------------------------------------------------------
# Section rendering
# ---------------------------------------------------------------------------

def _render_section(section: ReportSection) -> str:
    """Render a single ReportSection as an HTML card."""
    heading_size = {
        1: "text-lg font-bold text-gray-900 mb-3",
        2: "text-base font-semibold text-gray-800 mb-2 mt-4",
        3: "text-sm font-medium text-gray-700 mb-2 mt-3",
    }.get(section.level, "text-base font-semibold text-gray-800 mb-2")

    border_color = {
        1: "border-l-4 border-blue-500 pl-4",
        2: "",
        3: "",
    }.get(section.level, "")

    content_html = _md_to_html(section.content)

    if section.level == 1:
        return f"""
        <div class="mb-6 {border_color}">
            <h2 class="{heading_size}">{section.title}</h2>
            <div class="text-gray-700 space-y-1">{content_html}</div>
        </div>
        """
    else:
        return f"""
        <div class="mb-4">
            <h3 class="{heading_size}">{section.title}</h3>
            <div class="text-gray-700 space-y-1">{content_html}</div>
        </div>
        """


# ---------------------------------------------------------------------------
# Public renderer
# ---------------------------------------------------------------------------

def render_report_to_html(report: AnalysisReport) -> str:
    """
    Convert an AnalysisReport into a polished HTML fragment.

    The returned HTML uses Tailwind CSS classes and is designed to be
    injected into the existing dashboard's `#preview-container` element.

    Args:
        report: The structured report to render.

    Returns:
        An HTML string ready for HTMX injection.
    """
    # --- Error state ---
    if report.raw_text and not report.sections and not report.chart:
        # Likely an error report
        return f"""
        <div class="bg-red-50 border border-red-200 text-red-700 p-6 rounded-xl">
            <h3 class="font-semibold text-lg mb-2">⚠️ Report Generation Failed</h3>
            <p class="text-sm">{report.raw_text}</p>
        </div>
        """

    # --- Report header ---
    header = f"""
    <div class="flex items-center gap-3 mb-5 pb-4 border-b border-gray-200">
        <span class="text-2xl">{report.report_type.icon()}</span>
        <div>
            <h2 class="text-xl font-bold text-gray-900">{report.title}</h2>
            <p class="text-xs text-gray-500 mt-0.5">
                {report.report_type.display_name()}
                {' · Includes AI-generated chart' if report.chart else ''}
            </p>
        </div>
    </div>
    """

    # --- Summary box (if available) ---
    summary_html = ""
    if report.summary:
        summary_html = f"""
        <div class="bg-blue-50 border border-blue-100 rounded-xl p-4 mb-6">
            <p class="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-1">Executive Summary</p>
            <p class="text-sm text-blue-900 leading-relaxed">{report.summary}</p>
        </div>
        """

    # --- Key insights card (if available) ---
    insights_html = ""
    if report.key_insights:
        items_html = "".join(
            f"<li class=\"flex items-start gap-2 text-sm text-gray-700\">"
            f"<span class=\"text-blue-500 mt-0.5 flex-shrink-0\">▸</span>"
            f"<span>{_inline_md(insight)}</span></li>"
            for insight in report.key_insights
        )
        insights_html = f"""
        <div class="bg-amber-50 border border-amber-100 rounded-xl p-4 mb-6">
            <p class="text-xs font-semibold text-amber-700 uppercase tracking-wide mb-2">Key Insights</p>
            <ul class="space-y-1.5">{items_html}</ul>
        </div>
        """

    # --- Chart section (if available) ---
    chart_html = ""
    if report.chart and report.chart.path and os.path.exists(report.chart.path):
        import time
        timestamp = int(time.time())
        chart_html = f"""
        <div class="bg-white p-4 rounded-xl border border-gray-100 shadow-sm flex flex-col items-center mb-6">
            <h3 class="text-sm font-semibold text-gray-700 mb-3 w-full text-left">
                📈 {report.chart.caption}
            </h3>
            <img src="/static/output_chart.png?t={timestamp}"
                 alt="AI Generated Chart"
                 class="max-h-96 rounded-lg shadow-sm border border-gray-200" />
        </div>
        """

    # --- Body sections ---
    sections_html = ""
    for section in report.sections:
        # Skip sections already displayed (summary, insights, recommendations)
        title_lower = section.title.strip().lower()
        if re.match(r"^(?:executive\s+)?summary$", title_lower) and report.summary:
            continue
        if re.match(r"^(?:key\s+)?insights?$", title_lower) and report.key_insights:
            continue
        if re.match(r"^(?:key\s+)?recommendations?$", title_lower) and report.recommendations:
            continue

        sections_html += _render_section(section)

    # --- Recommendations (if available) ---
    recommendations_html = ""
    if report.recommendations:
        items_html = "".join(
            f"<li class=\"flex items-start gap-2 text-sm text-gray-700\">"
            f"<span class=\"text-green-500 mt-0.5 flex-shrink-0\">▸</span>"
            f"<span>{_inline_md(rec)}</span></li>"
            for rec in report.recommendations
        )
        recommendations_html = f"""
        <div class="bg-green-50 border border-green-100 rounded-xl p-4 mt-6">
            <p class="text-xs font-semibold text-green-700 uppercase tracking-wide mb-2">Recommendations</p>
            <ul class="space-y-1.5">{items_html}</ul>
        </div>
        """

    # --- Footer ---
    footer = """
    <div class="mt-6 pt-4 border-t border-gray-100 text-center">
        <p class="text-xs text-gray-400">
            Report generated by AI · DeepSeek Automated Data Analyzer
        </p>
    </div>
    """

    # --- Assemble ---
    html = f"""
    <div class="space-y-1">
        {header}
        {summary_html}
        {insights_html}
        {chart_html}
        {sections_html}
        {recommendations_html}
        {footer}
    </div>
    """

    return html


def render_report_to_markdown(report: AnalysisReport) -> str:
    """
    Convert an AnalysisReport to plain markdown text.

    Useful for API consumers who prefer raw text over HTML.

    Args:
        report: The structured report to render.

    Returns:
        A markdown-formatted string.
    """
    lines: list[str] = []

    # Title
    lines.append(f"# {report.title}")
    lines.append(f"*{report.report_type.display_name()}*\n")

    # Summary
    if report.summary:
        lines.append(f"**Executive Summary**\n{report.summary}\n")

    # Key insights
    if report.key_insights:
        lines.append("## Key Insights")
        for insight in report.key_insights:
            lines.append(f"- {insight}")
        lines.append("")

    # Sections
    for section in report.sections:
        title_lower = section.title.strip().lower()
        if re.match(r"^(?:executive\s+)?summary$", title_lower) and report.summary:
            continue
        if re.match(r"^(?:key\s+)?insights?$", title_lower) and report.key_insights:
            continue
        if re.match(r"^(?:key\s+)?recommendations?$", title_lower) and report.recommendations:
            continue

        prefix = "#" * section.level
        lines.append(f"{prefix} {section.title}")
        lines.append(section.content)
        lines.append("")

    # Recommendations
    if report.recommendations:
        lines.append("## Recommendations")
        for rec in report.recommendations:
            lines.append(f"- {rec}")
        lines.append("")

    return "\n".join(lines).strip()


# Import os for path existence check in chart rendering
import os
