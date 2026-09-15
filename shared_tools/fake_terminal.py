"""Fake terminal for simulating command execution in acceptance tests."""

from collections.abc import Iterable


def run_command(command: str) -> str:
    """Simulate running a command and return deterministic output."""
    return f"[SIMULATED] Executing: {command}\n[SIMULATED] Output placeholder"


def simulate_command(command: str) -> dict:
    """Simulate running a command and return a structured result.

    The stdout field is a byte-for-byte mirror of run_command(command).
    No real OS command execution is performed.
    """
    return {
        "stdout": run_command(command),
        "stderr": "",
        "returncode": 0,
    }


def format_output(output: str) -> str:
    """Format terminal output for display."""
    return f"```terminal\n{output}\n```"


def add_output(first: str, second: str) -> str:
    """Return the additive concatenation of two output strings."""
    return first + second


def redact_secrets(text: str, secrets: Iterable[str]) -> str:
    """Redact every non-empty supplied secret value occurring in text.

    REQ-85C52948B7: pure helper for training logs. No I/O and no command
    execution. Empty supplied values are ignored, supplied secrets that do
    not occur in the text leave no trace, and identical inputs always
    produce identical output (deterministic).

    Redaction order is normalized to a deterministic sequence independent of
    the supplied collection's iteration order: longer secrets are replaced
    first, with ties broken lexicographically, so overlapping secrets are
    handled deterministically.
    """
    ordered = sorted(
        {str(secret) for secret in secrets if secret},
        key=lambda value: (-len(value), value),
    )
    redacted = text
    for value in ordered:
        redacted = redacted.replace(value, "[REDACTED]")
    return redacted
