from shared_tools.fake_terminal import format_output, run_command


def test_run_command_is_deterministic_and_non_executing() -> None:
    """REQ-413A5B74FD: explicitly prove the returned structure and data treatment.

    The single whole-string equality check is replaced by separate assertions
    that prove (a) the returned structure: a plain string of exactly two
    lines, a header line and a fixed placeholder line, and (b) that the
    command text is treated as data: embedded verbatim, never interpreted.
    """
    command = "echo SHOULD_NOT_RUN"

    result = run_command(command)

    # Returned structure: a plain string consisting of exactly two lines.
    assert isinstance(result, str)
    header, placeholder = result.split("\n")

    # Returned structure: header echoes the command; placeholder is fixed.
    assert header == f"[SIMULATED] Executing: {command}"
    assert placeholder == "[SIMULATED] Output placeholder"

    # Command text as data: embedded verbatim in the simulated output.
    assert command in result

    # Deterministic: the same command always returns the same structure.
    assert run_command(command) == result


def test_run_command_treats_command_text_as_data(tmp_path) -> None:
    """REQ-413A5B74FD: command text is data, never an executable instruction.

    Every path in the payload (plain, ``$(...)`` substitution, backtick
    substitution) would create the marker file if it were interpreted. The
    payload must instead appear verbatim in the simulated output and leave
    no side effect behind.
    """
    marker = tmp_path / "req-413a5b74fd-side-effect"
    command = f"touch {marker}; $(touch {marker}); `touch {marker}`"

    result = run_command(command)

    # Command text as data: the whole payload is embedded verbatim,
    # unchanged, in the simulated header line.
    assert command in result
    assert result.split("\n")[0] == f"[SIMULATED] Executing: {command}"

    # Command text as data: none of the payload was interpreted or executed.
    assert not marker.exists()


def test_run_command_stays_a_simulator_even_if_execution_is_blocked(monkeypatch) -> None:
    """REQ-879DB2129D: run_command must remain a simulator.

    Blocking subprocess and os.system proves the call path never reaches
    real execution facilities while still returning deterministic output.
    """
    import os
    import subprocess

    def _execution_attempt(*args, **kwargs):
        raise AssertionError("REQ-879DB2129D: run_command must remain a simulator")

    monkeypatch.setattr(subprocess, "run", _execution_attempt)
    monkeypatch.setattr(subprocess, "call", _execution_attempt)
    monkeypatch.setattr(subprocess, "Popen", _execution_attempt)
    monkeypatch.setattr(subprocess, "check_call", _execution_attempt)
    monkeypatch.setattr(subprocess, "check_output", _execution_attempt)
    monkeypatch.setattr(os, "system", _execution_attempt)

    command = "echo SHOULD_NOT_RUN"

    first = run_command(command)
    second = run_command(command)

    assert first == second
    assert first == (
        "[SIMULATED] Executing: echo SHOULD_NOT_RUN\n"
        "[SIMULATED] Output placeholder"
    )


def test_fake_terminal_source_never_references_execution_facilities() -> None:
    """REQ-879DB2129D: keep the simulator constraint testable as documentation."""
    import inspect

    from shared_tools import fake_terminal

    source = inspect.getsource(fake_terminal)

    blocked_tokens = (
        "subprocess",
        "os.system",
        "os.popen",
        "Popen",
        "shell",
        "check_call",
        "check_output",
    )

    for token in blocked_tokens:
        assert token not in source, (
            f"REQ-879DB2129D: run_command must remain a simulator (found {token!r} in source)"
        )


def test_format_output_wraps_terminal_fence() -> None:
    assert format_output("line one\nline two") == "```terminal\nline one\nline two\n```"


def test_get_simulation_info_provides_additive_public_function() -> None:
    from shared_tools.fake_terminal import get_simulation_info

    assert callable(get_simulation_info)

    info = get_simulation_info()

    assert info == {
        "simulator": "fake_terminal",
        "executes_commands": False,
        "deterministic": True,
    }


