# analyze/report_generator.py
"""
Report generator — the core module that produces structured AnalysisReport
objects from a dataset and a user query.

Flow:
  1. Load the dataset from disk.
  2. Build a textual preview for the AI.
  3. Select the appropriate system prompt for the requested ReportType.
  4. Call the DeepSeek API (custom prompt variant).
  5. Parse the markdown response into structured sections.
  6. Extract key insights and recommendations from dedicated sections.
  7. Execute any chart code embedded in the response.
  8. Return a fully populated AnalysisReport.

All comments and display text are in English.
"""

import os
import re
from typing import Optional
import pandas as pd

from AI.api_call import (
    _load_dataset,
    _build_preview,
    call_deepseek_api_custom,
    _execute_chart_code,
)
from analyze.models import ReportType, ReportSection, ChartInfo, AnalysisReport
from analyze.report_prompts import get_prompt


# ---------------------------------------------------------------------------
# Section heading patterns
# ---------------------------------------------------------------------------
_H1_RE = re.compile(r"^# (.+)$", re.MULTILINE)
_H2_RE = re.compile(r"^## (.+)$", re.MULTILINE)
_H3_RE = re.compile(r"^### (.+)$", re.MULTILINE)

# Sections whose content should be parsed as insight / recommendation lists
_INSIGHT_HEADINGS = re.compile(r"^(?:key\s+)?insights?$", re.IGNORECASE)
_RECOMMENDATION_HEADINGS = re.compile(r"^(?:key\s+)?recommendations?$", re.IGNORECASE)

# Pattern to strip ```python blocks from section content (they are handled separately)
_PYTHON_BLOCK_RE = re.compile(r"```(?:python)?\s*.*?\s*```", re.DOTALL)


def _parse_sections(markdown_text: str) -> list[ReportSection]:
    """
    Parse markdown text into a list of ReportSection objects.

    Handles #, ##, and ### headings. Content before the first heading
    is treated as a preamble and placed in a section with title "Summary"
    at level 1.
    """
    if not markdown_text or not markdown_text.strip():
        return []

    sections: list[ReportSection] = []
    lines = markdown_text.split("\n")
    current_title = ""
    current_level = 1
    current_content: list[str] = []
    in_code_block = False
    heading_found = False

    for line in lines:
        # Track whether we are inside a fenced code block so we don't
        # mistake # ... inside a comment for a heading.
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            current_content.append(line)
            continue

        if in_code_block:
            current_content.append(line)
            continue

        h1_match = re.match(r"^# (.+)$", line)
        h2_match = re.match(r"^## (.+)$", line) if not h1_match else None
        h3_match = re.match(r"^### (.+)$", line) if not h1_match and not h2_match else None

        if h1_match:
            # Save the previous section before starting a new one
            if heading_found:
                sections.append(
                    ReportSection(
                        title=current_title,
                        content="\n".join(current_content).strip(),
                        level=current_level,
                    )
                )
            elif current_content:
                # Content before the first heading
                sections.append(
                    ReportSection(
                        title="Summary",
                        content="\n".join(current_content).strip(),
                        level=1,
                    )
                )
            current_title = h1_match.group(1).strip()
            current_level = 1
            current_content = []
            heading_found = True
        elif h2_match:
            if heading_found:
                sections.append(
                    ReportSection(
                        title=current_title,
                        content="\n".join(current_content).strip(),
                        level=current_level,
                    )
                )
            elif current_content:
                sections.append(
                    ReportSection(
                        title="Summary",
                        content="\n".join(current_content).strip(),
                        level=1,
                    )
                )
            current_title = h2_match.group(1).strip()
            current_level = 2
            current_content = []
            heading_found = True
        elif h3_match:
            if heading_found:
                sections.append(
                    ReportSection(
                        title=current_title,
                        content="\n".join(current_content).strip(),
                        level=current_level,
                    )
                )
            elif current_content:
                sections.append(
                    ReportSection(
                        title="Summary",
                        content="\n".join(current_content).strip(),
                        level=1,
                    )
                )
            current_title = h3_match.group(1).strip()
            current_level = 3
            current_content = []
            heading_found = True
        else:
            current_content.append(line)

    # Flush the last section
    if heading_found:
        sections.append(
            ReportSection(
                title=current_title,
                content="\n".join(current_content).strip(),
                level=current_level,
            )
        )
    elif current_content:
        sections.append(
            ReportSection(
                title="Summary",
                content="\n".join(current_content).strip(),
                level=1,
            )
        )

    # Strip Python code blocks from section content (they are handled
    # separately by _execute_chart_code and should not appear in rendered text).
    for sec in sections:
        sec.content = _PYTHON_BLOCK_RE.sub("", sec.content).strip()

    return sections


def _extract_list_items(text: str) -> list[str]:
    """
    Extract bullet or numbered list items from text.

    Handles:
      - Item
      * Item
      1. Item
      1) Item
    """
    items: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        # Match bullet list items
        bullet_match = re.match(r"^[-*+]\s+(.+)$", stripped)
        if bullet_match:
            items.append(bullet_match.group(1).strip())
            continue
        # Match numbered list items
        num_match = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if num_match:
            items.append(num_match.group(1).strip())
    return items


def _find_section(sections: list[ReportSection], heading_pattern: re.Pattern) -> Optional[ReportSection]:
    """Return the first section whose title matches the given pattern."""
    for sec in sections:
        if heading_pattern.match(sec.title.strip()):
            return sec
    return None


