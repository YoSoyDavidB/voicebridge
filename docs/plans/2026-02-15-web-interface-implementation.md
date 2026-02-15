# Web Interface Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a FastAPI + WebSocket web interface for VoiceBridge that enables browser-based microphone access, solving macOS permission issues while maintaining <500ms latency.

**Architecture:** FastAPI serves static HTML/CSS/JS and handles WebSocket connections. Browser captures audio via Web Audio API, sends chunks over WebSocket to backend, which processes through existing pipeline (VAD→STT→Translation→TTS), and returns translated audio to browser for playback.

**Tech Stack:** FastAPI, WebSockets, Web Audio API, vanilla JavaScript, existing VoiceBridge pipeline components

---

## Task 1: Install FastAPI Dependencies

**Files:**
- Modify: `requirements.txt`
- Modify: `pyproject.toml` (if using)

**Step 1: Add FastAPI dependencies to requirements.txt**

Add these lines:
```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.6
websockets>=12.0
```

**Step 2: Install dependencies**

Run: `python3 -m pip install -r requirements.txt`
Expected: All packages install successfully

**Step 3: Verify installation**

Run: `python3 -c "import fastapi; import uvicorn; print('FastAPI installed')"`
Expected: "FastAPI installed"

**Step 4: Commit**

```bash
git add requirements.txt
git commit -m "deps: add FastAPI and WebSocket dependencies"
```

---

## Task 2: Create Web Module Structure

**Files:**
- Create: `src/voicebridge/web/__init__.py`
- Create: `src/voicebridge/web/static/index.html`
- Create: `src/voicebridge/web/static/css/styles.css`
- Create: `src/voicebridge/web/static/js/audio.js`
- Create: `src/voicebridge/web/static/js/websocket.js`
- Create: `src/voicebridge/web/static/js/visualizer.js`
- Create: `src/voicebridge/web/static/js/config.js`

**Step 1: Create directory structure**

Run:
```bash
mkdir -p src/voicebridge/web/static/css
mkdir -p src/voicebridge/web/static/js
```

**Step 2: Create empty __init__.py**

```python
"""Web interface module for VoiceBridge."""

__all__ = ["app"]
```

**Step 3: Create placeholder files**

Run:
```bash
touch src/voicebridge/web/static/index.html
touch src/voicebridge/web/static/css/styles.css
touch src/voicebridge/web/static/js/audio.js
touch src/voicebridge/web/static/js/websocket.js
touch src/voicebridge/web/static/js/visualizer.js
touch src/voicebridge/web/static/js/config.js
```

**Step 4: Verify structure**

Run: `ls -R src/voicebridge/web/`
Expected: Shows all directories and files

**Step 5: Commit**

```bash
git add src/voicebridge/web/
git commit -m "feat(web): create web module structure"
```

---

## Task 3: Implement FastAPI Application

**Files:**
- Create: `src/voicebridge/web/app.py`
- Test: `tests/web/test_app.py` (create directory first)

**Step 1: Write failing test for FastAPI app**

Create `tests/web/__init__.py`:
```python
"""Tests for web module."""
```

Create `tests/web/test_app.py`:
```python
"""Tests for FastAPI application."""

from fastapi.testclient import TestClient


def test_app_serves_index():
    """Test that app serves index.html at root."""
    from voicebridge.web.app import app

    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_app_serves_static_files():
    """Test that app serves static files."""
    from voicebridge.web.app import app

    client = TestClient(app)
    response = client.get("/static/css/styles.css")

    assert response.status_code == 200
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/web/test_app.py -v`
Expected: FAIL with "cannot import name 'app'"

**Step 3: Implement FastAPI app**

Create `src/voicebridge/web/app.py`:
```python
"""FastAPI application for VoiceBridge web interface."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Get the directory where this file lives
WEB_DIR = Path(__file__).parent
STATIC_DIR = WEB_DIR / "static"

# Create FastAPI app
app = FastAPI(
    title="VoiceBridge",
    description="Real-time Spanish to English voice interpreter",
    version="1.0.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    """Serve the main HTML page."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
```

**Step 4: Add minimal HTML to make test pass**

