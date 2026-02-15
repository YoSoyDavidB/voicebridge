/**
 * Audio capture using Web Audio API
 */

class AudioCapture {
    constructor() {
        this.audioContext = null;
        this.mediaStream = null;
        this.sourceNode = null;
        this.analyserNode = null;
        this.processorNode = null;
        this.isCapturing = false;
        this.sampleRate = 16000; // Target sample rate for speech recognition
        this.chunkSize = 480; // ~30ms at 16kHz
        this.audioBuffer = [];
    }

    /**
     * Request microphone permission and initialize audio context
     */
    async initialize() {
        try {
            // Request microphone access
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: this.sampleRate,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });

            // Create audio context with target sample rate
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: this.sampleRate
            });

            // Create source node from microphone stream
            this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);

            // Create analyser for visualization
            this.analyserNode = this.audioContext.createAnalyser();
            this.analyserNode.fftSize = 2048;
            this.analyserNode.smoothingTimeConstant = 0.8;

            // Connect source to analyser
            this.sourceNode.connect(this.analyserNode);

            // Create script processor for audio chunks
            // Using ScriptProcessorNode (deprecated but still widely supported)
            // TODO: Migrate to AudioWorklet for better performance
            const bufferSize = 4096;
            this.processorNode = this.audioContext.createScriptProcessor(bufferSize, 1, 1);

            this.processorNode.onaudioprocess = (event) => {
                if (!this.isCapturing) return;

                const inputData = event.inputBuffer.getChannelData(0);
                this.processAudioChunk(inputData);
            };

            // Connect analyser to processor to destination
            this.analyserNode.connect(this.processorNode);
            this.processorNode.connect(this.audioContext.destination);

            console.log('Audio capture initialized successfully');
            return true;

        } catch (error) {
            console.error('Error initializing audio capture:', error);

            if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
                updateStatus('Microphone permission denied');
            } else if (error.name === 'NotFoundError') {
                updateStatus('No microphone found');
            } else {
                updateStatus('Error accessing microphone');
            }

            return false;
        }
    }

    /**
     * Start capturing audio
     */
    async start() {
        if (this.isCapturing) {
            console.warn('Already capturing audio');
            return;
        }

        // Initialize if not already done
        if (!this.audioContext) {
            const success = await this.initialize();
            if (!success) {
                return false;
            }
        }

        // Resume audio context if suspended
        if (this.audioContext.state === 'suspended') {
            await this.audioContext.resume();
        }

        this.isCapturing = true;
        this.audioBuffer = [];

        console.log('Started audio capture');
        updateStatus('Listening...');

        return true;
    }

    /**
     * Stop capturing audio
     */
    stop() {
        if (!this.isCapturing) {
            console.warn('Not currently capturing');
            return;
        }

        this.isCapturing = false;

        console.log('Stopped audio capture');
        updateStatus('Ready');
    }

    /**
     * Process audio chunk and send to server
     */
    processAudioChunk(audioData) {
        // Add samples to buffer
        this.audioBuffer.push(...audioData);

        // Send chunks of specified size
        while (this.audioBuffer.length >= this.chunkSize) {
            const chunk = this.audioBuffer.splice(0, this.chunkSize);

            // Convert Float32Array to Int16Array (PCM 16-bit)
            const pcmData = this.floatTo16BitPCM(chunk);

            // Convert to base64
            const base64Data = this.arrayBufferToBase64(pcmData.buffer);

            // Send to server via WebSocket
            if (wsClient && wsClient.isConnected()) {
                console.log(`[Audio] Sending chunk: ${chunk.length} samples, base64 length: ${base64Data.length}`);
                wsClient.sendAudio(base64Data);
            } else {
                console.warn('[Audio] WebSocket not connected, dropping chunk');
            }
        }
    }

    /**
     * Convert Float32Array to Int16Array (PCM 16-bit)
     */
    floatTo16BitPCM(floatSamples) {
        const int16Array = new Int16Array(floatSamples.length);

        for (let i = 0; i < floatSamples.length; i++) {
            // Clamp to [-1, 1] range
            const sample = Math.max(-1, Math.min(1, floatSamples[i]));

            // Convert to 16-bit integer
            int16Array[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
        }

        return int16Array;
    }

    /**
     * Convert ArrayBuffer to base64 string
     */
    arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';

        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }

        return btoa(binary);
    }

    /**
     * Get analyser node for visualization
     */
    getAnalyser() {
        return this.analyserNode;
    }

    /**
     * Clean up resources
     */
    cleanup() {
        this.stop();

        if (this.processorNode) {
            this.processorNode.disconnect();
            this.processorNode = null;
        }

        if (this.analyserNode) {
            this.analyserNode.disconnect();
            this.analyserNode = null;
        }

        if (this.sourceNode) {
            this.sourceNode.disconnect();
            this.sourceNode = null;
        }

        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }

        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }

        console.log('Audio capture cleaned up');
    }
}

// Global audio capture instance
let audioCapture;
let isListening = false;

// Initialize control button
document.addEventListener('DOMContentLoaded', () => {
    audioCapture = new AudioCapture();

    const controlBtn = document.getElementById('controlBtn');

    controlBtn.addEventListener('click', async () => {
        if (!configManager || !configManager.isComplete()) {
            updateStatus('Please configure API keys first');
            return;
        }

        if (!isListening) {
            // Start listening
            updateStatus('Connecting...');

            try {
                // Connect WebSocket first
                if (!wsClient.isConnected()) {
                    await wsClient.connect(configManager.getConfig());
                }

                // Start audio capture
                const started = await audioCapture.start();

                if (started) {
                    isListening = true;
                    controlBtn.classList.add('active');
                    controlBtn.querySelector('.text').textContent = 'STOP';

                    // Start visualizer if available
                    if (typeof visualizer !== 'undefined') {
                        visualizer.start(audioCapture.getAnalyser());
                    }
                }

            } catch (error) {
                console.error('Error starting:', error);
                updateStatus('Connection failed');
            }

        } else {
            // Stop listening
            audioCapture.stop();
            isListening = false;
            controlBtn.classList.remove('active');
            controlBtn.querySelector('.text').textContent = 'START';

            // Stop visualizer if available
            if (typeof visualizer !== 'undefined') {
                visualizer.stop();
            }

            updateStatus('Ready');
        }
    });
});
