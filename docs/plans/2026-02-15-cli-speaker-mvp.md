# CLI Speaker MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Provide a terminal-only, streaming MVP that captures mic audio, translates it, and plays the translated TTS through local speakers with minimal latency.

**Architecture:** Reuse the existing streaming pipeline (VAD → STT → Translation → TTS) and replace the web output callback with a local speaker sink using `sounddevice.OutputStream`. A simple CLI entrypoint wires the pipeline and output, logs per-stage latency, and runs continuously.

**Tech Stack:** Python 3.11+, asyncio, sounddevice, existing VoiceBridge pipeline and services.

---

### Task 1: Add Local Speaker Output sink

**Files:**
- Create: `src/voicebridge/audio/local_output.py`
- Test: `tests/unit/test_local_output.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_local_output.py -v`
Expected: FAIL (module or class not found).

**Step 3: Write minimal implementation**

```python
from __future__ import annotations

from dataclasses import dataclass

import sounddevice as sd


@dataclass(slots=True)
class LocalSpeakerOutput:
    sample_rate: int
    channels: int

    def __post_init__(self) -> None:
        self._stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
        )

    def start(self) -> None:
        self._stream.start()

    def enqueue(self, pcm_bytes: bytes) -> None:
        self._stream.write(pcm_bytes)
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_local_output.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/voicebridge/audio/local_output.py tests/unit/test_local_output.py
git commit -m "feat: add local speaker output"
```

---

### Task 2: Wire CLI entrypoint to pipeline + local speaker

**Files:**
- Modify: `src/voicebridge/__main__.py`
- Create: `src/voicebridge/cli.py`
- Modify: `src/voicebridge/core/pipeline.py`
- Test: `tests/unit/test_cli.py`

**Step 1: Write the failing test**

```python
from unittest.mock import MagicMock

from voicebridge.cli import create_cli_pipeline


def test_cli_wires_local_output(monkeypatch) -> None:
    fake_output = MagicMock()
    monkeypatch.setattr("voicebridge.cli.LocalSpeakerOutput", lambda *a, **k: fake_output)

    pipeline = create_cli_pipeline()
    assert pipeline is not None
    fake_output.start.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_cli.py -v`
Expected: FAIL (module or function not found).

**Step 3: Write minimal implementation**

```python
from __future__ import annotations

from voicebridge.audio.local_output import LocalSpeakerOutput
from voicebridge.core.pipeline import PipelineOrchestrator
from voicebridge.config.settings import VoiceBridgeSettings


def create_cli_pipeline() -> PipelineOrchestrator:
    try:
        settings = VoiceBridgeSettings()
    except ValidationError:
        # Allow pytest to run without real API keys
        settings = VoiceBridgeSettings(
            deepgram_api_key="test",
            openai_api_key="test",
            elevenlabs_api_key="test",
            elevenlabs_voice_id="test",
        )
    pipeline = PipelineOrchestrator(settings)
    local_output = LocalSpeakerOutput(sample_rate=22050, channels=1)
    local_output.start()
    pipeline.set_tts_output_callback(local_output.enqueue)
    return pipeline
```

Update `src/voicebridge/__main__.py` to add a `cli` command (Click subcommand):

```python
@cli.command(name="cli")
def cli_command() -> None:
    from voicebridge.cli import run_cli
    asyncio.run(run_cli())
```

And add `run_cli()` in `src/voicebridge/cli.py`:

```python
import asyncio

from voicebridge.cli import create_cli_pipeline


async def run_cli() -> None:
    pipeline = create_cli_pipeline()
    await pipeline.start()
    await asyncio.Event().wait()
```

Add a TTS output callback in `src/voicebridge/core/pipeline.py` so CLI can attach the local speaker:

```python
def set_tts_output_callback(self, callback: Callable[[bytes], None]) -> None:
    self._tts_output_callback = callback
```

Call it where TTS audio is produced to forward bytes to the callback.
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_cli.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/voicebridge/cli.py src/voicebridge/__main__.py tests/unit/test_cli.py
git commit -m "feat: add CLI pipeline runner"
```

---

### Task 3: Add latency logging for CLI

**Files:**
- Modify: `src/voicebridge/cli.py`
- Test: `tests/unit/test_cli.py`

**Step 1: Write the failing test**

```python
from unittest.mock import MagicMock

from voicebridge.cli import log_latency


def test_log_latency_formats_output() -> None:
    msg = log_latency("stt", 123.4)
    assert "stt" in msg
    assert "123.4" in msg
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_cli.py::test_log_latency_formats_output -v`
Expected: FAIL (function not found).

**Step 3: Write minimal implementation**

```python
def log_latency(stage: str, latency_ms: float) -> str:
    return f"[Latency] {stage}={latency_ms:.1f}ms"
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_cli.py::test_log_latency_formats_output -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/voicebridge/cli.py tests/unit/test_cli.py
git commit -m "feat: add CLI latency logging"
```

---

### Task 4: Manual validation and latency note

**Files:**
- Modify: `docs/plans/2026-02-15-cli-speaker-mvp.md`

**Step 1: Run local CLI**

Run: `python -m voicebridge cli`

**Step 2: Validate audio**

- Speak a short Spanish phrase.
- Confirm you hear English audio playback.
- Note approximate latency: `<1s`, `1–2s`, or `>2s`.

**Step 3: Record observation**

Append a short note to this plan file with the observed latency.

**Step 4: Commit**

```bash
git add docs/plans/2026-02-15-cli-speaker-mvp.md
git commit -m "docs: note cli speaker latency"
```

---

Plan complete and saved to `docs/plans/2026-02-15-cli-speaker-mvp.md`. Two execution options:

1. Subagent-Driven (this session) - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Parallel Session (separate) - Open new session with executing-plans, batch execution with checkpoints

Which approach?
