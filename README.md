# DeepSeek Automated Data Analyzer V1.0

Welcome to **DeepSeek Automated Data Analyzer**, a lightweight, intelligent web application designed to empower users to analyze tabular datasets and generate data visualizations dynamically using **DeepSeek AI** and **Python**.

---

## 👨‍💻 Developer

* **Developer:** JaceHe342 (A Canadian high school student)

---

## 🌟 Key Features

* **Multi-Format Dataset Support:** Upload data in **CSV**, **Excel (`.xlsx`, `.xls`)**, or **JSON** formats.
* **AI-Powered Insights & Chat:** Uses the DeepSeek API (`deepseek-v4-flash`) via the official OpenAI SDK to review dataset statistics and answer user prompts in professional Markdown reports.
* **Dynamic Code Execution:** Automatically extracts and safely executes Python plotting code blocks returned by DeepSeek to generate customized data charts.
* **Cache-Busting Image Rendering:** Automatically prevents browser caching to render freshly generated charts instantly.
* **Cost-Efficient:** Powered by DeepSeek's high-performance and extremely cost-effective API infrastructure.

---

## 📂 Project Structure

```text
AutoDataViz-API/
    |_ AI/
        |_ api_call.py        # DeepSeek API integration & safe code execution
        |_ __init__.py
    |_ analyze/
        |_ __init__.py
        |_ models.py
        |_ report_generator.py
        |_report_prompts.py
        |_ report_renderer.py
    |_ file_export/
        |_ __init__.py
        |_ export_handler.py
    |_history
        |___init__.py
        |_models.py
        |_recorder.py
        |_renderer.py
        |_routes.py
        |_store.py
    |_ plot/
        |_ __init__.py
    |_ static/                # Stores dynamically generated charts (e.g., output_chart.png)
    |_ uploads/               # Temporary storage for active user datasets
    |_ web/
        |_ __init__.py
        |_ main_web.py        # FastAPI application and static file mounting
        |_ route_analyze.py   # Analysis route handling prompts and chart rendering
        |_ route_upload.py    # File upload route handling
    |_ config.py              # Configuration settings
    |_ main.py                # Application entry point
    |_ .env.example           # Environment variable template
    |_ requirements.txt       # Project dependencies

```![img.png](img.png)

---

## 🛠️ Quick Start & Installation

### 1. Clone the Repository

```bash
git clone https://github.com/JaceHe342/AutoDataViz-API.git
cd AutoDataViz-API

```

### 2. Install Dependencies

Install all necessary Python packages using `requirements.txt`:

```bash
pip install -r requirements.txt

```

### 3. Configure Environment Variables

Create a `.env` file in the project root directory based on `.env.example`:

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here

```

### 4. Run the Application

Start the FastAPI server using Uvicorn:

```bash
uvicorn web.main_web:web --reload

```

Open your browser and navigate to `[http://127.0.0.1:8000](http://127.0.0.1:8000)` to start analyzing your data!!
