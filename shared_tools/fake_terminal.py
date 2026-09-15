"""Fake terminal for simulating command execution in acceptance tests."""


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
