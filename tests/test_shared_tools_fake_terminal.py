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


def test_simulate_command_returns_structure_and_treats_command_as_data(monkeypatch, tmp_path) -> None:
    """REQ-413A5B74FD: deterministic proof of structured, non-executing simulation.

    Proves two things:
    1. Structure - simulate_command returns a dict with exactly the
       stdout/stderr/returncode fields, with the required types and values,
       and the same result on every call (deterministic).
    2. Data treatment - the command text is inert data: no execution
       facility is reached, no filesystem side effect occurs, and the
       literal command string is embedded verbatim in the returned stdout.
    """
    import os
    import subprocess

    from shared_tools import fake_terminal

    def _execution_attempt(*args, **kwargs):
        raise AssertionError(
            "REQ-413A5B74FD: simulate_command must treat the command text as data"
        )

    monkeypatch.setattr(subprocess, "run", _execution_attempt)
    monkeypatch.setattr(subprocess, "call", _execution_attempt)
    monkeypatch.setattr(subprocess, "Popen", _execution_attempt)
    monkeypatch.setattr(subprocess, "check_call", _execution_attempt)
    monkeypatch.setattr(subprocess, "check_output", _execution_attempt)
    monkeypatch.setattr(os, "system", _execution_attempt)
    monkeypatch.setattr(os, "popen", _execution_attempt)

    # Command with a guaranteed observable side effect if actually executed.
    sentinel = tmp_path / "should_not_exist"
    command = f"touch {sentinel} && echo SHOULD_NOT_RUN"

    result = fake_terminal.simulate_command(command)

    # 1. Structure: exactly the required fields, with required types/values.
    assert isinstance(result, dict), (
        "REQ-413A5B74FD: simulate_command must return a structured dict"
    )
    assert set(result) == {"stdout", "stderr", "returncode"}, (
        "REQ-413A5B74FD: simulate_command must return stdout/stderr/returncode"
    )
    assert isinstance(result["stdout"], str)
    assert isinstance(result["stderr"], str)
    assert isinstance(result["returncode"], int) and result["returncode"] == 0
    assert result["stderr"] == ""

    # Deterministic: identical structure and content on every call.
    assert fake_terminal.simulate_command(command) == result

    # stdout remains the exact mirror of run_command for the same data.
    assert result["stdout"] == run_command(command)

    # 2. Data treatment: the command never executed (no side effect)...
    assert not sentinel.exists(), (
        "REQ-413A5B74FD: simulate_command must not execute the command text"
    )
    assert list(tmp_path.iterdir()) == []

    # ...and the command text is embedded verbatim as inert text.
    assert command in result["stdout"]
    assert result["stdout"] == (
        f"[SIMULATED] Executing: {command}\n[SIMULATED] Output placeholder"
    )
