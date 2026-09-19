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
