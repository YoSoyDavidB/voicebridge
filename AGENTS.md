# VoiceBridge AI Agents Guide

## 1️⃣ Project Purpose

**VoiceBridge** is a real-time Spanish-to-English voice interpreter for Microsoft Teams that:

- Captures microphone audio, translates it, and synthesizes it with the user's cloned voice
- Routes translated audio to Teams via virtual audio device
- **Target Latency**: < 800ms end-to-end
- **Critical Priority**: Minimize latency while maintaining translation accuracy and voice fidelity

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Language** | Python 3.11+ | Async support, ML ecosystem |
| **Audio** | sounddevice, PortAudio | Cross-platform audio I/O |
| **VAD** | Silero VAD | Voice activity detection |
| **STT** | Deepgram (WebSocket) | Real-time speech-to-text |
| **Translation** | GPT-4o-mini | Spanish → English translation |
| **TTS** | ElevenLabs Turbo v2.5 | Voice cloning + synthesis |
| **Testing** | pytest, pytest-asyncio | TDD methodology |
| **Config** | Pydantic Settings | Type-safe configuration |

### Project Goals

1. **Latency-First**: Every decision must prioritize low latency
2. **TDD Methodology**: Write tests before implementation (RED → GREEN → REFACTOR)
3. **Streaming Architecture**: All components stream data asynchronously
4. **Production-Ready**: Robust error handling, fallback strategies, monitoring

---

## 2️⃣ Agent Roles & Responsibilities

### 🏗️ ArchitectAgent
**Responsibility**: System design, component interfaces, architecture decisions
**Scope**:
- Pipeline architecture and data flow
- Protocol/interface design
- Component interaction patterns
- Performance optimization strategies
- Technology selection decisions

**Actions**:
- Review architectural changes
- Validate component boundaries
- Ensure adherence to streaming architecture
- Approve interface modifications

---

### 🧪 TestAgent
**Responsibility**: Test-Driven Development enforcement, test quality
**Scope**:
- Unit test creation (BEFORE implementation)
- Integration test design
- Performance benchmark tests
- Test fixture management
- Mock/stub strategies

**Actions**:
- **CRITICAL**: Ensure tests are written BEFORE code
- Review test coverage (must be > 90%)
- Validate test quality and assertions
- Create performance benchmarks
- Enforce TDD workflow: RED → GREEN → REFACTOR

---

### 🔧 ImplementationAgent
**Responsibility**: Write production code following TDD
**Scope**:
- Implement components after tests exist
- Async/await patterns
- Error handling and retry logic
- Latency optimization
- Code quality and type hints

**Actions**:
- **NEVER** write code without existing tests
- Implement minimum code to pass tests
- Refactor while keeping tests green
- Add type hints (mypy strict mode)
- Optimize for latency

---

### 🎤 AudioAgent
**Responsibility**: Audio capture, VAD, audio output
**Scope**:
- AudioCapture implementation
- VAD processor (Silero)
- AudioOutput to virtual device
- Audio resampling/format conversion
- Device discovery and management

**Actions**:
- Maintain low-latency audio I/O
- Handle audio device errors gracefully
- Ensure correct audio formats (PCM, sample rates)
- Implement fade-in/fade-out for anti-click

---

### 🌐 ServicesAgent
**Responsibility**: External API integrations (STT, Translation, TTS)
**Scope**:
- Deepgram WebSocket client
- OpenAI translation client
- ElevenLabs TTS WebSocket client
- API retry and circuit breaker logic
- Fallback strategies

**Actions**:
- Maintain persistent WebSocket connections
- Implement exponential backoff retry
- Handle streaming responses
- Manage API rate limits
- Implement fallback chains

---

### 🔄 PipelineAgent
**Responsibility**: Component orchestration, lifecycle management
**Scope**:
- PipelineOrchestrator implementation
- Queue management between components
- Health monitoring
- Metrics collection
- Graceful degradation/passthrough mode

**Actions**:
- Wire components via asyncio.Queue
- Monitor component health
- Collect latency metrics
- Activate fallback modes on failure
- Manage startup/shutdown sequences

---

### 📚 DocAgent
**Responsibility**: Documentation and knowledge management
**Scope**:
- API documentation
- Setup guides
- Troubleshooting documentation
- Architecture diagrams updates
- Inline code documentation

