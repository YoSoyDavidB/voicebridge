import types
from unittest.mock import MagicMock

import pytest

from voicebridge.audio.local_output import LocalSpeakerOutput


def test_local_output_writes_bytes_to_stream(monkeypatch) -> None:
    fake_stream = MagicMock()
    fake_stream.start = MagicMock()
    fake_stream.write = MagicMock()

    def fake_output_stream(*args, **kwargs):
        return fake_stream

    monkeypatch.setattr("sounddevice.OutputStream", fake_output_stream)

    output = LocalSpeakerOutput(sample_rate=22050, channels=1)
    output.start()
    output.enqueue(b"\x00\x01" * 10)

    fake_stream.start.assert_called_once()
    fake_stream.write.assert_called_once()
