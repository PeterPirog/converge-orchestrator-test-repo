from shared_tools.fake_terminal import format_output, run_command


def test_run_command_is_deterministic_and_non_executing() -> None:
    command = "echo SHOULD_NOT_RUN"

    result = run_command(command)

    assert result == (
        "[SIMULATED] Executing: echo SHOULD_NOT_RUN\n"
        "[SIMULATED] Output placeholder"
    )


def test_format_output_wraps_terminal_fence() -> None:
    assert format_output("line one\nline two") == "```terminal\nline one\nline two\n```"


def test_simulate_command_structured_result() -> None:
    from shared_tools.fake_terminal import simulate_command

    assert simulate_command("ls") == {
        "command": "ls",
        "exit_code": 0,
        "stdout": "[SIMULATED] Executing: ls\n[SIMULATED] Output placeholder",
        "stderr": "",
    }


def test_simulator_never_invokes_real_execution_apis(monkeypatch) -> None:
    """REQ-879DB2129D: the simulator must not reach any real shell-execution API."""
    import os
    import subprocess

    sentinel = "REQ-879DB2129D-REAL-EXECUTION-FORBIDDEN"

    def _forbidden(*args: object, **kwargs: object) -> object:
        raise RuntimeError(sentinel)

    for name in ("run", "Popen", "check_output", "check_call", "call"):
        monkeypatch.setattr(subprocess, name, _forbidden)
    monkeypatch.setattr(os, "system", _forbidden)
    monkeypatch.setattr(os, "popen", _forbidden)

    from shared_tools.fake_terminal import simulate_command

    assert run_command("echo SHOULD_NOT_RUN") == (
        "[SIMULATED] Executing: echo SHOULD_NOT_RUN\n"
        "[SIMULATED] Output placeholder"
    )
    assert simulate_command("ls") == {
        "command": "ls",
        "exit_code": 0,
        "stdout": "[SIMULATED] Executing: ls\n[SIMULATED] Output placeholder",
        "stderr": "",
    }


def test_req_0c50be10f3_structured_simulation_preserves_run_contract() -> None:
    """REQ-0C50BE10F3 (ACCEPT-001): structured simulation preserves the run_command contract.

    Pins that the existing ``run_command(command: str) -> str`` two-line [SIMULATED]
    contract is preserved, and that ``simulate_command(command)["stdout"]`` exactly
    mirrors ``run_command(command)`` for distinct command strings. Fully
    deterministic: no real OS command-execution API is invoked.
    """
    from shared_tools.fake_terminal import simulate_command

    # The existing two-line [SIMULATED] output contract is preserved.
    assert run_command("echo SHOULD_NOT_RUN") == (
        "[SIMULATED] Executing: echo SHOULD_NOT_RUN\n"
        "[SIMULATED] Output placeholder"
    )

    # simulate_command["stdout"] exactly mirrors run_command for distinct commands.
    for command in ("ls", "echo SHOULD_NOT_RUN", "git status --porcelain"):
        assert simulate_command(command)["stdout"] == run_command(command)


def test_req_413a5b74fd_command_text_is_inert_data_no_side_effects(tmp_path) -> None:
    """REQ-413A5B74FD (ACCEPT-001): prove the required structure AND that the
    command text is treated as inert data (carried verbatim, never executed).

    A command embedding a real side-effect instruction (``touch <sentinel>``)
    must be carried verbatim into ``result['command']`` and ``result['stdout']``
    while the sentinel file is never created — no execution, no side effects.
    Fully deterministic: no real OS command-execution API is invoked.
    """
    from shared_tools.fake_terminal import simulate_command

    sentinel = tmp_path / "REQ-413A5B74FD-SENTINEL"
    command = f"touch {sentinel} && echo SHOULD_NOT_RUN"

    result = simulate_command(command)

    # Required structure: exactly the four documented keys.
    assert set(result) == {"command", "exit_code", "stdout", "stderr"}
    # The command text is carried verbatim (unmodified) into the result.
    assert result["command"] == command
    # stdout mirrors run_command exactly and carries the command text verbatim.
    assert result["stdout"] == run_command(command)
    assert command in result["stdout"]
    # No side effects / no execution: the sentinel file was never created.
    assert not sentinel.exists()