Update `src/voicebridge/web/static/index.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VoiceBridge</title>
</head>
<body>
    <h1>VoiceBridge</h1>
</body>
</html>
```

Update `src/voicebridge/web/static/css/styles.css`:
```css
/* VoiceBridge Styles */
body {
    margin: 0;
    padding: 0;
}
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/web/test_app.py -v`
Expected: PASS (2 tests)

**Step 6: Commit**

```bash
git add src/voicebridge/web/app.py tests/web/ src/voicebridge/web/static/index.html src/voicebridge/web/static/css/styles.css
git commit -m "feat(web): implement FastAPI app with static file serving"
```

---

## Task 4: Implement Audio Bridge

**Files:**
- Create: `src/voicebridge/web/audio_bridge.py`
- Test: `tests/web/test_audio_bridge.py`

**Step 1: Write failing test**

Create `tests/web/test_audio_bridge.py`:
```python
"""Tests for audio bridge between Web Audio and Pipeline."""

import base64

from voicebridge.core.models import AudioChunk


def test_decode_web_audio():
    """Test decoding base64 web audio to AudioChunk."""
    from voicebridge.web.audio_bridge import WebAudioBridge

    bridge = WebAudioBridge()

    # Create test PCM data (480 samples @ 16kHz = 30ms)
    pcm_data = b'\x00\x00' * 480  # Silence
    base64_audio = base64.b64encode(pcm_data).decode('utf-8')

    chunk = bridge.decode_web_audio(base64_audio, timestamp_ms=1000.0)

    assert isinstance(chunk, AudioChunk)
    assert chunk.sample_rate == 16000
    assert chunk.channels == 1
    assert len(chunk.data) == 960  # 480 samples * 2 bytes


def test_encode_output_audio():
    """Test encoding pipeline audio to base64 for web."""
    from voicebridge.web.audio_bridge import WebAudioBridge

    bridge = WebAudioBridge()

    # Create test audio data
    pcm_data = b'\x00\x00' * 480

    base64_audio = bridge.encode_output_audio(pcm_data)

    assert isinstance(base64_audio, str)
    decoded = base64.b64decode(base64_audio)
    assert decoded == pcm_data
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/web/test_audio_bridge.py -v`
Expected: FAIL with "cannot import name 'WebAudioBridge'"

**Step 3: Implement audio bridge**

Create `src/voicebridge/web/audio_bridge.py`:
```python
"""Bridge between Web Audio API and VoiceBridge pipeline."""

from __future__ import annotations

import base64
import time

from voicebridge.core.models import AudioChunk


class WebAudioBridge:
    """Converts between web audio format and pipeline format."""

    def __init__(self):
        """Initialize audio bridge."""
        self.sample_rate = 16000
        self.channels = 1

    def decode_web_audio(self, base64_audio: str, timestamp_ms: float) -> AudioChunk:
        """Decode base64 web audio to AudioChunk.

        Args:
            base64_audio: Base64-encoded PCM audio data
            timestamp_ms: Timestamp in milliseconds

        Returns:
            AudioChunk for pipeline processing
        """
        # Decode base64 to raw PCM bytes
        pcm_data = base64.b64decode(base64_audio)

        # Calculate duration
        num_samples = len(pcm_data) // 2  # 16-bit = 2 bytes per sample
        duration_ms = (num_samples / self.sample_rate) * 1000

        # Create AudioChunk
        return AudioChunk(
            data=pcm_data,
            sample_rate=self.sample_rate,
            channels=self.channels,
            timestamp_ms=timestamp_ms,
            duration_ms=duration_ms,
            sequence_number=0,  # Will be set by pipeline
        )

    def encode_output_audio(self, pcm_data: bytes) -> str:
        """Encode pipeline audio output to base64 for web.

        Args:
            pcm_data: Raw PCM audio bytes

        Returns:
            Base64-encoded audio string
        """
        return base64.b64encode(pcm_data).decode('utf-8')
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/web/test_audio_bridge.py -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add src/voicebridge/web/audio_bridge.py tests/web/test_audio_bridge.py
git commit -m "feat(web): implement audio bridge for format conversion"
```

---

## Task 5: Implement WebSocket Handler

