"""Fake terminal for simulating command execution in acceptance tests."""


def run_command(command: str) -> str:
    """Simulate running a command and return deterministic output."""
    return f"[SIMULATED] Executing: {command}\n[SIMULATED] Output placeholder"


def format_output(output: str) -> str:
    """Format terminal output for display."""
    return f"```terminal\n{output}\n```"


def add_output(first: str, second: str) -> str:
    """Return the additive concatenation of two output strings."""
    return first + second
