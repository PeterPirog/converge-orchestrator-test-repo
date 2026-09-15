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


def test_add_output_concatenates_additively() -> None:
    """REQ-F92FFC55BA: add_output returns first + second, neither dropped."""
    from shared_tools.fake_terminal import add_output

    first, second = "abc", "def"

    assert add_output(first, second) == first + second == "abcdef"
