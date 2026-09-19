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
