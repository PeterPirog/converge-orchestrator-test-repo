"""Fake terminal for simulating command execution in acceptance tests."""


def run_command(command: str) -> str:
    """Simulate running a command and return deterministic output."""
    return f"[SIMULATED] Executing: {command}\n[SIMULATED] Output placeholder"


def format_output(output: str) -> str:
    """Format terminal output for display."""
    return f"```terminal\n{output}\n```"
def simulate_command(command: str) -> dict: return {"stdout": run_command(command)}


def redact_secrets(text: str, secrets: list[str]) -> str:
    """Deterministically redact every non-empty secret occurrence in text."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    return text
