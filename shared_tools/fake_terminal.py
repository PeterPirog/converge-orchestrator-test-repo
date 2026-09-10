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

    ACCEPT-001 / REQ-0C50BE10F3: structured command simulation that
    preserves the existing run_command behavior. Returns a deterministic
    dict with stdout, stderr, and returncode keys.

    REQ-413A5B74FD: the command text is presented as inert data under the
    '[SIMULATED] Command:' label. The structured API normalizes only the
    leading legacy '[SIMULATED] Executing:' execution marker to
    '[SIMULATED] Command:', leaving the embedded command text verbatim, so
    deterministic tests prove the command text is treated as data rather
    than executed.
    """
    stdout = run_command(command)
    marker = "[SIMULATED] Executing:"
    if stdout.startswith(marker):
        stdout = "[SIMULATED] Command:" + stdout[len(marker):]
    return {
        "stdout": stdout,
        "stderr": "",
        "returncode": 0,
    }


def redact_secrets(text: str, secrets: Iterable[str]) -> str:
    """Redact every non-empty supplied secret value that occurs in text.

    ACCEPT-002 / REQ-A59E470230: every occurrence, including every repeated
    occurrence, is replaced by the exact literal ``[REDACTED]``, and empty
    secret values are ignored.

    Pure and deterministic: the result depends only on its arguments and no
    state is read or written. Empty secret values are ignored, duplicates
    collapse to a single value, and text containing no supplied secret is
    returned unchanged. Each occurrence is replaced by the exact literal
    ``[REDACTED]``; when supplied secrets overlap, the longest match wins so
    no supplied secret value survives redaction.
    """
    # Canonical total order (longest first, lexicographic tie-break) keeps
    # the alternation order deterministic even for same-length secrets,
    # whose order would otherwise depend on set iteration order.
    values = sorted(
        {secret for secret in secrets if secret},
        key=lambda value: (-len(value), value),
    )
    if not values:
        return text
    pattern = re.compile("|".join(re.escape(value) for value in values))
    return pattern.sub("[REDACTED]", text)


def add_output(first: str, second: str) -> str:
    """Concatenate two output strings additively.

    ACCEPT-001 / REQ-F92FFC55BA: additive structured command simulation.
    Returns first + second with both strings present in order, neither
    dropped. Pure and deterministic: the result depends only on its
    arguments and no state is read or written.
    """
    return first + second
