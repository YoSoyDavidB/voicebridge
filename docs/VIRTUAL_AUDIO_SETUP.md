# Virtual Audio Device Setup for Teams/Zoom

This guide explains how to configure VoiceBridge to work with Microsoft Teams, Zoom, or any video conferencing application by using a virtual audio device.

## 🎯 Goal

Send the translated English audio from VoiceBridge directly to Teams/Zoom as if it were your microphone, so other participants hear the translation instead of your original Spanish.

## 📋 Architecture

```
Your Microphone → VoiceBridge (listens) → Translates Spanish to English
                                        ↓
                              Virtual Audio Device
                                        ↓
                          Teams/Zoom (selects as mic)
                                        ↓
                              Other Participants Hear English
```

---

## 🍎 macOS Setup (BlackHole)

### 1. Install BlackHole

```bash
brew install blackhole-2ch
```

**Alternative**: Download directly from https://existential.audio/blackhole/

### 2. Create Multi-Output Device (Optional - to hear yourself)

If you want to **hear the translated audio** while sending it to Teams:

1. Open **Audio MIDI Setup** (Applications → Utilities)
2. Click **+** (bottom left) → **Create Multi-Output Device**
3. Check both:
   - ✅ **BlackHole 2ch**
   - ✅ **MacBook Air Speakers** (or your preferred speakers)
4. Right-click the Multi-Output Device → **Use This Device For Sound Output**

### 3. Configure VoiceBridge

Run the device helper script:

```bash
python scripts/list_audio_devices.py
```

Find the device IDs and update your `.env`:

```bash
# Your physical microphone
AUDIO_INPUT_DEVICE_ID=0

# BlackHole for virtual output (or Multi-Output Device if created)
AUDIO_OUTPUT_DEVICE_ID=5  # Replace with actual BlackHole ID
```

### 4. Configure Teams/Zoom

In Teams/Zoom settings:
- **Microphone**: Select **BlackHole 2ch**
- **Speaker**: Select your normal speakers

### 5. Test

1. Start VoiceBridge: `python -m voicebridge.cli`
2. Join a Teams call
3. Speak in Spanish
4. Other participants should hear English translation

---

## 🪟 Windows Setup (VB-CABLE)

### 1. Install VB-CABLE

1. Download from: https://vb-audio.com/Cable/
2. Extract the ZIP file
3. Right-click `VBCABLE_Setup_x64.exe` → **Run as Administrator**
4. Click **Install Driver**
5. Restart your computer

### 2. Configure VoiceBridge

Run the device helper script:

```bash
python scripts/list_audio_devices.py
```

Find the device IDs and update your `.env`:

```bash
# Your physical microphone
AUDIO_INPUT_DEVICE_ID=0

# CABLE Input (this is the virtual device)
AUDIO_OUTPUT_DEVICE_ID=4  # Replace with actual CABLE Input ID
```

### 3. Configure Teams/Zoom

In Teams/Zoom settings:
- **Microphone**: Select **CABLE Output**
- **Speaker**: Select your normal speakers

### 4. Optional: Hear Yourself

If you want to hear the translated audio:

1. Open **Sound Settings** (Control Panel → Sound)
2. Go to **Recording** tab
3. Right-click **CABLE Output** → **Properties**
4. Go to **Listen** tab
5. Check **Listen to this device**
6. Select your speakers from dropdown
7. Click **Apply**

### 5. Test

1. Start VoiceBridge: `python -m voicebridge.cli`
2. Join a Teams call
3. Speak in Spanish
4. Other participants should hear English translation

---

## 🔧 Configuration Options

### .env File Settings

```bash
# ─── Input Configuration ─────────────────────────────────────────
AUDIO_INPUT_DEVICE_ID=0           # Your microphone (or None for default)
AUDIO_INPUT_GAIN=1.0              # Adjust if audio is too loud/quiet

# ─── Output Configuration ────────────────────────────────────────
AUDIO_OUTPUT_DEVICE_ID=5          # Virtual device ID
                                  # None = system default (for testing)
                                  # Set to BlackHole/VB-CABLE for Teams

AUDIO_OUTPUT_ENABLED=false        # Enable/disable audio playback
                                  # true = hear translations (testing mode)
                                  # false = silent mode (Teams/Zoom - recommended)

# ─── Audio Quality ───────────────────────────────────────────────
AUDIO_SAMPLE_RATE=16000           # Input sample rate (16kHz recommended)
TTS_OUTPUT_SAMPLE_RATE=24000      # Output sample rate (24kHz recommended)
```

