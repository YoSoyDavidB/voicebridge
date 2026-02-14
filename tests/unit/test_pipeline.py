"""Tests for PipelineOrchestrator."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from voicebridge.core.models import ComponentStatus, PipelineHealth, PipelineMetrics
from voicebridge.core.pipeline import PipelineOrchestrator


class TestPipelineOrchestratorInitialization:
    """Test PipelineOrchestrator initialization."""

    def test_creation_with_settings(self) -> None:
        """Pipeline should be creatable with settings."""
        mock_settings = MagicMock()
        mock_settings.audio_sample_rate = 16000
        mock_settings.audio_channels = 1
        mock_settings.deepgram_api_key = "test_deepgram_key"
        mock_settings.openai_api_key = "test_openai_key"
        mock_settings.elevenlabs_api_key = "test_elevenlabs_key"
        mock_settings.elevenlabs_voice_id = "test_voice_id"

        pipeline = PipelineOrchestrator(settings=mock_settings)

        assert pipeline.settings is mock_settings
        assert pipeline._is_running is False


class TestPipelineOrchestratorLifecycle:
    """Test pipeline start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_initializes_all_components(self) -> None:
        """Should create and start all pipeline components."""
        mock_settings = MagicMock()
        mock_settings.audio_sample_rate = 16000
        mock_settings.audio_channels = 1
        mock_settings.audio_chunk_duration_ms = 30
        mock_settings.vad_threshold = 0.5
        mock_settings.deepgram_api_key = "test_key"
        mock_settings.deepgram_model = "nova-2"
        mock_settings.deepgram_language = "es"
        mock_settings.openai_api_key = "test_key"
        mock_settings.openai_model = "gpt-4o-mini"
        mock_settings.openai_temperature = 0.3
        mock_settings.elevenlabs_api_key = "test_key"
        mock_settings.elevenlabs_voice_id = "test_voice"
        mock_settings.elevenlabs_model = "eleven_turbo_v2_5"
        mock_settings.tts_stability = 0.5
        mock_settings.tts_similarity_boost = 0.8
        mock_settings.tts_optimize_streaming_latency = 3
        mock_settings.tts_output_sample_rate = 24000

        with patch("voicebridge.core.pipeline.AudioCapture") as mock_capture_cls, \
             patch("voicebridge.core.pipeline.VADProcessor") as mock_vad_cls, \
             patch("voicebridge.core.pipeline.DeepgramSTTClient") as mock_stt_cls, \
             patch("voicebridge.core.pipeline.OpenAITranslationClient") as mock_trans_cls, \
             patch("voicebridge.core.pipeline.ElevenLabsTTSClient") as mock_tts_cls, \
             patch("voicebridge.core.pipeline.AudioOutput") as mock_output_cls:

            # Create mock instances
            mock_capture = AsyncMock()
            mock_vad = AsyncMock()
            mock_stt = AsyncMock()
            mock_trans = AsyncMock()
            mock_tts = AsyncMock()
            mock_output = AsyncMock()

            mock_capture_cls.return_value = mock_capture
            mock_vad_cls.return_value = mock_vad
            mock_stt_cls.return_value = mock_stt
            mock_trans_cls.return_value = mock_trans
            mock_tts_cls.return_value = mock_tts
            mock_output_cls.return_value = mock_output

            pipeline = PipelineOrchestrator(settings=mock_settings)

            # Start pipeline in background
            task = asyncio.create_task(pipeline.start())

            # Give it time to initialize
            await asyncio.sleep(0.1)

            # Stop pipeline
            await pipeline.stop()
            await task

            # Should have created all components
            mock_capture_cls.assert_called_once()
            mock_vad_cls.assert_called_once()
            mock_stt_cls.assert_called_once()
            mock_trans_cls.assert_called_once()
            mock_tts_cls.assert_called_once()
            mock_output_cls.assert_called_once()

            # Should have started all components
            mock_capture.start.assert_called_once()
            mock_vad.start.assert_called_once()
            mock_stt.start.assert_called_once()
            mock_trans.start.assert_called_once()
            mock_tts.start.assert_called_once()
            mock_output.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_shuts_down_gracefully(self) -> None:
        """Should stop all components in reverse order."""
        mock_settings = MagicMock()
        mock_settings.audio_sample_rate = 16000
        mock_settings.audio_channels = 1
        mock_settings.audio_chunk_duration_ms = 30
        mock_settings.vad_threshold = 0.5
        mock_settings.deepgram_api_key = "test_key"
        mock_settings.deepgram_model = "nova-2"
        mock_settings.deepgram_language = "es"
        mock_settings.openai_api_key = "test_key"
        mock_settings.openai_model = "gpt-4o-mini"
        mock_settings.openai_temperature = 0.3
        mock_settings.elevenlabs_api_key = "test_key"
        mock_settings.elevenlabs_voice_id = "test_voice"
        mock_settings.elevenlabs_model = "eleven_turbo_v2_5"
        mock_settings.tts_stability = 0.5
        mock_settings.tts_similarity_boost = 0.8
        mock_settings.tts_optimize_streaming_latency = 3
        mock_settings.tts_output_sample_rate = 24000

        with patch("voicebridge.core.pipeline.AudioCapture") as mock_capture_cls, \
             patch("voicebridge.core.pipeline.VADProcessor") as mock_vad_cls, \
             patch("voicebridge.core.pipeline.DeepgramSTTClient") as mock_stt_cls, \
             patch("voicebridge.core.pipeline.OpenAITranslationClient") as mock_trans_cls, \
             patch("voicebridge.core.pipeline.ElevenLabsTTSClient") as mock_tts_cls, \
             patch("voicebridge.core.pipeline.AudioOutput") as mock_output_cls:

            mock_capture = AsyncMock()
            mock_vad = AsyncMock()
            mock_stt = AsyncMock()
            mock_trans = AsyncMock()
            mock_tts = AsyncMock()
            mock_output = AsyncMock()

            mock_capture_cls.return_value = mock_capture
            mock_vad_cls.return_value = mock_vad
            mock_stt_cls.return_value = mock_stt
            mock_trans_cls.return_value = mock_trans
            mock_tts_cls.return_value = mock_tts
            mock_output_cls.return_value = mock_output

            pipeline = PipelineOrchestrator(settings=mock_settings)

            task = asyncio.create_task(pipeline.start())
            await asyncio.sleep(0.1)

            # Stop pipeline
            await pipeline.stop()
            await task

            # Should have stopped all components
            mock_output.stop.assert_called_once()
            mock_tts.stop.assert_called_once()
            mock_trans.stop.assert_called_once()
            mock_stt.stop.assert_called_once()
            mock_vad.stop.assert_called_once()
            mock_capture.stop.assert_called_once()


