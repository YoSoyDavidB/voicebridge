# PCM Web Player Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Stream ElevenLabs PCM audio in the browser with minimal latency using AudioContext and verified unit tests.

**Architecture:** WebSocket audio messages carry base64 PCM (16-bit, 22050 Hz). The frontend decodes base64 → Int16 → Float32 and schedules playback immediately via AudioContext. A small scheduler maintains `nextPlayTime` to avoid gaps while keeping latency low.

**Tech Stack:** FastAPI + WebSocket, vanilla JS, AudioContext, Vitest (unit tests).

---

### Task 1: Add JS test tooling (Vitest)

**Files:**
- Create: `package.json`
- Create: `vitest.config.js`

**Step 1: Write the failing test**

Create a minimal test file to prove the runner is wired.

File: `tests/web/smoke.test.js`

```js
import { describe, it, expect } from "vitest";

describe("vitest setup", () => {
  it("runs", () => {
    expect(1 + 1).toBe(2);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm test -- --run`
Expected: FAIL because package.json/vitest config is missing.

**Step 3: Write minimal implementation**

Create `package.json` with Vitest and a test script.

```json
{
  "name": "voicebridge-web-tests",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "vitest"
  },
  "devDependencies": {
    "vitest": "^2.1.9"
  }
}
```

Create `vitest.config.js` to scope tests.

```js
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["tests/web/**/*.test.js"],
    environment: "node"
  }
});
```

**Step 4: Run test to verify it passes**

Run: `npm install && npm test -- --run`
Expected: PASS.

**Step 5: Commit**

```bash
git add package.json vitest.config.js tests/web/smoke.test.js
git commit -m "test: add vitest setup for web audio"
```

---

### Task 2: Add PCM player unit tests

**Files:**
- Create: `tests/web/pcm_player.test.js`
- Create: `src/voicebridge/web/static/js/pcm_player.js` (empty scaffold for imports)

**Step 1: Write the failing test**

```js
import { describe, it, expect, vi, beforeEach } from "vitest";
import { PCMPlayer } from "../../src/voicebridge/web/static/js/pcm_player.js";

class FakeAudioBuffer {
  constructor(length) {
    this.length = length;
    this._data = new Float32Array(length);
  }
  getChannelData() {
    return this._data;
  }
}

class FakeSource {
  constructor() {
    this.startedAt = null;
  }
  connect() {}
  start(t) {
    this.startedAt = t;
  }
}

class FakeAudioContext {
  constructor() {
    this.currentTime = 1.0;
  }
  createBuffer(channels, length, sampleRate) {
    this.lastBufferArgs = { channels, length, sampleRate };
    return new FakeAudioBuffer(length);
  }
  createBufferSource() {
    this.lastSource = new FakeSource();
    return this.lastSource;
  }
  createGain() {
    return { connect() {} };
  }
}

describe("PCMPlayer", () => {
  let player;

  beforeEach(() => {
    player = new PCMPlayer({ sampleRate: 22050, AudioContextImpl: FakeAudioContext });
  });

  it("decodes base64 to Int16Array", () => {
    const bytes = new Uint8Array([0, 0, 255, 127]);
    const base64 = btoa(String.fromCharCode(...bytes));
    const decoded = player.decodeBase64ToInt16(base64);
    expect(decoded).toBeInstanceOf(Int16Array);
    expect(decoded.length).toBe(2);
    expect(decoded[1]).toBe(32767);
  });

  it("converts Int16 to Float32", () => {
    const float32 = player.int16ToFloat32(new Int16Array([0, 32767, -32768]));
    expect(float32[0]).toBe(0);
    expect(float32[1]).toBeCloseTo(1.0, 3);
    expect(float32[2]).toBeCloseTo(-1.0, 3);
  });

  it("schedules playback in order", () => {
    const float32 = new Float32Array(2205); // 0.1s @ 22050
    const t1 = player.playChunk(float32);
    const t2 = player.playChunk(float32);
    expect(t2).toBeGreaterThanOrEqual(t1);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm test -- --run`
Expected: FAIL because `pcm_player.js` doesn’t exist or has no implementation.

**Step 3: Write minimal implementation**

Create `src/voicebridge/web/static/js/pcm_player.js`:

