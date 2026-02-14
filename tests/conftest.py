"""Shared pytest fixtures for VoiceBridge tests."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator


@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create a new event loop for each test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_rate() -> int:
    """Standard sample rate for tests."""
    return 16000


@pytest.fixture
def chunk_duration_ms() -> int:
    """Standard chunk duration for tests."""
    return 30


@pytest.fixture
def sample_audio_data(sample_rate: int, chunk_duration_ms: int) -> bytes:
    """Generate synthetic audio data (random noise)."""
    num_samples = int(sample_rate * chunk_duration_ms / 1000)
    audio_array = np.random.randint(-32768, 32767, num_samples, dtype=np.int16)
    return audio_array.tobytes()


@pytest.fixture
def speech_audio_data(sample_rate: int, chunk_duration_ms: int) -> bytes:
    """Generate audio data that simulates speech (440Hz sine wave)."""
    num_samples = int(sample_rate * chunk_duration_ms / 1000)
    t = np.linspace(0, chunk_duration_ms / 1000, num_samples, False)
    audio_array = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)
    return audio_array.tobytes()


@pytest.fixture
def silence_audio_data(sample_rate: int, chunk_duration_ms: int) -> bytes:
    """Generate silence (zeros)."""
    num_samples = int(sample_rate * chunk_duration_ms / 1000)
    return bytes(num_samples * 2)  # 16-bit = 2 bytes per sample


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def audio_fixtures_dir(fixtures_dir: Path) -> Path:
    """Return path to audio fixtures directory."""
    return fixtures_dir / "audio"


@pytest.fixture
def transcript_fixtures_dir(fixtures_dir: Path) -> Path:
    """Return path to transcript fixtures directory."""
    return fixtures_dir / "transcripts"
