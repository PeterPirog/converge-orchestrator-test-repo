"""Fake terminal for simulating command execution in acceptance tests."""


def run_command(command: str) -> str:
    """Simulate running a command and return deterministic output."""
    return f"[SIMULATED] Executing: {command}\n[SIMULATED] Output placeholder"


def format_output(output: str) -> str:
    """Format terminal output for display."""
    return f"```terminal\n{output}\n```"


def add_output(first: str, second: str) -> str:
    """Concatenate two output strings additively.

    ACCEPT-001 / REQ-F92FFC55BA: additive structured command simulation.
    Returns first + second with both strings present in order, neither
    dropped. Pure and deterministic: the result depends only on its
    arguments and no state is read or written.
    """
    return first + second
