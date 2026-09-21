"""Fake terminal for simulating command execution in acceptance tests."""


def run_command(command: str) -> str:
    """Simulate running a command and return deterministic output."""
    return f"[SIMULATED] Executing: {command}\n[SIMULATED] Output placeholder"


def format_output(output: str) -> str:
    """Format terminal output for display."""
    return f"```terminal\n{output}\n```"


def simulate_command(command: str) -> dict:
    """Simulate running a command and return a structured result.

    This is an additive, pure and deterministic function. It performs no real
    command execution and simply reports the simulated run as a structured dict.
    """
    return {
        "command": command,
        "exit_code": 0,
        "simulated": True,
        "stdout": run_command(command),
    }


def redact_secrets(text: str, secrets: list) -> str:
    """Replace every non-empty supplied secret occurring in ``text`` with ``[REDACTED]``.

    A pure, deterministic helper for redacting secrets from training logs.
    Empty-string supplied secrets are ignored and never used as replacement
    targets; text containing none of the supplied secrets is returned
    unchanged; and repeated calls with identical input return identical output.
    The processing order is canonicalized (longest secret first, then value)
    so overlapping secrets redact identically regardless of the supplied
    iteration order.
    """
    ordered = sorted((secret for secret in secrets if secret),
                     key=lambda secret: (-len(secret), secret))
    for secret in ordered:
        text = text.replace(secret, "[REDACTED]")
    return text
