"""CLI output utilities that respect verbose/quiet modes."""

from __future__ import annotations

import os
from typing import Optional


def is_verbose() -> bool:
    """Check if verbose mode is enabled."""
    return os.getenv('VOICEBRIDGE_VERBOSE', '0') == '1'


def is_quiet() -> bool:
    """Check if quiet mode is enabled."""
    return os.getenv('VOICEBRIDGE_QUIET', '0') == '1'


def print_info(message: str, prefix: Optional[str] = None) -> None:
    """Print informational message (respects quiet mode).

    Args:
        message: Message to print
        prefix: Optional prefix (e.g., "[STT]")
    """
    if is_quiet():
        return

    if prefix:
        print(f"{prefix} {message}")
    else:
        print(message)


def print_verbose(message: str, prefix: Optional[str] = None) -> None:
    """Print verbose message (only in verbose mode).

    Args:
        message: Message to print
        prefix: Optional prefix (e.g., "[DEBUG]")
    """
    if not is_verbose():
        return

    if prefix:
        print(f"{prefix} {message}")
    else:
        print(message)


def print_error(message: str, prefix: Optional[str] = None) -> None:
    """Print error message (always shown).

    Args:
        message: Message to print
        prefix: Optional prefix (e.g., "[ERROR]")
    """
    if prefix:
        print(f"{prefix} {message}")
    else:
        print(message)


def print_success(message: str, prefix: Optional[str] = None) -> None:
    """Print success message (respects quiet mode).

    Args:
        message: Message to print
        prefix: Optional prefix (e.g., "[OK]")
    """
    if is_quiet():
        return

    if prefix:
        print(f"{prefix} {message}")
    else:
        print(message)