**Files:**
- Create: `src/voicebridge/web/websocket_handler.py`
- Test: `tests/web/test_websocket_handler.py`

**Step 1: Write failing test**

Create `tests/web/test_websocket_handler.py`:
```python
"""Tests for WebSocket message handling."""

import asyncio
import json

import pytest


@pytest.mark.asyncio
async def test_handle_config_message():
    """Test handling configuration message."""
    from voicebridge.web.websocket_handler import WebSocketHandler

    handler = WebSocketHandler()

    message = {
        "type": "config",
        "apiKeys": {
            "deepgram": "test_key",
            "openai": "test_key",
            "elevenlabs": "test_key",
            "voiceId": "test_voice"
        }
    }

    response = await handler.handle_message(json.dumps(message))

    assert response is not None
    assert json.loads(response)["type"] == "status"


@pytest.mark.asyncio
async def test_handle_audio_message():
    """Test handling audio chunk message."""
    from voicebridge.web.websocket_handler import WebSocketHandler

    handler = WebSocketHandler()

    # Configure first
    config_msg = {
        "type": "config",
        "apiKeys": {
            "deepgram": "test_key",
            "openai": "test_key",
            "elevenlabs": "test_key",
            "voiceId": "test_voice"
        }
    }
    await handler.handle_message(json.dumps(config_msg))

    # Send audio
    audio_msg = {
        "type": "audio",
        "data": "AAAA",  # base64 for silence
        "timestamp": 1000
    }

    response = await handler.handle_message(json.dumps(audio_msg))

    # Audio messages may not return immediate response
    assert response is None or "type" in json.loads(response)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/web/test_websocket_handler.py -v`
Expected: FAIL with "cannot import name 'WebSocketHandler'"

**Step 3: Implement WebSocket handler**

Create `src/voicebridge/web/websocket_handler.py`:
```python
"""WebSocket message handler for VoiceBridge web interface."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

from voicebridge.web.audio_bridge import WebAudioBridge


class WebSocketHandler:
    """Handles WebSocket messages from browser."""

    def __init__(self):
        """Initialize WebSocket handler."""
        self.audio_bridge = WebAudioBridge()
        self.config: Optional[dict[str, Any]] = None
        self.pipeline = None  # Will be initialized with config

    async def handle_message(self, message: str) -> Optional[str]:
        """Handle incoming WebSocket message.

        Args:
            message: JSON string message from client

        Returns:
            Optional JSON response to send back
        """
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "config":
                return await self._handle_config(data)
            elif msg_type == "audio":
                return await self._handle_audio(data)
            elif msg_type == "control":
                return await self._handle_control(data)
            else:
                return self._error_response(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            return self._error_response("Invalid JSON")
        except Exception as e:
            return self._error_response(f"Error: {str(e)}")

    async def _handle_config(self, data: dict[str, Any]) -> str:
        """Handle configuration message."""
        self.config = data.get("apiKeys", {})

        # TODO: Initialize pipeline with API keys
        # For now, just acknowledge

        return json.dumps({
            "type": "status",
            "state": "ready",
            "message": "Configuration received"
        })

    async def _handle_audio(self, data: dict[str, Any]) -> Optional[str]:
        """Handle audio chunk message."""
        if not self.config:
            return self._error_response("Not configured. Send config first.")

        base64_audio = data.get("data")
        timestamp = data.get("timestamp", 0)

        # Decode audio
        audio_chunk = self.audio_bridge.decode_web_audio(base64_audio, timestamp)

        # TODO: Send to pipeline
        # For now, just acknowledge receipt

        return None  # Audio processing is async, responses come separately

    async def _handle_control(self, data: dict[str, Any]) -> str:
        """Handle control message."""
        action = data.get("action")

        if action == "stop":
            # TODO: Stop pipeline
            return json.dumps({
                "type": "status",
                "state": "stopped",
                "message": "Processing stopped"
            })

        return self._error_response(f"Unknown action: {action}")

    def _error_response(self, message: str) -> str:
        """Create error response."""
        return json.dumps({
            "type": "error",
            "message": message,
            "code": "PROCESSING_ERROR"
        })
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/web/test_websocket_handler.py -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add src/voicebridge/web/websocket_handler.py tests/web/test_websocket_handler.py
git commit -m "feat(web): implement WebSocket message handler"
```

