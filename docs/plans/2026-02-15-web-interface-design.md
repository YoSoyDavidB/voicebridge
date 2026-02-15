# VoiceBridge Web Interface Design
**Date:** 2026-02-15
**Status:** Approved
**Version:** 1.0 (Minimalista)

## Overview

Design for a web-based interface for VoiceBridge to solve macOS microphone access issues and provide a platform-agnostic solution. The interface will use FastAPI + WebSocket for real-time audio streaming with the lowest possible latency (~300-400ms end-to-end).

## Goals

1. **Primary:** Bypass macOS PortAudio/sounddevice microphone access issues
2. **Performance:** Achieve <400ms latency for real-time translation
3. **UX:** Simple, futuristic interface inspired by NexAD portal
4. **Security:** API keys stored locally in browser localStorage
5. **Scalability:** Foundation for future dashboard features

## Architecture

### High-Level Flow

```
Browser (Chrome/Edge)
  ├─ Web Audio API (capture microphone)
  ├─ WebSocket client
  └─ Audio playback
      │
      │ WebSocket (localhost:8000)
      │ (audio chunks ↔ translated audio)
      ▼
FastAPI Backend (Python)
  ├─ WebSocket handler
  ├─ Audio bridge (Web Audio ↔ Pipeline)
  └─ Pipeline Orchestrator (existing)
      ├─ VAD (Silero)
      ├─ STT (Deepgram)
      ├─ Translation (OpenAI)
      └─ TTS (ElevenLabs)
```

### Technology Stack

**Backend:**
- FastAPI (async web framework)
- WebSockets for real-time bidirectional communication
- Existing pipeline components (no changes needed)

**Frontend:**
- Vanilla HTML/CSS/JavaScript (no framework overhead)
- Web Audio API for microphone capture
- Canvas API for waveform visualization
- LocalStorage for API key persistence

## File Structure

```
src/voicebridge/
├── web/                          # New web module
│   ├── __init__.py
│   ├── app.py                    # FastAPI application
│   ├── websocket_handler.py      # WebSocket message handling
│   ├── audio_bridge.py           # Adapter: Web Audio ↔ Pipeline
│   └── static/                   # Static assets
│       ├── index.html           # Main page
│       ├── css/
│       │   └── styles.css       # Futuristic styling
│       └── js/
│           ├── audio.js         # Web Audio API logic
│           ├── websocket.js     # WebSocket client
│           ├── visualizer.js    # Waveform visualization
│           └── config.js        # API key management
├── core/
│   └── pipeline.py              # (existing, reused)
└── __main__.py                  # Updated with 'web' command
```

## User Interface (v1 - Minimalista)

### Layout

```
┌─────────────────────────────────────────────────┐
│  VOICEBRIDGE                      [⚙️ Settings] │
├─────────────────────────────────────────────────┤
│                                                 │
│              ┌───────────────┐                  │
│              │               │                  │
│              │   [  🎤  ]    │                  │
│              │               │                  │
│              │   START       │                  │
│              │               │                  │
│              └───────────────┘                  │
│                                                 │
│         ████████░░░░░░░░░░░░                   │
│                                                 │
│         Status: Ready                           │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Visual Design (Futuristic/Tech)

**Color Scheme:**
- Background: Dark blue/black (#0a0e27, #1a1f3a)
- Accents: Cyan/green neon (#00ffff, #00ff88)
- Text: White/light gray (#ffffff, #e0e0e0)

**Typography:**
- Headers: Modern sans-serif (e.g., Inter, Space Grotesk)
- Monospace: JetBrains Mono for technical elements

**Effects:**
- Glassmorphism on panels (backdrop-filter: blur)
- Neon glow on active elements (box-shadow with cyan)
- Smooth animations (200-300ms transitions)
- Pulsing animation on "Recording" state

### Settings Panel (Collapsible)

**Fields:**
- Deepgram API Key (password input)
- OpenAI API Key (password input)
- ElevenLabs API Key (password input)
- ElevenLabs Voice ID (text input)

**Actions:**
- Save to LocalStorage (automatic)
- Test Connection button (validates all keys)
- Clear All button

### States

1. **Ready:** Default state, waiting to start
2. **Listening:** Microphone active, detecting speech
3. **Processing:** VAD detected speech, pipeline processing
4. **Speaking:** Playing translated audio

## WebSocket Protocol

### Client → Server Messages

```typescript
// Configuration (sent on connect)
{
  type: "config",
  apiKeys: {
    deepgram: string,
    openai: string,
    elevenlabs: string,
    voiceId: string
  }
}

// Audio chunk (sent every ~30ms)
{
  type: "audio",
  data: string,        // base64-encoded PCM audio
  timestamp: number    // milliseconds
}

// Control command
{
  type: "control",
  action: "stop"       // Stop processing
}
```

### Server → Client Messages

```typescript
// Status update
{
  type: "status",
  state: "listening" | "processing" | "speaking",
  message: string
}

// Translated audio output
{
  type: "audio_output",
  data: string         // base64-encoded PCM audio
}

