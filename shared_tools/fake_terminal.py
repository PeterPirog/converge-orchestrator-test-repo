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
