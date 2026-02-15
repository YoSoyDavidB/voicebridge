"""Configuration profile management for VoiceBridge.

Allows easy switching between testing mode and Teams/Zoom mode.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import click


def get_env_path() -> Path:
    """Get the path to the .env file."""
    # Try to find .env in current directory or parent directories
    current = Path.cwd()
    for _ in range(5):  # Search up to 5 levels up
        env_path = current / ".env"
        if env_path.exists():
            return env_path
        current = current.parent

    # Default to current directory
    return Path.cwd() / ".env"


def read_env() -> dict[str, str]:
    """Read current .env file into a dictionary."""
    env_path = get_env_path()
    if not env_path.exists():
        return {}

    env_vars = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key] = value

    return env_vars


def write_env(env_vars: dict[str, str]) -> None:
    """Write environment variables to .env file."""
    env_path = get_env_path()

    # Read the original file to preserve comments and structure
    lines = []
    if env_path.exists():
        with open(env_path) as f:
            lines = f.readlines()

    # Update or add the configuration values
    updated_lines = []
    updated_keys = set()

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0]
            if key in env_vars:
                updated_lines.append(f"{key}={env_vars[key]}\n")
                updated_keys.add(key)
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)

    # Add any keys that weren't in the original file
    for key, value in env_vars.items():
        if key not in updated_keys:
            updated_lines.append(f"{key}={value}\n")

    # Write back
    with open(env_path, "w") as f:
        f.writelines(updated_lines)


def apply_profile(profile: str, output_device_id: Optional[int] = None) -> None:
    """Apply a configuration profile.

    Args:
        profile: Either 'testing' or 'teams'
        output_device_id: Optional device ID for virtual audio device (Teams mode)
    """
    env_vars = read_env()

    if profile == "testing":
        # Testing mode: hear translations locally
        env_vars["AUDIO_OUTPUT_DEVICE_ID"] = ""
        env_vars["AUDIO_OUTPUT_ENABLED"] = "true"
        click.echo(click.style("✓ Testing mode activated", fg="green"))
        click.echo("  - Audio output: Default speakers")
        click.echo("  - You will hear translations")

    elif profile == "teams":
        # Teams mode: silent, send to virtual device
        if output_device_id is not None:
            env_vars["AUDIO_OUTPUT_DEVICE_ID"] = str(output_device_id)
        elif "AUDIO_OUTPUT_DEVICE_ID" not in env_vars or not env_vars["AUDIO_OUTPUT_DEVICE_ID"]:
            click.echo(click.style("⚠ Warning: No virtual device configured", fg="yellow"))
            click.echo("Run 'voicebridge devices' to find your virtual device ID")
            click.echo("Then run: voicebridge profile teams --device <ID>")
            return

        env_vars["AUDIO_OUTPUT_ENABLED"] = "false"
        click.echo(click.style("✓ Teams/Zoom mode activated", fg="green"))
        click.echo(f"  - Audio output: Device {env_vars['AUDIO_OUTPUT_DEVICE_ID']}")
        click.echo("  - Silent mode: You won't hear translation")
        click.echo("  - Teams/Zoom will capture audio from virtual device")

    else:
        click.echo(click.style(f"✗ Unknown profile: {profile}", fg="red"))
        click.echo("Available profiles: testing, teams")
        return

    write_env(env_vars)
    click.echo(f"\n.env file updated at: {get_env_path()}")


def show_current_profile() -> None:
    """Display the current configuration profile."""
    env_vars = read_env()

    output_enabled = env_vars.get("AUDIO_OUTPUT_ENABLED", "true").lower() == "true"
    output_device = env_vars.get("AUDIO_OUTPUT_DEVICE_ID", "")

    click.echo("\n" + "=" * 70)
    click.echo(click.style("CURRENT CONFIGURATION", fg="cyan", bold=True))
    click.echo("=" * 70 + "\n")

    if output_enabled and not output_device:
        click.echo(click.style("Profile: TESTING MODE", fg="green", bold=True))
        click.echo("  - Output device: Default speakers")
        click.echo("  - Audio playback: Enabled")
        click.echo("  - You will hear translations")
    elif not output_enabled and output_device:
        click.echo(click.style("Profile: TEAMS/ZOOM MODE", fg="blue", bold=True))
        click.echo(f"  - Output device: {output_device}")
        click.echo("  - Audio playback: Disabled (silent)")
        click.echo("  - Teams/Zoom captures from virtual device")
    else:
        click.echo(click.style("Profile: CUSTOM", fg="yellow", bold=True))
        click.echo(f"  - Output device: {output_device or 'default'}")
        click.echo(f"  - Audio playback: {'Enabled' if output_enabled else 'Disabled'}")

    click.echo("\nConfiguration file: " + str(get_env_path()))
    click.echo("\n" + "=" * 70 + "\n")