class TestPipelineOrchestratorQueues:
    """Test queue creation and connection."""

    @pytest.mark.asyncio
    async def test_creates_queues_between_components(self) -> None:
        """Should create asyncio.Queue objects to connect components."""
        mock_settings = MagicMock()
        mock_settings.audio_sample_rate = 16000
        mock_settings.audio_channels = 1
        mock_settings.audio_chunk_duration_ms = 30
        mock_settings.vad_threshold = 0.5
        mock_settings.deepgram_api_key = "test_key"
        mock_settings.deepgram_model = "nova-2"
        mock_settings.deepgram_language = "es"
        mock_settings.openai_api_key = "test_key"
        mock_settings.openai_model = "gpt-4o-mini"
        mock_settings.openai_temperature = 0.3
        mock_settings.elevenlabs_api_key = "test_key"
        mock_settings.elevenlabs_voice_id = "test_voice"
        mock_settings.elevenlabs_model = "eleven_turbo_v2_5"
        mock_settings.tts_stability = 0.5
        mock_settings.tts_similarity_boost = 0.8
        mock_settings.tts_optimize_streaming_latency = 3
        mock_settings.tts_output_sample_rate = 24000

        with patch("voicebridge.core.pipeline.AudioCapture") as mock_capture_cls, \
             patch("voicebridge.core.pipeline.VADProcessor") as mock_vad_cls, \
             patch("voicebridge.core.pipeline.DeepgramSTTClient") as mock_stt_cls, \
             patch("voicebridge.core.pipeline.OpenAITranslationClient") as mock_trans_cls, \
             patch("voicebridge.core.pipeline.ElevenLabsTTSClient") as mock_tts_cls, \
             patch("voicebridge.core.pipeline.AudioOutput") as mock_output_cls:

            mock_capture = AsyncMock()
            mock_vad = AsyncMock()
            mock_stt = AsyncMock()
            mock_trans = AsyncMock()
            mock_tts = AsyncMock()
            mock_output = AsyncMock()

            mock_capture_cls.return_value = mock_capture
            mock_vad_cls.return_value = mock_vad
            mock_stt_cls.return_value = mock_stt
            mock_trans_cls.return_value = mock_trans
            mock_tts_cls.return_value = mock_tts
            mock_output_cls.return_value = mock_output

            pipeline = PipelineOrchestrator(settings=mock_settings)

            task = asyncio.create_task(pipeline.start())
            await asyncio.sleep(0.1)
            await pipeline.stop()
            await task

            # Should have connected queues
            mock_capture.set_output_queue.assert_called_once()
            mock_vad.set_input_queue.assert_called_once()
            mock_vad.set_output_queue.assert_called_once()
            mock_stt.set_input_queue.assert_called_once()
            mock_stt.set_output_queue.assert_called_once()
            mock_trans.set_input_queue.assert_called_once()
            mock_trans.set_output_queue.assert_called_once()
            mock_tts.set_input_queue.assert_called_once()
            mock_tts.set_output_queue.assert_called_once()
            mock_output.set_input_queue.assert_called_once()


class TestPipelineOrchestratorHealth:
    """Test health monitoring."""

    @pytest.mark.asyncio
    async def test_health_check_returns_status(self) -> None:
        """Should return pipeline health status."""
        mock_settings = MagicMock()
        mock_settings.audio_sample_rate = 16000

        pipeline = PipelineOrchestrator(settings=mock_settings)

        health = await pipeline.health_check()

        assert isinstance(health, PipelineHealth)
        assert isinstance(health.is_healthy, bool)
        assert isinstance(health.component_statuses, dict)


class TestPipelineOrchestratorMetrics:
    """Test metrics collection."""

    def test_get_metrics_returns_performance_data(self) -> None:
        """Should return pipeline performance metrics."""
        mock_settings = MagicMock()
        mock_settings.audio_sample_rate = 16000

        pipeline = PipelineOrchestrator(settings=mock_settings)

        metrics = pipeline.get_metrics()

        assert isinstance(metrics, PipelineMetrics)
        assert metrics.total_latency_ms >= 0.0
        assert isinstance(metrics.queue_depths, dict)