**Actions**:
- Keep documentation in sync with code
- Update VOICEBRIDGE_ARCHITECTURE.md when needed
- Write clear docstrings (Google style)
- Create troubleshooting guides

---

### 🔒 SecurityAgent
**Responsibility**: API key management, audio privacy, security
**Scope**:
- API key storage (env files, keychain)
- Network security (TLS, WSS)
- Audio data privacy
- Dependency vulnerability scanning

**Actions**:
- Ensure API keys NEVER in git
- Validate all network connections use encryption
- Review audio data handling (no persistence)
- Check for security vulnerabilities

---

## 3️⃣ Global Rules for All Agents

### 🚫 Prohibited Actions

1. **NEVER** modify code outside your scope/responsibility
2. **NEVER** commit code without tests (TDD is mandatory)
3. **NEVER** add features not in VOICEBRIDGE_ARCHITECTURE.md
4. **NEVER** introduce breaking changes to component protocols
5. **NEVER** commit API keys or secrets
6. **NEVER** bypass type checking or tests

### ✅ Required Actions

1. **ALWAYS** write tests before implementation
2. **ALWAYS** use async/await for I/O operations
3. **ALWAYS** measure and log latency metrics
4. **ALWAYS** handle errors with proper exception hierarchy
5. **ALWAYS** use type hints (Python 3.11+ syntax)
6. **ALWAYS** follow the streaming architecture pattern
7. **ALWAYS** check configuration via Pydantic Settings

### 📐 Design Principles

1. **Single Responsibility**: Each component does one thing
2. **Interface Segregation**: Use Protocol classes for all interfaces
3. **Dependency Injection**: Components receive dependencies via constructor
4. **Async-First**: All I/O is async
5. **Streaming Everywhere**: No component waits for completion
6. **Fail-Safe**: Activate passthrough mode on critical failures
7. **Observable**: Emit timing metrics for every operation

---

## 4️⃣ Code Conventions

### Naming Conventions

```python
# Classes: PascalCase
class AudioCaptureProtocol(Protocol): ...
class VADProcessor: ...

# Functions/methods: snake_case
async def start_capture() -> None: ...
def get_available_devices() -> list[AudioDevice]: ...

# Constants: UPPER_SNAKE_CASE
MAX_UTTERANCE_DURATION_MS = 15000
DEFAULT_SAMPLE_RATE = 16000

# Private members: _leading_underscore
def _internal_helper() -> None: ...

# Dataclasses: Use @dataclass with frozen=True, slots=True
@dataclass(frozen=True, slots=True)
class AudioChunk:
    data: bytes
    timestamp_ms: float
```

### Project Structure

```
src/voicebridge/
├── config/          # Pydantic Settings
├── core/            # Protocols, models, pipeline, exceptions
├── audio/           # Capture, VAD, output
├── services/        # STT, translation, TTS clients
│   ├── stt/
│   ├── translation/
│   └── tts/
├── ui/              # System tray, settings (optional)
└── utils/           # Logging, retry, helpers

tests/
├── unit/            # Fast, no external dependencies
├── integration/     # Requires API keys
├── performance/     # Latency benchmarks
└── fixtures/        # Test audio files
```

### Import Order (Ruff)

1. Standard library
2. Third-party packages
3. Local imports

```python
import asyncio
from dataclasses import dataclass
from typing import Protocol

import numpy as np
import sounddevice as sd
from pydantic import BaseModel

from voicebridge.core.models import AudioChunk
from voicebridge.core.protocols import AudioCaptureProtocol
```

### Type Hints (Required)

```python
# Use Python 3.11+ type syntax
def process_audio(data: bytes, rate: int) -> AudioChunk: ...
async def connect_websocket(url: str) -> None: ...

# Use Protocol for interfaces
class STTClientProtocol(Protocol):
    async def transcribe(self, audio: bytes) -> str: ...

# Use | for unions (not Union)
def get_device(device_id: int | None = None) -> AudioDevice: ...
```

### Async Patterns

```python
# ✅ Correct: Use async/await for I/O
async def send_audio(data: bytes) -> None:
    async with websockets.connect(url) as ws:
        await ws.send(data)

# ✅ Correct: Use asyncio.Queue for inter-component communication
async def producer(queue: asyncio.Queue[AudioChunk]) -> None:
    chunk = create_chunk()
    await queue.put(chunk)

# ❌ Incorrect: Don't use blocking calls in async functions
async def bad_example() -> None:
    time.sleep(1)  # BAD! Use await asyncio.sleep(1)
```

