# web/route_upload.py
import os
import shutil
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import HTMLResponse

router = APIRouter()

# Create upload directory if it does not exist
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", response_class=HTMLResponse)
async def upload_file(file: UploadFile = File(...)):
    """Saves uploaded dataset to a fixed file path and returns UI preview."""

    # Save the uploaded file to a deterministic path
    file_path = os.path.join(UPLOAD_DIR, "active_dataset.xlsx")

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        return f"<div class='text-red-500 p-4'>❌ Failed to save file: {str(e)}</div>"

    return f"""
    <div class="bg-green-50 border border-green-200 text-green-700 p-4 rounded-xl">
        <p class="font-semibold">✅ File uploaded successfully!</p>
        <p class="text-xs text-green-600 mt-1">Filename: {file.filename} (Saved as active dataset)</p>
    </div>
    """


@router.post("/delete", response_class=HTMLResponse)
async def delete_file():
    """Removes the active dataset from the server."""
    file_path = os.path.join(UPLOAD_DIR, "active_dataset.xlsx")
    if os.path.exists(file_path):
        os.remove(file_path)

    return """
    <div class="border border-gray-200 rounded-lg h-96 flex flex-col items-center justify-center bg-gray-50 text-gray-400">
        <p class="text-sm">Dataset cleared. Upload a new file to start.</p>
    </div>
    """