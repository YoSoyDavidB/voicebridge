/**
 * Canvas-based waveform visualization
 */

class Visualizer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.analyser = null;
        this.dataArray = null;
        this.bufferLength = 0;
        this.isRunning = false;
        this.animationId = null;

        // Set canvas size
        this.resize();

        // Handle window resize
        window.addEventListener('resize', () => this.resize());
    }

    /**
     * Resize canvas to match display size
     */
    resize() {
        const rect = this.canvas.getBoundingClientRect();
        this.canvas.width = rect.width * window.devicePixelRatio;
        this.canvas.height = rect.height * window.devicePixelRatio;
        this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    }

    /**
     * Start visualization
     */
    start(analyser) {
        if (!analyser) {
            console.error('No analyser node provided');
            return;
        }

        this.analyser = analyser;
        this.bufferLength = analyser.frequencyBinCount;
        this.dataArray = new Uint8Array(this.bufferLength);
        this.isRunning = true;

        console.log('Visualizer started');
        this.draw();
    }

    /**
     * Stop visualization
     */
    stop() {
        this.isRunning = false;

        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }

        // Clear canvas
        this.clear();

        console.log('Visualizer stopped');
    }

    /**
     * Clear canvas
     */
    clear() {
        const rect = this.canvas.getBoundingClientRect();
        this.ctx.fillStyle = '#0a0a0a';
        this.ctx.fillRect(0, 0, rect.width, rect.height);
    }

    /**
     * Draw waveform
     */
    draw() {
        if (!this.isRunning) {
            return;
        }

        // Schedule next frame
        this.animationId = requestAnimationFrame(() => this.draw());

        // Get waveform data from analyser
        this.analyser.getByteTimeDomainData(this.dataArray);

        const rect = this.canvas.getBoundingClientRect();
        const width = rect.width;
        const height = rect.height;

        // Clear canvas with dark background
        this.ctx.fillStyle = '#0a0a0a';
        this.ctx.fillRect(0, 0, width, height);

        // Set up waveform drawing
        this.ctx.lineWidth = 2;
        this.ctx.strokeStyle = this.createGradient(width, height);
        this.ctx.shadowBlur = 10;
        this.ctx.shadowColor = '#00ffff';

        this.ctx.beginPath();

        const sliceWidth = width / this.bufferLength;
        let x = 0;

        for (let i = 0; i < this.bufferLength; i++) {
            // Normalize data from [0, 255] to [-1, 1]
            const v = this.dataArray[i] / 128.0;
            const y = (v * height) / 2;

            if (i === 0) {
                this.ctx.moveTo(x, y);
            } else {
                this.ctx.lineTo(x, y);
            }

            x += sliceWidth;
        }

        this.ctx.lineTo(width, height / 2);
        this.ctx.stroke();

        // Reset shadow for next frame
        this.ctx.shadowBlur = 0;
    }

    /**
     * Create cyan to green gradient for futuristic look
     */
    createGradient(width, height) {
        const gradient = this.ctx.createLinearGradient(0, 0, width, 0);
        gradient.addColorStop(0, '#00ffff');    // Cyan
        gradient.addColorStop(0.5, '#00ff88');  // Cyan-green
        gradient.addColorStop(1, '#00ff00');    // Green
        return gradient;
    }
}

// Global visualizer instance
let visualizer;

// Initialize visualizer on page load
document.addEventListener('DOMContentLoaded', () => {
    visualizer = new Visualizer('visualizer');
    console.log('Visualizer initialized');
});
