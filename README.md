# VoiceBridge

Real-time Spanish-to-English voice interpreter for Microsoft Teams with voice cloning.

## 🎯 Project Status

**Version:** 1.0.0 (In Development)

**Target:** < 800ms end-to-end latency for real-time voice translation

## 🏗️ Architecture

VoiceBridge captures your microphone audio, translates Spanish to English in real-time, synthesizes the translation using a clone of your voice, and routes it to Microsoft Teams via a virtual audio device.

**Pipeline:**
```
Physical Mic → Audio Capture → VAD → STT (Deepgram) → Translation (GPT-4o-mini)
→ TTS (ElevenLabs) → Virtual Mic → Microsoft Teams
```

## 🛠️ Technology Stack

- **Language:** Python 3.11+
- **Audio:** sounddevice, PortAudio
- **VAD:** Silero VAD
- **STT:** Deepgram (WebSocket streaming)
- **Translation:** GPT-4o-mini (OpenAI)
- **TTS:** ElevenLabs Turbo v2.5 (voice cloning)
- **Testing:** pytest with TDD methodology

## 📋 Prerequisites

- Python 3.9 or higher
- API keys for:
  - Deepgram (Speech-to-Text)
  - OpenAI (Translation)
  - ElevenLabs (Text-to-Speech with voice cloning)
- Virtual audio device (optional for Teams integration):
  - Windows: VB-Audio Virtual Cable
  - macOS: BlackHole

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/YoSoyDavidB/voicebridge.git
cd voicebridge

# Install dependencies and VoiceBridge CLI
pip install -e .

# Install development dependencies
make install-dev

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

### Usage

After installation, use the `voicebridge` command:

```bash
# Start VoiceBridge
voicebridge

# Check current profile
voicebridge profile

# Switch to testing mode (hear translations)
voicebridge profile testing

# Switch to Teams mode (silent, sends to virtual device)
voicebridge profile teams -d 5  # Replace 5 with your device ID

# List audio devices
voicebridge devices

# Check configuration
voicebridge check

# Show help
voicebridge --help
```

**See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for detailed command guide.**

### Development

```bash
# Run tests
make test

# Run linter
make lint

# Run type checker
make typecheck

# Format code
make format

# Run all checks
make check
```

## 📁 Project Structure

```
VoiceBridge/
├── src/voicebridge/          # Source code
│   ├── config/               # Configuration (Pydantic Settings)
│   ├── core/                 # Core models, protocols, pipeline
│   ├── audio/                # Audio capture, VAD, output
│   ├── services/             # External API clients (STT, TTS, Translation)
│   └── utils/                # Utilities (logging, retry, etc.)
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests (no external dependencies)
│   ├── integration/          # Integration tests (require API keys)
│   └── performance/          # Performance benchmarks
├── scripts/                  # Setup and utility scripts
└── docs/                     # Documentation

```

## 🧪 Testing

VoiceBridge follows **Test-Driven Development (TDD)** methodology.

```bash
# Run unit tests only (fast, no API calls)
make test-unit

# Run integration tests (requires API keys in .env)
make test-integration

# Run performance benchmarks
make test-performance

# Run all tests
make test-all

# Generate coverage report
make coverage
```

## 📖 Documentation

- [Architecture Document](./VOICEBRIDGE_ARCHITECTURE.md) - Complete system design
- [AI Agents Guide](./AGENTS.md) - Development workflow and agent roles

## 🔐 Security

- API keys are stored in `.env` (gitignored)
- Audio data is **never** persisted to disk
- All network connections use TLS/WSS encryption
- No telemetry or analytics

## 📝 License

MIT

## 🤝 Contributing

This project follows strict TDD methodology:
1. Write failing tests first (RED)
2. Write minimum code to pass (GREEN)
3. Refactor while keeping tests green (REFACTOR)

See [AGENTS.md](./AGENTS.md) for detailed development guidelines.

---

**Built with ❤️ for seamless multilingual communication**
