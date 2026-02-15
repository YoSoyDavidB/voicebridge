# Quick Start: Virtual Audio for Teams

## 🚀 5-Minute Setup

### Step 1: Install Virtual Audio Device

**macOS:**
```bash
brew install blackhole-2ch
```

**Windows:**
Download and install: https://vb-audio.com/Cable/

---

### Step 2: Find Your Device IDs

```bash
python scripts/list_audio_devices.py
```

Look for:
- Your **microphone ID** (input)
- **BlackHole 2ch** or **CABLE Input** ID (output)

---

### Step 3: Update .env

**For Teams/Zoom (Silent Mode - Recommended):**
```bash
AUDIO_INPUT_DEVICE_ID=0           # Your microphone
AUDIO_OUTPUT_DEVICE_ID=5          # BlackHole or VB-CABLE
AUDIO_OUTPUT_ENABLED=false        # Silent mode - don't play to speakers
```

**For Local Testing (Hear Translations):**
```bash
AUDIO_INPUT_DEVICE_ID=0           # Your microphone
AUDIO_OUTPUT_DEVICE_ID=           # Empty = default speakers
AUDIO_OUTPUT_ENABLED=true         # Play audio locally
```

---

### Step 4: Start VoiceBridge

```bash
python -m voicebridge.cli
```

You should see:
```
[Pipeline] 📝 Transcript logging enabled: ~/voicebridge_sessions/session_...
[Pipeline] 🔗 Connecting components with queues
```

---

### Step 5: Configure Teams/Zoom

**In Teams/Zoom Settings:**
- **Microphone**: Select **BlackHole 2ch** (macOS) or **CABLE Output** (Windows)
- **Speaker**: Select your normal speakers

---

### Step 6: Test!

1. Join a Teams call
2. Speak in Spanish: *"Hola, ¿cómo estás?"*
3. Other participants hear: *"Hello, how are you?"*

---

## 🎧 Configuration Modes

### Mode 1: Silent Mode (Recommended for Teams/Zoom)

**What**: VoiceBridge generates audio but doesn't play it to speakers.
**Why**: Avoid hearing both original and translation during calls (confusing!).
**How**: Set `AUDIO_OUTPUT_ENABLED=false` in `.env`

```bash
AUDIO_OUTPUT_ENABLED=false   # Silent - audio goes only to virtual device
```

When VoiceBridge runs, you'll see:
```
[CLI] 🔇 Audio output disabled (silent mode)
[Speaker] 🔇 Silent mode: 4800 bytes generated (not playing)
```

### Mode 2: Testing Mode (Hear Translations Locally)

**What**: Play translated audio to your speakers.
**Why**: Test VoiceBridge before using in meetings.
**How**: Set `AUDIO_OUTPUT_ENABLED=true` and use default speakers

```bash
AUDIO_OUTPUT_DEVICE_ID=       # Empty = default speakers
AUDIO_OUTPUT_ENABLED=true     # Play audio
```

When VoiceBridge runs, you'll see:
```
[CLI] 🔊 Audio output enabled to device default
[Speaker] 🔊 Playing 4800 bytes (final=True)
```

---

## ❌ Troubleshooting

**Teams can't hear me:**
- Verify VoiceBridge is running
- Check Teams mic is set to BlackHole/CABLE Output
- Run `list_audio_devices.py` to verify device IDs

**Audio is distorted:**
- Lower `AUDIO_INPUT_GAIN=0.8` in `.env`
- Move microphone further from mouth

**No virtual device showing:**
- macOS: `sudo killall coreaudiod` (restart Core Audio)
- Windows: Reinstall VB-CABLE as Admin + restart

---

## 📚 Full Documentation

See [VIRTUAL_AUDIO_SETUP.md](docs/VIRTUAL_AUDIO_SETUP.md) for complete guide.

---

**Ready to translate! 🌉**