def _extract_summary(sections: list[ReportSection], raw_text: str) -> str:
    """
    Extract an executive summary from the report.

    First tries the "Executive Summary" or "Overview" section.
    Falls back to the first paragraph of the first section.
    """
    summary_pattern = re.compile(r"^(?:executive\s+)?summary$|^overview$", re.IGNORECASE)
    sec = _find_section(sections, summary_pattern)
    if sec and sec.content:
        # Take just the first paragraph
        paragraphs = [p.strip() for p in sec.content.split("\n\n") if p.strip()]
        return paragraphs[0] if paragraphs else sec.content[:300]

    # Fallback: first paragraph of the entire raw text
    paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
    for p in paragraphs:
        # Skip headings and empty lines
        if not re.match(r"^#", p) and len(p) > 40:
            return p[:500]
    return ""


def _guess_report_title(sections: list[ReportSection], raw_text: str) -> str:
    """
    Derive a report title from the first level-1 section heading,
    or from the first line of raw text.
    """
    if sections and sections[0].level == 1:
        return sections[0].title
    # Fallback: first non-empty line
    for line in raw_text.strip().split("\n"):
        stripped = line.strip().strip("#").strip()
        if stripped:
            return stripped
    return "Analysis Report"


def _clean_python_blocks(text: str) -> str:
    """Remove Python code blocks from text for cleaner display."""
    return _PYTHON_BLOCK_RE.sub("", text).strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class ReportGenerator:
    """
    Generates structured, AI-powered analysis reports from datasets.

    Usage:
        generator = ReportGenerator()
        report = generator.generate("path/to/file.xlsx", ".xlsx",
                                     "Analyze sales trends", ReportType.COMPREHENSIVE)
        html = render_report_to_html(report)
    """

    def generate(
        self,
        file_path: str,
        ext: str,
        user_prompt: str,
        report_type: ReportType = ReportType.COMPREHENSIVE,
    ) -> AnalysisReport:
        """
        Generate a structured AnalysisReport from a dataset.

        Args:
            file_path:   Path to the dataset file on disk.
            ext:         File extension (e.g. '.xlsx', '.csv').
            user_prompt: The user's query or area of interest.
            report_type: The type of report to generate.

        Returns:
            A fully populated AnalysisReport. If loading or generation
            fails, the report's raw_text contains the error message and
            sections will be empty.
        """
        # --- 1. Load dataset ---
        df = _load_dataset(file_path, ext)
        if df is None:
            return AnalysisReport(
                title="Error: Could Not Load Dataset",
                report_type=report_type,
                raw_text="Failed to load the dataset. Please check the file path and format.",
            )

        if df.empty:
            return AnalysisReport(
                title="Error: Empty Dataset",
                report_type=report_type,
                raw_text="The uploaded dataset contains no rows. Please upload a non-empty file.",
            )

        # --- 2. Build dataset preview ---
        df_preview = _build_preview(df)

        # --- 3. Select system prompt for the requested report type ---
        system_prompt = get_prompt(report_type)

        # Add the user's prompt as additional context
        full_user_prompt = (
            f"Please generate a {report_type.display_name().lower()} based on the dataset. "
            f"The user is specifically interested in: {user_prompt}"
        )

        # --- 4. Call the AI API ---
        raw_text = call_deepseek_api_custom(df_preview, system_prompt, full_user_prompt)

        # --- 5. Parse sections ---
        sections = _parse_sections(raw_text)

        # --- 6. Extract insights and recommendations ---
        insights_sec = _find_section(sections, _INSIGHT_HEADINGS)
        recommendations_sec = _find_section(sections, _RECOMMENDATION_HEADINGS)

        key_insights = _extract_list_items(insights_sec.content) if insights_sec else []
        recommendations = _extract_list_items(recommendations_sec.content) if recommendations_sec else []

        # If parsing produced items but they were not under dedicated
        # headings, fall back to scanning the raw text for list items.
        if not key_insights:
            potential = _extract_list_items(raw_text)
            key_insights = potential[:8] if potential else []

        # --- 7. Extract summary ---
        summary = _extract_summary(sections, raw_text)

        # --- 8. Guess a title ---
        title = _guess_report_title(sections, raw_text)

        # --- 9. Execute chart code ---
        chart_path = _execute_chart_code(df, raw_text)
        chart = ChartInfo(path=chart_path, caption="AI-Generated Visualization") if chart_path else None

        # Clean python blocks from section content for display
        for sec in sections:
            sec.content = _clean_python_blocks(sec.content)

        # --- 10. Build and return the report ---
        return AnalysisReport(
            title=title,
            report_type=report_type,
            sections=sections,
            chart=chart,
            summary=summary,
            key_insights=key_insights,
            recommendations=recommendations,
            raw_text=raw_text,
        )


# Convenience module-level function
def generate_report(
    file_path: str,
    ext: str,
    user_prompt: str,
    report_type: ReportType = ReportType.COMPREHENSIVE,
) -> AnalysisReport:
    """
    Generate a structured AnalysisReport (convenience wrapper).

    Usage:
        report = generate_report("data.xlsx", ".xlsx", "Analyze trends")
    """
    generator = ReportGenerator()
    return generator.generate(file_path, ext, user_prompt, report_type)