### Error Handling

```python
# Use custom exception hierarchy
from voicebridge.core.exceptions import STTError, STTConnectionError

try:
    await stt_client.connect()
except STTConnectionError as e:
    logger.error("stt_connection_failed", error=str(e))
    await activate_fallback()
    raise
```

### Logging (structlog)

```python
import structlog

logger = structlog.get_logger()

# ✅ Structured logging
logger.info(
    "utterance_processed",
    utterance_id=seq_num,
    latency_ms=total_latency,
    original_text=spanish,
    translated_text=english,
)

# ❌ Don't use print() or basic logging
print(f"Latency: {latency}")  # BAD
```

---

## 5️⃣ Workflow for Common Tasks

### 🆕 Adding a New Component

1. **TestAgent**: Write protocol/interface definition in `core/protocols.py`
2. **TestAgent**: Write data model in `core/models.py` with tests
3. **TestAgent**: Write failing unit tests for the component
4. **ImplementationAgent**: Implement minimum code to pass tests
5. **ImplementationAgent**: Refactor while keeping tests green
6. **PipelineAgent**: Wire component into pipeline
7. **DocAgent**: Update documentation

### 🐛 Fixing a Bug

1. **TestAgent**: Write a failing test that reproduces the bug
2. **ImplementationAgent**: Fix the bug (minimal change)
3. **TestAgent**: Verify all tests pass
4. **SecurityAgent**: Review if bug was security-related

### ⚡ Optimizing Latency

1. **TestAgent**: Add performance benchmark test
2. **ImplementationAgent**: Profile and identify bottleneck
3. **ArchitectAgent**: Review if optimization changes architecture
4. **ImplementationAgent**: Implement optimization
5. **TestAgent**: Verify benchmark shows improvement
6. **TestAgent**: Ensure unit tests still pass

### 🔌 Adding External API Integration

1. **TestAgent**: Write mock client with tests
2. **ServicesAgent**: Implement WebSocket/HTTP client
3. **ServicesAgent**: Add retry logic and circuit breaker
4. **ServicesAgent**: Implement fallback strategy
5. **TestAgent**: Write integration test (marked with `@pytest.mark.integration`)
6. **SecurityAgent**: Review API key handling

### 📊 Adding Metrics

1. **PipelineAgent**: Define metric in `core/metrics.py`
2. **TestAgent**: Write test for metric collection
3. **ImplementationAgent**: Emit metric at appropriate point
4. **DocAgent**: Document metric in monitoring section

---

## 6️⃣ TDD Workflow (MANDATORY)

### The Rule: RED → GREEN → REFACTOR

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  1. 🔴 RED: Write failing test                         │
│     ↓                                                   │
│  2. 🟢 GREEN: Write minimum code to pass               │
│     ↓                                                   │
│  3. 🔵 REFACTOR: Clean up while tests stay green       │
│     ↓                                                   │
│  4. ✅ COMMIT: All tests pass                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Test Categories

1. **Unit Tests**: Fast, no external dependencies, use mocks
   - Run with: `pytest -m unit`
   - Must pass BEFORE integration tests

2. **Integration Tests**: Require API keys, test real services
   - Run with: `pytest -m integration`
   - Mark with: `@pytest.mark.integration`

3. **Performance Tests**: Measure latency and memory
   - Run with: `pytest -m performance`
   - Must validate < 800ms end-to-end latency

### Development Order (by Phase)

```
Phase 1 — Foundation:
  ✅ config/settings.py + tests
  ✅ core/models.py + tests
  ✅ core/exceptions.py
  ✅ core/protocols.py

Phase 2 — Audio Layer:
  ✅ audio/capture.py + tests
  ✅ audio/vad.py + tests
  ✅ audio/output.py + tests

Phase 3 — Service Clients:
  ✅ services/stt/deepgram_client.py + tests
  ✅ services/translation/openai_client.py + tests
  ✅ services/tts/elevenlabs_client.py + tests

Phase 4 — Pipeline:
  ✅ core/pipeline.py + tests
  ✅ Integration tests
  ✅ Performance benchmarks

Phase 5 — Voice Cloning & Polish:
  ✅ Voice recording scripts
  ✅ End-to-end testing
  ✅ Latency optimization

Phase 6 — UI & Distribution (Optional):
  ✅ System tray app
  ✅ Installer scripts
```

