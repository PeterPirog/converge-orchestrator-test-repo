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


def test_simulate_command_stdout_mirrors_run_command() -> None:
    from shared_tools.fake_terminal import simulate_command

    command = "echo hello"

    result = simulate_command(command)

    assert result["stdout"] == run_command(command), (
        "SIMULATE_COMMAND_MIRRORS_RUN_COMMAND: simulate_command(command)['stdout'] "
        "must equal run_command(command) (REQ-0C50BE10F3)"
    )


def test_simulate_command_stdout_mirrors_run_command_for_varied_commands() -> None:
    from shared_tools.fake_terminal import simulate_command

    commands = [
        "",
        "   ",
        "echo hello",
        'echo "quoted arg" && ls -la | grep pattern',
        "multi\nline\ncmd",
        "unicode-\u00fcn\u00efc\u00f8d\u00e9",
    ]

    for command in commands:
        assert simulate_command(command)["stdout"] == run_command(command), (
            "SIMULATE_COMMAND_MIRRORS_RUN_COMMAND: "
            "simulate_command(command)['stdout'] must equal run_command(command) "
            "for every command (REQ-0C50BE10F3)"
        )


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


def test_simulate_command_treats_command_text_as_data() -> None:
    from shared_tools.fake_terminal import simulate_command

    command = "echo DATA_MARKER_42"

    result = simulate_command(command)

    assert set(result) == {"stdout", "stderr", "returncode"}, (
        "COMMAND_TEXT_AS_DATA: simulate_command must return the structured "
        "result dict (REQ-413A5B74FD)"
    )
    assert command in result["stdout"], (
        "COMMAND_TEXT_AS_DATA: the command text must be embedded verbatim "
        "in stdout rather than executed (REQ-413A5B74FD)"
    )
    assert "DATA_MARKER_42" not in result["stdout"].splitlines(), (
        "COMMAND_TEXT_AS_DATA: a bare DATA_MARKER_42 line would prove the "
        "command was executed as a shell command (REQ-413A5B74FD)"
    )


def test_redact_secrets_redacts_non_empty_supplied_secrets() -> None:
    try:
        from shared_tools.fake_terminal import redact_secrets
    except ImportError as exc:
        raise AssertionError(
            "FAIL_RED_REDACT_SECRETS_NOT_IMPLEMENTED: shared_tools.fake_terminal "
            "must provide a pure redact_secrets helper for training logs "
            "(REQ-85C52948B7)"
        ) from exc

    secrets = ["hunter2", "sk-live-abc123"]
    text = (
        "training log line with api key sk-live-abc123 and password hunter2 here"
    )

    result = redact_secrets(text, secrets)

    assert "sk-live-abc123" not in result, (
        "REDACT_SECRETS: non-empty supplied secret values occurring in text "
        "must be redacted (REQ-85C52948B7)"
    )
    assert "hunter2" not in result, (
        "REDACT_SECRETS: non-empty supplied secret values occurring in text "
        "must be redacted (REQ-85C52948B7)"
    )
    assert result == redact_secrets(text, secrets), (
        "REDACT_SECRETS: redaction must be deterministic (REQ-85C52948B7)"
    )
    assert redact_secrets(text, ["value-not-in-text"]) == text, (
        "REDACT_SECRETS: text without any supplied secret must be unchanged "
        "(REQ-85C52948B7)"
    )
    assert redact_secrets(text, [""]) == text, (
        "REDACT_SECRETS: empty secret values must be ignored (REQ-85C52948B7)"
    )


def test_redact_secrets_redacts_each_repeated_occurrence_with_exact_literal() -> None:
    try:
        from shared_tools.fake_terminal import redact_secrets
    except ImportError as exc:
        raise AssertionError(
            "FAIL_RED_REDACT_SECRETS_NOT_IMPLEMENTED: shared_tools.fake_terminal "
            "must provide a pure redact_secrets helper for training logs "
            "(REQ-A59E470230)"
        ) from exc

    secrets = ["hunter2", "sk-live-abc123", ""]
    text = (
        "first pass hunter2 then sk-live-abc123 again; "
        "second pass hunter2 and sk-live-abc123 once more; "
        "third pass hunter2 sk-live-abc123"
    )

    result = redact_secrets(text, secrets)

    assert text.count("hunter2") == 3
    assert text.count("sk-live-abc123") == 3
    assert "hunter2" not in result, (
        "REDACT_SECRETS: every repeated occurrence of a supplied secret "
        "must be redacted (REQ-A59E470230)"
    )
    assert "sk-live-abc123" not in result, (
        "REDACT_SECRETS: every repeated occurrence of a supplied secret "
        "must be redacted (REQ-A59E470230)"
    )
    assert result == (
        "first pass [REDACTED] then [REDACTED] again; "
        "second pass [REDACTED] and [REDACTED] once more; "
        "third pass [REDACTED] [REDACTED]"
    ), (
        "REDACT_SECRETS: each repeated occurrence must be replaced with the "
        "exact literal [REDACTED] (REQ-A59E470230)"
    )
    assert result.count("[REDACTED]") == 6, (
        "REDACT_SECRETS: one exact [REDACTED] literal must replace each of "
        "the six occurrences, and the empty secret value must be ignored "
        "(REQ-A59E470230)"
    )
    assert redact_secrets(text, secrets) == result, (
        "REDACT_SECRETS: repeated-occurrence redaction must be deterministic "
        "(REQ-A59E470230)"
    )


def test_add_output_concatenates_two_output_strings_additively() -> None:
    try:
        from shared_tools.fake_terminal import add_output
    except ImportError as exc:
        raise AssertionError(
            "FAIL_ADDITIVE_NOT_IMPLEMENTED: shared_tools.fake_terminal "
            "must provide an additive add_output helper that concatenates "
            "two output strings (REQ-F92FFC55BA)"
        ) from exc

    first = "[SIMULATED] Executing: cmd A\n[SIMULATED] Output A"
    second = "[SIMULATED] Executing: cmd B\n[SIMULATED] Output B"

    result = add_output(first, second)

    assert result == first + second, (
        "ADDITIVE_OUTPUT: add_output must concatenate the two supplied "
        "output strings additively (REQ-F92FFC55BA)"
    )
    assert first in result and second in result, (
        "ADDITIVE_OUTPUT: both supplied output strings must be present in "
        "order, with neither dropped (REQ-F92FFC55BA)"
    )
    assert add_output(first, second) == result, (
        "ADDITIVE_OUTPUT: add_output must be deterministic (REQ-F92FFC55BA)"
    )