def test_redact_secrets_redacts_every_non_empty_supplied_secret() -> None:
    """REQ-85C52948B7 (ACCEPT-002): redact_secrets is a pure, deterministic redaction helper.

    Every non-empty supplied secret value occurring in ``text`` is replaced by the
    literal ``[REDACTED]``; empty supplied values are ignored; non-occurring secrets
    leave no trace; and identical inputs always yield identical output. Pure and
    deterministic: no I/O, no subprocess, no real command execution.
    """
    import shared_tools.fake_terminal as fake_terminal

    # RED guard: the helper under test must exist. Before implementation this
    # assertion fails with the literal marker; after implementation it passes and
    # the redaction/determinism contract below is exercised.
    assert hasattr(fake_terminal, "redact_secrets"), (
        "RED-REQ-85C52948B7-redact_secrets_not_implemented"
    )

    redact_secrets = fake_terminal.redact_secrets

    # Every non-empty supplied secret that occurs in the text is redacted and
    # leaves no trace; a non-occurring supplied secret is simply absent.
    result = redact_secrets(
        "api_key=sk-abc123 user=bob token=sk-abc123", ["sk-abc123", "hunter2", ""]
    )
    assert "sk-abc123" not in result
    assert "hunter2" not in result

    # Empty supplied values are ignored entirely.
    assert redact_secrets("plain text", [""]) == "plain text"

    # Determinism: identical inputs always yield identical output.
    repeated = redact_secrets(
        "api_key=sk-abc123 user=bob token=sk-abc123", ["sk-abc123", "hunter2", ""]
    )
    assert repeated == result


def test_req_a59e470230_accept002_redact_secrets() -> None:
    """REQ-A59E470230 (ACCEPT-002): redact_secrets exact-literal and repeated-occurrence contract.

    Every occurrence of each non-empty supplied secret is replaced with the exact
    literal ``[REDACTED]``; empty supplied secret values are ignored; all repeated
    occurrences are replaced; and identical inputs yield identical output.
    Pure and deterministic: no I/O, no subprocess, no real command execution.
    """
    from shared_tools.fake_terminal import redact_secrets

    text = "api_key=sk-abc123 user=bob token=sk-abc123"
    secrets = ["sk-abc123", "hunter2", ""]

    # Every occurrence of each non-empty supplied secret is replaced with the exact
    # literal ``[REDACTED]`` — the count equals the number of replaced
    # occurrences (``sk-abc123`` occurs twice).
    result = redact_secrets(text, secrets)
    assert "sk-abc123" not in result
    assert "hunter2" not in result
    assert result.count("[REDACTED]") == 2
    assert result == "api_key=[REDACTED] user=bob token=[REDACTED]"

    # Empty supplied secret values are ignored entirely.
    assert redact_secrets("plain text", [""]) == "plain text"
    assert redact_secrets("plain text", ["", ""]) == "plain text"

    # All repeated occurrences of every non-empty supplied secret are replaced.
    repeated_text = "top=hunter2 mid=hunter2 bottom=hunter2"
    assert redact_secrets(repeated_text, ["hunter2", ""]) == (
        "top=[REDACTED] mid=[REDACTED] bottom=[REDACTED]"
    )
    assert redact_secrets(repeated_text, ["hunter2", ""]).count("[REDACTED]") == 3

    # Determinism: identical inputs always yield identical output.
    assert redact_secrets(text, secrets) == result


def test_req_cf0d222bf0_overlapping_secrets_order_independent() -> None:
    """REQ-CF0D222BF0 (ACCEPT-002): overlapping secrets produce order-independent output.

    When one secret is a substring of another, the output must be identical
    regardless of input order. The deterministic sort key is
    ``(-len(secret), secret)`` so longer secrets take priority and ties break
    lexicographically. Pure and deterministic: no I/O, no subprocess.
    """
    from shared_tools.fake_terminal import redact_secrets

    order_a = redact_secrets("xabcy", ["ab", "abc"])
    order_b = redact_secrets("xabcy", ["abc", "ab"])

    assert order_a == order_b, (
        "RED-REQ-CF0D222BF0-overlapping-order-dependent"
    )


