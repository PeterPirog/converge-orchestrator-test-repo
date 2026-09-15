from shared_tools.fake_terminal import format_output, run_command


def test_run_command_is_deterministic_and_non_executing() -> None:
    command = "echo SHOULD_NOT_RUN"

    result = run_command(command)

    assert result == (
        "[SIMULATED] Executing: echo SHOULD_NOT_RUN\n"
        "[SIMULATED] Output placeholder"
    )


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


def test_add_output_concatenates_additively() -> None:
    """REQ-F92FFC55BA: add_output returns first + second, neither dropped."""
    from shared_tools.fake_terminal import add_output

    first, second = "abc", "def"

    assert add_output(first, second) == first + second == "abcdef"


def test_simulate_command_stdout_exact_mirror_req_0c50be10f3() -> None:
    """REQ-0C50BE10F3: simulate_command.stdout must mirror run_command byte-for-byte.

    The structured simulation API must not delegate to any real OS command
    execution and must return stdout that is byte-for-byte identical to
    run_command(command) for the same command string.
    """
    from shared_tools import fake_terminal

    command = "echo SHOULD_NOT_RUN"

    assert hasattr(fake_terminal, "simulate_command"), (
        "REQ-0C50BE10F3: simulate_command stdout must exactly mirror run_command output"
    )

    result = fake_terminal.simulate_command(command)

    assert result["stdout"] == run_command(command), (
        "REQ-0C50BE10F3: simulate_command stdout must exactly mirror run_command output"
    )
