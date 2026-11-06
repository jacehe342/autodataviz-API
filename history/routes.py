# history/routes.py
"""
FastAPI routes for viewing and managing analysis history.

Endpoints:
  GET  /history                    — HTML list of all saved records (newest first).
  GET  /history/{record_id}        — HTML detail view of a single record.
  POST /history/{record_id}/delete — Delete one record and refresh the list.
  POST /history/clear              — Delete every record and refresh the list.

All responses are HTML fragments designed for HTMX injection into the
dashboard's '#preview-container'. All comments and display text are in
English.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from history import renderer
from history.store import history_store

router = APIRouter(tags=["history"])


@router.get("/history", response_class=HTMLResponse)
async def list_history():
    """Return the history list view."""
    return renderer.render_history_list(history_store.all())


@router.post("/history/clear", response_class=HTMLResponse)
async def clear_history():
    """Delete all history records and their chart snapshots."""
    history_store.clear()
    return renderer.render_history_list(history_store.all())


@router.get("/history/{record_id}", response_class=HTMLResponse)
async def view_history_record(record_id: str):
    """Return the detail view for a single history record."""
    record = history_store.get(record_id)
    if record is None:
        return renderer.render_history_error(
            "The requested history record could not be found. "
            "It may have been deleted or removed during cleanup."
        )
    return renderer.render_history_detail(record)


@router.post("/history/{record_id}/delete", response_class=HTMLResponse)
async def delete_history_record(record_id: str):
    """Delete a single history record and return the refreshed list."""
    history_store.delete(record_id)
    return renderer.render_history_list(history_store.all())