def test_req_0320ab815a_redact_secrets_never_reads_external_state(monkeypatch) -> None:
    """REQ-0320AB815A (ACCEPT-002): redact_secrets must not read environment
    variables, files, network resources, or process state.

    Deterministic compliance pin: while ``redact_secrets`` runs, every
    forbidden entry point (env access, file access, socket APIs,
    process-spawning APIs) is monkeypatched with a sentinel guard that fails
    the test with the unique literal marker
    ``REQ-0320AB815A-EXTERNAL-STATE-FORBIDDEN``; ``redact_secrets`` still
    returns the exact deterministic redaction output for fixed inputs.
    The guards are undone (``monkeypatch.undo``) as soon as the guarded
    calls finish, so the pytest framework's own phase bookkeeping never
    observes the sentinels. Fully deterministic: no real I/O, network, or
    subprocess is ever performed.
    """
    import builtins
    import os
    import socket
    import subprocess

    sentinel = "REQ-0320AB815A-EXTERNAL-STATE-FORBIDDEN"

    def _forbidden(*args: object, **kwargs: object) -> object:
        raise RuntimeError(sentinel)

    # Environment access: os.getenv and any os.environ mapping access.
    class _SentinelEnvironment:
        def _deny(self, *args: object, **kwargs: object) -> object:
            raise RuntimeError(sentinel)

        __getitem__ = _deny
        __setitem__ = _deny
        __delitem__ = _deny
        __contains__ = _deny
        __iter__ = _deny
        __len__ = _deny
        get = _deny
        setdefault = _deny
        update = _deny
        pop = _deny
        clear = _deny
        copy = _deny
        keys = _deny
        values = _deny
        items = _deny

    monkeypatch.setattr(os, "environ", _SentinelEnvironment())
    monkeypatch.setattr(os, "getenv", _forbidden)

    # File access.
    monkeypatch.setattr(builtins, "open", _forbidden)
    monkeypatch.setattr(os, "open", _forbidden)

    # Network access.
    for name in ("socket", "create_connection", "getaddrinfo"):
        monkeypatch.setattr(socket, name, _forbidden)

    # Process spawning / process state.
    for name in ("run", "Popen", "call", "check_call", "check_output"):
        monkeypatch.setattr(subprocess, name, _forbidden)
    monkeypatch.setattr(os, "system", _forbidden)
    monkeypatch.setattr(os, "popen", _forbidden)

    from shared_tools.fake_terminal import redact_secrets

    text = "api_key=sk-abc123 user=bob token=sk-abc123"
    secrets = ["sk-abc123", "hunter2", ""]

    try:
        # Any forbidden access by redact_secrets (or anything it calls)
        # raises the sentinel marker above. The exact deterministic
        # redaction output is still produced for fixed inputs.
        assert redact_secrets(text, secrets) == "api_key=[REDACTED] user=bob token=[REDACTED]"
        # Determinism: identical inputs always yield identical output.
        assert redact_secrets(text, secrets) == "api_key=[REDACTED] user=bob token=[REDACTED]"
    finally:
        # Restore the real APIs before pytest's phase bookkeeping runs.
        monkeypatch.undo()


def test_req_5c3f7ab352_redaction_never_logs_input_text_or_secrets() -> None:
    """REQ-5C3F7AB352 (ACCEPT-002): redact_secrets must not log either the input
    text or secret values, and must redact deterministically.

    Deterministic compliance pin: while ``redact_secrets`` runs, the current
    ``sys.stdout`` and ``sys.stderr`` are swapped for in-memory buffers; the
    helper still returns the exact deterministic redaction output for fixed
    inputs covering repeated secret occurrences, empty supplied values, and
    non-occurring supplied values; and the captured stdout+stderr contain
    neither the raw input text nor any supplied non-empty secret value. The
    captured streams are restored in a ``finally`` block. Fully deterministic
    and hermetic: no real I/O, network, subprocess, time, or randomness.
    """
    import io
    import sys

    from shared_tools.fake_terminal import redact_secrets

    text = "api_key=sk-abc123 user=bob token=sk-abc123"
    secrets = ["sk-abc123", "hunter2", ""]
    expected = "api_key=[REDACTED] user=bob token=[REDACTED]"

    captured_out = io.StringIO()
    captured_err = io.StringIO()
    original_out = sys.stdout
    original_err = sys.stderr

    try:
        sys.stdout = captured_out
        sys.stderr = captured_err

        # (a) Exact deterministic redaction for repeated, empty, and non-occurring
        # secret values.
        result = redact_secrets(text, secrets)
        assert result == expected
        # Every repeated occurrence of a non-empty supplied secret is replaced.
        assert result.count("[REDACTED]") == 2
        # Empty supplied values are ignored entirely.
        assert redact_secrets("plain text", ["", ""]) == "plain text"
        # Non-occurring supplied secrets leave no trace in the output.
        assert "hunter2" not in result
        # A secret value supplied more than once still yields the same output.
        assert redact_secrets(text, ["sk-abc123", "sk-abc123"]) == expected
        # Determinism: identical inputs always yield identical output.
        assert redact_secrets(text, secrets) == expected
    finally:
        # Restore the original streams before pytest's bookkeeping runs.
        sys.stdout = original_out
        sys.stderr = original_err

    # (b) Neither the raw input text nor any supplied non-empty secret value is
    # logged/emitted to stdout or stderr.
    emitted = captured_out.getvalue() + captured_err.getvalue()
    assert text not in emitted
    for secret in secrets:
        if secret:
            assert secret not in emitted
