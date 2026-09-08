"""Fake terminal for simulating command execution in acceptance tests."""


def run_command(command: str) -> str:
    """Simulate running a command and return deterministic output."""
    return f"[SIMULATED] Executing: {command}\n[SIMULATED] Output placeholder"


def format_output(output: str) -> str:
    """Format terminal output for display."""
    return f"```terminal\n{output}\n```"


def simulate_command(command: str) -> dict:
    """Simulate a command and return a structured result dict.

    Returns a deterministic dict with stdout, stderr, and returncode keys.
    """
    return {
        "stdout": f"[SIMULATED] Output for: {command}\n",
        "stderr": "",
        "returncode": 0,
    }
