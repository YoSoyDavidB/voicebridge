import { describe, it, expect, beforeEach } from "vitest";
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
    this.disconnected = false;
    this.onended = null;
  }
  connect() {}
  disconnect() {
    this.disconnected = true;
  }
  start(t) {
    this.startedAt = t;
  }
}

class FakeAudioContext {
  constructor() {
    this.currentTime = 1.0;
    this.state = "running";
    this.destination = {};
    this.resumeCalled = false;
    this.closeCalled = false;
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
    this.gainNode = {
      connect: (destination) => {
        this.gainConnectCount = (this.gainConnectCount ?? 0) + 1;
        this.gainConnectDestination = destination;
      },
    };
    return this.gainNode;
  }
  resume() {
    this.resumeCalled = true;
    this.state = "running";
    return Promise.resolve();
  }
  close() {
    this.closeCalled = true;
    return Promise.resolve("closed");
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
    const float32 = new Float32Array(2205);
    const t1 = player.playChunk(float32);
    const t2 = player.playChunk(float32);
    expect(t2).toBeGreaterThanOrEqual(t1);
  });

  it("connects gain node once in constructor", () => {
    expect(player.audioContext.gainConnectCount).toBe(1);
    expect(player.audioContext.gainConnectDestination).toBe(player.audioContext.destination);
  });

  it("disconnects source on ended", () => {
    const float32 = new Float32Array(2205);
    player.playChunk(float32);
    expect(player.audioContext.lastSource.onended).toBeTypeOf("function");
    player.audioContext.lastSource.onended();
    expect(player.audioContext.lastSource.disconnected).toBe(true);
  });

  it("resumes audio context when suspended", () => {
    player.audioContext.state = "suspended";
    const float32 = new Float32Array(2205);
    player.playChunk(float32);
    expect(player.audioContext.resumeCalled).toBe(true);
  });

  it("close returns AudioContext close promise", async () => {
    const result = await player.close();
    expect(result).toBe("closed");
    expect(player.audioContext.closeCalled).toBe(true);
  });

  it("throws if AudioContext is missing", () => {
    expect(() => new PCMPlayer({ sampleRate: 22050, AudioContextImpl: null })).toThrow(
      "AudioContext is not available"
    );
  });
});
