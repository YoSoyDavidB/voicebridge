/**
 * WebSocket client for bidirectional communication with backend
 */

import { PCMPlayer } from "./pcm_player.js";

export class WebSocketClient {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectDelay = 8000; // 8 seconds max
        this.reconnectTimer = null;
        this.isIntentionallyClosed = false;
        this.onStatusChange = null;
        this.onError = null;
        this.isReady = false;
        this.readyResolve = null;
        this.pcmPlayer = new PCMPlayer({ sampleRate: 22050 });
    }

    /**
     * Connect to WebSocket server
     */
    connect(config) {
        return new Promise((resolve, reject) => {
            try {
                this.isIntentionallyClosed = false;
                this.isReady = false;
                const wsUrl = `ws://${window.location.host}/ws`;
                console.log('[WebSocket] Connecting to:', wsUrl);

                this.ws = new WebSocket(wsUrl);

                // Store resolve for when we receive "ready" status
                this.readyResolve = resolve;

                this.ws.onopen = () => {
                    console.log('[WebSocket] Connection opened');
                    this.reconnectAttempts = 0;

                    // Send configuration message
                    console.log('[WebSocket] Sending config...');
                    this.sendConfig(config);

                    if (this.onStatusChange) {
                        this.onStatusChange('connected');
                    }

                    // Don't resolve yet - wait for "ready" status
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

                this.ws.onclose = (event) => {
                    console.log(`[WebSocket] Connection closed: code=${event.code}, reason=${event.reason}, clean=${event.wasClean}`);

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

        console.log(`[WebSocket] Sending audio message: ${audioBase64.length} bytes`);
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
                    console.log('[WebSocket] Status:', message.state, '-', message.message);
                    if (this.onStatusChange) {
                        this.onStatusChange(message.message);
                    }
                    updateStatus(message.message);

                    // If we're ready and waiting for confirmation, resolve the connect promise
                    if (message.state === 'ready' && this.readyResolve) {
                        console.log('[WebSocket] System ready - resolving connect promise');
                        this.isReady = true;
                        this.readyResolve();
                        this.readyResolve = null;
                    }
                    break;

                case 'error':
                    console.error('[WebSocket] Server error:', message.message);
                    if (this.onError) {
                        this.onError(message.message);
                    }
                    updateStatus(`Error: ${message.message}`);
                    break;

                case 'audio':
                    // Handle audio response from server
                    console.log('[WebSocket] Received audio from server');
                    this.pcmPlayer.enqueue(message.data);
                    break;

                default:
                    console.warn('[WebSocket] Unknown message type:', message.type);
            }
        } catch (error) {
            console.error('[WebSocket] Error handling message:', error);
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
    globalThis.wsClient = wsClient;

    // Set up status change handler
    wsClient.onStatusChange = (status) => {
        console.log('WebSocket status changed:', status);
    };

    // Set up error handler
    wsClient.onError = (error) => {
        console.error('WebSocket error:', error);
    };
});
