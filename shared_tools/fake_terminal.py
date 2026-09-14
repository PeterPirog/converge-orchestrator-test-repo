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

from typing import Iterable


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


def redact_secrets(text: str, secrets: Iterable[str]) -> str:
    """Redact supplied secret values from ``text`` deterministically.

    REQ-85C52948B7 (ACCEPT-002 — Deterministic secret redaction helper): a
    pure helper for training logs. Every non-empty supplied secret value that
    occurs in ``text`` is replaced with the fixed marker ``[REDACTED]``. The
    output depends only on ``text`` and the supplied secret values, so
    repeated calls with identical inputs return identical output.

    REQ-0320AB815A (ACCEPT-002): the redaction is pure string manipulation —
    it reads no environment variables, files, network resources, or process
    state, and secret values are treated as literal data (never interpreted).

    Longer values are matched before shorter ones at each position so a
    shorter value is never left half-substituted inside a longer one.
    Equally long values are broken alphabetically, so the match order — and
    the output — never depends on the supplied iterable's iteration order
    (e.g. a set). The scan is single-pass: replaced text is never re-examined,
    so the ``[REDACTED]`` marker itself can never be matched by a later secret.
    """
    values = [secret for secret in secrets if secret]
    if not values:
        return text

    # Sort longest-first, breaking ties alphabetically, so the match order
    # is fully deterministic and independent of the input's iteration order.
    ordered = sorted(set(values), key=lambda value: (-len(value), value))

    # Single-pass greedy longest-match scan. At each position, try each
    # secret (longest first) against the remaining text. On a match, emit
    # the marker and advance past the matched span. Otherwise emit the
    # current character and advance by one. Replaced text is never
    # re-scanned, so the marker is never re-matched by a subsequent secret.
    marker = "[REDACTED]"
    result = []
    i = 0
    n = len(text)
    while i < n:
        for value in ordered:
            if text.startswith(value, i):
                result.append(marker)
                i += len(value)
                break
        else:
            result.append(text[i])
            i += 1
    return "".join(result)
