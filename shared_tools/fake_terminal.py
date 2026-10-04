"""Fake terminal for simulating command execution in acceptance tests."""


def run_command(command: str) -> str:
    """Simulate running a command and return deterministic output."""
    return f"[SIMULATED] Executing: {command}\n[SIMULATED] Output placeholder"


def simulate_command(command: str) -> dict:
    """Return a deterministic structured simulation of a command."""
    return {
        "command": command,
        "simulated": True,
        "output": run_command(command),
    }


def format_output(output: str) -> str:
    """Format terminal output for display."""
    return f"```terminal\n{output}\n```"