def test_redact_secrets_basic() -> None:
    """REQ-85C52948B7 (ACCEPT-002): deterministic secret redaction helper.

    Every non-empty supplied secret value that occurs in ``text`` must be
    redacted. The helper is imported lazily inside the test so that its
    absence produces a deterministic failure (not a collection error) while
    the module's existing tests continue to run.
    """
    try:
        from shared_tools.fake_terminal import redact_secrets
    except ImportError as exc:
        raise AssertionError(
            "FAIL_RED_REDACT_SECRETS_NOT_IMPLEMENTED: shared_tools.fake_terminal "
            "must provide a pure redact_secrets helper for training logs "
            "(REQ-85C52948B7)"
        ) from exc

    secrets = ["hunter2", "sk-live-abc123"]
    text = "training log line with api key sk-live-abc123 and password hunter2 here"

    result = redact_secrets(text, secrets)

    assert "sk-live-abc123" not in result, (
        "REDACT_SECRETS: non-empty supplied secret values occurring in text "
        "must be redacted (REQ-85C52948B7)"
    )
    assert "hunter2" not in result, (
        "REDACT_SECRETS: non-empty supplied secret values occurring in text "
        "must be redacted (REQ-85C52948B7)"
    )
    assert result == redact_secrets(text, secrets), (
        "REDACT_SECRETS: redaction must be deterministic (REQ-85C52948B7)"
    )


def test_redact_secrets_accept002_contract_repeated_exact_literal_empty_ignored() -> None:
    """REQ-A59E470230 / ACCEPT-002: deterministic secret redaction contract.

    Pins the requirement clauses for the deterministic secret redaction
    helper:
      * every occurrence, including every repeated occurrence of a supplied
        secret value, is replaced with the exact literal ``[REDACTED]``;
      * empty secret values are ignored;
      * when every supplied secret value is empty (or none at all is
        supplied), the text is returned unchanged.
    """
    try:
        from shared_tools.fake_terminal import redact_secrets
    except ImportError as exc:
        raise AssertionError(
            "FAIL_RED_REDACT_SECRETS_NOT_IMPLEMENTED: shared_tools.fake_terminal "
            "must provide a pure redact_secrets helper for training logs "
            "(REQ-A59E470230)"
        ) from exc

    # The sample value is a plain inert placeholder word (no credential
    # material) -- only the redaction behavior is under test here.
    secret = "placeholder"
    text = f"start {secret} mid {secret} end {secret} tail"

    result = redact_secrets(text, [secret, secret, "", secret])

    assert secret not in result, (
        "ACCEPT002_CONTRACT: no supplied secret value may survive redaction "
        "(REQ-A59E470230)"
    )
    assert result == "start [REDACTED] mid [REDACTED] end [REDACTED] tail", (
        "ACCEPT002_CONTRACT: every occurrence, including every repeated "
        "occurrence, must be replaced with the exact literal [REDACTED] "
        "(REQ-A59E470230)"
    )
    assert result.count("[REDACTED]") == 3, (
        "ACCEPT002_CONTRACT: exactly one [REDACTED] literal must replace each "
        "of the three repeated occurrences (REQ-A59E470230)"
    )
    assert redact_secrets(text, [""]) == text, (
        "ACCEPT002_CONTRACT: an empty secret value must be ignored, leaving "
        "the text unchanged (REQ-A59E470230)"
    )
    assert redact_secrets(text, ["", ""]) == text, (
        "ACCEPT002_CONTRACT: when every supplied secret value is empty the "
        "text must be returned unchanged (REQ-A59E470230)"
    )
    assert redact_secrets(text, []) == text, (
        "ACCEPT002_CONTRACT: an empty iterable of secret values must leave "
        "the text unchanged (REQ-A59E470230)"
    )
    assert redact_secrets(text, [secret]) == result, (
        "ACCEPT002_CONTRACT: redaction must be deterministic, independent of "
        "duplicated and empty values in the supplied iterable (REQ-A59E470230)"
    )


