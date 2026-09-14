"""Fake terminal for simulating command execution in acceptance tests."""


def run_command(command: str) -> str:
    """Simulate running a command and return deterministic output."""
    return f"[SIMULATED] Executing: {command}\n[SIMULATED] Output placeholder"


def format_output(output: str) -> str:
    """Format terminal output for display."""
    return f"```terminal\n{output}\n```"


def get_simulation_info() -> dict:
    """Return deterministic metadata describing this fake terminal simulator.

    Additive public API: reports that the module simulates (never executes)
    commands and produces stable, deterministic output.
    """
    return {
        "simulator": "fake_terminal",
        "executes_commands": False,
        "deterministic": True,
    }
