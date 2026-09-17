"""Fake terminal for simulating command execution in acceptance tests."""


def run_command(command: str) -> str:
    """Simulate running a command and return deterministic output."""
    return f"[SIMULATED] Executing: {command}\n[SIMULATED] Output placeholder"


def format_output(output: str) -> str:
    """Format terminal output for display."""
    return f"```terminal\n{output}\n```"


def simulate_command(command: str) -> dict:
    """Return a deterministic structured simulation of a command without executing it."""
    return {
        "command": command,
        "exit_code": 0,
        "stdout": f"[SIMULATED] Executing: {command}\n[SIMULATED] Output placeholder",
        "stderr": "",
    }