---

## Task 6: Add WebSocket Endpoint to FastAPI

**Files:**
- Modify: `src/voicebridge/web/app.py`
- Test: `tests/web/test_websocket_endpoint.py`

**Step 1: Write failing test**

Create `tests/web/test_websocket_endpoint.py`:
```python
"""Tests for WebSocket endpoint."""

import json

import pytest
from fastapi.testclient import TestClient


def test_websocket_connection():
    """Test WebSocket connection."""
    from voicebridge.web.app import app

    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Send config
        config = {
            "type": "config",
            "apiKeys": {
                "deepgram": "test",
                "openai": "test",
                "elevenlabs": "test",
                "voiceId": "test"
            }
        }
        websocket.send_text(json.dumps(config))

        # Receive response
        response = websocket.receive_text()
        data = json.loads(response)

        assert data["type"] == "status"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/web/test_websocket_endpoint.py -v`
Expected: FAIL with "404 Not Found" or similar

**Step 3: Add WebSocket endpoint to app**

Update `src/voicebridge/web/app.py`:
```python
"""FastAPI application for VoiceBridge web interface."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from voicebridge.web.websocket_handler import WebSocketHandler

# Get the directory where this file lives
WEB_DIR = Path(__file__).parent
STATIC_DIR = WEB_DIR / "static"

# Create FastAPI app
app = FastAPI(
    title="VoiceBridge",
    description="Real-time Spanish to English voice interpreter",
    version="1.0.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    """Serve the main HTML page."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time audio processing."""
    await websocket.accept()

    handler = WebSocketHandler()

    try:
        while True:
            # Receive message from client
            message = await websocket.receive_text()

            # Handle message
            response = await handler.handle_message(message)

            # Send response if any
            if response:
                await websocket.send_text(response)

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/web/test_websocket_endpoint.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/voicebridge/web/app.py tests/web/test_websocket_endpoint.py
git commit -m "feat(web): add WebSocket endpoint to FastAPI app"
```

---

## Task 7: Create Frontend HTML Structure

**Files:**
- Modify: `src/voicebridge/web/static/index.html`

**Step 1: Implement complete HTML structure**

Update `src/voicebridge/web/static/index.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VoiceBridge - Real-time Voice Translation</title>
    <link rel="stylesheet" href="/static/css/styles.css">
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="header">
            <h1 class="logo">VOICEBRIDGE</h1>
            <button class="settings-btn" id="settingsBtn">⚙️ Settings</button>
        </header>

        <!-- Main Content -->
        <main class="main">
            <!-- Start/Stop Button -->
            <div class="control-section">
                <button class="control-btn" id="controlBtn" disabled>
                    <div class="icon">🎤</div>
                    <div class="text">START</div>
                </button>
            </div>

            <!-- Visualizer -->
            <canvas id="visualizer" class="visualizer"></canvas>

            <!-- Status -->
            <div class="status" id="status">
                <span class="status-text">Initializing...</span>
            </div>
        </main>

        <!-- Settings Panel (Hidden by default) -->
        <div class="settings-panel" id="settingsPanel">
            <div class="settings-content">
                <h2>Configuration</h2>

                <div class="form-group">
                    <label for="deepgramKey">Deepgram API Key</label>
                    <input type="password" id="deepgramKey" placeholder="Enter Deepgram API key">
                </div>

                <div class="form-group">
                    <label for="openaiKey">OpenAI API Key</label>
                    <input type="password" id="openaiKey" placeholder="Enter OpenAI API key">
                </div>

                <div class="form-group">
                    <label for="elevenlabsKey">ElevenLabs API Key</label>
                    <input type="password" id="elevenlabsKey" placeholder="Enter ElevenLabs API key">
                </div>

                <div class="form-group">
                    <label for="voiceId">ElevenLabs Voice ID</label>
                    <input type="text" id="voiceId" placeholder="Enter Voice ID">
                </div>

                <div class="settings-actions">
                    <button class="btn btn-primary" id="saveSettingsBtn">Save</button>
                    <button class="btn btn-secondary" id="testKeysBtn">Test Connection</button>
                    <button class="btn btn-danger" id="clearSettingsBtn">Clear All</button>
                </div>

                <button class="close-btn" id="closeSettingsBtn">×</button>
            </div>
        </div>
    </div>

    <!-- Scripts -->
    <script src="/static/js/config.js"></script>
    <script src="/static/js/audio.js"></script>
    <script src="/static/js/visualizer.js"></script>
    <script src="/static/js/websocket.js"></script>
</body>
</html>
```

