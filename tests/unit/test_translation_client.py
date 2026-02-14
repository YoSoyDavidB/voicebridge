"""Tests for Translation client."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from voicebridge.core.models import TranscriptResult, TranslationResult
from voicebridge.services.translation.openai_client import OpenAITranslationClient


class TestOpenAITranslationClientInitialization:
    """Test OpenAITranslationClient initialization."""

    def test_creation_with_config(self) -> None:
        """Translation client should be creatable with configuration."""
        client = OpenAITranslationClient(
            api_key="test_key",
            model="gpt-4o-mini",
            temperature=0.3,
        )

        assert client.api_key == "test_key"
        assert client.model == "gpt-4o-mini"
        assert client.temperature == 0.3


class TestOpenAITranslationClientTranslation:
    """Test translation functionality."""

    @pytest.mark.asyncio
    async def test_translates_spanish_to_english(self) -> None:
        """Should produce English translation of Spanish input."""
        # Mock OpenAI response
        mock_choice = MagicMock()
        mock_choice.message.content = "We need to review the budget"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        with patch("voicebridge.services.translation.openai_client.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create = MagicMock(return_value=mock_response)
            mock_openai_cls.return_value = mock_client

            client = OpenAITranslationClient(
                api_key="test_key",
                model="gpt-4o-mini",
                temperature=0.3,
            )

            result = await client._translate_text("Necesitamos revisar el presupuesto", start_time=0.0)

            assert result is not None
            assert result.original_text == "Necesitamos revisar el presupuesto"
            assert result.translated_text == "We need to review the budget"

    @pytest.mark.asyncio
    async def test_empty_input_returns_none(self) -> None:
        """Should handle empty transcript gracefully."""
        with patch("voicebridge.services.translation.openai_client.OpenAI"):
            client = OpenAITranslationClient(
                api_key="test_key",
                model="gpt-4o-mini",
                temperature=0.3,
            )

            result = await client._translate_text("", start_time=0.0)

            assert result is None

    @pytest.mark.asyncio
    async def test_whitespace_input_returns_none(self) -> None:
        """Should handle whitespace-only transcript gracefully."""
        with patch("voicebridge.services.translation.openai_client.OpenAI"):
            client = OpenAITranslationClient(
                api_key="test_key",
                model="gpt-4o-mini",
                temperature=0.3,
            )

            result = await client._translate_text("   ", start_time=0.0)

            assert result is None


class TestOpenAITranslationClientSystemPrompt:
    """Test system prompt configuration."""

    def test_system_prompt_is_set(self) -> None:
        """Should include the interpreter system prompt."""
        client = OpenAITranslationClient(
            api_key="test_key",
            model="gpt-4o-mini",
            temperature=0.3,
        )

        assert "real-time interpreter" in client._system_prompt.lower()
        assert "spanish" in client._system_prompt.lower()
        assert "english" in client._system_prompt.lower()


class TestOpenAITranslationClientQueue:
    """Test queue management."""

    @pytest.mark.asyncio
    async def test_set_input_queue(self) -> None:
        """Should allow setting input queue."""
        with patch("voicebridge.services.translation.openai_client.OpenAI"):
            client = OpenAITranslationClient(
                api_key="test_key",
                model="gpt-4o-mini",
                temperature=0.3,
            )

            queue: asyncio.Queue[TranscriptResult] = asyncio.Queue()
            client.set_input_queue(queue)

            assert client._input_queue is queue

    @pytest.mark.asyncio
    async def test_set_output_queue(self) -> None:
        """Should allow setting output queue."""
        with patch("voicebridge.services.translation.openai_client.OpenAI"):
            client = OpenAITranslationClient(
                api_key="test_key",
                model="gpt-4o-mini",
                temperature=0.3,
            )

            queue: asyncio.Queue[TranslationResult] = asyncio.Queue()
            client.set_output_queue(queue)

            assert client._output_queue is queue


class TestOpenAITranslationClientLatency:
    """Test latency tracking."""

    @pytest.mark.asyncio
    async def test_tracks_latency(self) -> None:
        """Should calculate processing_latency_ms correctly."""
        mock_choice = MagicMock()
        mock_choice.message.content = "Hello world"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        with patch("voicebridge.services.translation.openai_client.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create = MagicMock(return_value=mock_response)
            mock_openai_cls.return_value = mock_client

            client = OpenAITranslationClient(
                api_key="test_key",
                model="gpt-4o-mini",
                temperature=0.3,
            )

            import time
            start_time = time.monotonic()
            time.sleep(0.05)  # Simulate 50ms delay

            result = await client._translate_text("hola mundo", start_time=start_time)

            assert result is not None
            assert result.processing_latency_ms >= 50.0
