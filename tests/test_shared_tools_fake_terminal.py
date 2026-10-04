from shared_tools.fake_terminal import format_output, run_command


def test_simulate_command_returns_deterministic_structured_output() -> None:
    from shared_tools.fake_terminal import simulate_command

    command = "echo SHOULD_NOT_RUN"

    result = simulate_command(command)

    assert isinstance(result, dict)
    assert result == {
        "command": command,
        "simulated": True,
        "output": (
            "[SIMULATED] Executing: echo SHOULD_NOT_RUN\n"
            "[SIMULATED] Output placeholder"
        ),
    }
    assert simulate_command(command) == result


def test_run_command_is_deterministic_and_non_executing() -> None:
    command = "echo SHOULD_NOT_RUN"

    result = run_command(command)

    assert result == (
        "[SIMULATED] Executing: echo SHOULD_NOT_RUN\n"
        "[SIMULATED] Output placeholder"
    )


def test_format_output_wraps_terminal_fence() -> None:
    assert format_output("line one\nline two") == "```terminal\nline one\nline two\n```"