```js
export class PCMPlayer {
  constructor({ sampleRate, AudioContextImpl = globalThis.AudioContext }) {
    this.sampleRate = sampleRate;
    this.AudioContextImpl = AudioContextImpl;
    this.audioContext = new this.AudioContextImpl();
    this.gainNode = this.audioContext.createGain();
    this.nextPlayTime = this.audioContext.currentTime;
  }

  decodeBase64ToInt16(base64) {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return new Int16Array(bytes.buffer);
  }

  int16ToFloat32(int16) {
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
      float32[i] = Math.max(-1, Math.min(1, int16[i] / 32768));
    }
    return float32;
  }

  playChunk(float32) {
    const buffer = this.audioContext.createBuffer(1, float32.length, this.sampleRate);
    buffer.getChannelData(0).set(float32);

    const source = this.audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(this.gainNode);
    this.gainNode.connect(this.audioContext.destination);

    const startTime = Math.max(this.nextPlayTime, this.audioContext.currentTime);
    source.start(startTime);
    this.nextPlayTime = startTime + float32.length / this.sampleRate;
    return startTime;
  }

  enqueue(base64) {
    const int16 = this.decodeBase64ToInt16(base64);
    const float32 = this.int16ToFloat32(int16);
    return this.playChunk(float32);
  }

  close() {
    this.audioContext.close();
  }
}
```

**Step 4: Run test to verify it passes**

Run: `npm test -- --run`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/voicebridge/web/static/js/pcm_player.js tests/web/pcm_player.test.js
git commit -m "feat: add PCM audio player for web"
```

---

### Task 3: Wire PCM player into WebSocket client

**Files:**
- Modify: `src/voicebridge/web/static/js/websocket.js`
- Modify: `src/voicebridge/web/static/index.html`

**Step 1: Write the failing test**

Create test to ensure audio messages call PCMPlayer.

File: `tests/web/websocket_audio.test.js`

```js
import { describe, it, expect, vi, beforeEach } from "vitest";
import { WebSocketClient } from "../../src/voicebridge/web/static/js/websocket.js";

describe("WebSocket audio handling", () => {
  it("routes audio data to PCMPlayer", () => {
    const ws = new WebSocketClient();
    ws._pcmPlayer = { enqueue: vi.fn() };
    ws.handleMessage(JSON.stringify({ type: "audio", data: "AQID" }));
    expect(ws._pcmPlayer.enqueue).toHaveBeenCalledWith("AQID");
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm test -- --run`
Expected: FAIL because WebSocketClient does not expose a testable method or PCMPlayer integration.

**Step 3: Write minimal implementation**

Update `src/voicebridge/web/static/js/websocket.js`:

```js
import { PCMPlayer } from "./pcm_player.js";

class WebSocketClient {
  constructor() {
    this.ws = null;
    this._pcmPlayer = new PCMPlayer({ sampleRate: 22050 });
    // ...existing fields
  }

  handleMessage(data) {
    // ...existing parsing
    if (message.type === "audio") {
      this._pcmPlayer.enqueue(message.data);
      return;
    }
    // ...existing cases
  }
}

export { WebSocketClient };
```

Because `websocket.js` is now loaded as a module, expose the instance for
`audio.js` (which currently expects a global `wsClient`) by assigning:

```js
globalThis.wsClient = wsClient;
```

Update `index.html` to load module with ES module support:

```html
<script type="module" src="/static/js/websocket.js"></script>
```

**Step 4: Run test to verify it passes**

Run: `npm test -- --run`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/voicebridge/web/static/js/websocket.js src/voicebridge/web/static/index.html tests/web/websocket_audio.test.js
git commit -m "feat: wire PCM player into websocket audio"
```

---

### Task 4: Manual validation for MVP latency

**Files:**
- None

**Step 1: Run local server**

Run: `python -m voicebridge web`

**Step 2: Test audio**

- Speak a short Spanish phrase.
- Confirm you hear English audio playback.
- Note rough latency (subjective).

**Step 3: Record observation**

Add a short note to `docs/plans/2026-02-15-pcm-player.md` with latency observations.

**Step 4: Commit**

```bash
git add docs/plans/2026-02-15-pcm-player.md
git commit -m "docs: note pcm playback latency" 
```

---

Plan complete and saved to `docs/plans/2026-02-15-pcm-player.md`. Two execution options:

1. Subagent-Driven (this session) - I dispatch a fresh subagent per task, review between tasks.
2. Parallel Session (separate) - Open new session with executing-plans, batch execution with checkpoints.

Which approach?