**Step 2: Test in browser**

Run: `uvicorn voicebridge.web.app:app --reload`
Visit: http://localhost:8000
Expected: Page loads with unstyled HTML elements

**Step 3: Commit**

```bash
git add src/voicebridge/web/static/index.html
git commit -m "feat(web): create HTML structure for UI"
```

---

## Task 8: Implement Futuristic CSS Styling

**Files:**
- Modify: `src/voicebridge/web/static/css/styles.css`

**Step 1: Implement complete CSS**

Update `src/voicebridge/web/static/css/styles.css`:
```css
/* VoiceBridge - Futuristic Tech Styling */

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono&display=swap');

:root {
    /* Colors */
    --bg-primary: #0a0e27;
    --bg-secondary: #1a1f3a;
    --bg-tertiary: #252b4a;
    --accent-cyan: #00ffff;
    --accent-green: #00ff88;
    --text-primary: #ffffff;
    --text-secondary: #e0e0e0;
    --text-muted: #8b92b0;
    --error: #ff4444;

    /* Spacing */
    --spacing-xs: 0.5rem;
    --spacing-sm: 1rem;
    --spacing-md: 1.5rem;
    --spacing-lg: 2rem;
    --spacing-xl: 3rem;

    /* Border radius */
    --radius-sm: 0.5rem;
    --radius-md: 1rem;
    --radius-lg: 1.5rem;

    /* Transitions */
    --transition-fast: 200ms;
    --transition-normal: 300ms;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Inter', sans-serif;
    background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
    color: var(--text-primary);
    min-height: 100vh;
    overflow: hidden;
}

.container {
    max-width: 800px;
    margin: 0 auto;
    padding: var(--spacing-lg);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

/* Header */
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-xl);
}

.logo {
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    background: linear-gradient(90deg, var(--accent-cyan), var(--accent-green));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-shadow: 0 0 30px rgba(0, 255, 255, 0.3);
}

.settings-btn {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: var(--text-primary);
    padding: var(--spacing-sm) var(--spacing-md);
    border-radius: var(--radius-md);
    cursor: pointer;
    font-size: 1rem;
    transition: all var(--transition-normal);
}

.settings-btn:hover {
    background: rgba(255, 255, 255, 0.1);
    box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
}

/* Main Content */
.main {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}

/* Control Button */
.control-section {
    margin-bottom: var(--spacing-xl);
}

.control-btn {
    width: 200px;
    height: 200px;
    border-radius: 50%;
    background: linear-gradient(135deg, rgba(0, 255, 255, 0.1), rgba(0, 255, 136, 0.1));
    backdrop-filter: blur(10px);
    border: 3px solid var(--accent-cyan);
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-sm);
    transition: all var(--transition-normal);
    box-shadow: 0 0 40px rgba(0, 255, 255, 0.3);
}

.control-btn:hover:not(:disabled) {
    transform: scale(1.05);
    box-shadow: 0 0 60px rgba(0, 255, 255, 0.5);
}

.control-btn:active:not(:disabled) {
    transform: scale(0.95);
}

.control-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.control-btn.active {
    background: linear-gradient(135deg, rgba(255, 68, 68, 0.2), rgba(255, 0, 0, 0.2));
    border-color: var(--error);
    box-shadow: 0 0 40px rgba(255, 68, 68, 0.5);
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% {
        box-shadow: 0 0 40px rgba(255, 68, 68, 0.5);
    }
    50% {
        box-shadow: 0 0 60px rgba(255, 68, 68, 0.8);
    }
}

.control-btn .icon {
    font-size: 4rem;
}

.control-btn .text {
    font-size: 1.25rem;
    font-weight: 600;
    letter-spacing: 0.1em;
}

/* Visualizer */
.visualizer {
    width: 100%;
    max-width: 600px;
    height: 100px;
    margin-bottom: var(--spacing-lg);
    background: rgba(0, 0, 0, 0.3);
    border-radius: var(--radius-md);
    border: 1px solid rgba(255, 255, 255, 0.1);
}

/* Status */
.status {
    text-align: center;
    padding: var(--spacing-md);
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(10px);
    border-radius: var(--radius-md);
    border: 1px solid rgba(255, 255, 255, 0.1);
    min-width: 300px;
}

.status-text {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem;
    color: var(--accent-cyan);
}

/* Settings Panel */
.settings-panel {
    position: fixed;
    top: 0;
    right: -400px;
    width: 400px;
    height: 100vh;
    background: rgba(26, 31, 58, 0.95);
    backdrop-filter: blur(20px);
    border-left: 1px solid rgba(255, 255, 255, 0.1);
    padding: var(--spacing-lg);
    transition: right var(--transition-normal);
    overflow-y: auto;
    z-index: 1000;
}

.settings-panel.open {
    right: 0;
    box-shadow: -10px 0 40px rgba(0, 0, 0, 0.5);
}

.settings-content h2 {
    margin-bottom: var(--spacing-lg);
    color: var(--accent-cyan);
}

.form-group {
    margin-bottom: var(--spacing-md);
}

.form-group label {
    display: block;
    margin-bottom: var(--spacing-xs);
    font-size: 0.9rem;
    color: var(--text-secondary);
}

.form-group input {
    width: 100%;
    padding: var(--spacing-sm);
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    transition: all var(--transition-fast);
}

.form-group input:focus {
    outline: none;
    border-color: var(--accent-cyan);
    box-shadow: 0 0 10px rgba(0, 255, 255, 0.3);
}

.settings-actions {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
    margin-top: var(--spacing-lg);
}

.btn {
    padding: var(--spacing-sm) var(--spacing-md);
    border: none;
    border-radius: var(--radius-sm);
    cursor: pointer;
    font-weight: 600;
    transition: all var(--transition-fast);
}

.btn-primary {
    background: linear-gradient(90deg, var(--accent-cyan), var(--accent-green));
    color: var(--bg-primary);
}

.btn-primary:hover {
    box-shadow: 0 0 20px rgba(0, 255, 255, 0.5);
}

.btn-secondary {
    background: rgba(255, 255, 255, 0.1);
    color: var(--text-primary);
}

.btn-secondary:hover {
    background: rgba(255, 255, 255, 0.15);
}

.btn-danger {
    background: rgba(255, 68, 68, 0.2);
    color: var(--error);
}

.btn-danger:hover {
    background: rgba(255, 68, 68, 0.3);
}

.close-btn {
    position: absolute;
    top: var(--spacing-md);
    right: var(--spacing-md);
    background: none;
    border: none;
    color: var(--text-primary);
    font-size: 2rem;
    cursor: pointer;
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    transition: all var(--transition-fast);
}

.close-btn:hover {
    background: rgba(255, 255, 255, 0.1);
}

/* Responsive */
@media (max-width: 768px) {
    .settings-panel {
        width: 100%;
        right: -100%;
    }

    .control-btn {
        width: 150px;
        height: 150px;
    }

    .control-btn .icon {
        font-size: 3rem;
    }
}
```

