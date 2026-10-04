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


def test_simulate_command_structured_simulation_req_f92ffc55ba() -> None:
    """simulate_command structured simulation (REQ-F92FFC55BA) returns dict with stdout mirroring run_command."""
    from shared_tools.fake_terminal import simulate_command

    command = "echo SHOULD_NOT_RUN"

    result = simulate_command(command)

    assert isinstance(result, dict)
    assert result["stdout"] == run_command(command)
    # command text is inert data: no real execution, deterministic fake output
    assert simulate_command("rm -rf /")["stdout"].startswith("[SIMULATED] Executing:")
