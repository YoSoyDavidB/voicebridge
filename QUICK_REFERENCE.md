# VoiceBridge - Quick Reference Guide

## 🚀 Installation (One-Time Setup)

```bash
cd /path/to/VoiceBridge
pip install -e .
```

After installation, you can use `voicebridge` from anywhere!

---

## ⚡ Common Commands

### Start VoiceBridge
```bash
voicebridge           # Start with current profile
voicebridge start     # Same as above (explicit)
```

### Manage Profiles
```bash
voicebridge profile             # Show current profile
voicebridge profile testing     # Switch to testing mode
voicebridge profile teams -d 5  # Switch to Teams mode (device ID 5)
```

### List Audio Devices
```bash
voicebridge devices   # List all input/output devices
```

### Check Configuration
```bash
voicebridge check     # Verify API keys and settings
```

---

## 📋 Configuration Profiles

### Testing Mode
**Use when:** Testing VoiceBridge before a meeting

```bash
voicebridge profile testing
```

**What it does:**
- ✅ Plays translated audio to your default speakers
- ✅ You hear the English translation
- ❌ Don't use during Teams calls (confusing!)

---

### Teams/Zoom Mode
**Use when:** During actual meetings

```bash
voicebridge profile teams -d 5  # Replace 5 with your virtual device ID
```

**What it does:**
- ✅ Sends audio to virtual device (BlackHole/VB-CABLE)
- ✅ Silent mode - you don't hear translation (no confusion!)
- ✅ Teams/Zoom captures audio from virtual device
- ✅ Recommended for production use

**First time setup:**
1. Find your virtual device ID:
   ```bash
   voicebridge devices
   ```
   Look for "BlackHole 2ch" or "CABLE Input"

2. Set Teams mode with that device:
   ```bash
   voicebridge profile teams -d <ID>
   ```

---

## 🔄 Typical Workflow

### Before a Meeting (First Time)
```bash
# 1. Check configuration
voicebridge check

# 2. Find virtual device
voicebridge devices

# 3. Set Teams mode
voicebridge profile teams -d 5  # Use your device ID

# 4. Test it
voicebridge
# Speak in Spanish, verify it works
# Press Ctrl+C to stop
```

### Before Each Meeting (After Setup)
```bash
# 1. Switch to Teams mode (if not already)
voicebridge profile teams

# 2. Start VoiceBridge
voicebridge

# 3. Join Teams/Zoom call
# 4. Set Teams mic to virtual device
# 5. Speak Spanish, participants hear English!
```

### Testing/Development
```bash
# Switch to testing mode
voicebridge profile testing

# Start and hear translations
voicebridge

# Press Ctrl+C when done
```

---

## 🎯 Profile Quick Reference

| Command | Output Device | Audio Playback | Use Case |
|---------|---------------|----------------|----------|
| `profile testing` | Default speakers | Enabled | Testing |
| `profile teams -d N` | Virtual device N | Disabled | Teams/Zoom |

---

## 💡 Tips

### Switching Profiles is Instant
```bash
voicebridge profile testing   # Switch to testing
voicebridge                   # Run in testing mode
# Press Ctrl+C

voicebridge profile teams     # Switch to Teams
voicebridge                   # Run in Teams mode
```

### Check Current Profile Anytime
```bash
voicebridge profile
```

### Save Device ID for Later
Once you know your virtual device ID (e.g., 5), you can always switch back:
```bash
voicebridge profile teams -d 5
```

The configuration persists in `.env` file!

---

## 📝 Session Logs

All translations are automatically saved to:
```
~/voicebridge_sessions/session_YYYY-MM-DD_HH-MM-SS.md
```

Review these files after meetings to study English!

---

## ❌ Troubleshooting

### Command not found: voicebridge
```bash
# Reinstall in editable mode
cd /path/to/VoiceBridge
pip install -e .
```

### Teams can't hear me
1. Verify VoiceBridge is running
2. Check Teams mic is set to virtual device (BlackHole/CABLE Output)
3. Verify device ID: `voicebridge devices`
4. Check profile: `voicebridge profile`

### Audio sounds bad
```bash
# Edit .env manually and adjust gain
AUDIO_INPUT_GAIN=0.8  # Lower if too loud
```

---

## 🔗 Full Documentation

- Virtual Audio Setup: `docs/VIRTUAL_AUDIO_SETUP.md`
- Quick Start: `QUICK_START_VIRTUAL_AUDIO.md`
- Configuration: `.env.example`

---

**Happy translating! 🌉**
