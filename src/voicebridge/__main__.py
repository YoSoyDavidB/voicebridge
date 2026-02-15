"""VoiceBridge CLI - Real-time Spanish to English voice interpreter.

Usage:
    python -m voicebridge              # Run with .env configuration
    python -m voicebridge web          # Start web interface
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
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--quiet", "-q", is_flag=True, help="Quiet mode (errors only)")
def cli(ctx: click.Context, verbose: bool, quiet: bool) -> None:
    """VoiceBridge - Real-time Spanish to English voice interpreter."""
    # Store verbosity level in context
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet

    # Set environment variable for other modules
    import os
    if verbose:
        os.environ['VOICEBRIDGE_VERBOSE'] = '1'
    if quiet:
        os.environ['VOICEBRIDGE_QUIET'] = '1'

    if ctx.invoked_subcommand is None:
        # Use run_cli() which has silent mode support
        from voicebridge.cli import run_cli
        asyncio.run(run_cli())


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


@cli.command(name="start")
def start_command() -> None:
    """Start VoiceBridge with current profile."""
    from voicebridge.cli import run_cli

    asyncio.run(run_cli())


@cli.command()
@click.argument("mode", type=click.Choice(["testing", "teams"]), required=False)
@click.option("--device", "-d", type=int, help="Virtual audio device ID (for teams mode)")
@click.option("--auto", is_flag=True, help="Auto-detect virtual device (teams mode)")
def profile(mode: str | None, device: int | None, auto: bool) -> None:
    """Manage configuration profiles.

    \b
    Modes:
      testing  - Hear translations locally (for testing)
      teams    - Silent mode with virtual device (for Teams/Zoom)

    \b
    Examples:
      voicebridge profile              # Show current profile
      voicebridge profile testing      # Switch to testing mode
      voicebridge profile teams --auto # Auto-detect virtual device
      voicebridge profile teams -d 5   # Switch to Teams mode with device 5
    """
    from voicebridge.utils.profiles import apply_profile, show_current_profile

    if mode is None:
        show_current_profile()
    else:
        apply_profile(mode, device, auto)


@cli.command()
def test() -> None:
    """Test VoiceBridge with a sample translation."""
    click.echo("\n" + "=" * 70)
    click.echo(click.style("VOICEBRIDGE TEST MODE", fg="cyan", bold=True))
    click.echo("=" * 70 + "\n")

    try:
        click.echo("Loading configuration...")
        from voicebridge.config.settings import VoiceBridgeSettings
        settings = VoiceBridgeSettings()
        click.echo(click.style("✓ Configuration loaded", fg="green"))

        click.echo("\nTesting translation service...")

        # Test phrase
        test_phrase_es = "Hola, esta es una prueba del sistema"

        click.echo(f"\n{click.style('→ Spanish:', fg='yellow')} {test_phrase_es}")

        import asyncio
        from voicebridge.services.translation.openai_client import OpenAITranslationClient

        async def test_translation():
            translator = OpenAITranslationClient(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
                temperature=settings.openai_temperature,
            )

            import time
            start = time.monotonic()
            translation = await translator._translate_text(test_phrase_es, start)
            latency = (time.monotonic() - start) * 1000

            if translation:
                click.echo(click.style(f"✓ Translation successful ({latency:.0f}ms)", fg="green"))
                click.echo(f"{click.style('→ English:', fg='yellow')} {translation.translated_text}")
                return True
            else:
                click.echo(click.style("✗ Translation failed", fg="red"))
                return False

        success = asyncio.run(test_translation())

        if success:
            click.echo("\n" + "=" * 70)
            click.echo(click.style("✓ TEST PASSED - VoiceBridge is ready!", fg="green", bold=True))
            click.echo("=" * 70)
            click.echo(click.style("\nNext steps:", fg="cyan"))
            click.echo("  1. voicebridge profile teams --auto  # Configure for Teams")
            click.echo("  2. voicebridge                        # Start translating")
        else:
            click.echo("\n" + "=" * 70)
            click.echo(click.style("✗ TEST FAILED", fg="red", bold=True))
            click.echo("=" * 70)
            click.echo("\nCheck your OpenAI API key in .env\n")
            sys.exit(1)

    except Exception as e:
        click.echo(click.style(f"\n✗ Error: {e}", fg="red"))
        click.echo("\nMake sure you have configured your .env file")
        sys.exit(1)


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
@click.option("--port", default=8000, help="Port to bind to (default: 8000)")
@click.option("--reload", is_flag=True, help="Enable auto-reload on code changes")
def web(host: str, port: int, reload: bool) -> None:
    """Start the web interface server."""
    import webbrowser
    from threading import Timer

    click.echo("\n" + "=" * 70)
    click.echo(click.style("VOICEBRIDGE WEB INTERFACE", fg="cyan", bold=True))
    click.echo("=" * 70 + "\n")

    click.echo(f"Starting server at http://{host}:{port}")
    click.echo(click.style("✓ Web interface ready", fg="green"))
    click.echo("\nConfigure API keys in the Settings panel (⚙️ button)")
    click.echo("Press Ctrl+C to stop\n")

    # Open browser after a short delay
    def open_browser():
        webbrowser.open(f"http://{host}:{port}")

    Timer(1.5, open_browser).start()

    # Start uvicorn server
    try:
        import uvicorn

        uvicorn.run(
            "voicebridge.web.app:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
        )
    except KeyboardInterrupt:
        click.echo(click.style("\n✓ Server stopped", fg="green"))
    except Exception as e:
        click.echo(click.style(f"\n✗ Error: {e}", fg="red"))
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
