from unittest.mock import MagicMock

from voicebridge.cli import create_cli_pipeline


def test_cli_wires_local_output(monkeypatch) -> None:
    fake_output = MagicMock()
    monkeypatch.setattr("voicebridge.cli.LocalSpeakerOutput", lambda *a, **k: fake_output)

    pipeline = create_cli_pipeline()
    assert pipeline is not None
    fake_output.start.assert_called_once()
