"""FastAPI application for VoiceBridge web interface.

Serves the web interface and handles WebSocket connections for real-time
audio streaming.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Create FastAPI application instance
app = FastAPI(
    title="VoiceBridge",
    description="Real-time audio transcription with OpenAI Whisper",
    version="0.1.0",
)

# Get the static directory path
STATIC_DIR = Path(__file__).parent / "static"

# Mount static files directory
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def serve_index() -> FileResponse:
    """Serve the main index.html page."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}
