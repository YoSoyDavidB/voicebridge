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

// Global config manager instance
let configManager;

// Initialize settings panel functionality
document.addEventListener('DOMContentLoaded', () => {
    configManager = new ConfigManager();
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
