import asyncio
from unittest.mock import MagicMock

import pytest

from voicebridge.audio.local_output import LocalSpeakerOutput


def test_local_output_writes_bytes_to_stream(monkeypatch) -> None:
    fake_stream = MagicMock()
    fake_stream.start = MagicMock()
    fake_stream.write = MagicMock()

    def fake_output_stream(*args, **kwargs):
        return fake_stream

    monkeypatch.setattr("voicebridge.audio.local_output.sd.OutputStream", fake_output_stream)

    output = LocalSpeakerOutput(sample_rate=22050, channels=1)
    output.start()
    output.enqueue(b"\x00\x01" * 10)

    fake_stream.start.assert_called_once()
    fake_stream.write.assert_called_once()


def test_local_output_stops_and_closes_stream(monkeypatch) -> None:
    fake_stream = MagicMock()
    fake_stream.start = MagicMock()
    fake_stream.stop = MagicMock()
    fake_stream.close = MagicMock()

    def fake_output_stream(*args, **kwargs):
        return fake_stream

    monkeypatch.setattr("voicebridge.audio.local_output.sd.OutputStream", fake_output_stream)

    output = LocalSpeakerOutput(sample_rate=22050, channels=1)
    output.start()
    output.stop()
    output.close()

    fake_stream.start.assert_called_once()
    fake_stream.stop.assert_called_once()
    fake_stream.close.assert_called_once()


@pytest.mark.asyncio
async def test_local_output_enqueue_async_writes_bytes(monkeypatch) -> None:
    fake_stream = MagicMock()
    fake_stream.write = MagicMock()

    def fake_output_stream(*args, **kwargs):
        return fake_stream

    monkeypatch.setattr("voicebridge.audio.local_output.sd.OutputStream", fake_output_stream)

    output = LocalSpeakerOutput(sample_rate=22050, channels=1)
    await output.enqueue_async(b"\x00\x01" * 10)

    fake_stream.write.assert_called_once()
