# main_web.py
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles  # Import StaticFiles module

try:
    from web.route_upload import router as upload_router
    from web.route_analyze import router as analyze_router
except ImportError as e:
    print(f'FILE ERROR IN MAIN_WEB!!! Details: {e}')
    raise e

web = FastAPI(title='DeepSeek Automated Data Analyzer')

# Ensure the static and export directories exist on server startup
os.makedirs("static", exist_ok=True)
os.makedirs("file_export", exist_ok=True)

# Mount the 'static' folder to the '/static' route
web.mount("/static", StaticFiles(directory="static"), name="static")

web.include_router(upload_router)
web.include_router(analyze_router)


# HTMLResponse to render the custom DeepSeek dashboard interface
@web.get("/", response_class=HTMLResponse)
def read_root():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DeepSeek Data Analyzer</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://unpkg.com/htmx.org@1.9.10"></script>
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    </head>
    <body class="bg-gray-50 text-gray-800 font-sans">

        <!-- Navigation Bar with DeepSeek Branding -->
        <nav class="bg-blue-600 text-white px-6 py-4 flex justify-between items-center shadow-md">
            <h1 class="text-xl font-bold flex items-center gap-2">
                🐳 DeepSeek Automated Data Analyzer V1.0
            </h1>
            <div class="flex gap-4">
                <a href="/docs" target="_blank" class="hover:text-blue-200 transition">API Docs</a>
            </div>
        </nav>

        <main class="max-w-7xl mx-auto p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">

            <!-- Left Panel: Control Form -->
            <section class="lg:col-span-1 space-y-6">

                <!-- 1. Upload Dataset Block -->
                <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                    <h2 class="text-lg font-semibold mb-3">1. Upload Dataset</h2>

                    <form hx-post="/upload" hx-encoding="multipart/form-data" hx-target="#preview-container" class="space-y-3">
                        <div class="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-500 cursor-pointer transition relative">
                            <input 
                                id="file-input"
                                type="file" 
                                name="file" 
                                class="absolute inset-0 w-full h-full opacity-0 cursor-pointer" 
                                onchange="this.form.requestSubmit()" 
                            />
                            <p class="text-sm text-gray-500 mb-2">Click or drag & drop file here</p>
                            <p class="text-xs text-gray-400">Supports CSV, Excel (.xlsx, .xls) and JSON</p>
                        </div>
                    </form>

                    <div class="mt-4 border-t pt-3 flex justify-end">
                        <button 
                            hx-post="/delete" 
                            hx-target="#preview-container" 
                            onclick="document.getElementById('file-input').value = '';"
                            class="text-xs font-medium text-red-600 hover:text-red-800 hover:bg-red-50 px-2.5 py-1.5 rounded-md transition flex items-center gap-1 border border-red-200"
                        >
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                            Clear Active Dataset
                        </button>
                    </div>
                </div>

                <!-- 2. Quick Analysis (original form) -->
                <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                    <h2 class="text-lg font-semibold mb-3 flex items-center gap-2">
                        <span class="text-blue-500">⚡</span> Quick Analysis
                    </h2>

                    <form hx-post="/analyze" hx-target="#preview-container">
                        <textarea
                            name="prompt"
                            rows="3"
                            placeholder="e.g., Analyze the sales trends and plot a pie chart for book categories..."
                            class="w-full border border-gray-300 rounded-lg p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 mb-3"
                        ></textarea>

                        <button type="submit"
                                class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 rounded-lg text-sm transition flex justify-center items-center gap-2">
                            🐳 Run DeepSeek Analysis
                        </button>
                    </form>
                </div>

                <!-- 3. Structured Report (new) -->
                <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                    <h2 class="text-lg font-semibold mb-3 flex items-center gap-2">
                        <span class="text-green-500">📑</span> Structured Report
                    </h2>
                    <p class="text-xs text-gray-400 mb-3">
                        Generate a professionally formatted report with parsed sections,
                        key insights, and recommendations.
                    </p>

                    <form hx-post="/analyze/report" hx-target="#preview-container">
                        <textarea
                            name="prompt"
                            rows="3"
                            placeholder="e.g., Analyze customer churn patterns and provide recommendations..."
                            class="w-full border border-gray-300 rounded-lg p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 mb-3"
                        ></textarea>

                        <!-- Report type dropdown (loaded dynamically) -->
                        <div id="report-type-picker"
                             hx-get="/analyze/report/types"
                             hx-trigger="load"
                             class="mb-3">
                            <div class="text-xs text-gray-400 animate-pulse">Loading report types...</div>
                        </div>

                        <button type="submit"
                                class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 rounded-lg text-sm transition flex justify-center items-center gap-2">
                            📄 Generate Report
                        </button>
                    </form>
                </div>

            </section>

            <!-- Right Panel: Results Output -->
            <section class="lg:col-span-2 bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-between">
                <div>
                    <div class="flex justify-between items-center mb-4">
                        <h2 class="text-lg font-semibold">Results &amp; DeepSeek Report</h2>

                        <!-- Export Actions Panel -->
                        <div class="flex items-center gap-2">
                            <button onclick="exportReport('md')"
                                    class="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium px-3 py-1.5 rounded-lg transition border border-gray-300 flex items-center gap-1">
                                📥 Export MD
                            </button>
                            <button onclick="exportReport('html')"
                                    class="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium px-3 py-1.5 rounded-lg transition border border-gray-300 flex items-center gap-1">
                                🌐 Export HTML
                            </button>
                            <button onclick="exportReport('json')"
                                    class="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium px-3 py-1.5 rounded-lg transition border border-gray-300 flex items-center gap-1">
                                📦 Export JSON
                            </button>
                            <button onclick="exportReport('txt')"
                                    class="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium px-3 py-1.5 rounded-lg transition border border-gray-300 flex items-center gap-1">
                                📄 Export TXT
                            </button>
                        </div>
                    </div>

                    <div id="preview-container">
                        <div class="border border-gray-200 rounded-lg h-96 flex flex-col items-center justify-center bg-gray-50 text-gray-400">
                            <svg class="w-12 h-12 mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                            </svg>
                            <p class="text-sm">Upload your dataset then run an analysis or generate a structured report</p>
                        </div>
                    </div>
                </div>
            </section>

        </main>

        <!-- Script: update report-type description & handle report export -->
        <script>
            document.addEventListener('htmx:afterSwap', function(evt) {
                if (evt.detail.target.id === 'report-type-picker') {
                    var select = document.getElementById('report-type');
                    var desc   = document.getElementById('report-type-desc');
                    if (select && desc) {
                        select.addEventListener('change', function() {
                            var opt = select.options[select.selectedIndex];
                            desc.textContent = opt.getAttribute('data-desc') || '';
                        });
                    }
                }
            });

            // Function to handle report export by extracting text from preview container
            async function exportReport(format) {
                const container = document.getElementById('preview-container');
                if (!container || container.innerText.trim() === "" || container.querySelector('svg')) {
                    alert("Please generate or view a report first before exporting.");
                    return;
                }

                // Extract text content from the current results view
                const reportContent = container.innerText;

                try {
                    const response = await fetch('/export-report', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            content: reportContent,
                            format: format
                        })
                    });

                    const result = await response.json();
                    if (response.ok && result.file_path) {
                        // Clean up path and extract only the pure filename (e.g., analysis_report_20260731_115235.md)
                        let cleanPath = result.file_path.startsWith('/') ? result.file_path.slice(1) : result.file_path;
                        if (cleanPath.startsWith('file_export/')) {
                            cleanPath = cleanPath.replace('file_export/', '');
                        }
                        const fileName = cleanPath.split('/').pop();

                        // Trigger download safely
                        window.location.href = `/download-report/${fileName}`;
                        // Notify the user which auto-generated file was created
                        alert(`Report exported successfully: ${fileName}`);
                    } else {
                        alert("Failed to export report: " + (result.detail || "Unknown error"));
                    }
                } catch (error) {
                    console.error("Export error:", error);
                    alert("An error occurred while exporting the report.");
                }
            }
        </script>
    </body>
    </html>
    """
    return html_content


class MainWeb:
    pass