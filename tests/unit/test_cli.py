from unittest.mock import MagicMock

from voicebridge.cli import create_cli_pipeline


def test_cli_wires_local_output(monkeypatch) -> None:
    fake_output = MagicMock()
    fake_constructor = MagicMock(return_value=fake_output)
    monkeypatch.setattr("voicebridge.cli.LocalSpeakerOutput", fake_constructor)
    monkeypatch.setenv("TTS_OUTPUT_SAMPLE_RATE", "48000")

    pipeline = create_cli_pipeline()
    assert pipeline is not None
    fake_constructor.assert_called_once_with(sample_rate=48000, channels=1)
    fake_output.start.assert_called_once()
