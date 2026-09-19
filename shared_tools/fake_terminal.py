"""Fake terminal for simulating command execution in acceptance tests."""

from typing import Sequence


def run_command(command: str) -> str:
    """Simulate running a command and return deterministic output."""
    return f"[SIMULATED] Executing: {command}\n[SIMULATED] Output placeholder"


def format_output(output: str) -> str:
    """Format terminal output for display."""
    return f"```terminal\n{output}\n```"


def simulate_command(command: str) -> dict:
    """Simulate running a command and return a structured result without executing it."""
    return {
        "command": command,
        "exit_code": 0,
        "stdout": run_command(command),
        "stderr": "",
    }


def redact_secrets(text: str, secrets: Sequence[str]) -> str:
    """Replace every non-empty supplied secret occurring in ``text`` with ``[REDACTED]``.

    A pure, deterministic helper for training logs (REQ-85C52948B7 / ACCEPT-002):
    every non-empty supplied secret value that occurs in ``text`` is replaced by
    the literal ``[REDACTED]``; empty supplied values are ignored; non-occurring
    secrets leave no trace; and identical inputs always yield identical output.
    No I/O, no subprocess, no real command execution.
    """
    result = text
    for secret in secrets:
        if secret:
            result = result.replace(secret, "[REDACTED]")
    return result
