from unittest.mock import MagicMock

from voicebridge.cli import create_cli_pipeline, log_latency
from voicebridge.core.models import TTSAudioResult


def test_cli_wires_local_output(monkeypatch) -> None:
    fake_output = MagicMock()
    fake_constructor = MagicMock(return_value=fake_output)
    monkeypatch.setattr("voicebridge.cli.LocalSpeakerOutput", fake_constructor)
    monkeypatch.setenv("TTS_OUTPUT_SAMPLE_RATE", "48000")

    pipeline = create_cli_pipeline()
    assert pipeline is not None
    fake_constructor.assert_called_once_with(sample_rate=48000, channels=1)
    fake_output.start.assert_called_once()


def test_log_latency_formats_output() -> None:
    msg = log_latency("stt", 123.4)
    assert "stt" in msg
    assert "123.4" in msg


def test_cli_tts_callback_logs_and_enqueues(monkeypatch) -> None:
    fake_output = MagicMock()

    monkeypatch.setattr("voicebridge.cli.LocalSpeakerOutput", lambda *a, **k: fake_output)

    logged: list[tuple[str, float]] = []

    def fake_log_latency(stage: str, latency_ms: float) -> str:
        logged.append((stage, latency_ms))
        return "ok"

    monkeypatch.setattr("voicebridge.cli.log_latency", fake_log_latency)

    pipeline = create_cli_pipeline()
    callback = pipeline._tts_output_callback

    assert callback is not None

    tts_result = TTSAudioResult(
        audio_data=b"\x00\x01",
        sample_rate=24000,
        channels=1,
        is_final=True,
        start_timestamp_ms=0.0,
        processing_latency_ms=123.4,
        sequence_number=0,
    )

    callback(tts_result)

    fake_output.enqueue.assert_called_once_with(b"\x00\x01")
    assert logged == [("tts", 123.4)]
