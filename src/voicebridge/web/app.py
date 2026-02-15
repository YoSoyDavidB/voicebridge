"""FastAPI application for VoiceBridge web interface.

Serves the web interface and handles WebSocket connections for real-time
audio streaming.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from voicebridge.web.audio_bridge import WebAudioBridge
from voicebridge.web.websocket_handler import WebSocketHandler

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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time audio streaming.

    Handles bidirectional communication between browser and backend:
    - Receives config, audio, and control messages from browser
    - Sends status, transcription, and error responses back

    Args:
        websocket: WebSocket connection from FastAPI
    """
    # Accept the WebSocket connection
    await websocket.accept()

    try:
        # Create WebAudioBridge and WebSocketHandler instances
        audio_bridge = WebAudioBridge()
        handler = WebSocketHandler(audio_bridge)

        # Set callback for sending TTS audio back to browser
        async def send_audio_to_browser(audio_base64: str) -> None:
            """Send TTS audio to browser."""
            import json
            message = json.dumps({
                "type": "audio",
                "data": audio_base64
            })
            await websocket.send_text(message)

        handler.set_audio_output_callback(send_audio_to_browser)

        # Message processing loop
        message_count = 0
        while True:
            # Receive message from browser
            message = await websocket.receive_text()
            message_count += 1

            # Log every message (temporary debug)
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"[WebSocket] Message #{message_count} received, length={len(message)}")

            # Handle message and get response (if any)
            response = await handler.handle_message(message)

            # Send response if one was returned (audio messages return None)
            if response is not None:
                await websocket.send_text(response)

    except Exception as e:
        # Log error and close connection gracefully
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"WebSocket error: {e}", exc_info=True)

    finally:
        # Ensure connection is closed
        try:
            await websocket.close()
        except Exception:
            # Connection might already be closed
            pass