// Error
{
  type: "error",
  message: string,
  code: "AUTH_ERROR" | "PROCESSING_ERROR" | "CONNECTION_ERROR"
}
```

### Audio Format

- **Sample Rate:** 16kHz (matches pipeline)
- **Channels:** 1 (mono)
- **Encoding:** PCM 16-bit little-endian
- **Chunk Size:** 480 samples (~30ms @ 16kHz)
- **Transport:** Base64-encoded over WebSocket

## Component Integration

### Audio Bridge (New)

Adapts between Web Audio format and Pipeline format:

```python
class WebAudioBridge:
    """Bridges Web Audio API and VoiceBridge pipeline."""

    async def process_web_audio(self, base64_audio: str) -> None:
        """Decode web audio and feed to pipeline."""
        # Decode base64 → PCM bytes
        # Create AudioChunk
        # Push to pipeline queue

    async def send_output_audio(self, audio_data: bytes) -> str:
        """Encode pipeline output for web playback."""
        # Encode PCM bytes → base64
        # Return for WebSocket transmission
```

### Pipeline Modifications

**Minimal changes needed:**
- AudioCapture: Skip (audio comes from WebSocket)
- AudioOutput: Skip (audio sent via WebSocket)
- VAD, STT, Translation, TTS: Reuse as-is

**New WebSocket Pipeline:**
```python
WebSocket → AudioBridge → VAD → STT → Translation → TTS → AudioBridge → WebSocket
```

## Error Handling

### API Key Validation
- Test connection on first config message
- Return specific error codes for each service
- Show user-friendly error messages in UI

### WebSocket Disconnection
- Auto-reconnect with exponential backoff (1s, 2s, 4s, 8s max)
- Show "Reconnecting..." status in UI
- Resume from last known state

### Microphone Permissions
- Request permissions explicitly on button click
- Show clear message if denied
- Provide instructions to enable in browser settings

### High Latency
- Monitor end-to-end latency
- Show warning if >1 second
- Suggest checking internet connection

## Security Considerations

1. **API Keys:**
   - Stored only in browser localStorage
   - Never transmitted to external servers
   - Cleared on logout/clear data

2. **WebSocket:**
   - Bind to localhost only (127.0.0.1)
   - No external connections accepted
   - CORS headers restricted to localhost

3. **Input Validation:**
   - Validate all WebSocket message formats
   - Sanitize API keys before use
   - Rate limit messages to prevent abuse

## CLI Integration

### New Command

```bash
python -m voicebridge web [--port 8000] [--host 127.0.0.1]
```

**Behavior:**
1. Start FastAPI server
2. Open default browser to http://localhost:8000
3. Show server logs in terminal
4. Ctrl+C to stop

### Existing Command

```bash
python -m voicebridge [devices|check]
```

**Behavior:** Unchanged (terminal mode for supported platforms)

## Performance Targets

### Latency Breakdown (Target)

| Component | Target Latency |
|-----------|---------------|
| Web Audio capture | 30ms |
| WebSocket transport | 20ms |
| VAD processing | 50ms |
| STT (Deepgram) | 100ms |
| Translation (OpenAI) | 80ms |
| TTS (ElevenLabs) | 120ms |
| WebSocket transport | 20ms |
| Browser playback | 30ms |
| **Total** | **~450ms** |

### Optimization Strategies

1. Use smaller audio chunks (30ms vs 100ms)
2. Pre-warm API connections
3. Parallel processing where possible
4. Binary WebSocket frames (future optimization)

## Future Enhancements (Dashboard v2)

**Features to add later:**
- Real-time transcription display (Spanish + English)
- Per-component latency metrics
- Translation history/log
- API usage statistics and costs
- Advanced settings (VAD threshold, model selection)
- Dark/light theme toggle
- Responsive mobile layout
- Recording/playback of sessions

**Technical additions:**
- Session persistence (IndexedDB)
- Offline mode with cached translations
- Multiple language support
- Custom voice training interface

## Dependencies

**New Python packages:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `websockets` - WebSocket support
- `python-multipart` - Form data (for future file uploads)

**Browser requirements:**
- Chrome 90+ / Edge 90+ / Safari 14+
- Web Audio API support
- WebSocket support
- LocalStorage support

## Testing Strategy

### Unit Tests
- WebSocket message parsing/encoding
- Audio bridge format conversions
- API key validation logic

### Integration Tests
- Full WebSocket flow (connect → config → audio → output)
- Pipeline integration with web audio
- Error handling and reconnection

### Manual Testing
- Browser compatibility (Chrome, Edge, Safari)
- Microphone permission flow
- Various audio input volumes
- Network disconnection scenarios
- Multiple concurrent sessions

## Rollout Plan

1. **Phase 1:** Backend implementation (FastAPI + WebSocket)
2. **Phase 2:** Frontend UI (HTML/CSS/JS)
3. **Phase 3:** Integration testing
4. **Phase 4:** Documentation update
5. **Phase 5:** Demo and user feedback

## Success Criteria

- ✅ Web interface loads and connects successfully
- ✅ Microphone capture works in browser
- ✅ End-to-end latency < 500ms
- ✅ No microphone permission issues on macOS
- ✅ API keys persist across sessions
- ✅ Graceful error handling and recovery
- ✅ Works on macOS and Windows

## References

- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)
- [Web Audio API Specification](https://www.w3.org/TR/webaudio/)
- [WebSocket Protocol RFC 6455](https://tools.ietf.org/html/rfc6455)