---

## 7️⃣ Context & Knowledge Sources

### Priority Order for Decision Making

1. **VOICEBRIDGE_ARCHITECTURE.md** (single source of truth)
2. **Protocol definitions** in `core/protocols.py`
3. **Existing tests** (they define expected behavior)
4. **API documentation** (Deepgram, OpenAI, ElevenLabs)
5. **This file** (AGENTS.md)

### Critical Constraints

- **Latency Target**: < 800ms end-to-end (CRITICAL)
- **Audio Format**: 16kHz PCM for STT, 24kHz for TTS
- **Chunk Size**: 30ms audio chunks for minimal latency
- **VAD Silence Threshold**: 300ms silence = end of utterance
- **Supported Platforms**: Windows 10/11 (primary), macOS (secondary)

### External API Constraints

| Service | Limit | Handling |
|---------|-------|----------|
| Deepgram | WebSocket timeout after 10s silence | Send keepalive every 10s |
| OpenAI | Rate limit: 500 RPM | Retry with exponential backoff |
| ElevenLabs | 50 concurrent requests | Circuit breaker pattern |

---

## 8️⃣ Security & Compliance

### API Key Management

- **Storage**: `.env` file locally, OS keychain for production
- **Validation**: Check at startup, fail fast if invalid
- **Transmission**: HTTPS/WSS only, headers only (never in URLs)
- **Git**: `.env` is gitignored, use `.env.example` as template

### Audio Privacy

- **No Persistence**: Audio NEVER written to disk in production
- **External APIs**: Audio sent to Deepgram, ElevenLabs (user must acknowledge)
- **Logging**: Transcripts/translations logged ONLY at DEBUG level
- **Telemetry**: NONE — no analytics or tracking

### Network Security

- **TLS 1.2+** for all connections
- **WSS** (WebSocket Secure) for Deepgram/ElevenLabs
- **Certificate Validation**: Always enabled

---

## 9️⃣ Error Handling & Resilience

### Fallback Chain

```
TTS Failure:
  1. Retry ElevenLabs WebSocket (3x)
  2. Fallback: ElevenLabs REST API
  3. Fallback: OpenAI TTS (non-cloned voice)
  4. Fallback: Passthrough mode (original audio)

STT Failure:
  1. Retry Deepgram WebSocket (5x)
  2. Fallback: Passthrough mode

Translation Failure:
  1. Retry GPT-4o-mini (3x)
  2. Fallback: GPT-4o
  3. Fallback: Passthrough mode
```

### Retry Configuration

```python
# Exponential backoff with jitter
deepgram: max_retries=5, base_delay=0.5s, max_delay=30s
openai: max_retries=3, base_delay=0.3s, max_delay=10s
elevenlabs: max_retries=3, base_delay=0.5s, max_delay=15s
```

### Circuit Breaker

- **Threshold**: 5 consecutive failures → OPEN state
- **Recovery**: After 30s, transition to HALF_OPEN
- **Success**: First success → CLOSED state

---

## 🔟 Performance Targets

### Non-Functional Requirements

| Metric | Target | Priority |
|--------|--------|----------|
| End-to-end latency | < 800ms | CRITICAL |
| Voice fidelity | > 90% MOS similarity | HIGH |
| Translation accuracy | > 95% BLEU score | HIGH |
| CPU usage | < 30% | MEDIUM |
| Memory usage | < 512MB RSS | MEDIUM |
| Uptime | 99.9% during meetings | CRITICAL |

### Latency Breakdown (Target)

- Audio Capture: ~30ms (1 chunk)
- VAD Processing: < 5ms
- STT (Deepgram): ~250ms
- Translation (GPT-4o-mini): ~150ms
- TTS (ElevenLabs): ~300ms (first byte)
- Audio Output: ~50ms
- **Total**: ~600-700ms (with streaming overlap)

---

## 1️⃣1️⃣ Examples of Agent Tasks

### Example 1: TestAgent — Adding VAD Tests

