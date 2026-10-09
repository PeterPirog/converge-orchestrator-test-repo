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


def summarize_simulation(simulation: dict) -> dict:
    """Return a deterministic, fixed-structure summary of a simulation."""
    return {
        "command": simulation["command"],
        "simulated": True,
        "summary": f"[SUMMARY] {simulation['command']}",
    }


def format_output(output: str) -> str:
    """Format terminal output for display."""
    return f"```terminal\n{output}\n```"


def redact_secrets(text: str, secrets) -> str:
    """Return ``text`` with every non-empty secret value replaced by '[REDACTED]'.

    Empty strings and ``None`` entries in ``secrets`` are ignored. The
    replacement is performed in-process using only string operations so the
    result is deterministic for identical inputs.
    """
    ordered = sorted(
        (secret for secret in secrets if secret),
        key=lambda secret: (-len(secret), secret),
    )
    for secret in ordered:
        text = text.replace(secret, "[REDACTED]")
    return text