**Step 2: Test styling in browser**

Run: `uvicorn voicebridge.web.app:app --reload`
Visit: http://localhost:8000
Expected: Futuristic styled interface

**Step 3: Commit**

```bash
git add src/voicebridge/web/static/css/styles.css
git commit -m "feat(web): implement futuristic CSS styling"
```

---

## Task 9: Implement Config Management (LocalStorage)

**Files:**
- Modify: `src/voicebridge/web/static/js/config.js`

**Step 1: Implement config.js**

Update `src/voicebridge/web/static/js/config.js`:
```javascript
/**
 * Configuration management using LocalStorage
 */

const CONFIG_KEY = 'voicebridge_config';

class ConfigManager {
    constructor() {
        this.config = this.load();
    }

    /**
     * Load configuration from LocalStorage
     */
    load() {
        try {
            const stored = localStorage.getItem(CONFIG_KEY);
            if (stored) {
                return JSON.parse(stored);
            }
        } catch (error) {
            console.error('Error loading config:', error);
        }
        return {
            deepgram: '',
            openai: '',
            elevenlabs: '',
            voiceId: ''
        };
    }

    /**
     * Save configuration to LocalStorage
     */
    save(config) {
        try {
            localStorage.setItem(CONFIG_KEY, JSON.stringify(config));
            this.config = config;
            return true;
        } catch (error) {
            console.error('Error saving config:', error);
            return false;
        }
    }

    /**
     * Clear all configuration
     */
    clear() {
        localStorage.removeItem(CONFIG_KEY);
        this.config = {
            deepgram: '',
            openai: '',
            elevenlabs: '',
            voiceId: ''
        };
    }

    /**
     * Check if configuration is complete
     */
    isComplete() {
        return this.config.deepgram &&
               this.config.openai &&
               this.config.elevenlabs &&
               this.config.voiceId;
    }

    /**
     * Get configuration object for WebSocket
     */
    getConfig() {
        return { ...this.config };
    }
}

// Initialize settings panel functionality
document.addEventListener('DOMContentLoaded', () => {
    const configManager = new ConfigManager();
    const settingsPanel = document.getElementById('settingsPanel');
    const settingsBtn = document.getElementById('settingsBtn');
    const closeSettingsBtn = document.getElementById('closeSettingsBtn');
    const saveSettingsBtn = document.getElementById('saveSettingsBtn');
    const clearSettingsBtn = document.getElementById('clearSettingsBtn');

    // Load saved config into form
    function loadConfigToForm() {
        const config = configManager.getConfig();
        document.getElementById('deepgramKey').value = config.deepgram || '';
        document.getElementById('openaiKey').value = config.openai || '';
        document.getElementById('elevenlabsKey').value = config.elevenlabs || '';
        document.getElementById('voiceId').value = config.voiceId || '';
    }

    // Open settings
    settingsBtn.addEventListener('click', () => {
        settingsPanel.classList.add('open');
        loadConfigToForm();
    });

    // Close settings
    closeSettingsBtn.addEventListener('click', () => {
        settingsPanel.classList.remove('open');
    });

    // Save settings
    saveSettingsBtn.addEventListener('click', () => {
        const config = {
            deepgram: document.getElementById('deepgramKey').value.trim(),
            openai: document.getElementById('openaiKey').value.trim(),
            elevenlabs: document.getElementById('elevenlabsKey').value.trim(),
            voiceId: document.getElementById('voiceId').value.trim()
        };

        if (configManager.save(config)) {
            alert('Configuration saved successfully!');
            settingsPanel.classList.remove('open');
            // Enable start button if config is complete
            if (configManager.isComplete()) {
                document.getElementById('controlBtn').disabled = false;
            }
        } else {
            alert('Error saving configuration');
        }
    });

    // Clear settings
    clearSettingsBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to clear all settings?')) {
            configManager.clear();
            loadConfigToForm();
            document.getElementById('controlBtn').disabled = true;
        }
    });

    // Initial check - enable button if config exists
    if (configManager.isComplete()) {
        document.getElementById('controlBtn').disabled = false;
        updateStatus('Ready');
    } else {
        updateStatus('Configure API keys to start');
    }
});

// Helper function to update status (will be used by other modules)
function updateStatus(message) {
    const statusText = document.querySelector('.status-text');
    if (statusText) {
        statusText.textContent = message;
    }
}
```

**Step 2: Test in browser**

Run: `uvicorn voicebridge.web.app:app --reload`
Visit: http://localhost:8000
Test: Open settings, enter keys, save, close and reopen
Expected: Settings persist across page reloads

**Step 3: Commit**

```bash
git add src/voicebridge/web/static/js/config.js
git commit -m "feat(web): implement config management with LocalStorage"
```

---

**(Continuing in next message due to length...)**

Would you like me to continue with the remaining tasks (WebSocket client, Audio capture, Visualizer, Pipeline integration, and CLI command)?