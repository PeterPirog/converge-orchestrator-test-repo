from shared_tools.fake_terminal import format_output, run_command


def test_run_command_is_deterministic_and_non_executing() -> None:
    """REQ-413A5B74FD: explicitly prove the returned structure and data treatment.

    Separate assertions prove (a) the returned structure: a plain string of
    exactly two lines — a header line and a fixed placeholder line — and
    (b) that the command text is treated as data: embedded verbatim, never
    interpreted or executed.
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