```python
# tests/unit/test_vad.py

class TestVADProcessor:
    def test_detects_speech(self, mock_silero, speech_audio_chunk):
        """VAD should detect speech in audio with speech content."""
        vad = VADProcessor(config=VADConfig())
        result = vad.process(speech_audio_chunk)
        assert result is not None
        assert result.confidence > 0.8

    def test_ignores_silence(self, mock_silero, silence_audio_chunk):
        """VAD should not emit result for pure silence."""
        vad = VADProcessor(config=VADConfig())
        result = vad.process(silence_audio_chunk)
        assert result is None
```

### Example 2: ServicesAgent — Deepgram WebSocket Client

```python
# src/voicebridge/services/stt/deepgram_client.py

class DeepgramSTTClient:
    async def connect(self) -> None:
        """Establish WebSocket connection with retry logic."""
        retry_config = RETRY_CONFIGS["deepgram"]
        for attempt in range(retry_config.max_retries):
            try:
                self._ws = await websockets.connect(
                    self._build_url(),
                    extra_headers=self._auth_headers(),
                )
                logger.info("deepgram_connected", attempt=attempt)
                return
            except Exception as e:
                delay = retry_config.calculate_delay(attempt)
                logger.warning("deepgram_connect_failed", attempt=attempt, delay=delay)
                await asyncio.sleep(delay)
        raise STTConnectionError("Max retries exceeded")
```

### Example 3: PipelineAgent — Wiring Components

```python
# src/voicebridge/core/pipeline.py

class PipelineOrchestrator:
    def __init__(self, settings: VoiceBridgeSettings):
        # Create queues
        self.q_audio_to_vad = asyncio.Queue[AudioChunk](maxsize=50)
        self.q_vad_to_stt = asyncio.Queue[VADResult](maxsize=10)
        self.q_stt_to_translation = asyncio.Queue[TranscriptResult](maxsize=10)
        self.q_translation_to_tts = asyncio.Queue[TranslationResult](maxsize=10)
        self.q_tts_to_output = asyncio.Queue[TTSAudioResult](maxsize=50)

        # Create components
        self.audio_capture = AudioCapture(settings.audio)
        self.vad = VADProcessor(settings.vad)
        self.stt_client = DeepgramSTTClient(settings.stt)
        # ... etc

        # Wire components
        self.audio_capture.set_output_queue(self.q_audio_to_vad)
        self.vad.set_input_queue(self.q_audio_to_vad)
        self.vad.set_output_queue(self.q_vad_to_stt)
        # ... etc
```

---

## 1️⃣2️⃣ Quick Reference

### Commands

```bash
# Run unit tests only
pytest -m unit

# Run integration tests (requires API keys)
pytest -m integration

# Run performance benchmarks
pytest -m performance

# Run all tests
pytest

# Type checking
mypy src/voicebridge

# Linting
ruff check src/

# Format code
ruff format src/
```

### Configuration Files

- `.env` — API keys and settings (gitignored)
- `.env.example` — Template for configuration
- `pyproject.toml` — Python dependencies and tool configs
- `VOICEBRIDGE_ARCHITECTURE.md` — Single source of truth

### Key Files to Reference

- `src/voicebridge/core/protocols.py` — All component interfaces
- `src/voicebridge/core/models.py` — All data models
- `src/voicebridge/core/exceptions.py` — Exception hierarchy
- `src/voicebridge/config/settings.py` — Pydantic Settings

---

## 📝 Final Notes

### Agent Collaboration

- **TestAgent** ALWAYS works BEFORE ImplementationAgent
- **ArchitectAgent** reviews changes that affect multiple components
- **SecurityAgent** reviews ALL external API integrations
- **DocAgent** updates documentation after component completion

### When in Doubt

1. Check **VOICEBRIDGE_ARCHITECTURE.md** first
2. Look at existing **tests** for similar components
3. Prioritize **latency** over features
4. Follow **TDD** — no exceptions

### Success Criteria

- ✅ All unit tests pass
- ✅ Integration tests pass with real APIs
- ✅ End-to-end latency < 800ms
- ✅ Type checking passes (mypy strict)
- ✅ Code coverage > 90%
- ✅ No security vulnerabilities
- ✅ Documentation is up-to-date

---

**Remember: This is a latency-critical real-time system. Every millisecond counts. Test first, optimize always, fail gracefully.**
