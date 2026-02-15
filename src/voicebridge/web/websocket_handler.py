"""WebSocket message handler for VoiceBridge web interface.

Handles WebSocket message routing and processing for real-time audio streaming.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from voicebridge.web.audio_bridge import WebAudioBridge
from voicebridge.web.web_pipeline import WebPipeline

logger = logging.getLogger(__name__)


class WebSocketHandler:
    """WebSocket message handler for routing and processing messages.

    Handles three types of messages:
    - config: Store API keys and configuration
    - audio: Process incoming audio data (requires config first)
    - control: Handle control commands (stop, etc.)

    Args:
        audio_bridge: WebAudioBridge for audio format conversion
    """

    def __init__(self, audio_bridge: WebAudioBridge) -> None:
        """Initialize WebSocketHandler.

        Args:
            audio_bridge: WebAudioBridge instance for audio conversion
        """
        self._audio_bridge = audio_bridge
        self._config: Optional[dict[str, Any]] = None
        self._pipeline: Optional[WebPipeline] = None
        self._audio_output_callback: Optional[callable] = None

    def set_audio_output_callback(self, callback: callable) -> None:
        """Set callback for sending TTS audio to browser.

        Args:
            callback: Async function that takes base64 audio string
        """
        self._audio_output_callback = callback

    async def handle_message(self, message: str) -> Optional[str]:
        """Handle incoming WebSocket message.

        Routes message to appropriate handler based on "type" field.

        Args:
            message: JSON string message from browser

        Returns:
            JSON response string, or None if no response needed

        Message types:
            - config: {"type": "config", "apiKeys": {...}}
            - audio: {"type": "audio", "audio": "base64...", "timestamp": 1234.5}
            - control: {"type": "control", "action": "stop"}
        """
        try:
            # Parse JSON message
            data = json.loads(message)

            # Get message type
            message_type = data.get("type")
            if not message_type:
                return self._error_response("Missing 'type' field in message")

            # Route to appropriate handler
            if message_type == "config":
                return await self._handle_config(data)
            elif message_type == "audio":
                return await self._handle_audio(data)
            elif message_type == "control":
                return await self._handle_control(data)
            else:
                return self._error_response(f"Unknown message type: {message_type}")

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return self._error_response(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            return self._error_response(f"Processing error: {e}")

    async def _handle_config(self, data: dict[str, Any]) -> str:
        """Handle config message - store API keys and configuration.

        Args:
            data: Config message data with "apiKeys" field

        Returns:
            JSON status response indicating ready state
        """
        # Store configuration
        self._config = data
        api_keys = data.get("apiKeys", {})

        # Add voiceId to api_keys (it comes separately in the message)
        api_keys['voiceId'] = data.get("voiceId", "")

        logger.info("Configuration received, initializing pipeline...")

        try:
            # Stop existing pipeline if any
            if self._pipeline:
                await self._pipeline.stop()

            # Create new pipeline with API keys
            self._pipeline = WebPipeline(api_keys)

            # Set audio output callback
            if self._audio_output_callback:
                self._pipeline.set_audio_output_callback(self._audio_output_callback)

            # Start pipeline
            await self._pipeline.start()

            logger.info("Pipeline initialized and started successfully")

            # Return status response
            return json.dumps({
                "type": "status",
                "state": "ready",
                "message": "System configured and ready"
            })

        except Exception as e:
            logger.error(f"Error initializing pipeline: {e}", exc_info=True)
            return self._error_response(f"Pipeline initialization error: {e}")

    async def _handle_audio(self, data: dict[str, Any]) -> Optional[str]:
        """Handle audio message - decode and process audio data.

        Args:
            data: Audio message with "audio" (base64) and "timestamp" fields

        Returns:
            None (responses come separately from pipeline)

        Note:
            Requires config to be sent first. Audio is decoded and will be
            passed to pipeline for processing.
        """
        logger.debug(f"[WebSocket] Received audio message: {len(str(data))} bytes")

        # Check if config has been received and pipeline is running
        if self._config is None:
            logger.warning("[WebSocket] No config - rejecting audio")
            return self._error_response("Configuration required before sending audio")

        if self._pipeline is None:
            logger.warning("[WebSocket] No pipeline - rejecting audio")
            return self._error_response("Pipeline not initialized")

        # Get audio data and timestamp
        base64_audio = data.get("audio")
        timestamp_ms = data.get("timestamp")

        if not base64_audio:
            logger.warning("[WebSocket] Missing 'audio' field")
            return self._error_response("Missing 'audio' field")
        if timestamp_ms is None:
            logger.warning("[WebSocket] Missing 'timestamp' field")
            return self._error_response("Missing 'timestamp' field")

        logger.debug(f"[WebSocket] Audio data: {len(base64_audio)} base64 chars, timestamp={timestamp_ms}")

        # Decode audio to AudioChunk
        try:
            audio_chunk = self._audio_bridge.decode_web_audio(base64_audio, timestamp_ms)
            logger.info(
                f"[WebSocket] Decoded audio chunk: {audio_chunk.duration_ms:.1f}ms, "
                f"seq={audio_chunk.sequence_number}, {len(audio_chunk.data)} samples"
            )

            # Send to pipeline for processing
            await self._pipeline.process_audio_chunk(audio_chunk)
            logger.debug(f"[WebSocket] Sent chunk to pipeline queue")

        except Exception as e:
            logger.error(f"Error processing audio: {e}", exc_info=True)
            return self._error_response(f"Audio processing error: {e}")

        # Audio processing is async - responses come separately from pipeline
        return None

    async def _handle_control(self, data: dict[str, Any]) -> str:
        """Handle control message - process control commands.

        Args:
            data: Control message with "action" field

        Returns:
            JSON status response

        Supported actions:
            - stop: Stop audio processing
        """
        action = data.get("action")

        if action == "stop":
            logger.info("Stop command received")

            # Stop pipeline
            if self._pipeline:
                await self._pipeline.stop()
                self._pipeline = None

            # Clear configuration
            self._config = None

            return json.dumps({
                "type": "status",
                "state": "stopped",
                "message": "Processing stopped"
            })
        else:
            return self._error_response(f"Unknown control action: {action}")

    def _error_response(self, message: str) -> str:
        """Create error response JSON.

        Args:
            message: Error message description

        Returns:
            JSON error response string
        """
        return json.dumps({
            "type": "error",
            "message": message,
            "code": "PROCESSING_ERROR"
        })
