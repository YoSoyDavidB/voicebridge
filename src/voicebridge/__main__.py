"""VoiceBridge CLI - Real-time Spanish to English voice interpreter.

Usage:
    python -m voicebridge              # Run with .env configuration
    python -m voicebridge --help       # Show help
    python -m voicebridge devices      # List audio devices
    python -m voicebridge check        # Check configuration
"""

from __future__ import annotations

import asyncio
import sys

import click

from voicebridge.config.settings import VoiceBridgeSettings
from voicebridge.core.pipeline import PipelineOrchestrator


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """VoiceBridge - Real-time Spanish to English voice interpreter."""
    if ctx.invoked_subcommand is None:
        asyncio.run(run_pipeline())


@cli.command()
def devices() -> None:
    """List available audio devices."""
    import sounddevice as sd

    click.echo("\n" + "=" * 70)
    click.echo("AVAILABLE AUDIO DEVICES")
    click.echo("=" * 70 + "\n")

    devices_list = sd.query_devices()
    if isinstance(devices_list, dict):
        devices_list = [devices_list]

    click.echo(click.style("INPUT DEVICES:", fg="cyan", bold=True))
    for idx, device in enumerate(devices_list):
        if device["max_input_channels"] > 0:
            default = " [DEFAULT]" if idx == sd.default.device[0] else ""
            click.echo(f"  {idx}: {device['name']}{default}")

    click.echo("\n" + click.style("OUTPUT DEVICES:", fg="cyan", bold=True))
    for idx, device in enumerate(devices_list):
        if device["max_output_channels"] > 0:
            default = " [DEFAULT]" if idx == sd.default.device[1] else ""
            click.echo(f"  {idx}: {device['name']}{default}")

    click.echo("\n" + "=" * 70 + "\n")


@cli.command()
def check() -> None:
    """Check configuration."""
    click.echo("\n" + "=" * 70)
    click.echo("CONFIGURATION CHECK")
    click.echo("=" * 70 + "\n")

    try:
        settings = VoiceBridgeSettings()
        click.echo(click.style("✓ Configuration loaded successfully!", fg="green"))
        click.echo(f"\nDeepgram API Key: {settings.deepgram_api_key[:4]}...{settings.deepgram_api_key[-4:]}")
        click.echo(f"OpenAI API Key:   {settings.openai_api_key[:4]}...{settings.openai_api_key[-4:]}")
        click.echo(f"ElevenLabs Key:   {settings.elevenlabs_api_key[:4]}...{settings.elevenlabs_api_key[-4:]}")
        click.echo(f"Voice ID:         {settings.elevenlabs_voice_id}")
        click.echo("\n" + "=" * 70 + "\n")
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        click.echo("\nMake sure you have a .env file with your API keys.")
        click.echo("See .env.example for a template.\n")
        sys.exit(1)


async def run_pipeline() -> None:
    """Run the pipeline."""
    click.echo("\n" + "=" * 70)
    click.echo(click.style("VOICEBRIDGE", fg="cyan", bold=True))
    click.echo("=" * 70 + "\n")

    try:
        click.echo("Loading configuration...")
        settings = VoiceBridgeSettings()
        click.echo(click.style("✓ Configuration loaded", fg="green"))

        click.echo("Creating pipeline...")
        click.echo("  - Initializing components...")
        click.echo("  - Loading VAD model (this may take a moment on first run)...")
        pipeline = PipelineOrchestrator(settings=settings)
        click.echo(click.style("✓ Pipeline created", fg="green"))

        click.echo(click.style("\nPIPELINE ACTIVE - Speak in Spanish...", fg="green", bold=True))
        click.echo("Press Ctrl+C to stop\n")

        await pipeline.start()

    except KeyboardInterrupt:
        click.echo(click.style("\nStopping...", fg="yellow"))
        if "pipeline" in locals():
            await pipeline.stop()
        click.echo(click.style("✓ Stopped", fg="green"))
    except Exception as e:
        click.echo(click.style(f"\n✗ Error: {e}", fg="red"))
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
