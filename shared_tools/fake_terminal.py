"""Fake terminal for simulating command execution in acceptance tests."""

import re
from collections.abc import Iterable


def run_command(command: str) -> str:
    """Simulate running a command and return deterministic output."""
    return f"[SIMULATED] Executing: {command}\n[SIMULATED] Output placeholder"


def format_output(output: str) -> str:
    """Format terminal output for display."""
    return f"```terminal\n{output}\n```"


def simulate_command(command: str) -> dict:
    """Simulate a command and return a structured result dict.

    Returns a deterministic dict with stdout, stderr, and returncode keys.
    stdout mirrors run_command(command) so the structured API preserves the
    legacy output semantics.
    """
    return {
        "stdout": run_command(command),
        "stderr": "",
        "returncode": 0,
    }


def redact_secrets(text: str, secrets: Iterable[str]) -> str:
    """Redact every non-empty supplied secret value that occurs in text.

    Pure and deterministic: the result depends only on its arguments and no
    state is read or written. Empty secret values are ignored, and text
    containing no supplied secret is returned unchanged.
    """
    values = sorted({secret for secret in secrets if secret}, key=len, reverse=True)
    if not values:
        return text
    pattern = re.compile("|".join(re.escape(value) for value in values))
    return pattern.sub("[REDACTED]", text)


def add_output(first: str, second: str) -> str:
    """Concatenate two output strings additively.

    Pure and deterministic: returns first + second with both strings
    present in order, neither dropped.
    """
    return first + second