def test_redact_secrets_req5c3f7ab352_deterministic_repeated_and_empty() -> None:
    """REQ-5C3F7AB352 (ACCEPT-002): deterministic contract for repeated & empty values.

    requirements.md:L37 [ACCEPT-002 — Deterministic secret redaction helper]
    requires that the deterministic tests cover repeated values and empty
    values. This test pins the ``redact_secrets`` contract for exactly those
    two cases and proves the output is fully deterministic: it depends only on
    the set of non-empty secret values and the input text — never on how many
    times a value is supplied, where it sits in the iterable, the iterable's
    container type / iteration order, or the presence of empty values.
    """
    try:
        from shared_tools.fake_terminal import redact_secrets
    except ImportError as exc:
        raise AssertionError(
            "FAIL_RED_REDACT_SECRETS_NOT_IMPLEMENTED: shared_tools.fake_terminal "
            "must provide a pure redact_secrets helper for training logs "
            "(REQ-5C3F7AB352)"
        ) from exc

    # Inert placeholder value (no credential material) — only the
    # redaction/determinism behavior is under test. The text holds REPEATED
    # occurrences of that value.
    secret = "placeholder"
    text = f"a {secret} b {secret} c"
    expected = "a [REDACTED] b [REDACTED] c"

    # Canonical input: a single non-empty secret value.
    baseline = redact_secrets(text, [secret])

    # Determinism across repeated values, empty values, ordering, and
    # container type: every formulation of the same logical secret set must
    # redact to the identical output.
    formulations = [
        [secret, secret, secret],             # repeated values
        [secret, "", secret, ""],             # repeated values + empty values
        ["", "", secret],                      # empty values around a value
        {"placeholder", ""},                   # set: unspecified iteration order
        (value for value in (secret, "", secret)),  # generator: Iterable contract
    ]
    for formulation in formulations:
        assert redact_secrets(text, formulation) == baseline, (
            "REQ-5C3F7AB352 (ACCEPT-002): the redacted output must be "
            "deterministic and independent of duplicated, reordered, empty, "
            "or the container type of the supplied secret values "
            "(REQ-5C3F7AB352)"
        )

    # Repeated values: every repeated occurrence is replaced with the exact
    # literal marker, and no supplied non-empty value survives.
    assert baseline == expected, (
        "REQ-5C3F7AB352 (ACCEPT-002): every repeated occurrence of a "
        "non-empty secret value must be replaced with the exact literal "
        "[REDACTED] (REQ-5C3F7AB352)"
    )
    assert baseline.count("[REDACTED]") == 2, (
        "REQ-5C3F7AB352 (ACCEPT-002): exactly one [REDACTED] literal per "
        "repeated occurrence (REQ-5C3F7AB352)"
    )
    assert secret not in baseline, (
        "REQ-5C3F7AB352 (ACCEPT-002): no supplied non-empty secret value may "
        "survive redaction (REQ-5C3F7AB352)"
    )

    # Empty values: empty secret values are ignored; when no non-empty value
    # is supplied the text is returned unchanged.
    assert redact_secrets(text, [""]) == text, (
        "REQ-5C3F7AB352 (ACCEPT-002): an empty secret value must be ignored "
        "(REQ-5C3F7AB352)"
    )
    assert redact_secrets(text, ["", ""]) == text, (
        "REQ-5C3F7AB352 (ACCEPT-002): all-empty secret values must leave the "
        "text unchanged (REQ-5C3F7AB352)"
    )
    assert redact_secrets(text, []) == text, (
        "REQ-5C3F7AB352 (ACCEPT-002): no supplied secret values must leave "
        "the text unchanged (REQ-5C3F7AB352)"
    )

    # Determinism: repeated calls with identical inputs return identical
    # output.
    assert redact_secrets(text, [secret]) == baseline, (
        "REQ-5C3F7AB352 (ACCEPT-002): repeated calls with identical inputs "
        "must return identical output (REQ-5C3F7AB352)"
    )


