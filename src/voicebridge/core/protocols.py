"""Protocol definitions for VoiceBridge components.

All components implement these protocols, ensuring loose coupling and
easy testing via dependency injection and mocking.
"""

from __future__ import annotations

import asyncio
from typing import Protocol

from voicebridge.core.models import (
    AudioChunk,
    TranscriptResult,
    TranslationResult,
    TTSAudioResult,
    VADResult,
)


class AudioCaptureProtocol(Protocol):
    """Protocol for audio capture from physical microphone."""

    async def start(self) -> None:
        """Start capturing audio from the microphone."""
        ...

    async def stop(self) -> None:
        """Stop capturing audio and release the device."""
        ...

    def set_output_queue(self, queue: asyncio.Queue[AudioChunk]) -> None:
        """Set the queue where captured audio chunks will be pushed."""
        ...

    def get_available_devices(self) -> list[dict[str, str | int]]:
        """List all available audio input devices."""
        ...

    def set_device(self, device_id: int) -> None:
        """Set the input device to use for capture."""
        ...


class VADProcessorProtocol(Protocol):
    """Protocol for Voice Activity Detection processor."""

    async def start(self) -> None:
        """Start the VAD processor."""
        ...

    async def stop(self) -> None:
        """Stop the VAD processor."""
        ...

    def set_input_queue(self, queue: asyncio.Queue[AudioChunk]) -> None:
        """Set the queue to read audio chunks from."""
        ...

    def set_output_queue(self, queue: asyncio.Queue[VADResult]) -> None:
        """Set the queue to push VAD results to."""
        ...


class STTClientProtocol(Protocol):
    """Protocol for Speech-to-Text client."""

    async def start(self) -> None:
        """Start the STT client processing loop."""
        ...

    async def stop(self) -> None:
        """Stop the STT client."""
        ...

    async def connect(self) -> None:
        """Establish connection to STT service (e.g., WebSocket)."""
        ...

    async def disconnect(self) -> None:
        """Close connection to STT service."""
        ...

    def set_input_queue(self, queue: asyncio.Queue[VADResult]) -> None:
        """Set the queue to read VAD results from."""
        ...

    def set_output_queue(self, queue: asyncio.Queue[TranscriptResult]) -> None:
        """Set the queue to push transcription results to."""
        ...


class TranslationClientProtocol(Protocol):
    """Protocol for translation client."""

    async def start(self) -> None:
        """Start the translation client processing loop."""
        ...

    async def stop(self) -> None:
        """Stop the translation client."""
        ...

    def set_input_queue(self, queue: asyncio.Queue[TranscriptResult]) -> None:
        """Set the queue to read transcripts from."""
        ...

    def set_output_queue(self, queue: asyncio.Queue[TranslationResult]) -> None:
        """Set the queue to push translation results to."""
        ...


class TTSClientProtocol(Protocol):
    """Protocol for Text-to-Speech client."""

    async def start(self) -> None:
        """Start the TTS client processing loop."""
        ...

    async def stop(self) -> None:
        """Stop the TTS client."""
        ...

    async def connect(self) -> None:
        """Establish connection to TTS service (e.g., WebSocket)."""
        ...

    async def disconnect(self) -> None:
        """Close connection to TTS service."""
        ...

    def set_input_queue(self, queue: asyncio.Queue[TranslationResult]) -> None:
        """Set the queue to read translations from."""
        ...

    def set_output_queue(self, queue: asyncio.Queue[TTSAudioResult]) -> None:
        """Set the queue to push synthesized audio to."""
        ...


class AudioOutputProtocol(Protocol):
    """Protocol for audio output to virtual microphone."""

    async def start(self) -> None:
        """Start audio output."""
        ...

    async def stop(self) -> None:
        """Stop audio output and release the device."""
        ...

    def set_input_queue(self, queue: asyncio.Queue[TTSAudioResult]) -> None:
        """Set the queue to read synthesized audio from."""
        ...

    def set_output_device(self, device_id: int) -> None:
        """Set the output device (virtual microphone)."""
        ...

    def get_available_devices(self) -> list[dict[str, str | int]]:
        """List all available audio output devices."""
        ...
