#!/usr/bin/env python3
"""List all available audio devices for input and output configuration.

This script helps you find the correct device IDs for your .env configuration.
"""

from __future__ import annotations

import sounddevice as sd


def list_audio_devices() -> None:
    """List all audio devices with their IDs and capabilities."""
    print("=" * 80)
    print("VOICEBRIDGE - Audio Device Configuration Helper")
    print("=" * 80)
    print()

    devices = sd.query_devices()
    default_input = sd.default.device[0]
    default_output = sd.default.device[1]

    print(f"System Default Input:  {default_input}")
    print(f"System Default Output: {default_output}")
    print()
    print("=" * 80)
    print("AVAILABLE AUDIO DEVICES")
    print("=" * 80)
    print()

    # Group devices by type
    input_devices = []
    output_devices = []

    for i, device in enumerate(devices):
        if device["max_input_channels"] > 0:
            input_devices.append((i, device))
        if device["max_output_channels"] > 0:
            output_devices.append((i, device))

    # Display input devices
    print("🎤 INPUT DEVICES (Microphones)")
    print("-" * 80)
    for device_id, device in input_devices:
        is_default = " [DEFAULT]" if device_id == default_input else ""
        print(f"ID {device_id}: {device['name']}{is_default}")
        print(f"       Channels: {device['max_input_channels']}")
        print(f"       Sample Rate: {int(device['default_samplerate'])} Hz")
        print()

    # Display output devices
    print("🔊 OUTPUT DEVICES (Speakers/Virtual Devices)")
    print("-" * 80)
    for device_id, device in output_devices:
        is_default = " [DEFAULT]" if device_id == default_output else ""
        is_virtual = ""

        # Detect virtual audio devices
        name_lower = device['name'].lower()
        if 'blackhole' in name_lower:
            is_virtual = " [VIRTUAL - macOS]"
        elif 'vb-cable' in name_lower or 'vb-audio' in name_lower:
            is_virtual = " [VIRTUAL - Windows]"
        elif 'soundflower' in name_lower:
            is_virtual = " [VIRTUAL - macOS]"

        print(f"ID {device_id}: {device['name']}{is_default}{is_virtual}")
        print(f"       Channels: {device['max_output_channels']}")
        print(f"       Sample Rate: {int(device['default_samplerate'])} Hz")
        print()

    print("=" * 80)
    print("CONFIGURATION GUIDE")
    print("=" * 80)
    print()
    print("For normal usage (hear translations locally):")
    print("  AUDIO_INPUT_DEVICE_ID=<your_microphone_id>")
    print("  AUDIO_OUTPUT_DEVICE_ID=<your_speakers_id>")
    print()
    print("For Teams/Zoom usage (send to virtual device):")
    print("  AUDIO_INPUT_DEVICE_ID=<your_microphone_id>")
    print("  AUDIO_OUTPUT_DEVICE_ID=<virtual_device_id>  # BlackHole or VB-CABLE")
    print()
    print("Then in Teams/Zoom, select the virtual device as your microphone.")
    print()
    print("=" * 80)
    print("VIRTUAL DEVICE INSTALLATION")
    print("=" * 80)
    print()
    print("macOS:")
    print("  brew install blackhole-2ch")
    print("  # After install, run this script again to see BlackHole")
    print()
    print("Windows:")
    print("  Download VB-CABLE from: https://vb-audio.com/Cable/")
    print("  # After install, run this script again to see CABLE Input/Output")
    print()


if __name__ == "__main__":
    try:
        list_audio_devices()
    except Exception as e:
        print(f"Error listing devices: {e}")
        import traceback
        traceback.print_exc()
