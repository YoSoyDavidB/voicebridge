/**
 * WebSocket client for bidirectional communication with backend
 */

class WebSocketClient {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectDelay = 8000; // 8 seconds max
        this.reconnectTimer = null;
        this.isIntentionallyClosed = false;
        this.onStatusChange = null;
        this.onError = null;
    }

    /**
     * Connect to WebSocket server
     */
    connect(config) {
        return new Promise((resolve, reject) => {
            try {
                this.isIntentionallyClosed = false;
                const wsUrl = `ws://${window.location.host}/ws`;
                console.log('Connecting to WebSocket:', wsUrl);

                this.ws = new WebSocket(wsUrl);

                this.ws.onopen = () => {
                    console.log('WebSocket connected');
                    this.reconnectAttempts = 0;

                    // Send configuration message
                    this.sendConfig(config);

                    if (this.onStatusChange) {
                        this.onStatusChange('connected');
                    }

                    resolve();
                };

                this.ws.onmessage = (event) => {
                    this.handleMessage(event.data);
                };

                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    if (this.onError) {
                        this.onError('Connection error');
                    }
                    reject(error);
                };

                this.ws.onclose = () => {
                    console.log('WebSocket disconnected');

                    if (this.onStatusChange) {
                        this.onStatusChange('disconnected');
                    }

                    // Auto-reconnect if not intentionally closed
                    if (!this.isIntentionallyClosed) {
                        this.scheduleReconnect(config);
                    }
                };

            } catch (error) {
                console.error('Failed to create WebSocket:', error);
                reject(error);
            }
        });
    }

    /**
     * Send configuration to server
     */
    sendConfig(config) {
        const message = {
            type: 'config',
            apiKeys: {
                deepgram: config.deepgram,
                openai: config.openai,
                elevenlabs: config.elevenlabs
            },
            voiceId: config.voiceId
        };

        this.send(message);
    }

    /**
     * Send audio chunk to server
     */
    sendAudio(audioBase64) {
        const message = {
            type: 'audio',
            audio: audioBase64,
            timestamp: Date.now()
        };

        this.send(message);
    }

    /**
     * Send message to server
     */
    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket not connected, cannot send message');
        }
    }

    /**
     * Handle incoming message from server
     */
    handleMessage(data) {
        try {
            const message = JSON.parse(data);

            switch (message.type) {
                case 'status':
                    console.log('Status:', message.message);
                    if (this.onStatusChange) {
                        this.onStatusChange(message.message);
                    }
                    updateStatus(message.message);
                    break;

                case 'error':
                    console.error('Server error:', message.message);
                    if (this.onError) {
                        this.onError(message.message);
                    }
                    updateStatus(`Error: ${message.message}`);
                    break;

                case 'audio':
                    // Handle audio response from server
                    console.log('Received audio from server');
                    this.playAudio(message.data);
                    break;

                default:
                    console.warn('Unknown message type:', message.type);
            }
        } catch (error) {
            console.error('Error handling message:', error);
        }
    }

    /**
     * Play audio received from server
     */
    playAudio(audioBase64) {
        try {
            // Convert base64 to audio blob
            const audioData = atob(audioBase64);
            const arrayBuffer = new ArrayBuffer(audioData.length);
            const view = new Uint8Array(arrayBuffer);

            for (let i = 0; i < audioData.length; i++) {
                view[i] = audioData.charCodeAt(i);
            }

            const blob = new Blob([arrayBuffer], { type: 'audio/mpeg' });
            const url = URL.createObjectURL(blob);

            const audio = new Audio(url);
            audio.play();

            // Clean up URL after playback
            audio.onended = () => {
                URL.revokeObjectURL(url);
            };

        } catch (error) {
            console.error('Error playing audio:', error);
        }
    }

    /**
     * Schedule reconnection with exponential backoff
     */
    scheduleReconnect(config) {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
        }

        // Calculate delay: 1s, 2s, 4s, 8s max
        const delay = Math.min(
            1000 * Math.pow(2, this.reconnectAttempts),
            this.maxReconnectDelay
        );

        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts + 1})`);

        this.reconnectTimer = setTimeout(() => {
            this.reconnectAttempts++;
            this.connect(config).catch(err => {
                console.error('Reconnection failed:', err);
            });
        }, delay);
    }

    /**
     * Close WebSocket connection
     */
    close() {
        this.isIntentionallyClosed = true;

        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }

        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    /**
     * Check if connected
     */
    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }
}

// Global WebSocket client instance
let wsClient;

// Initialize WebSocket client on page load
document.addEventListener('DOMContentLoaded', () => {
    wsClient = new WebSocketClient();

    // Set up status change handler
    wsClient.onStatusChange = (status) => {
        console.log('WebSocket status changed:', status);
    };

    // Set up error handler
    wsClient.onError = (error) => {
        console.error('WebSocket error:', error);
    };
});
