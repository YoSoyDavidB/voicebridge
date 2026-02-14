# VoiceBridge — Real-Time Voice Interpreter for Microsoft Teams

## PROJECT IDENTITY

- **Project Name**: VoiceBridge
- **Version**: 1.0.0
- **Purpose**: Real-time Spanish-to-English voice interpreter that captures the user's microphone audio, translates it, synthesizes the translated speech using a clone of the user's own voice, and routes it to Microsoft Teams via a virtual audio device.
- **Target Latency**: < 800ms end-to-end (from speech capture to translated audio output)
- **Target Audience for this Document**: AI developer agent. This document is the single source of truth for building the entire system from scratch using TDD methodology.

---

## TABLE OF CONTENTS

1. [System Overview](#1-system-overview)
2. [Architecture Design](#2-architecture-design)
3. [Component Specifications](#3-component-specifications)
4. [Data Flow & Pipeline](#4-data-flow--pipeline)
5. [Voice Cloning Setup](#5-voice-cloning-setup)
6. [Latency Optimization Strategies](#6-latency-optimization-strategies)
7. [Project Structure](#7-project-structure)
8. [Configuration Management](#8-configuration-management)
9. [TDD Strategy & Test Plan](#9-tdd-strategy--test-plan)
10. [Docker & Deployment](#10-docker--deployment)
11. [API Contracts & Integrations](#11-api-contracts--integrations)
12. [Error Handling & Resilience](#12-error-handling--resilience)
13. [Monitoring & Observability](#13-monitoring--observability)
14. [Security Considerations](#14-security-considerations)
15. [Development Phases](#15-development-phases)
16. [Appendix](#16-appendix)

---

## 1. SYSTEM OVERVIEW

### 1.1 Problem Statement

The user participates in Microsoft Teams meetings where they speak Spanish but need their voice to be heard in English by other participants. The system must:

- Capture audio from the physical microphone in real-time
- Transcribe Spanish speech to text (STT)
- Translate Spanish text to English
- Synthesize the English text using a cloned version of the user's own voice (TTS)
- Route the synthesized audio to a virtual microphone device
- Teams picks up the virtual microphone as its input device

### 1.2 Non-Functional Requirements

| Requirement | Target | Priority |
|-------------|--------|----------|
| End-to-end latency | < 800ms | CRITICAL |
| Voice fidelity (clone similarity) | > 90% MOS similarity | HIGH |
| Translation accuracy | > 95% BLEU score for conversational ES→EN | HIGH |
| Audio quality | 24kHz, 16-bit minimum | HIGH |
| Uptime during meetings | 99.9% (no crashes mid-meeting) | CRITICAL |
| CPU usage | < 30% (to not interfere with Teams) | MEDIUM |
| Memory usage | < 512MB RSS | MEDIUM |
| Startup time | < 10 seconds | LOW |

### 1.3 Supported Platforms

- **Primary**: Windows 10/11 (most Teams users)
- **Secondary**: macOS (Ventura+)
- **Linux**: Ubuntu 22.04+ (development/testing only)

### 1.4 Technology Stack Summary

| Layer | Technology | Justification |
|-------|-----------|---------------|
| Language | Python 3.11+ | Ecosystem for audio/ML, async support |
| Async Runtime | asyncio + uvloop | Low-overhead event loop |
| Audio Capture | sounddevice (PortAudio) | Cross-platform, low-latency audio I/O |
| VAD | Silero VAD | Fast, accurate, local, < 1ms inference |
| STT | Deepgram (streaming WebSocket) | ~200-300ms, best streaming latency |
| Translation | GPT-4o-mini (OpenAI API) | Fast, high quality, streaming support |
| TTS | ElevenLabs Turbo v2.5 (streaming) | Professional voice cloning + low latency |
| Virtual Audio | VB-Audio Virtual Cable (Win) / BlackHole (Mac) | Industry standard virtual audio routing |
| Configuration | Pydantic Settings + .env | Type-safe config with validation |
| Testing | pytest + pytest-asyncio + pytest-mock | TDD with async support |
| Containerization | Docker + Docker Compose | Reproducible dev environment |
| CI/CD | GitHub Actions | Automated testing pipeline |

---

## 2. ARCHITECTURE DESIGN

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         VoiceBridge Application                         │
│                                                                         │
│  ┌──────────┐   ┌──────────┐   ┌───────────┐   ┌──────────┐           │
│  │  Audio    │──▶│   VAD    │──▶│    STT    │──▶│Translator│           │
│  │ Capture   │   │ (Silero) │   │(Deepgram) │   │(GPT-4o-  │           │
│  │(sounddev) │   │          │   │ Streaming │   │  mini)   │           │
│  └──────────┘   └──────────┘   └───────────┘   └────┬─────┘           │
│       ▲                                              │                  │
│       │                                              ▼                  │
│  ┌──────────┐                                  ┌──────────┐            │
│  │ Physical │                                  │   TTS    │            │
│  │   Mic    │                                  │(Eleven   │            │
│  └──────────┘                                  │  Labs)   │            │
│                                                └────┬─────┘            │
│                                                     │                  │
│                                                     ▼                  │
│                                               ┌──────────┐            │
│                                               │  Audio   │            │
│                                               │  Output  │            │
│                                               │(Virtual  │            │
│                                               │   Mic)   │            │
│                                               └────┬─────┘            │
│                                                    │                   │
└────────────────────────────────────────────────────┼───────────────────┘
                                                     │
                                                     ▼
                                              ┌──────────────┐
                                              │  Microsoft   │
                                              │    Teams     │
                                              │ (picks up    │
                                              │ virtual mic) │
                                              └──────────────┘
```

### 2.2 Component Architecture (Detailed)

The system follows a **Pipeline Architecture** with **async streaming** between components. Each component is an independent async processor connected via `asyncio.Queue` objects.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Pipeline Orchestrator                               │
│                                                                                  │
│  AudioCapture ──Queue──▶ VADProcessor ──Queue──▶ STTClient ──Queue──▶           │
│                                                                                  │
│  ──Queue──▶ TranslationClient ──Queue──▶ TTSClient ──Queue──▶ AudioOutput       │
│                                                                                  │
│  Each Queue carries typed dataclasses (AudioChunk, VADResult, Transcript, etc.)  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Design Principles

1. **Single Responsibility**: Each component does exactly one thing
2. **Interface Segregation**: All components implement abstract base classes (protocols)
3. **Dependency Injection**: Components receive their dependencies via constructor
4. **Async-First**: All I/O-bound operations use async/await
5. **Streaming Everywhere**: No component waits for full completion; all stream partial results
6. **Fail-Safe**: If any component fails, audio passthrough (original mic) activates
7. **Observable**: Every component emits timing metrics

---

## 3. COMPONENT SPECIFICATIONS

### 3.1 AudioCapture

**Responsibility**: Capture raw audio from the physical microphone in real-time and push audio chunks to the pipeline.

```python
# Interface
class AudioCaptureProtocol(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    def set_output_queue(self, queue: asyncio.Queue[AudioChunk]) -> None: ...
    def get_available_devices(self) -> list[AudioDevice]: ...
    def set_device(self, device_id: int) -> None: ...
```

**Configuration**:
```python
class AudioCaptureConfig(BaseModel):
    sample_rate: int = 16000          # 16kHz for STT compatibility
    channels: int = 1                  # Mono
    chunk_duration_ms: int = 30        # 30ms chunks (480 samples at 16kHz)
    dtype: str = "int16"               # 16-bit PCM
    device_id: int | None = None       # None = system default
    buffer_size: int = 10              # Queue max size before backpressure
```

**Data Model**:
```python
@dataclass(frozen=True, slots=True)
class AudioChunk:
    data: bytes                        # Raw PCM audio bytes
    timestamp_ms: float                # Monotonic timestamp when captured
    sample_rate: int                   # Sample rate of the audio
    channels: int                      # Number of channels
    duration_ms: float                 # Duration of this chunk in ms
    sequence_number: int               # Monotonically increasing sequence
```

**Implementation Notes**:
- Use `sounddevice.RawInputStream` with a callback function
- The callback pushes `AudioChunk` objects to the output queue
- Use `time.monotonic()` for timestamps (not wall clock)
- Chunk size of 30ms balances latency vs overhead
- The callback runs in a separate thread; use `loop.call_soon_threadsafe` to put items on the asyncio queue

### 3.2 VADProcessor (Voice Activity Detection)

**Responsibility**: Filter audio chunks to identify speech segments. Only forward audio that contains speech, grouping chunks into utterances.

```python
class VADProcessorProtocol(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    def set_input_queue(self, queue: asyncio.Queue[AudioChunk]) -> None: ...
    def set_output_queue(self, queue: asyncio.Queue[VADResult]) -> None: ...
```

**Configuration**:
```python
class VADConfig(BaseModel):
    threshold: float = 0.5             # Speech probability threshold
    min_speech_duration_ms: int = 250  # Minimum speech segment
    min_silence_duration_ms: int = 300 # Silence before end of utterance
    speech_pad_ms: int = 100           # Padding around speech segments
    max_utterance_duration_ms: int = 15000  # Force-split long utterances
    model_name: str = "silero_vad"     # VAD model identifier
```

**Data Model**:
```python
@dataclass(frozen=True, slots=True)
class VADResult:
    audio_data: bytes                  # Concatenated speech audio
    start_timestamp_ms: float          # When speech started
    end_timestamp_ms: float            # When speech ended
    duration_ms: float                 # Total speech duration
    confidence: float                  # Average speech probability
    is_partial: bool                   # True if utterance was force-split
    sequence_number: int
```

**Implementation Notes**:
- Use Silero VAD from `torch.hub` or `silero-vad` package
- Silero expects 16kHz mono audio in 30ms frames (512 samples)
- Accumulate chunks while speech is detected
- Emit `VADResult` when silence exceeds `min_silence_duration_ms`
- Force-emit partial results after `max_utterance_duration_ms` to prevent unbounded latency
- The `speech_pad_ms` prevents cutting off the beginning/end of words

**CRITICAL for latency**: The `min_silence_duration_ms` parameter directly impacts latency. 300ms is a good balance — shorter values cause false splits mid-sentence, longer values add unnecessary delay.

### 3.3 STTClient (Speech-to-Text)

**Responsibility**: Transcribe speech audio segments to Spanish text using Deepgram's streaming API.

```python
class STTClientProtocol(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    def set_input_queue(self, queue: asyncio.Queue[VADResult]) -> None: ...
    def set_output_queue(self, queue: asyncio.Queue[TranscriptResult]) -> None: ...
```

**Configuration**:
```python
class STTConfig(BaseModel):
    provider: str = "deepgram"
    api_key: str                        # Deepgram API key
    language: str = "es"                # Source language: Spanish
    model: str = "nova-2"              # Deepgram Nova 2 model
    encoding: str = "linear16"          # PCM 16-bit
    sample_rate: int = 16000
    channels: int = 1
    punctuate: bool = True              # Add punctuation
    smart_format: bool = True           # Smart formatting
    interim_results: bool = True        # Get partial transcripts
    endpointing: int = 300              # ms of silence to finalize
    utterance_end_ms: int = 1000        # Max wait for utterance end
    vad_events: bool = True             # VAD events from Deepgram
```

**Data Model**:
```python
@dataclass(frozen=True, slots=True)
class TranscriptResult:
    text: str                           # Transcribed Spanish text
    is_final: bool                      # True if this is the final transcript
    confidence: float                   # Transcription confidence
    start_timestamp_ms: float           # From original audio capture time
    processing_latency_ms: float        # Time spent in STT
    language: str                       # Detected/configured language
    words: list[WordInfo] | None        # Word-level timing (if available)
    sequence_number: int

@dataclass(frozen=True, slots=True)
class WordInfo:
    word: str
    start_ms: float
    end_ms: float
    confidence: float
```

**Implementation Notes**:
- Maintain a persistent WebSocket connection to Deepgram
- Send audio bytes from `VADResult` immediately upon receipt
- Listen for both `interim_results` (partial) and final transcripts
- Forward ONLY `is_final=True` results to the translation queue (to avoid translating incomplete sentences)
- HOWEVER: if `interim_results` text hasn't changed for > 500ms, treat it as final (Deepgram sometimes delays finalization)
- Reconnect automatically on WebSocket disconnection with exponential backoff
- Keep the WebSocket alive with keepalive messages every 10 seconds

**Deepgram WebSocket Protocol**:
```
wss://api.deepgram.com/v1/listen?
  model=nova-2&
  language=es&
  encoding=linear16&
  sample_rate=16000&
  channels=1&
  punctuate=true&
  smart_format=true&
  interim_results=true&
  endpointing=300&
  utterance_end_ms=1000&
  vad_events=true
```

### 3.4 TranslationClient

**Responsibility**: Translate Spanish text to English using GPT-4o-mini with streaming.

```python
class TranslationClientProtocol(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    def set_input_queue(self, queue: asyncio.Queue[TranscriptResult]) -> None: ...
    def set_output_queue(self, queue: asyncio.Queue[TranslationResult]) -> None: ...
```

**Configuration**:
```python
class TranslationConfig(BaseModel):
    provider: str = "openai"
    api_key: str                        # OpenAI API key
    model: str = "gpt-4o-mini"
    source_language: str = "Spanish"
    target_language: str = "English"
    max_tokens: int = 500
    temperature: float = 0.3            # Low temp for consistent translations
    timeout_seconds: float = 5.0
    system_prompt: str = """You are a real-time interpreter translating spoken Spanish to English.

CRITICAL RULES:
1. Translate the spoken Spanish text to natural, conversational English.
2. Maintain the speaker's tone, intent, and register (formal/informal).
3. Do NOT add explanations, notes, or commentary.
4. Do NOT translate proper nouns (names, company names, etc.).
5. Handle filler words naturally: "este..." → "um...", "o sea" → "I mean".
6. Preserve technical jargon when it's used in English in the source (common in tech meetings).
7. If the input is unclear or incomplete, translate what you can and keep the same level of ambiguity.
8. Output ONLY the English translation, nothing else.
9. Match the formality level: "usted" → formal English, "tú" → casual English.
10. For numbers, dates, and measurements, use the English convention."""
```

**Data Model**:
```python
@dataclass(frozen=True, slots=True)
class TranslationResult:
    original_text: str                  # Original Spanish text
    translated_text: str                # Translated English text
    start_timestamp_ms: float           # From original audio capture time
    processing_latency_ms: float        # Time spent in translation
    sequence_number: int
```

**Implementation Notes**:
- Use the OpenAI Python SDK with `stream=True`
- Accumulate streamed tokens and emit the result when the stream completes
- DO NOT wait for the full response before forwarding — instead, use a **speculative forwarding** strategy:
  - After receiving the first ~80% of expected tokens (based on input length heuristic), start forwarding partial translation to TTS
  - The TTS can begin synthesis while the last few tokens arrive
- Use a conversation-style prompt (not a formal document translation prompt)
- Timeout after `timeout_seconds` and forward whatever partial translation exists
- Log all translations for debugging

**Latency Optimization — Parallel Streaming**:
```
STT final transcript arrives at T=0
  T=0ms:   Send to OpenAI API
  T=50ms:  First token arrives via stream
  T=80ms:  ~3-4 words accumulated → forward partial to TTS
  T=150ms: Full translation complete → signal TTS that translation is final
```

### 3.5 TTSClient (Text-to-Speech with Voice Cloning)

**Responsibility**: Synthesize English text into speech using a clone of the user's voice via ElevenLabs.

```python
class TTSClientProtocol(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    def set_input_queue(self, queue: asyncio.Queue[TranslationResult]) -> None: ...
    def set_output_queue(self, queue: asyncio.Queue[TTSAudioResult]) -> None: ...
```

**Configuration**:
```python
class TTSConfig(BaseModel):
    provider: str = "elevenlabs"
    api_key: str                        # ElevenLabs API key
    voice_id: str                       # Cloned voice ID (from ElevenLabs)
    model_id: str = "eleven_turbo_v2_5" # Turbo model for low latency
    output_format: str = "pcm_24000"    # 24kHz PCM for quality
    stability: float = 0.5             # Voice stability (0-1)
    similarity_boost: float = 0.8      # How close to original voice (0-1)
    style: float = 0.0                 # Style exaggeration (keep at 0 for natural)
    use_speaker_boost: bool = True     # Enhance voice clarity
    optimize_streaming_latency: int = 3 # 0-4, higher = lower latency but lower quality
    websocket_mode: bool = True        # Use WebSocket for streaming (lower latency)
```

**Data Model**:
```python
@dataclass(frozen=True, slots=True)
class TTSAudioResult:
    audio_data: bytes                   # PCM audio bytes
    sample_rate: int                    # 24000 Hz
    channels: int                       # 1 (mono)
    is_partial: bool                    # True if more audio coming for this utterance
    start_timestamp_ms: float           # From original audio capture time
    processing_latency_ms: float        # Total pipeline latency so far
    sequence_number: int
```

**Implementation Notes**:
- Use ElevenLabs WebSocket API for streaming TTS (much lower latency than REST)
- WebSocket endpoint: `wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id=eleven_turbo_v2_5&output_format=pcm_24000`
- Send text chunks as they arrive from translation (don't wait for full translation)
- Receive audio chunks as they're generated and immediately forward to AudioOutput
- The WebSocket mode allows sending text incrementally and receiving audio incrementally
- Keep connection alive between utterances to avoid reconnection overhead

**ElevenLabs WebSocket Protocol**:
```json
// Initial message (BOS - Beginning of Stream)
{
  "text": " ",
  "voice_settings": {
    "stability": 0.5,
    "similarity_boost": 0.8,
    "style": 0.0,
    "use_speaker_boost": true
  },
  "generation_config": {
    "chunk_length_schedule": [120, 160, 250, 290]
  },
  "xi_api_key": "YOUR_API_KEY"
}

// Text chunks (send as translation streams in)
{
  "text": "Hello, ",
  "try_trigger_generation": true
}

// End of stream (EOS)
{
  "text": ""
}

// Response format (audio chunks)
{
  "audio": "base64_encoded_pcm_audio",
  "isFinal": false,
  "normalizedAlignment": { ... }
}
```

### 3.6 AudioOutput

**Responsibility**: Write synthesized audio to the virtual microphone device for Teams to pick up.

```python
class AudioOutputProtocol(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    def set_input_queue(self, queue: asyncio.Queue[TTSAudioResult]) -> None: ...
    def set_output_device(self, device_id: int) -> None: ...
    def get_available_devices(self) -> list[AudioDevice]: ...
```

**Configuration**:
```python
class AudioOutputConfig(BaseModel):
    sample_rate: int = 24000           # Match TTS output
    channels: int = 1                   # Mono
    dtype: str = "int16"               # 16-bit PCM
    device_id: int | None = None       # Virtual mic device ID
    buffer_size_ms: int = 50           # Output buffer size
    resample_quality: str = "high"     # Resampling quality if needed
    fade_in_ms: int = 5                # Anti-click fade in
    fade_out_ms: int = 5               # Anti-click fade out
```

**Implementation Notes**:
- Use `sounddevice.RawOutputStream` targeting the virtual audio device
- If TTS sample rate (24kHz) differs from virtual device requirement, resample using `scipy.signal.resample_poly` or `soxr`
- Apply short fade-in/fade-out to prevent audio clicks between utterances
- Maintain an internal buffer to handle jitter in TTS audio delivery
- If the buffer runs dry (TTS is slow), output silence rather than glitching
- Support writing to VB-Audio Virtual Cable (Windows) or BlackHole (macOS)

### 3.7 PipelineOrchestrator

**Responsibility**: Wire all components together, manage lifecycle, handle errors, and provide system-wide coordination.

```python
class PipelineOrchestrator:
    """
    Central coordinator that:
    1. Instantiates all components with their configs
    2. Creates and connects asyncio.Queue objects between components
    3. Starts/stops all components in the correct order
    4. Monitors component health
    5. Handles graceful degradation (fallback to passthrough)
    6. Collects and reports latency metrics
    """

    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def health_check(self) -> PipelineHealth: ...
    def get_metrics(self) -> PipelineMetrics: ...
    def set_passthrough_mode(self, enabled: bool) -> None: ...
```

**Data Models**:
```python
@dataclass
class PipelineHealth:
    is_healthy: bool
    component_statuses: dict[str, ComponentStatus]
    uptime_seconds: float
    total_utterances_processed: int
    average_latency_ms: float

@dataclass
class ComponentStatus:
    name: str
    is_running: bool
    queue_depth: int
    last_error: str | None
    avg_processing_time_ms: float

@dataclass
class PipelineMetrics:
    total_latency_ms: float            # End-to-end
    capture_latency_ms: float          # Audio capture
    vad_latency_ms: float              # VAD processing
    stt_latency_ms: float              # Speech-to-text
    translation_latency_ms: float      # Translation
    tts_latency_ms: float              # Text-to-speech
    output_latency_ms: float           # Audio output
    queue_depths: dict[str, int]       # Current queue sizes
    timestamp: float                   # When metrics were collected
```

---

## 4. DATA FLOW & PIPELINE

### 4.1 Streaming Data Flow (Happy Path)

```
Time ─────────────────────────────────────────────────────────────────────▶

User speaks: "Necesitamos revisar el presupuesto del Q3"

T=0ms     AudioCapture: chunk[0] (30ms audio)
T=30ms    AudioCapture: chunk[1] (30ms audio)
          VAD: analyzing chunk[0] → speech_prob=0.92
T=60ms    AudioCapture: chunk[2]
          VAD: analyzing chunk[1] → speech_prob=0.95
...
T=1800ms  User stops speaking
T=2100ms  VAD: silence detected (300ms) → emit VADResult (1800ms of audio)
          STT: receives VADResult, sends audio to Deepgram
T=2350ms  STT: final transcript → "Necesitamos revisar el presupuesto del Q3"
          Translation: receives transcript, sends to GPT-4o-mini
T=2450ms  Translation: first tokens stream → "We need to"
          TTS: receives partial text, starts synthesis
T=2550ms  Translation: more tokens → "We need to review the Q3 budget"
          TTS: first audio chunk ready
          AudioOutput: starts playing cloned voice
T=2700ms  TTS: final audio chunk
          AudioOutput: finishes playback
T=2700ms  Total latency from end of speech: ~600ms
          Total latency from start of speech: ~2700ms (includes speaking time)
```

### 4.2 Queue Specification

| Queue | From → To | Type | Max Size | Backpressure Strategy |
|-------|-----------|------|----------|----------------------|
| Q1 | AudioCapture → VAD | `AudioChunk` | 50 | Drop oldest chunks |
| Q2 | VAD → STT | `VADResult` | 10 | Block (critical data) |
| Q3 | STT → Translation | `TranscriptResult` | 10 | Block (critical data) |
| Q4 | Translation → TTS | `TranslationResult` | 10 | Block (critical data) |
| Q5 | TTS → AudioOutput | `TTSAudioResult` | 50 | Drop oldest (avoid buffering) |

### 4.3 Parallel Streaming Strategy (Critical for Latency)

The key latency optimization is **NOT** running components sequentially, but **overlapping** them:

```
Traditional (Sequential):
  VAD ──────▶ STT ──────▶ Translate ──────▶ TTS ──────▶ Output
  300ms        250ms        200ms            400ms        50ms  = 1200ms

Optimized (Parallel Streaming):
  VAD ──────▶ STT ─┐
                    ├──▶ Translate ─┐
              (streaming)           ├──▶ TTS ─┐
                              (streaming)     ├──▶ Output
                                        (streaming)
  300ms        250ms   100ms       150ms     50ms  = ~600ms (overlapped)
```

**How to achieve this**:
1. STT sends `interim_results` while still processing → Translation begins early
2. Translation streams tokens → TTS begins synthesizing the first words
3. TTS streams audio chunks → AudioOutput begins playing immediately
4. Net effect: ~40-50% latency reduction

---

## 5. VOICE CLONING SETUP

### 5.1 ElevenLabs Professional Voice Clone

**Process for creating the voice clone**:

1. **Audio Collection**:
   - Record 30+ minutes of the user's voice
   - Mix of Spanish and English speech (ElevenLabs handles multilingual)
   - Requirements:
     - Quiet environment (< 40dB ambient noise)
     - Good microphone (USB condenser recommended)
     - 44.1kHz or 48kHz, 16-bit WAV format
     - Natural speaking pace, varied intonation
     - Include different emotions: neutral, enthusiastic, serious
   - Content suggestions:
     - Read aloud from news articles (5 minutes)
     - Read aloud from a novel (5 minutes)
     - Conversational monologue about work topics (10 minutes)
     - Technical explanations (5 minutes)
     - Free-form storytelling (5 minutes)

2. **Upload to ElevenLabs**:
   - Use the Professional Voice Clone feature (requires Scale or Pro plan)
   - Upload all audio files
   - Complete identity verification (required by ElevenLabs)
   - Processing takes 24-48 hours

3. **Voice ID**:
   - Once processed, note the `voice_id` from ElevenLabs dashboard
   - Store this in the configuration as `TTS_VOICE_ID`

### 5.2 Voice Clone Quality Verification

Create a verification script that:
1. Takes a set of English test phrases
2. Synthesizes them with the cloned voice
3. Runs MOS (Mean Opinion Score) comparison against recordings of the user speaking the same phrases
4. Outputs a similarity score

```python
# Test phrases for voice clone verification
VERIFICATION_PHRASES = [
    "Good morning everyone, let's get started with today's meeting.",
    "I think we should focus on the third quarter budget projections.",
    "Can you share your screen so we can review the data together?",
    "That's a great point. Let me add that to our action items.",
    "We'll need to follow up on this before our next meeting on Friday.",
]
```

### 5.3 Fallback Voice Strategy

If ElevenLabs is unavailable:
1. **Primary fallback**: Use ElevenLabs REST API instead of WebSocket
2. **Secondary fallback**: Use OpenAI TTS (`tts-1` model, `onyx` voice) — not cloned, but functional
3. **Emergency fallback**: Pass through original Spanish audio (no translation)

---

## 6. LATENCY OPTIMIZATION STRATEGIES

### 6.1 Audio Capture Optimizations

- Use 30ms chunks (not 100ms+) to reduce initial buffering delay
- Use `RawInputStream` instead of `InputStream` to avoid numpy overhead
- Pin the audio callback to a dedicated thread with high priority
- Pre-allocate audio buffers to avoid GC during capture

### 6.2 VAD Optimizations

- Run Silero VAD in a dedicated thread with `torch.no_grad()`
- Use ONNX runtime instead of PyTorch for ~2x faster inference
- Cache the VAD model in memory at startup
- Use aggressive endpointing: 300ms silence = end of utterance

### 6.3 STT Optimizations

- Maintain a persistent WebSocket connection (avoid connection overhead)
- Send audio immediately as VAD emits — don't batch
- Use Deepgram's `endpointing=300` to match our VAD settings
- Enable `interim_results` but only forward finals to translation

### 6.4 Translation Optimizations

- Use GPT-4o-mini (faster than GPT-4o, sufficient quality for translation)
- Stream the response (`stream=True`)
- Begin TTS before translation is complete (speculative execution)
- Keep the system prompt short and focused
- Use `temperature=0.3` (low randomness = faster generation)

### 6.5 TTS Optimizations

- Use ElevenLabs WebSocket API (not REST) for input streaming
- Set `optimize_streaming_latency=3` (prioritize speed)
- Use `pcm_24000` output format (no decoding overhead)
- Use `chunk_length_schedule: [120, 160, 250, 290]` for fast first chunk
- Start synthesis from partial translation text
- Keep the WebSocket connection alive between utterances

### 6.6 Audio Output Optimizations

- Pre-allocate output buffer
- Use non-blocking writes to the virtual audio device
- Apply minimal post-processing (just fade in/out for anti-click)
- If resampling is needed, use `soxr` (fastest resampler)

### 6.7 System-Level Optimizations

- Use `uvloop` as the asyncio event loop (2-4x faster than default)
- Set process priority to high/realtime on Windows
- Disable Python GC during active pipeline processing
- Use `__slots__` on all dataclasses (already specified with `slots=True`)
- Pre-warm all API connections at startup (connect WebSockets before first utterance)

---

## 7. PROJECT STRUCTURE

```
voicebridge/
├── pyproject.toml                     # Project metadata, dependencies, tool configs
├── Dockerfile                         # Production container
├── Dockerfile.dev                     # Development container with test tools
├── docker-compose.yml                 # Full development environment
├── docker-compose.test.yml            # Testing environment
├── .env.example                       # Template for environment variables
├── .env                               # Local environment variables (gitignored)
├── README.md                          # Project overview and quick start
├── Makefile                           # Common development commands
│
├── src/
│   └── voicebridge/
│       ├── __init__.py
│       ├── __main__.py                # Entry point: `python -m voicebridge`
│       ├── app.py                     # Application bootstrap and CLI
│       │
│       ├── config/
│       │   ├── __init__.py
│       │   ├── settings.py            # Pydantic Settings (all configuration)
│       │   └── constants.py           # Immutable constants
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── protocols.py           # All Protocol/ABC definitions
│       │   ├── models.py              # All dataclass models (AudioChunk, etc.)
│       │   ├── pipeline.py            # PipelineOrchestrator
│       │   ├── metrics.py             # MetricsCollector
│       │   └── exceptions.py          # Custom exception hierarchy
│       │
│       ├── audio/
│       │   ├── __init__.py
│       │   ├── capture.py             # AudioCapture implementation
│       │   ├── output.py              # AudioOutput implementation
│       │   ├── vad.py                 # VADProcessor implementation
│       │   ├── resampler.py           # Audio resampling utilities
│       │   └── devices.py             # Audio device discovery and management
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   ├── stt/
│       │   │   ├── __init__.py
│       │   │   ├── base.py            # STT protocol/base
│       │   │   ├── deepgram_client.py # Deepgram WebSocket implementation
│       │   │   └── mock_client.py     # Mock STT for testing
│       │   │
│       │   ├── translation/
│       │   │   ├── __init__.py
│       │   │   ├── base.py            # Translation protocol/base
│       │   │   ├── openai_client.py   # GPT-4o-mini implementation
│       │   │   └── mock_client.py     # Mock translation for testing
│       │   │
│       │   └── tts/
│       │       ├── __init__.py
│       │       ├── base.py            # TTS protocol/base
│       │       ├── elevenlabs_client.py  # ElevenLabs WebSocket implementation
│       │       ├── openai_client.py   # OpenAI TTS fallback
│       │       └── mock_client.py     # Mock TTS for testing
│       │
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── tray.py                # System tray icon and menu
│       │   ├── settings_window.py     # Settings GUI (device selection, etc.)
│       │   └── status_overlay.py      # Floating overlay showing current status
│       │
│       └── utils/
│           ├── __init__.py
│           ├── logging.py             # Structured logging setup
│           ├── retry.py               # Retry/backoff utilities
│           └── audio_utils.py         # Audio format conversion helpers
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # Shared fixtures
│   │
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_models.py             # Test data models
│   │   ├── test_audio_capture.py      # Test AudioCapture
│   │   ├── test_vad.py                # Test VADProcessor
│   │   ├── test_stt_client.py         # Test STT client
│   │   ├── test_translation_client.py # Test translation
│   │   ├── test_tts_client.py         # Test TTS client
│   │   ├── test_audio_output.py       # Test AudioOutput
│   │   ├── test_pipeline.py           # Test PipelineOrchestrator
│   │   ├── test_metrics.py            # Test metrics collection
│   │   ├── test_config.py             # Test configuration loading
│   │   └── test_retry.py              # Test retry logic
│   │
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_stt_deepgram.py       # Live Deepgram integration
│   │   ├── test_translation_openai.py # Live OpenAI integration
│   │   ├── test_tts_elevenlabs.py     # Live ElevenLabs integration
│   │   ├── test_audio_pipeline.py     # Capture → VAD → Output
│   │   └── test_full_pipeline.py      # End-to-end with real APIs
│   │
│   ├── performance/
│   │   ├── __init__.py
│   │   ├── test_latency.py            # Latency benchmarks per component
│   │   ├── test_throughput.py          # Throughput under load
│   │   └── test_memory.py             # Memory usage profiling
│   │
│   └── fixtures/
│       ├── audio/
│       │   ├── spanish_short.wav       # 2s Spanish speech sample
│       │   ├── spanish_medium.wav      # 10s Spanish speech sample
│       │   ├── spanish_long.wav        # 30s Spanish speech sample
│       │   ├── silence.wav             # 2s silence
│       │   ├── noise.wav               # 2s background noise
│       │   └── mixed_speech_noise.wav  # Speech with background noise
│       └── transcripts/
│           ├── expected_transcripts.json  # Expected STT outputs
│           └── expected_translations.json # Expected translation outputs
│
├── scripts/
│   ├── setup_virtual_audio.py         # Install/configure virtual audio device
│   ├── record_voice_samples.py        # Guide user through voice recording
│   ├── verify_voice_clone.py          # Test voice clone quality
│   ├── benchmark_latency.py           # Run latency benchmarks
│   └── generate_test_fixtures.py      # Generate test audio fixtures
│
└── docs/
    ├── SETUP.md                       # Setup instructions
    ├── VOICE_CLONING.md               # Voice cloning guide
    ├── TROUBLESHOOTING.md             # Common issues and fixes
    └── API_REFERENCE.md               # Internal API documentation
```

---

## 8. CONFIGURATION MANAGEMENT

### 8.1 Environment Variables

```bash
# .env.example

# ─── API Keys ─────────────────────────────────────────────
DEEPGRAM_API_KEY=your_deepgram_api_key
OPENAI_API_KEY=your_openai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key

# ─── Voice Configuration ──────────────────────────────────
ELEVENLABS_VOICE_ID=your_cloned_voice_id
TTS_MODEL=eleven_turbo_v2_5
TTS_STABILITY=0.5
TTS_SIMILARITY_BOOST=0.8
TTS_OPTIMIZE_STREAMING_LATENCY=3

# ─── Audio Configuration ──────────────────────────────────
AUDIO_INPUT_DEVICE_ID=               # Empty = system default
AUDIO_OUTPUT_DEVICE_ID=              # Virtual mic device ID
AUDIO_SAMPLE_RATE=16000
AUDIO_CHUNK_DURATION_MS=30

# ─── STT Configuration ────────────────────────────────────
STT_PROVIDER=deepgram
STT_LANGUAGE=es
STT_MODEL=nova-2

# ─── Translation Configuration ────────────────────────────
TRANSLATION_PROVIDER=openai
TRANSLATION_MODEL=gpt-4o-mini
TRANSLATION_TEMPERATURE=0.3

# ─── VAD Configuration ────────────────────────────────────
VAD_THRESHOLD=0.5
VAD_MIN_SILENCE_MS=300
VAD_MAX_UTTERANCE_MS=15000

# ─── Pipeline Configuration ───────────────────────────────
PIPELINE_PASSTHROUGH_MODE=false
PIPELINE_LOG_LEVEL=INFO
PIPELINE_METRICS_ENABLED=true
PIPELINE_METRICS_INTERVAL_SECONDS=30

# ─── Fallback Configuration ───────────────────────────────
FALLBACK_TTS_PROVIDER=openai
FALLBACK_TTS_VOICE=onyx
```

### 8.2 Pydantic Settings Model

```python
# src/voicebridge/config/settings.py

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator

class VoiceBridgeSettings(BaseSettings):
    """
    Centralized configuration using Pydantic Settings.
    Values are loaded from environment variables and .env file.
    """

    # API Keys
    deepgram_api_key: str = Field(..., description="Deepgram API key")
    openai_api_key: str = Field(..., description="OpenAI API key")
    elevenlabs_api_key: str = Field(..., description="ElevenLabs API key")

    # Voice
    elevenlabs_voice_id: str = Field(..., description="Cloned voice ID")
    tts_model: str = "eleven_turbo_v2_5"
    tts_stability: float = Field(0.5, ge=0.0, le=1.0)
    tts_similarity_boost: float = Field(0.8, ge=0.0, le=1.0)
    tts_optimize_streaming_latency: int = Field(3, ge=0, le=4)

    # Audio
    audio_input_device_id: int | None = None
    audio_output_device_id: int | None = None
    audio_sample_rate: int = 16000
    audio_chunk_duration_ms: int = 30

    # STT
    stt_provider: str = "deepgram"
    stt_language: str = "es"
    stt_model: str = "nova-2"

    # Translation
    translation_provider: str = "openai"
    translation_model: str = "gpt-4o-mini"
    translation_temperature: float = Field(0.3, ge=0.0, le=2.0)

    # VAD
    vad_threshold: float = Field(0.5, ge=0.0, le=1.0)
    vad_min_silence_ms: int = 300
    vad_max_utterance_ms: int = 15000

    # Pipeline
    pipeline_passthrough_mode: bool = False
    pipeline_log_level: str = "INFO"
    pipeline_metrics_enabled: bool = True
    pipeline_metrics_interval_seconds: int = 30

    # Fallback
    fallback_tts_provider: str = "openai"
    fallback_tts_voice: str = "onyx"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
```

---

## 9. TDD STRATEGY & TEST PLAN

### 9.1 TDD Workflow

For EVERY component, follow this strict order:

1. **RED**: Write a failing test that defines the expected behavior
2. **GREEN**: Write the minimum code to make the test pass
3. **REFACTOR**: Clean up the code while keeping tests green

### 9.2 Test Categories

#### Category 1: Unit Tests (MUST pass before any integration work)

Each component must have unit tests that use mocks for all external dependencies.

**test_models.py** — Test all data models:
```python
class TestAudioChunk:
    def test_creation_with_valid_data(self):
        """AudioChunk should be creatable with valid PCM data."""

    def test_frozen_immutability(self):
        """AudioChunk should be immutable (frozen dataclass)."""

    def test_duration_calculation(self):
        """AudioChunk duration_ms should match data length / sample_rate."""

class TestVADResult:
    def test_creation_with_speech_audio(self):
        """VADResult should contain concatenated speech audio."""

    def test_partial_flag_for_long_utterances(self):
        """VADResult should set is_partial=True when force-split."""

class TestTranscriptResult:
    def test_final_transcript(self):
        """TranscriptResult with is_final=True should contain complete text."""

    def test_latency_tracking(self):
        """processing_latency_ms should be positive and reasonable."""

class TestTranslationResult:
    def test_contains_both_languages(self):
        """TranslationResult should have both original and translated text."""

class TestTTSAudioResult:
    def test_audio_format(self):
        """TTSAudioResult should have correct sample_rate and channels."""
```

**test_audio_capture.py** — Test audio capture:
```python
class TestAudioCapture:
    def test_start_opens_stream(self, mock_sounddevice):
        """Starting capture should open a RawInputStream."""

    def test_stop_closes_stream(self, mock_sounddevice):
        """Stopping capture should close the stream."""

    def test_chunks_pushed_to_queue(self, mock_sounddevice):
        """Audio callback should push AudioChunk to output queue."""

    def test_chunk_has_correct_duration(self, mock_sounddevice):
        """Each chunk should have duration matching chunk_duration_ms config."""

    def test_sequence_numbers_increment(self, mock_sounddevice):
        """Chunk sequence numbers should monotonically increase."""

    def test_timestamps_are_monotonic(self, mock_sounddevice):
        """Chunk timestamps should be monotonically increasing."""

    def test_device_selection(self, mock_sounddevice):
        """Should use specified device_id when configured."""

    def test_default_device_when_none(self, mock_sounddevice):
        """Should use system default when device_id is None."""

    def test_get_available_devices(self, mock_sounddevice):
        """Should list all available audio input devices."""
```

**test_vad.py** — Test VAD processor:
```python
class TestVADProcessor:
    def test_detects_speech(self, mock_silero):
        """Should detect speech in audio with speech content."""

    def test_ignores_silence(self, mock_silero):
        """Should not emit VADResult for pure silence."""

    def test_groups_continuous_speech(self, mock_silero):
        """Should group continuous speech chunks into one VADResult."""

    def test_splits_on_silence(self, mock_silero):
        """Should split into separate VADResults on silence gap."""

    def test_min_silence_duration(self, mock_silero):
        """Should not split on silence shorter than min_silence_duration_ms."""

    def test_max_utterance_duration(self, mock_silero):
        """Should force-split utterances exceeding max_utterance_duration_ms."""

    def test_partial_flag_on_force_split(self, mock_silero):
        """Force-split VADResult should have is_partial=True."""

    def test_speech_padding(self, mock_silero):
        """Should include speech_pad_ms of audio before/after speech."""

    def test_confidence_is_average(self, mock_silero):
        """Confidence should be average of speech probabilities."""

    def test_handles_noise_gracefully(self, mock_silero):
        """Should not trigger on non-speech noise."""
```

**test_stt_client.py** — Test STT client:
```python
class TestDeepgramSTTClient:
    @pytest.mark.asyncio
    async def test_connect_establishes_websocket(self, mock_websocket):
        """Should establish WebSocket connection to Deepgram."""

    @pytest.mark.asyncio
    async def test_sends_audio_on_receive(self, mock_websocket):
        """Should send VADResult audio bytes over WebSocket."""

    @pytest.mark.asyncio
    async def test_parses_final_transcript(self, mock_websocket):
        """Should emit TranscriptResult for final transcripts."""

    @pytest.mark.asyncio
    async def test_ignores_interim_results(self, mock_websocket):
        """Should not forward interim (non-final) transcripts."""

    @pytest.mark.asyncio
    async def test_reconnects_on_disconnect(self, mock_websocket):
        """Should automatically reconnect on WebSocket close."""

    @pytest.mark.asyncio
    async def test_exponential_backoff_on_failure(self, mock_websocket):
        """Reconnection attempts should use exponential backoff."""

    @pytest.mark.asyncio
    async def test_tracks_latency(self, mock_websocket):
        """Should calculate processing_latency_ms correctly."""

    @pytest.mark.asyncio
    async def test_handles_empty_transcript(self, mock_websocket):
        """Should not forward empty/whitespace-only transcripts."""

    @pytest.mark.asyncio
    async def test_keepalive_messages(self, mock_websocket):
        """Should send keepalive messages periodically."""
```

**test_translation_client.py** — Test translation:
```python
class TestOpenAITranslationClient:
    @pytest.mark.asyncio
    async def test_translates_spanish_to_english(self, mock_openai):
        """Should produce English translation of Spanish input."""

    @pytest.mark.asyncio
    async def test_uses_streaming(self, mock_openai):
        """Should use stream=True for OpenAI API call."""

    @pytest.mark.asyncio
    async def test_preserves_proper_nouns(self, mock_openai):
        """Should not translate proper nouns."""

    @pytest.mark.asyncio
    async def test_handles_technical_jargon(self, mock_openai):
        """Should preserve English tech terms in Spanish input."""

    @pytest.mark.asyncio
    async def test_timeout_returns_partial(self, mock_openai):
        """Should return partial translation on timeout."""

    @pytest.mark.asyncio
    async def test_empty_input_returns_empty(self, mock_openai):
        """Should handle empty transcript gracefully."""

    @pytest.mark.asyncio
    async def test_system_prompt_is_set(self, mock_openai):
        """Should include the interpreter system prompt."""

    @pytest.mark.asyncio
    async def test_tracks_latency(self, mock_openai):
        """Should calculate processing_latency_ms correctly."""
```

**test_tts_client.py** — Test TTS client:
```python
class TestElevenLabsTTSClient:
    @pytest.mark.asyncio
    async def test_connect_establishes_websocket(self, mock_websocket):
        """Should establish WebSocket to ElevenLabs."""

    @pytest.mark.asyncio
    async def test_sends_bos_on_connect(self, mock_websocket):
        """Should send BOS (Beginning of Stream) message on connect."""

    @pytest.mark.asyncio
    async def test_sends_text_chunks(self, mock_websocket):
        """Should send translation text as WebSocket messages."""

    @pytest.mark.asyncio
    async def test_sends_eos_after_text(self, mock_websocket):
        """Should send EOS (End of Stream) after full text."""

    @pytest.mark.asyncio
    async def test_receives_audio_chunks(self, mock_websocket):
        """Should parse and forward received PCM audio chunks."""

    @pytest.mark.asyncio
    async def test_audio_format_correct(self, mock_websocket):
        """Output audio should be PCM 24kHz mono."""

    @pytest.mark.asyncio
    async def test_voice_settings_applied(self, mock_websocket):
        """Should apply configured stability/similarity settings."""

    @pytest.mark.asyncio
    async def test_reconnects_on_disconnect(self, mock_websocket):
        """Should reconnect WebSocket on disconnection."""

    @pytest.mark.asyncio
    async def test_fallback_to_openai_tts(self, mock_websocket, mock_openai):
        """Should fall back to OpenAI TTS on persistent ElevenLabs failure."""
```

**test_audio_output.py** — Test audio output:
```python
class TestAudioOutput:
    def test_start_opens_output_stream(self, mock_sounddevice):
        """Should open RawOutputStream to virtual audio device."""

    def test_writes_audio_to_device(self, mock_sounddevice):
        """Should write TTSAudioResult audio to output stream."""

    def test_applies_fade_in(self, mock_sounddevice):
        """Should apply fade-in to prevent audio clicks."""

    def test_applies_fade_out(self, mock_sounddevice):
        """Should apply fade-out to prevent audio clicks."""

    def test_resamples_if_needed(self, mock_sounddevice):
        """Should resample audio if TTS rate != output device rate."""

    def test_outputs_silence_on_buffer_underrun(self, mock_sounddevice):
        """Should output silence if no audio available."""

    def test_device_selection(self, mock_sounddevice):
        """Should use configured virtual audio device."""
```

**test_pipeline.py** — Test orchestrator:
```python
class TestPipelineOrchestrator:
    @pytest.mark.asyncio
    async def test_start_initializes_all_components(self):
        """Starting pipeline should start all components in order."""

    @pytest.mark.asyncio
    async def test_stop_shuts_down_gracefully(self):
        """Stopping pipeline should stop all components in reverse order."""

    @pytest.mark.asyncio
    async def test_queues_connected_correctly(self):
        """Each component's output queue should be the next component's input."""

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self):
        """Health check should report all components healthy when running."""

    @pytest.mark.asyncio
    async def test_health_check_detects_failure(self):
        """Health check should detect when a component has failed."""

    @pytest.mark.asyncio
    async def test_passthrough_mode(self):
        """Passthrough mode should route mic audio directly to output."""

    @pytest.mark.asyncio
    async def test_fallback_on_stt_failure(self):
        """Should activate fallback when STT fails repeatedly."""

    @pytest.mark.asyncio
    async def test_fallback_on_tts_failure(self):
        """Should fall back to alternative TTS on failure."""

    @pytest.mark.asyncio
    async def test_metrics_collection(self):
        """Should collect latency metrics from all components."""

    @pytest.mark.asyncio
    async def test_end_to_end_with_mocks(self):
        """Full pipeline should produce translated audio from mock input."""
```

#### Category 2: Integration Tests (Require API keys)

```python
# tests/integration/test_stt_deepgram.py
class TestDeepgramIntegration:
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_transcribe_spanish_audio(self):
        """Should transcribe Spanish WAV file to text via Deepgram."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_streaming_transcription(self):
        """Should handle streaming audio and return incremental results."""

# tests/integration/test_translation_openai.py
class TestOpenAITranslationIntegration:
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_translate_spanish_to_english(self):
        """Should translate Spanish text to English via GPT-4o-mini."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_streaming_translation(self):
        """Should stream translation tokens."""

# tests/integration/test_tts_elevenlabs.py
class TestElevenLabsIntegration:
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_synthesize_with_cloned_voice(self):
        """Should produce audio using the cloned voice."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_websocket_streaming(self):
        """Should stream audio chunks via WebSocket."""

# tests/integration/test_full_pipeline.py
class TestFullPipelineIntegration:
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_audio_file_through_full_pipeline(self):
        """Should process a Spanish WAV file and produce English audio."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_latency_under_target(self):
        """End-to-end latency should be under 800ms for short utterances."""
```

#### Category 3: Performance Tests

```python
# tests/performance/test_latency.py
class TestLatencyBenchmarks:
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_vad_latency_under_5ms(self):
        """VAD processing should complete in < 5ms per chunk."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_stt_latency_under_400ms(self):
        """STT should return final transcript in < 400ms."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_translation_latency_under_300ms(self):
        """Translation should complete in < 300ms."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_tts_first_byte_under_300ms(self):
        """TTS should produce first audio byte in < 300ms."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_end_to_end_under_800ms(self):
        """Full pipeline latency should be < 800ms."""

# tests/performance/test_memory.py
class TestMemoryUsage:
    @pytest.mark.performance
    def test_memory_under_512mb(self):
        """Pipeline should use < 512MB RSS after 100 utterances."""

    @pytest.mark.performance
    def test_no_memory_leak(self):
        """Memory should not grow after processing 1000 utterances."""
```

### 9.3 Test Fixtures

**conftest.py — Shared Fixtures**:
```python
import pytest
import asyncio
import numpy as np

@pytest.fixture
def event_loop():
    """Create a new event loop for each test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def sample_audio_chunk():
    """Generate a valid AudioChunk with synthetic audio data."""
    sample_rate = 16000
    duration_ms = 30
    num_samples = int(sample_rate * duration_ms / 1000)
    audio_data = np.random.randint(-32768, 32767, num_samples, dtype=np.int16).tobytes()
    return AudioChunk(
        data=audio_data,
        timestamp_ms=0.0,
        sample_rate=sample_rate,
        channels=1,
        duration_ms=duration_ms,
        sequence_number=0,
    )

@pytest.fixture
def speech_audio_chunk():
    """Generate an AudioChunk that simulates speech (440Hz tone)."""
    sample_rate = 16000
    duration_ms = 30
    t = np.linspace(0, duration_ms / 1000, int(sample_rate * duration_ms / 1000), False)
    audio = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)
    return AudioChunk(
        data=audio.tobytes(),
        timestamp_ms=0.0,
        sample_rate=sample_rate,
        channels=1,
        duration_ms=duration_ms,
        sequence_number=0,
    )

@pytest.fixture
def silence_audio_chunk():
    """Generate an AudioChunk with silence."""
    sample_rate = 16000
    duration_ms = 30
    num_samples = int(sample_rate * duration_ms / 1000)
    return AudioChunk(
        data=bytes(num_samples * 2),  # 16-bit zeros
        timestamp_ms=0.0,
        sample_rate=sample_rate,
        channels=1,
        duration_ms=duration_ms,
        sequence_number=0,
    )

@pytest.fixture
def sample_vad_result():
    """Generate a valid VADResult."""
    return VADResult(
        audio_data=b'\x00' * 32000,  # 1 second of 16kHz 16-bit audio
        start_timestamp_ms=0.0,
        end_timestamp_ms=1000.0,
        duration_ms=1000.0,
        confidence=0.95,
        is_partial=False,
        sequence_number=0,
    )

@pytest.fixture
def sample_transcript():
    """Generate a valid TranscriptResult."""
    return TranscriptResult(
        text="Necesitamos revisar el presupuesto",
        is_final=True,
        confidence=0.97,
        start_timestamp_ms=0.0,
        processing_latency_ms=250.0,
        language="es",
        words=None,
        sequence_number=0,
    )

@pytest.fixture
def sample_translation():
    """Generate a valid TranslationResult."""
    return TranslationResult(
        original_text="Necesitamos revisar el presupuesto",
        translated_text="We need to review the budget",
        start_timestamp_ms=0.0,
        processing_latency_ms=150.0,
        sequence_number=0,
    )

@pytest.fixture
def mock_settings():
    """Generate test settings with dummy API keys."""
    return VoiceBridgeSettings(
        deepgram_api_key="test_deepgram_key",
        openai_api_key="test_openai_key",
        elevenlabs_api_key="test_elevenlabs_key",
        elevenlabs_voice_id="test_voice_id",
    )

@pytest.fixture
def spanish_audio_file():
    """Path to a test Spanish audio WAV file."""
    return Path(__file__).parent / "fixtures" / "audio" / "spanish_short.wav"
```

### 9.4 Test Configuration

```toml
# pyproject.toml — pytest section

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "unit: Unit tests (no external dependencies)",
    "integration: Integration tests (require API keys)",
    "performance: Performance benchmarks",
    "slow: Tests that take > 10 seconds",
]
addopts = "-v --tb=short --strict-markers -x"
filterwarnings = [
    "ignore::DeprecationWarning",
]

# Default: run only unit tests
# For integration: pytest -m integration
# For all: pytest -m "unit or integration"
# For performance: pytest -m performance
```

### 9.5 Development Order (TDD Sequence)

Build components in this exact order, completing all unit tests before moving to the next:

```
Phase 1 — Foundation:
  1. config/settings.py + test_config.py
  2. core/models.py + test_models.py
  3. core/exceptions.py
  4. core/protocols.py

Phase 2 — Audio Layer:
  5. audio/capture.py + test_audio_capture.py
  6. audio/vad.py + test_vad.py
  7. audio/output.py + test_audio_output.py
  8. audio/resampler.py + tests

Phase 3 — Service Clients:
  9. services/stt/deepgram_client.py + test_stt_client.py
  10. services/translation/openai_client.py + test_translation_client.py
  11. services/tts/elevenlabs_client.py + test_tts_client.py

Phase 4 — Pipeline:
  12. core/pipeline.py + test_pipeline.py
  13. core/metrics.py + test_metrics.py

Phase 5 — Integration:
  14. Integration tests with real APIs
  15. Performance benchmarks

Phase 6 — UI (Optional):
  16. ui/tray.py
  17. ui/settings_window.py
```

---

## 10. DOCKER & DEPLOYMENT

### 10.1 Dockerfile (Production)

```dockerfile
FROM python:3.11-slim AS base

# System dependencies for audio
RUN apt-get update && apt-get install -y --no-install-recommends \
    libportaudio2 \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[prod]"

# Copy source
COPY src/ src/

# Non-root user
RUN useradd -m voicebridge
USER voicebridge

ENTRYPOINT ["python", "-m", "voicebridge"]
```

### 10.2 Dockerfile.dev (Development)

```dockerfile
FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libportaudio2 \
    libsndfile1 \
    ffmpeg \
    portaudio19-dev \
    pulseaudio \
    alsa-utils \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install all dependencies including dev/test
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev,test]"

# Copy everything
COPY . .

# Expose for potential debug/monitoring endpoints
EXPOSE 8080

CMD ["pytest", "-v"]
```

### 10.3 docker-compose.yml

```yaml
version: "3.8"

services:
  voicebridge:
    build:
      context: .
      dockerfile: Dockerfile.dev
    env_file: .env
    volumes:
      - ./src:/app/src
      - ./tests:/app/tests
      - /dev/snd:/dev/snd  # Audio device passthrough (Linux)
    devices:
      - /dev/snd  # Linux audio
    privileged: true  # Required for audio device access
    network_mode: host  # Required for PulseAudio access
    environment:
      - PULSE_SERVER=unix:/run/user/1000/pulse/native
    volumes:
      - ./src:/app/src
      - ./tests:/app/tests
      - /run/user/1000/pulse:/run/user/1000/pulse  # PulseAudio socket
      - ~/.config/pulse/cookie:/home/voicebridge/.config/pulse/cookie  # PulseAudio auth

  test:
    build:
      context: .
      dockerfile: Dockerfile.dev
    env_file: .env
    command: pytest -v -m unit
    volumes:
      - ./src:/app/src
      - ./tests:/app/tests

  test-integration:
    build:
      context: .
      dockerfile: Dockerfile.dev
    env_file: .env
    command: pytest -v -m integration
    volumes:
      - ./src:/app/src
      - ./tests:/app/tests
```

### 10.4 Native Deployment (Recommended for Audio)

Due to audio device access complexities in Docker, the recommended deployment for actual use is **native** (non-containerized):

```bash
# Windows
python -m pip install -e ".[prod]"
python -m voicebridge

# macOS
brew install portaudio blackhole-2ch
python -m pip install -e ".[prod]"
python -m voicebridge
```

Docker is used for development and testing only. Audio I/O is best handled natively.

---

## 11. API CONTRACTS & INTEGRATIONS

### 11.1 Deepgram WebSocket API

**Connection**:
```
URL: wss://api.deepgram.com/v1/listen
Headers:
  Authorization: Token {DEEPGRAM_API_KEY}
Query Params:
  model=nova-2
  language=es
  encoding=linear16
  sample_rate=16000
  channels=1
  punctuate=true
  smart_format=true
  interim_results=true
  endpointing=300
  utterance_end_ms=1000
  vad_events=true
```

**Send**: Raw PCM audio bytes (binary frames)

**Receive** (JSON):
```json
{
  "type": "Results",
  "channel_index": [0, 1],
  "duration": 1.5,
  "start": 0.0,
  "is_final": true,
  "speech_final": true,
  "channel": {
    "alternatives": [
      {
        "transcript": "necesitamos revisar el presupuesto",
        "confidence": 0.97,
        "words": [
          {"word": "necesitamos", "start": 0.1, "end": 0.5, "confidence": 0.99}
        ]
      }
    ]
  }
}
```

### 11.2 OpenAI Chat Completions API (Translation)

**Request**:
```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "system", "content": "<system_prompt>"},
    {"role": "user", "content": "Necesitamos revisar el presupuesto del Q3"}
  ],
  "stream": true,
  "temperature": 0.3,
  "max_tokens": 500
}
```

**Response** (streamed SSE):
```
data: {"choices":[{"delta":{"content":"We"},"index":0}]}
data: {"choices":[{"delta":{"content":" need"},"index":0}]}
data: {"choices":[{"delta":{"content":" to"},"index":0}]}
...
data: [DONE]
```

### 11.3 ElevenLabs WebSocket API (TTS)

**Connection**:
```
URL: wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input
Query Params:
  model_id=eleven_turbo_v2_5
  output_format=pcm_24000
  optimize_streaming_latency=3
```

**Send** (JSON messages):
```json
// BOS (first message)
{
  "text": " ",
  "voice_settings": {
    "stability": 0.5,
    "similarity_boost": 0.8,
    "style": 0.0,
    "use_speaker_boost": true
  },
  "generation_config": {
    "chunk_length_schedule": [120, 160, 250, 290]
  },
  "xi_api_key": "YOUR_API_KEY"
}

// Text chunk
{"text": "We need to review ", "try_trigger_generation": true}

// EOS (last message)
{"text": ""}
```

**Receive** (JSON):
```json
{
  "audio": "base64_encoded_pcm_bytes",
  "isFinal": false,
  "normalizedAlignment": {
    "char_start_times_ms": [0, 50, 100],
    "chars_durations_ms": [50, 50, 50],
    "chars": ["W", "e", " "]
  }
}
```

---

## 12. ERROR HANDLING & RESILIENCE

### 12.1 Exception Hierarchy

```python
class VoiceBridgeError(Exception):
    """Base exception for all VoiceBridge errors."""

class ConfigurationError(VoiceBridgeError):
    """Invalid configuration."""

class AudioDeviceError(VoiceBridgeError):
    """Audio device not found or inaccessible."""

class STTError(VoiceBridgeError):
    """Speech-to-text service error."""

class STTConnectionError(STTError):
    """Cannot connect to STT service."""

class STTTimeoutError(STTError):
    """STT processing timed out."""

class TranslationError(VoiceBridgeError):
    """Translation service error."""

class TranslationTimeoutError(TranslationError):
    """Translation timed out."""

class TTSError(VoiceBridgeError):
    """Text-to-speech service error."""

class TTSConnectionError(TTSError):
    """Cannot connect to TTS service."""

class TTSTimeoutError(TTSError):
    """TTS processing timed out."""

class PipelineError(VoiceBridgeError):
    """Pipeline orchestration error."""
```

### 12.2 Retry Strategy

```python
# Retry configuration per service
RETRY_CONFIGS = {
    "deepgram": RetryConfig(
        max_retries=5,
        base_delay_seconds=0.5,
        max_delay_seconds=30.0,
        exponential_base=2.0,
        jitter=True,
    ),
    "openai": RetryConfig(
        max_retries=3,
        base_delay_seconds=0.3,
        max_delay_seconds=10.0,
        exponential_base=2.0,
        jitter=True,
    ),
    "elevenlabs": RetryConfig(
        max_retries=3,
        base_delay_seconds=0.5,
        max_delay_seconds=15.0,
        exponential_base=2.0,
        jitter=True,
    ),
}
```

### 12.3 Fallback Chain

```
TTS Failure:
  1. Retry ElevenLabs WebSocket (3 attempts)
  2. Fallback to ElevenLabs REST API
  3. Fallback to OpenAI TTS (non-cloned voice)
  4. Activate passthrough mode (original audio)

STT Failure:
  1. Retry Deepgram WebSocket (5 attempts)
  2. Activate passthrough mode

Translation Failure:
  1. Retry GPT-4o-mini (3 attempts)
  2. Try GPT-4o as fallback
  3. Activate passthrough mode

Audio Device Failure:
  1. Retry device open (3 attempts)
  2. Show error to user, suggest device selection
```

### 12.4 Circuit Breaker Pattern

Implement a circuit breaker for each external service:

```python
class CircuitBreaker:
    """
    States: CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing recovery)

    CLOSED → OPEN: After `failure_threshold` consecutive failures
    OPEN → HALF_OPEN: After `recovery_timeout` seconds
    HALF_OPEN → CLOSED: On first success
    HALF_OPEN → OPEN: On first failure
    """
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0
```

---

## 13. MONITORING & OBSERVABILITY

### 13.1 Structured Logging

```python
# Use structlog for structured JSON logging
import structlog

logger = structlog.get_logger()

# Log format
logger.info(
    "utterance_processed",
    utterance_id=seq_num,
    total_latency_ms=total,
    stt_latency_ms=stt,
    translation_latency_ms=trans,
    tts_latency_ms=tts,
    original_text=spanish,
    translated_text=english,
    word_count=len(english.split()),
)
```

### 13.2 Metrics to Track

```python
# Latency percentiles (per component and end-to-end)
metrics = {
    "latency_p50_ms": float,
    "latency_p95_ms": float,
    "latency_p99_ms": float,
    "utterances_processed": int,
    "utterances_failed": int,
    "api_calls_total": dict[str, int],
    "api_errors_total": dict[str, int],
    "audio_buffer_underruns": int,
    "queue_depths": dict[str, int],
    "memory_rss_mb": float,
    "cpu_percent": float,
}
```

### 13.3 Status Overlay (Optional UI)

A small floating window that shows:
- Current pipeline status (🟢 Active / 🟡 Degraded / 🔴 Error)
- Last utterance latency
- Current translation (for debugging)
- Passthrough mode indicator

---

## 14. SECURITY CONSIDERATIONS

### 14.1 API Key Management

- Store API keys ONLY in `.env` file (never commit to git)
- `.env` is in `.gitignore`
- For production: use OS keychain (Windows Credential Manager / macOS Keychain)
- API keys are validated at startup; fail fast if invalid

### 14.2 Audio Privacy

- Audio data is NEVER persisted to disk in production mode
- Audio is sent to external APIs (Deepgram, ElevenLabs) — user must acknowledge this
- Transcripts and translations are logged ONLY at DEBUG level
- No telemetry or analytics are sent anywhere

### 14.3 Network Security

- All API connections use TLS 1.2+
- WebSocket connections use WSS (encrypted)
- API keys are sent via headers, never in URLs

---

## 15. DEVELOPMENT PHASES

### Phase 1: Foundation (Week 1)
- [ ] Project scaffolding (pyproject.toml, Docker, CI)
- [ ] Configuration management (Pydantic Settings)
- [ ] Data models with full test coverage
- [ ] Exception hierarchy
- [ ] Protocol definitions

### Phase 2: Audio Layer (Week 2)
- [ ] AudioCapture with tests
- [ ] VAD with Silero + tests
- [ ] AudioOutput with tests
- [ ] Audio resampling utilities
- [ ] Virtual audio device setup script

### Phase 3: Service Clients (Week 3)
- [ ] Deepgram STT client with WebSocket + tests
- [ ] OpenAI translation client with streaming + tests
- [ ] ElevenLabs TTS client with WebSocket + tests
- [ ] Mock clients for all services

### Phase 4: Pipeline & Integration (Week 4)
- [ ] PipelineOrchestrator with tests
- [ ] Metrics collection
- [ ] Retry and circuit breaker logic
- [ ] Integration tests with real APIs
- [ ] Performance benchmarks

### Phase 5: Voice Cloning & Polish (Week 5)
- [ ] Voice recording guide and script
- [ ] Voice clone verification tool
- [ ] Latency optimization tuning
- [ ] End-to-end testing
- [ ] Error handling edge cases

### Phase 6: UI & Distribution (Week 6)
- [ ] System tray application
- [ ] Settings window (device selection)
- [ ] Status overlay
- [ ] Installer/setup script for Windows and macOS
- [ ] User documentation

---

## 16. APPENDIX

### 16.1 Python Dependencies

```toml
# pyproject.toml

[project]
name = "voicebridge"
version = "1.0.0"
requires-python = ">=3.11"

dependencies = [
    "sounddevice>=0.4.6",
    "numpy>=1.24",
    "scipy>=1.11",
    "soxr>=0.3",
    "websockets>=12.0",
    "aiohttp>=3.9",
    "openai>=1.12",
    "httpx>=0.27",
    "pydantic>=2.5",
    "pydantic-settings>=2.1",
    "structlog>=24.1",
    "uvloop>=0.19; sys_platform != 'win32'",
    "torch>=2.0",
    "torchaudio>=2.0",
    "onnxruntime>=1.16",
]

[project.optional-dependencies]
dev = [
    "ruff>=0.2",
    "mypy>=1.8",
    "pre-commit>=3.6",
]
test = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.12",
    "pytest-cov>=4.1",
    "pytest-timeout>=2.2",
    "pytest-benchmark>=4.0",
    "psutil>=5.9",
]
ui = [
    "pystray>=0.19",
    "Pillow>=10.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "ANN", "B", "SIM"]

[tool.mypy]
python_version = "3.11"
strict = true
```

### 16.2 Virtual Audio Device Setup

**Windows (VB-Audio Virtual Cable)**:
```
1. Download from https://vb-audio.com/Cable/
2. Install VB-Audio Virtual Cable
3. In Windows Sound Settings:
   - The virtual cable appears as "CABLE Input" (playback) and "CABLE Output" (recording)
   - VoiceBridge writes to "CABLE Input"
   - Teams microphone setting → "CABLE Output"
4. Find device ID:
   python -c "import sounddevice; print(sounddevice.query_devices())"
   # Look for "CABLE Input" in the output device list
```

**macOS (BlackHole)**:
```
1. brew install blackhole-2ch
2. BlackHole appears as an audio device
3. VoiceBridge writes to "BlackHole 2ch"
4. Teams microphone setting → "BlackHole 2ch"
5. Find device ID:
   python -c "import sounddevice; print(sounddevice.query_devices())"
```

### 16.3 Glossary

| Term | Definition |
|------|-----------|
| STT | Speech-to-Text: converting audio to text |
| TTS | Text-to-Speech: converting text to audio |
| VAD | Voice Activity Detection: detecting when someone is speaking |
| PCM | Pulse-Code Modulation: raw uncompressed audio format |
| BOS | Beginning of Stream: initial message in a streaming protocol |
| EOS | End of Stream: final message in a streaming protocol |
| MOS | Mean Opinion Score: subjective audio quality metric (1-5) |
| DI | Dependency Injection: design pattern for loose coupling |
| WSS | WebSocket Secure: encrypted WebSocket connection |

### 16.4 Estimated Monthly Costs (10 hrs of meetings)

| Service | Monthly Cost |
|---------|-------------|
| Deepgram (STT) | ~$2.50 |
| OpenAI GPT-4o-mini (Translation) | ~$1.50 |
| ElevenLabs Scale (TTS + Voice Clone) | ~$22.00 |
| **Total** | **~$26.00/month** |

### 16.5 Key Design Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Python over Node.js | Python | Better ML ecosystem, async support, audio libraries |
| Deepgram over Whisper API | Deepgram | True streaming WebSocket, 200-300ms vs 500ms+ |
| GPT-4o-mini over DeepL | GPT-4o-mini | Streaming support, handles context/slang better |
| ElevenLabs over Cartesia | ElevenLabs | Best voice cloning fidelity (~95% similarity) |
| WebSocket over REST | WebSocket | ~50% lower latency for streaming use cases |
| asyncio over threading | asyncio | Better for I/O-bound concurrent streaming |
| Pydantic Settings over dotenv | Pydantic | Type validation, IDE support, default values |
| pytest over unittest | pytest | Better async support, fixtures, less boilerplate |
| structlog over stdlib logging | structlog | Structured JSON output, better for debugging |

---

## END OF ARCHITECTURE DOCUMENT

**This document contains everything needed to build VoiceBridge from scratch using TDD methodology. Each section is self-contained and references other sections where needed. The AI developer should follow the Development Phases (Section 15) in order, implementing each component with its tests before moving to the next.**
