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
