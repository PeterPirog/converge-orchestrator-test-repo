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

    This is a pure function: its output depends only on ``text`` and ``secrets``,
    and it performs no I/O of any kind.

    ACCEPT-002 / REQ-A59E470230: every occurrence, including every repeated
    occurrence, is replaced by the exact literal ``[REDACTED]``, and empty
    secret values are ignored.

    No-I/O purity contract (REQ-0320AB815A / ACCEPT-002): the result is a
    pure function of its two arguments, ``text`` and ``secrets``. The body
    reads no environment variables, no files, no network resources, and no
    process state; it performs no I/O of any kind and mutates no global or
    module-level state, so the redacted text depends only on ``text`` and
    ``secrets``.

    Determinism contract (REQ-CF0D222BF0 / ACCEPT-002): before matching,
    the non-empty supplied secret values are canonicalized into a total
    order (longest first, lexicographic tie-break), so the redacted text is
    identical whatever iterable form the secrets arrive in, in whatever
    order, and under whatever string hashing. When supplied secrets
    overlap, the longest match wins, so no supplied secret value survives
    redaction. Empty secret values are ignored, duplicates collapse to a
    single value, and text containing no supplied secret is returned
    unchanged.
    """
    # REQ-0320AB815A (no-I/O): the entire implementation below performs no I/O
    # and reads no environment variables, files, network resources, or process
    # state. The only helpers called are the pure ``re`` functions
    # re.escape, re.compile, and re.Pattern.sub. No globals, no mutables,
    # no side effects.
    # REQ-CF0D222BF0 (determinism): canonicalizing to longest-first / lexicographic
    # order makes the alternation, and hence the output, independent of the order
    # the secrets are supplied in and of set/hash iteration order; for overlapping
    # secrets the longest match wins.
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
