#!/bin/bash
# VoiceBridge helper script
# Makes it easier to run commands without typing python3 -m voicebridge

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Run voicebridge with all arguments
python3 -m voicebridge "$@"
