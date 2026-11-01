# AI/api_call.py
"""
AI API call module for DeepSeek integration.

Provides both a simple query function and a full analysis pipeline
that loads a dataset, calls the AI, and optionally executes
AI-generated chart code. All prompts and display text are in English.
"""

import os
import re
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server environments
import matplotlib.pyplot as plt
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# DeepSeek model used for all AI analysis calls
DEEPSEEK_MODEL = "deepseek-v4-flash"

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def _get_client() -> OpenAI | None:
    """
    Create and return an OpenAI-compatible client for DeepSeek.

    Returns None if the API key is missing (caller should handle).
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def call_deepseek_api(df_preview: str, prompt: str) -> str:
    """
    Call DeepSeek API with a default analysis system prompt.

    Args:
        df_preview: A text representation of the dataset (columns, head, stats).
        prompt:     The user's analysis query.

    Returns:
        The model's markdown response, or an error message string.
    """
    system_instruction = (
        "You are an expert data analyst and visualization engineer. "
        "Analyze the dataset preview provided and answer the user's prompt professionally in Markdown. "
        "If the user asks for charts, visual insights, or if a plot is helpful: "
        "Include a valid executable Python code block using ```python ... ``` at the end. "
        "Requirements for the code block:\n"
        "1. Assume the DataFrame variable `df` is already loaded.\n"
        "2. Do NOT use `plt.show()`. Use `plt.savefig('static/output_chart.png', bbox_inches='tight')` instead.\n"
        "3. Ensure plot titles and labels are clear and well-formatted."
    )
    return _call_api(system_instruction, df_preview, prompt)


def call_deepseek_api_custom(df_preview: str, system_prompt: str, user_prompt: str) -> str:
    """
    Call DeepSeek API with a custom system prompt.

    This is the flexible variant used by the report generator to pass
    structured report-type-specific prompts.

    Args:
        df_preview:    A text representation of the dataset.
        system_prompt: The system-level instruction for the AI.
        user_prompt:   The user's specific query or additional instructions.

    Returns:
        The model's markdown response, or an error message string.
    """
    return _call_api(system_prompt, df_preview, user_prompt)


def _call_api(system_prompt: str, df_preview: str, user_message: str) -> str:
    """
    Low-level API call shared by all public functions.

    Args:
        system_prompt: System-level instruction for the model.
        df_preview:    Dataset preview text included in the user message.
        user_message:  The user's query.

    Returns:
        The model's response text, or an error message.
    """
    client = _get_client()
    if client is None:
        return (
            "### Configuration Required\n"
            "`DEEPSEEK_API_KEY` is not set in your `.env` file. "
            "Please add it and restart the server."
        )

    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Dataset Preview:\n{df_preview}\n\nUser Query: {user_message}",
                },
            ],
            temperature=0.2,
            stream=False,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"### DeepSeek API Error\nDetails: {str(e)}"


def _load_dataset(file_path: str, ext: str) -> pd.DataFrame | None:
    """
    Load a dataset from disk into a pandas DataFrame.

    Returns None (and prints the error) if loading fails.
    """
    try:
        if ext in (".xlsx", ".xls"):
            return pd.read_excel(file_path)
        elif ext == ".csv":
            return pd.read_csv(file_path)
        else:
            # Fallback: try Excel first, then CSV
            try:
                return pd.read_excel(file_path)
            except Exception:
                return pd.read_csv(file_path)
    except Exception as e:
        print(f"[_load_dataset] Failed to load {file_path}: {e}")
        return None


def _build_preview(df: pd.DataFrame) -> str:
    """
    Build a textual preview string of a DataFrame for the AI.

    Includes column names, shape, first rows, and summary statistics.
    """
    return (
        f"Columns: {df.columns.tolist()}\n"
        f"Shape (Rows, Cols): {df.shape}\n"
        f"First 5 Rows:\n{df.head(5).to_string()}\n"
        f"Summary Stats:\n{df.describe(include='all').to_string()}"
    )


def _execute_chart_code(df: pd.DataFrame, text: str) -> str | None:
    """
    Extract and execute a Python chart code block from the AI's response.

    Looks for a ```python ... ``` block, replaces plt.savefig paths
    to point to static/output_chart.png, and executes the code.

    Args:
        df:   The dataset DataFrame (injected into the exec scope).
        text: The AI response text to search for code blocks.

    Returns:
        The path to the saved chart image, or None on failure.
    """
    code_match = re.search(r"```(?:python)?\s*(.*?)\s*```", text, re.DOTALL)
    if not code_match:
        return None

    python_code = code_match.group(1)

    # Force the save path regardless of what the AI wrote
    python_code = re.sub(
        r"plt\.savefig\s*\(\s*['\"].*?['\"]",
        "plt.savefig('static/output_chart.png'",
        python_code,
    )

    try:
        os.makedirs("static", exist_ok=True)

        # Clear any previous matplotlib state
        plt.clf()
        plt.cla()
        plt.close("all")

        exec_scope = {"df": df, "plt": plt, "pd": pd}
        exec(python_code, exec_scope)
        plt.close("all")

        target_img = os.path.join("static", "output_chart.png")
        return target_img if os.path.exists(target_img) else None
    except Exception as e:
        print(f"[_execute_chart_code] Failed: {e}")
        return None


def analyze_data_with_deepseek(file_path: str, ext: str, prompt: str) -> tuple[str, str | None]:
    """
    High-level analysis entry point: load data -> call AI -> execute chart code.

    This is the original integration function kept for backward compatibility
    with the existing /analyze route.

    Args:
        file_path: Path to the dataset file on disk.
        ext:       File extension (e.g. '.xlsx', '.csv').
        prompt:    The user's analysis query.

    Returns:
        A tuple of (text_report, chart_image_path_or_None).
    """
    df = _load_dataset(file_path, ext)
    if df is None:
        return "### File Error\nFailed to load dataset. Check that the file exists and is a valid format.", None

    if df.empty:
        return "### Dataset is Empty\nNo valid rows inside the uploaded file.", None

    df_preview = _build_preview(df)
    text_report = call_deepseek_api(df_preview, prompt)
    chart_path = _execute_chart_code(df, text_report)

    return text_report, chart_path