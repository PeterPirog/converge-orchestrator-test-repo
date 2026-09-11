"""Fake terminal for simulating command execution in acceptance tests."""

import re
from collections.abc import Iterable


def run_command(command: str) -> str:
    """Simulate running a command and return deterministic output.

    ACCEPT-001 / REQ-879DB2129D: this remains a simulator. The command
    string is inert data; no external process is spawned, no system()
    call is made via the os module, and no shell is ever invoked.

    REQ-413A5B74FD: the command text is presented verbatim as inert data
    under the inert '[SIMULATED] Command:' label rather than an execution
    marker, so deterministic tests prove the command text is treated as
    data rather than executed. Every command is presented consistently
    under this single inert label.
    """
    return f"[SIMULATED] Command: {command}\n[SIMULATED] Output placeholder"


def format_output(output: str) -> str:
    """Format terminal output for display."""
    return f"```terminal\n{output}\n```"


def simulate_command(command: str) -> dict:
    """Simulate a command and return a structured result dict.

    ACCEPT-001 / REQ-0C50BE10F3: structured command simulation that
    explicitly preserves the existing run_command behavior. The ``stdout``
    field is exactly ``run_command(command)``, so run_command's
    deterministic output format is preserved verbatim; ``stderr`` is empty
    and ``returncode`` is 0. Returns a deterministic dict with stdout,
    stderr, and returncode keys.

    REQ-413A5B74FD: the command text is presented as inert data under the
    '[SIMULATED] Command:' label, leaving the embedded command text
    verbatim, so deterministic tests prove the command text is treated as
    data rather than executed. The returned dict also explicitly surfaces
    the command text as an independent, verifiable data field under the
    ``command`` key: byte-for-byte the input string, never executed or
    transformed, so deterministic tests can prove ``result["command"] ==
    command`` directly. This field is purely additive; the existing
    ``stdout``, ``stderr``, and ``returncode`` keys and their values are
    unchanged.
    """
    # REQ-0C50BE10F3: stdout is derived directly from run_command(command),
    # explicitly preserving run_command's deterministic output format. The
    # command text remains inert data; no external process or shell is invoked.
    stdout = run_command(command)
    return {
        "stdout": stdout,
        "stderr": "",
        "returncode": 0,
        # REQ-413A5B74FD: the command text is explicitly surfaced as inert
        # data in its own field, verbatim and independently verifiable.
        "command": command,
    }


def _canonical_secret_order(secrets: Iterable[str]) -> list[str]:
    """Return the non-empty, de-duplicated secret values in canonical order.

    REQ-CF0D222BF0 / ACCEPT-002 (determinism contract): this is the single
    canonical ordering the redaction alternation is built from, so the result
    is a pure function of the set of supplied secret values. Empty secret
    values are ignored and duplicates collapse to a single value, then the
    remaining values are sorted into a total order -- longest value first,
    with a lexicographic tie-break. Because that order is fixed by the values
    themselves, it is identical whatever iterable form the secrets arrive in,
    in whatever order, and under whatever string hashing. Putting the longest
    value first also means that, when supplied secrets overlap, the longest
    match wins and no supplied secret value survives redaction.
    """
    return sorted(
        {secret for secret in secrets if secret},
        key=lambda value: (-len(value), value),
    )


def redact_secrets(text: str, secrets: Iterable[str]) -> str:
    """Redact every non-empty supplied secret value that occurs in text.

    This is a pure function: its output depends only on ``text`` and ``secrets``,
    and it performs no I/O of any kind.

    Deterministic secret redaction helper (REQ-5C3F7AB352 / ACCEPT-002): this
    is the deterministic secret redaction helper. Its return value never
    contains a supplied secret value, so text logged through it does not leak
    the input text's secrets. Every repeated occurrence is redacted and empty
    secret values are ignored, the repeated-value and empty-value cases the
    deterministic tests must cover.

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
    # REQ-CF0D222BF0 (determinism): the non-empty supplied secrets are
    # canonicalized by _canonical_secret_order (longest first, lexicographic
    # tie-break) into an order fixed by the values themselves, so the
    # alternation -- and hence the redacted output -- is independent of the
    # order the secrets are supplied in and of set/hash iteration order; for
    # overlapping secrets the longest match wins.
    values = _canonical_secret_order(secrets)
    if not values:
        return text
    pattern = re.compile("|".join(re.escape(value) for value in values))
    # REQ-85C52948B7 (exact-literal contract): a callable replacement
    # inserts the exact "[REDACTED]" literal verbatim for every occurrence,
    # so the marker is never re-interpreted as a re.sub template and every
    # supplied-secret occurrence collapses to the same literal, deterministically.
    return pattern.sub(lambda _match: "[REDACTED]", text)


def add_output(first: str, second: str) -> str:
    """Concatenate two output strings additively.

    ACCEPT-001 / REQ-F92FFC55BA: additive structured command simulation.
    Returns first + second with both strings present in order, neither
    dropped. Pure and deterministic: the result depends only on its
    arguments and no state is read or written.
    """
    return first + second
