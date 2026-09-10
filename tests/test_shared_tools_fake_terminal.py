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


def test_run_command_output_is_inert_simulated_data_at_runtime(
    monkeypatch, tmp_path
) -> None:
    """Runtime complement to the static source-pattern check above.

    REQ-879DB2129D: run_command must remain a simulator. The real
    subprocess/shell entry points are armed so that any attempt to reach
    them fails with the expected violation pattern, and the returned text
    is proven to be inert simulated data: the command is embedded verbatim,
    labeled simulated, produces no bare command output, and leaves no
    filesystem side effects.
    """
    import os
    import subprocess

    def subsystem_violation(*_args, **_kwargs):
        raise AssertionError(
            "FAKE_TERMINAL_RUNTIME_SUBSYSTEM_VIOLATION: run_command reached "
            "a real subprocess/shell entry point; it must remain an inert "
            "simulator (REQ-879DB2129D)"
        )

    for entry_point in (
        "Popen",
        "run",
        "call",
        "check_call",
        "check_output",
        "getoutput",
        "getstatusoutput",
    ):
        monkeypatch.setattr(subprocess, entry_point, subsystem_violation)
    monkeypatch.setattr(os, "system", subsystem_violation)
    monkeypatch.setattr(os, "popen", subsystem_violation)
    for entry_point in ("execv", "execve", "execvp", "execvpe"):
        monkeypatch.setattr(os, entry_point, subsystem_violation)

    marker = "RUNTIME_INERT_PROOF_9F2E"
    side_effect_path = tmp_path / "runtime_execution_proof.txt"
    command = (
        f"echo {marker} && touch {side_effect_path} && "
        f"python3 -c \"open(r'{side_effect_path}', 'w').write('{marker}')\""
    )

    result = run_command(command)

    assert isinstance(result, str), (
        "FAKE_TERMINAL_RUNTIME_SUBSYSTEM_VIOLATION: run_command must return "
        "inert simulated text (REQ-879DB2129D)"
    )
    assert command in result, (
        "FAKE_TERMINAL_RUNTIME_SUBSYSTEM_VIOLATION: the command text must be "
        "present verbatim as inert data in the output rather than executed "
        "(REQ-879DB2129D)"
    )
    assert "[SIMULATED]" in result, (
        "FAKE_TERMINAL_RUNTIME_SUBSYSTEM_VIOLATION: the output must be "
        "labeled as simulated data (REQ-879DB2129D)"
    )
    assert marker not in result.splitlines(), (
        "FAKE_TERMINAL_RUNTIME_SUBSYSTEM_VIOLATION: a bare marker line in "
        "the output would prove the command was executed by a shell "
        "(REQ-879DB2129D)"
    )
    assert not side_effect_path.exists(), (
        "FAKE_TERMINAL_RUNTIME_SUBSYSTEM_VIOLATION: a filesystem side effect "
        "would prove real command execution (REQ-879DB2129D)"
    )
    assert run_command(command) == result, (
        "FAKE_TERMINAL_RUNTIME_SUBSYSTEM_VIOLATION: the simulated output "
        "must be deterministic (REQ-879DB2129D)"
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


def test_simulate_command_presents_command_text_as_inert_data() -> None:
    from shared_tools.fake_terminal import simulate_command

    command = "echo INERT_DATA_7"

    result = simulate_command(command)

    assert set(result) == {"stdout", "stderr", "returncode"}, (
        "INERT_COMMAND_DATA: simulate_command must return the structured "
        "result dict (REQ-413A5B74FD)"
    )
    assert command in result["stdout"], (
        "INERT_COMMAND_DATA: the command text must be embedded verbatim in "
        "stdout as inert data rather than executed (REQ-413A5B74FD)"
    )
    assert "[SIMULATED] Executing:" not in result["stdout"], (
        "INERT_COMMAND_DATA: simulate_command output must present the "
        "command text as inert data and must not carry the "
        "'[SIMULATED] Executing:' execution marker (REQ-413A5B74FD)"
    )


def test_simulate_command_legacy_pinned_input_is_inert_data() -> None:
    from shared_tools.fake_terminal import simulate_command

    command = "echo SHOULD_NOT_RUN"

    result = simulate_command(command)

    assert set(result) == {"stdout", "stderr", "returncode"}, (
        "INERT_COMMAND_DATA: simulate_command must return the structured "
        "result dict (REQ-413A5B74FD)"
    )
    assert command in result["stdout"], (
        "INERT_COMMAND_DATA: the command text must be embedded verbatim in "
        "stdout as inert data rather than executed (REQ-413A5B74FD)"
    )
    assert "SHOULD_NOT_RUN" not in result["stdout"].splitlines(), (
        "INERT_COMMAND_DATA: a bare SHOULD_NOT_RUN line would prove the "
        "command was executed as a shell command (REQ-413A5B74FD)"
    )
    assert result["stderr"] == "" and result["returncode"] == 0, (
        "INERT_COMMAND_DATA: the structured result must remain deterministic "
        "inert data (REQ-413A5B74FD)"
    )
    assert "[SIMULATED] Executing:" not in result["stdout"], (
        "INERT_COMMAND_DATA: simulate_command output must present the "
        "command text as inert data and must not carry the "
        "'[SIMULATED] Executing:' execution marker (REQ-413A5B74FD)"
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


def test_redact_secrets_prefers_longest_match_when_supplied_secrets_overlap() -> None:
    try:
        from shared_tools.fake_terminal import redact_secrets
    except ImportError as exc:
        raise AssertionError(
            "FAIL_RED_REDACT_SECRETS_NOT_IMPLEMENTED: shared_tools.fake_terminal "
            "must provide a pure redact_secrets helper for training logs "
            "(REQ-85C52948B7)"
        ) from exc

    secrets = ["ab", "abc", "abcd"]
    text = "token abcd then abc and ab end"

    result = redact_secrets(text, secrets)

    assert "abcd" not in result, (
        "REDACT_SECRETS: the longest supplied secret must be redacted when "
        "it overlaps a shorter one (REQ-85C52948B7)"
    )
    assert "abc" not in result, (
        "REDACT_SECRETS: no supplied secret value may survive redaction of an "
        "overlapping longer secret (REQ-85C52948B7)"
    )
    assert result == "token [REDACTED] then [REDACTED] and [REDACTED] end", (
        "REDACT_SECRETS: each overlapping occurrence must collapse to exactly "
        "one [REDACTED] literal (REQ-85C52948B7)"
    )
    assert result == redact_secrets(text, secrets), (
        "REDACT_SECRETS: overlapping-secret redaction must be deterministic "
        "(REQ-85C52948B7)"
    )


def test_redact_secrets_treats_regex_special_characters_as_literal() -> None:
    try:
        from shared_tools.fake_terminal import redact_secrets
    except ImportError as exc:
        raise AssertionError(
            "FAIL_RED_REDACT_SECRETS_NOT_IMPLEMENTED: shared_tools.fake_terminal "
            "must provide a pure redact_secrets helper for training logs "
            "(REQ-85C52948B7)"
        ) from exc

    secrets = ["a.b", "c+d"]
    text = (
        "decoy axb stays and cx d stays, "
        "real a.b goes and real c+d goes"
    )

    result = redact_secrets(text, secrets)

    assert "a.b" not in result, (
        "REDACT_SECRETS: a supplied secret containing regex special "
        "characters must be redacted (REQ-85C52948B7)"
    )
    assert "c+d" not in result, (
        "REDACT_SECRETS: a supplied secret containing regex special "
        "characters must be redacted (REQ-85C52948B7)"
    )
    assert "axb" in result and "cx d" in result, (
        "REDACT_SECRETS: secrets must match as exact literals, so lookalike "
        "text that does not equal a supplied secret stays (REQ-85C52948B7)"
    )
    assert result == (
        "decoy axb stays and cx d stays, "
        "real [REDACTED] goes and real [REDACTED] goes"
    ), (
        "REDACT_SECRETS: literal [REDACTED] must replace only exact secret "
        "occurrences (REQ-85C52948B7)"
    )


def test_redact_secrets_collapses_duplicates_and_ignores_input_order() -> None:
    try:
        from shared_tools.fake_terminal import redact_secrets
    except ImportError as exc:
        raise AssertionError(
            "FAIL_RED_REDACT_SECRETS_NOT_IMPLEMENTED: shared_tools.fake_terminal "
            "must provide a pure redact_secrets helper for training logs "
            "(REQ-85C52948B7)"
        ) from exc

    text = "token-1 and token-2 and token-1"

    result_a = redact_secrets(text, ["token-1", "token-2", "token-1", ""])
    result_b = redact_secrets(text, ["token-2", "token-1", "token-1"])

    assert result_a == "[REDACTED] and [REDACTED] and [REDACTED]", (
        "REDACT_SECRETS: duplicated and empty secret values must not change "
        "the redacted output (REQ-85C52948B7)"
    )
    assert result_a == result_b, (
        "REDACT_SECRETS: redaction of same-length secrets must be "
        "independent of the order in which they are supplied "
        "(REQ-85C52948B7)"
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
