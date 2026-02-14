# VoiceBridge Setup Guide

## Prerequisites

### 1. Python Version

**Required:** Python 3.11 or higher

Check your current Python version:
```bash
python3 --version
```

If you need to install Python 3.11+:

**macOS (using Homebrew):**
```bash
brew install python@3.11
# Or for the latest version
brew install python@3.12
```

**Windows:**
Download from [python.org](https://www.python.org/downloads/)

**Linux (Ubuntu/Debian):**
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-venv
```

### 2. Virtual Audio Device

#### macOS - BlackHole
```bash
brew install blackhole-2ch
```

After installation, BlackHole will appear as an audio device in System Settings.

#### Windows - VB-Audio Virtual Cable
1. Download from [vb-audio.com/Cable](https://vb-audio.com/Cable/)
2. Run the installer
3. Restart your computer
4. The virtual cable will appear as "CABLE Input" (playback) and "CABLE Output" (recording)

### 3. API Keys

You'll need API keys from:

1. **Deepgram** (Speech-to-Text)
   - Sign up at [deepgram.com](https://deepgram.com)
   - Get your API key from the console

2. **OpenAI** (Translation)
   - Sign up at [platform.openai.com](https://platform.openai.com)
   - Create an API key from your account settings

3. **ElevenLabs** (Voice Cloning & TTS)
   - Sign up at [elevenlabs.io](https://elevenlabs.io)
   - You'll need a **Professional Voice Clone** (requires Scale or Pro plan)
   - Get your API key and voice ID

## Installation Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd VoiceBridge
```

### 2. Create Virtual Environment

```bash
# Create venv with Python 3.11+
python3.11 -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install development dependencies (includes test tools)
make install-dev

# Or manually:
pip install -e ".[dev,test]"
```

### 4. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your API keys
nano .env  # or use any text editor
```

Required variables in `.env`:
```bash
DEEPGRAM_API_KEY=your_deepgram_api_key
OPENAI_API_KEY=your_openai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_VOICE_ID=your_cloned_voice_id
```

### 5. Find Audio Device IDs

```bash
# Run this Python script to list audio devices
python3 -c "import sounddevice; print(sounddevice.query_devices())"
```

Look for:
- **Input device**: Your physical microphone
- **Output device**: The virtual audio device (BlackHole or CABLE Input)

Update `.env` with device IDs if needed (optional, defaults to system default):
```bash
AUDIO_INPUT_DEVICE_ID=  # Your mic device ID
AUDIO_OUTPUT_DEVICE_ID=  # Virtual device ID
```

## Voice Cloning Setup

### Record Voice Samples

To create your voice clone with ElevenLabs:

1. **Record 30+ minutes of audio**:
   - Mix of Spanish and English speech
   - Quiet environment (< 40dB ambient noise)
   - Good quality microphone
   - Natural speaking pace
   - Include varied intonations

2. **Content suggestions**:
   - Read aloud from news articles (5 min)
   - Read from a novel (5 min)
   - Conversational monologue about work (10 min)
   - Technical explanations (5 min)
   - Free-form storytelling (5 min)

3. **Upload to ElevenLabs**:
   - Go to Voice Lab → Professional Voice Clone
   - Upload all audio files
   - Complete identity verification
   - Wait 24-48 hours for processing

4. **Get Voice ID**:
   - Once processed, copy the `voice_id` from ElevenLabs dashboard
   - Add to `.env`: `ELEVENLABS_VOICE_ID=your_voice_id`

## Verify Installation

### 1. Run Tests

```bash
# Run unit tests (fast, no API calls)
make test-unit
```

If all tests pass, the basic setup is correct.

### 2. Test API Connections (optional)

```bash
# Run integration tests (requires valid API keys)
make test-integration
```

These tests will verify:
- Deepgram connection and transcription
- OpenAI translation
- ElevenLabs voice synthesis

### 3. Run the Application

```bash
# Start VoiceBridge
make run

# Or:
python -m voicebridge
```

## Configure Microsoft Teams

1. **Open Teams Settings** → Audio devices
2. **Microphone**: Select the virtual audio device
   - macOS: "BlackHole 2ch"
   - Windows: "CABLE Output"
3. **Speaker**: Select your normal speakers/headphones
4. **Test audio**: Speak in Spanish, verify you hear English translation

## Troubleshooting

### "Python version not supported"
Ensure you're using Python 3.11+:
```bash
python3 --version
```

### "No module named 'sounddevice'"
Install dependencies:
```bash
make install-dev
```

### "Audio device not found"
List devices and verify IDs:
```bash
python3 -c "import sounddevice; print(sounddevice.query_devices())"
```

### "API key invalid"
Check your `.env` file:
- No spaces around `=`
- No quotes around keys
- Keys are valid and active

### Virtual audio device not appearing
- **macOS**: Restart after installing BlackHole
- **Windows**: Restart after installing VB-Cable

### High latency (> 1 second)
Check in order:
1. Internet connection speed
2. API keys are valid (not free tier with rate limits)
3. VAD settings in `.env` (try reducing `VAD_MIN_SILENCE_MS`)

## Next Steps

Once setup is complete:
1. Test with a short Spanish phrase
2. Verify translation quality
3. Check voice clone fidelity
4. Measure end-to-end latency
5. Join a test Teams meeting

For development workflow, see [AGENTS.md](../AGENTS.md).
