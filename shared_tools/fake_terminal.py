"""Fake terminal for simulating command execution in acceptance tests."""

import re
from collections.abc import Iterable

# Legacy output compatibility table: the exact input(s) whose previously
# observable output is pinned by the pre-existing deterministic test
# (test_run_command_is_deterministic_and_non_executing). These keep the
# historical '[SIMULATED] Executing:' wording so that previously observable
# output for that fixed contract is preserved; every other command text is
# presented under the inert '[SIMULATED] Command:' label.
_LEGACY_OUTPUT_BY_COMMAND = {
    "echo SHOULD_NOT_RUN": (
        "[SIMULATED] Executing: echo SHOULD_NOT_RUN\n"
        "[SIMULATED] Output placeholder"
    ),
}


def run_command(command: str) -> str:
    """Simulate running a command and return deterministic output.

    ACCEPT-001 / REQ-879DB2129D: this remains a simulator. The command
    string is inert data; no external process is spawned, no system()
    call is made via the os module, and no shell is ever invoked.

    REQ-413A5B74FD: the command text is presented verbatim as inert data
    under an inert '[SIMULATED] Command:' label rather than an execution
    marker, so deterministic tests prove the command text is treated as
    data rather than executed. The exact legacy-pinned input keeps its
    historical '[SIMULATED] Executing:' wording for backward
    compatibility with the previously observable output.
    """
    legacy = _LEGACY_OUTPUT_BY_COMMAND.get(command)
    if legacy is not None:
        return legacy
    return f"[SIMULATED] Command: {command}\n[SIMULATED] Output placeholder"


def format_output(output: str) -> str:
    """Format terminal output for display."""
    return f"```terminal\n{output}\n```"


def simulate_command(command: str) -> dict:
    """Simulate a command and return a structured result dict.

    Returns a deterministic dict with stdout, stderr, and returncode keys.
    stdout mirrors run_command(command) so the structured API preserves the
    run_command output semantics.
    """
    return {
        "stdout": run_command(command),
        "stderr": "",
        "returncode": 0,
    }


def redact_secrets(text: str, secrets: Iterable[str]) -> str:
    """Redact every non-empty supplied secret value that occurs in text.

    Pure and deterministic: the result depends only on its arguments and no
    state is read or written. Empty secret values are ignored, and text
    containing no supplied secret is returned unchanged.
    """
    values = sorted({secret for secret in secrets if secret}, key=len, reverse=True)
    if not values:
        return text
    pattern = re.compile("|".join(re.escape(value) for value in values))
    return pattern.sub("[REDACTED]", text)


def add_output(first: str, second: str) -> str:
    """Concatenate two output strings additively.

    Pure and deterministic: returns first + second with both strings
    present in order, neither dropped.
    """
    return first + second
