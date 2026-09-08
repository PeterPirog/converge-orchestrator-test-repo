import re

import shared_tools.fake_terminal as fake_terminal
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


def test_simulate_command_returns_structured_result() -> None:
    from shared_tools.fake_terminal import simulate_command

    result = simulate_command("echo hello")

    assert isinstance(result, dict)
    assert set(result) == {"stdout", "stderr", "returncode"}
    assert isinstance(result["stdout"], str)
    assert isinstance(result["stderr"], str)
    assert isinstance(result["returncode"], int)
    assert simulate_command("echo hello") == result


def test_fake_terminal_source_has_no_subprocess_or_shell_references() -> None:
    with open(fake_terminal.__file__, "r", encoding="utf-8") as handle:
        source = handle.read()

    forbidden_patterns = [
        r"subprocess",
        r"os\.system",
        r"os\.popen",
        r"shell\s*=\s*True",
        r"os\.exec",
    ]

    offenders = [pattern for pattern in forbidden_patterns if re.search(pattern, source)]

    assert not offenders, (
        "fake_terminal must remain a simulator and must not invoke "
        f"subprocess or a shell (REQ-879DB2129D); found: {offenders}"
    )
