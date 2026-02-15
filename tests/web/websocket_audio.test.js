import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

class FakeAudioContext {
  constructor() {
    this.destination = {};
  }
  createGain() {
    return { connect: vi.fn() };
  }
}

describe("WebSocketClient audio handling", () => {
  const originalDocument = globalThis.document;
  const originalAudioContext = globalThis.AudioContext;

  beforeEach(() => {
    vi.resetModules();
    globalThis.document = { addEventListener: vi.fn() };
    globalThis.AudioContext = FakeAudioContext;
  });

  afterEach(() => {
    globalThis.document = originalDocument;
    globalThis.AudioContext = originalAudioContext;
  });

  it("routes audio messages to PCMPlayer enqueue", async () => {
    const { WebSocketClient } = await import(
      "../../src/voicebridge/web/static/js/websocket.js"
    );
    const client = new WebSocketClient();
    const enqueue = vi.fn();
    client._pcmPlayer = { enqueue };

    client.handleMessage(JSON.stringify({ type: "audio", data: "Zm9v" }));

    expect(enqueue).toHaveBeenCalledWith("Zm9v");
  });
});
