"""Fake terminal for simulating command execution in acceptance tests.

REQ-0C50BE10F3 (ACCEPT-001 — Structured command simulation): the structured
command-simulation contract is an exact mirror of this module's plain-text
simulator. Any structured representation of a simulated command execution
must carry a stdout field that is a byte-for-byte mirror of the string
returned by ``run_command(command: str) -> str`` for the same command —
identical bytes, order, and length, with no reformatting, normalization,
truncation, or added context. ``run_command`` never delegates to any other
operating-system command execution API; it only returns deterministic
simulated text, and that exact text is what structured simulations must
reproduce.
"""


def run_command(command: str) -> str:
    """Simulate running a command and return deterministic output."""
    return f"[SIMULATED] Executing: {command}\n[SIMULATED] Output placeholder"


def format_output(output: str) -> str:
    """Format terminal output for display."""
    return f"```terminal\n{output}\n```"


def get_simulation_info() -> dict:
    """Return static metadata describing the fake terminal simulator."""
    return {
        "simulator": "fake_terminal",
        "executes_commands": False,
        "deterministic": True,
    }


REDACTED_MARKER = "***REDACTED***"


def redact_secrets(text: str, secrets: list) -> str:
    """Redact supplied secret values from text for training logs.

    REQ-85C52948B7 (ACCEPT-002 — Deterministic secret redaction helper): a
    pure, deterministic helper. Every non-empty supplied secret value that
    occurs in ``text`` is replaced with the redaction marker
    ``***REDACTED***``. Empty supplied values are ignored, text that
    contains no supplied secret value is returned unchanged, and identical
    inputs always produce identical output.
    """
    ordered = sorted(
        {secret for secret in secrets if secret},
        key=lambda secret: (-len(secret), secret),
    )
    result = text
    for secret in ordered:
        result = result.replace(secret, REDACTED_MARKER)
    return result
