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


def test_simulate_command_returns_structured_result(tmp_path) -> None:
    """REQ-F92FFC55BA: simulate_command returns a deterministic structured result."""
    from shared_tools.fake_terminal import simulate_command

    sentinel = tmp_path / "should_not_exist"
    command = f"touch {sentinel} && echo SHOULD_NOT_RUN"

    result = simulate_command(command)

    assert set(result) == {"command", "exit_code", "stdout", "stderr"}
    assert result["command"] == command
    assert result["exit_code"] == 0
    assert isinstance(result["stdout"], str)
    assert isinstance(result["stderr"], str)
    assert simulate_command(command) == result
    assert not sentinel.exists()