### Finding Device IDs

Always run this after installing virtual devices:

```bash
python scripts/list_audio_devices.py
```

Example output:

```
🔊 OUTPUT DEVICES (Speakers/Virtual Devices)
────────────────────────────────────────────────────────────────────────────────
ID 0: MacBook Air Speakers [DEFAULT]
       Channels: 2
       Sample Rate: 48000 Hz

ID 5: BlackHole 2ch [VIRTUAL - macOS]
       Channels: 2
       Sample Rate: 48000 Hz
```

---

## ✅ Testing Your Setup

### Quick Test (Without Teams)

1. Configure `.env` to use **system speakers**:
   ```bash
   AUDIO_OUTPUT_DEVICE_ID=  # Leave empty for default
   ```

2. Start VoiceBridge:
   ```bash
   python -m voicebridge.cli
   ```

3. Speak in Spanish
4. You should **hear** the English translation from your speakers

### Teams Test

1. Configure `.env` to use **virtual device**:
   ```bash
   AUDIO_OUTPUT_DEVICE_ID=5  # Your BlackHole/VB-CABLE ID
   ```

2. Start VoiceBridge:
   ```bash
   python -m voicebridge.cli
   ```

3. Join a Teams call (select virtual device as mic)
4. Speak in Spanish
5. Ask another participant if they hear English

---

## ❌ Troubleshooting

### No audio in Teams

**Problem**: Teams can't hear the translation

**Solution**:
1. Verify VoiceBridge is running
2. Check Teams microphone is set to **BlackHole/CABLE Output**
3. Run `list_audio_devices.py` to verify device IDs
4. Check VoiceBridge console for errors

### Can't hear translations yourself

**macOS**: Create Multi-Output Device (see Step 2 above)

**Windows**: Enable "Listen to this device" (see Step 4 above)

### Audio sounds distorted

**Problem**: Audio quality is poor

**Solution**:
1. Lower `AUDIO_INPUT_GAIN` in `.env` (try 0.8 or 0.5)
2. Check microphone isn't too close to mouth
3. Verify sample rates match:
   ```bash
   TTS_OUTPUT_SAMPLE_RATE=24000
   ```

### Virtual device not appearing

**macOS**:
```bash
# Reinstall BlackHole
brew uninstall blackhole-2ch
brew install blackhole-2ch

# Restart Core Audio
sudo killall coreaudiod
```

**Windows**:
- Reinstall VB-CABLE as Administrator
- Restart computer
- Check Device Manager for audio devices

---

## 🔄 Configuration Modes

VoiceBridge supports three main modes:

### Mode 1: Local Testing (Hear Translations)
**Use Case**: Test VoiceBridge before meetings
```bash
AUDIO_OUTPUT_DEVICE_ID=           # Empty = default speakers
AUDIO_OUTPUT_ENABLED=true         # Play audio to speakers
```
✅ You hear the English translation from your speakers
✅ Good for testing accuracy and latency
❌ Don't use during Teams calls (confusing!)

### Mode 2: Teams/Zoom Silent Mode (Recommended)
**Use Case**: During actual Teams/Zoom meetings
```bash
AUDIO_OUTPUT_DEVICE_ID=5          # BlackHole or VB-CABLE
AUDIO_OUTPUT_ENABLED=false        # Silent - no speaker playback
```
✅ Audio goes to virtual device for Teams/Zoom
✅ You don't hear the translation (not confusing)
✅ Other participants hear only the English translation
✅ Recommended for production use

### Mode 3: Teams/Zoom with Self-Monitor
**Use Case**: Want to hear yourself during Teams calls
```bash
AUDIO_OUTPUT_DEVICE_ID=5          # Multi-Output Device (macOS) or CABLE with Listen (Windows)
AUDIO_OUTPUT_ENABLED=true         # Play to multi-output
```
⚠️ More complex setup required (see sections above)
⚠️ Can be confusing to hear both original and translation
⚠️ Only use if you really need to monitor yourself

---

## 📝 Session Logging

All translations are automatically saved to:
```
~/voicebridge_sessions/session_YYYY-MM-DD_HH-MM-SS.md
```

Review these files after meetings to study the English translations!

---

## 🆘 Additional Help

- **macOS BlackHole**: https://github.com/ExistentialAudio/BlackHole
- **Windows VB-CABLE**: https://vb-audio.com/Cable/
- **VoiceBridge Issues**: Open an issue on GitHub

---

**Happy translating! 🌉**