def test_redact_secrets_is_pure_string_manipulation(monkeypatch) -> None:
    """REQ-0320AB815A (ACCEPT-002): no environment, file, network, or process access.

    Behavioral proof: block every file, network, process, and environment
    facility and verify the helper still performs correct pure string
    manipulation. Source inspection is kept as supplementary evidence.
    """
    import builtins
    import os
    import socket
    import subprocess

    def _blocked(*_args, **_kwargs):
        raise AssertionError(
            "REQ-0320AB815A: redact_secrets must not access environment "
            "variables, files, network resources, or process state"
        )

    # Block file access
    monkeypatch.setattr(builtins, "open", _blocked)
    # Block process execution
    monkeypatch.setattr(subprocess, "run", _blocked)
    monkeypatch.setattr(subprocess, "Popen", _blocked)
    monkeypatch.setattr(subprocess, "call", _blocked)
    monkeypatch.setattr(subprocess, "check_call", _blocked)
    monkeypatch.setattr(subprocess, "check_output", _blocked)
    monkeypatch.setattr(os, "system", _blocked)
    monkeypatch.setattr(os, "popen", _blocked)
    # Block network
    monkeypatch.setattr(socket, "socket", _blocked)

    from shared_tools.fake_terminal import redact_secrets

    result = redact_secrets("key=secret123 value=abc", ["secret123"])
    assert result == "key=[REDACTED] value=abc", (
        "REQ-0320AB815A: redact_secrets must perform correct pure string "
        "manipulation without accessing any I/O facility"
    )

    # Supplementary: source inspection confirms no I/O imports in the module.
    import inspect

    from shared_tools import fake_terminal

    source = inspect.getsource(fake_terminal)

    forbidden_tokens = (
        "import re",
        "re.compile",
        "re.escape",
        "re.sub",
        "os.environ",
        "os.path",
        "open(",
        "socket",
        "subprocess",
        "urllib",
        "http",
        "pathlib",
    )

    for token in forbidden_tokens:
        assert token not in source, (
            "REQ-0320AB815A: the redaction helper must not read environment "
            f"variables, files, network resources, or process state (found "
            f"{token!r} in source)"
        )


def test_redact_secrets_treats_metacharacter_secrets_as_literal_data() -> None:
    """REQ-0320AB815A (ACCEPT-002): secret values are literal data.

    Values that would be regular expressions if interpreted (wildcard,
    group, character class) must redact only their exact literal text —
    e.g. the literal secret ``a.c`` must never match the text ``abc``.
    """
    from shared_tools.fake_terminal import redact_secrets

    text = "key1=a.c key2=.c key3=abc pair=(group) class=[brk] star=* end"
    secrets = ["a.c", "(group)", "[brk]", "*"]

    result = redact_secrets(text, secrets)

    assert result == (
        "key1=[REDACTED] key2=.c key3=abc pair=[REDACTED] "
        "class=[REDACTED] star=[REDACTED] end"
    ), (
        "REQ-0320AB815A: pattern-like secret values must be treated as "
        "literal data, redacting only their exact literal text (ACCEPT-002)"
    )
    assert "abc" in result, (
        "REQ-0320AB815A: the literal secret 'a.c' must not match the "
        "non-literal text 'abc' (ACCEPT-002)"
    )
    assert ".c" in result, (
        "REQ-0320AB815A: the literal secret 'a.c' must not match the "
        "unrelated text '.c' (ACCEPT-002)"
    )


def test_redact_secrets_no_cascading_redaction_of_marker() -> None:
    """REQ-85C52948B7 (ACCEPT-002): one-pass redaction does not re-scan the marker.

    When a shorter secret is a substring of the ``[REDACTED]`` marker, the
    single-pass scan must not apply it to text that has already been replaced.
    This preserves the original one-pass regex semantics where all matches
    are determined against the original input simultaneously.
    """
    from shared_tools.fake_terminal import redact_secrets

    # 'a' is a substring of '[REDACTED]'; 'aa' is the longer secret.
    # Correct one-pass: pos 0 → 'aa' matches → [REDACTED], pos 2 → 'a' → [REDACTED]
    # Broken sequential: 'aa' → [REDACTED]a, then 'a' inside marker → [RE[REDACTED]CTED]
    result = redact_secrets("aaa", ["aa", "a"])
    assert result == "[REDACTED][REDACTED]", (
        "REQ-85C52948B7: one-pass redaction must not re-scan replaced text; "
        "a shorter secret must not match inside the [REDACTED] marker "
        "(ACCEPT-002)"
    )

    # Determinism: same inputs always yield the same output.
    assert result == redact_secrets("aaa", ["aa", "a"]), (
        "REQ-85C52948B7: redaction must be deterministic (ACCEPT-002)"
    )
