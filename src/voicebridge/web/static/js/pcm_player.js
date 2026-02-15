export class PCMPlayer {
  constructor({ sampleRate, AudioContextImpl = globalThis.AudioContext }) {
    if (!AudioContextImpl) {
      throw new Error("AudioContext is not available");
    }
    this.sampleRate = sampleRate;
    this.AudioContextImpl = AudioContextImpl;
    this.audioContext = new this.AudioContextImpl();
    this.gainNode = this.audioContext.createGain();
    this.gainNode.connect(this.audioContext.destination);
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
    if (this.audioContext.state === "suspended") {
      this.audioContext.resume();
    }
    const buffer = this.audioContext.createBuffer(1, float32.length, this.sampleRate);
    buffer.getChannelData(0).set(float32);

    const source = this.audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(this.gainNode);
    source.onended = () => {
      source.disconnect();
    };

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
    return this.audioContext.close();
  }
}
