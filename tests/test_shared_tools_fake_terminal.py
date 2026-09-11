import re

import shared_tools.fake_terminal as fake_terminal
from shared_tools.fake_terminal import format_output, run_command


def test_run_command_is_deterministic_and_non_executing() -> None:
    command = "echo SHOULD_NOT_RUN"

    result = run_command(command)

    assert result == (
        "[SIMULATED] Command: echo SHOULD_NOT_RUN\n"
        "[SIMULATED] Output placeholder"
    )


def test_run_command_uses_inert_command_label_and_not_legacy_executing_marker() -> None:
    """REQ-879DB2129D / REQ-413A5B74FD: consistent inert command label.

    Every command -- including the previously legacy-pinned input -- must be
    presented under the single inert '[SIMULATED] Command:' label rather
    than a legacy '[SIMULATED] Executing:' execution marker, and the
    structured API must mirror the raw API for the same input.
    """
    from shared_tools.fake_terminal import simulate_command

    commands = [
        "echo SHOULD_NOT_RUN",
        "echo hello",
        "ls -la | grep pattern",
        "multi\nline\ncmd",
        "",
    ]

    for command in commands:
        output = run_command(command)
        assert "[SIMULATED] Executing:" not in output, (
            "INERT_COMMAND_LABEL: run_command must not carry the legacy "
            "'[SIMULATED] Executing:' execution marker (REQ-879DB2129D, "
            "REQ-413A5B74FD)"
        )
        assert output.startswith("[SIMULATED] Command: "), (
            "INERT_COMMAND_LABEL: run_command must present the command "
            "under the inert '[SIMULATED] Command:' label (REQ-413A5B74FD)"
        )
        assert simulate_command(command)["stdout"] == output, (
            "INERT_COMMAND_LABEL: simulate_command must mirror run_command "
            "for every command, including the previously legacy-pinned input "
            "(REQ-0C50BE10F3)"
        )


def test_format_output_wraps_terminal_fence() -> None:
    assert format_output("line one\nline two") == "```terminal\nline one\nline two\n```"


def test_simulate_command_returns_structured_result() -> None:
    from shared_tools.fake_terminal import simulate_command

    result = simulate_command("echo hello")

    assert isinstance(result, dict)
    assert set(result) == {"stdout", "stderr", "returncode", "command"}
    assert isinstance(result["stdout"], str)
    assert isinstance(result["stderr"], str)
    assert isinstance(result["returncode"], int)
    assert isinstance(result["command"], str), (
        "COMMAND_FIELD_DATA: the returned structure must explicitly surface "
        "the command text as an independent str data field (REQ-413A5B74FD)"
    )
    assert result["command"] == "echo hello", (
        "COMMAND_FIELD_DATA: the command field must carry the command text "
        "verbatim as inert data (REQ-413A5B74FD)"
    )
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

    assert set(result) == {"stdout", "stderr", "returncode", "command"}, (
        "COMMAND_TEXT_AS_DATA: simulate_command must return the structured "
        "result dict, including the explicit command data field "
        "(REQ-413A5B74FD)"
    )
    assert result["command"] == command, (
        "COMMAND_TEXT_AS_DATA: the explicit command field must carry the "
        "command text verbatim as inert data, independently of stdout "
        "(REQ-413A5B74FD)"
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

    assert set(result) == {"stdout", "stderr", "returncode", "command"}, (
        "INERT_COMMAND_DATA: simulate_command must return the structured "
        "result dict, including the explicit command data field "
        "(REQ-413A5B74FD)"
    )
    assert result["command"] == command, (
        "INERT_COMMAND_DATA: the explicit command field must carry the "
        "command text verbatim as inert data (REQ-413A5B74FD)"
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

    assert set(result) == {"stdout", "stderr", "returncode", "command"}, (
        "INERT_COMMAND_DATA: simulate_command must return the structured "
        "result dict, including the explicit command data field "
        "(REQ-413A5B74FD)"
    )
    assert result["command"] == command, (
        "INERT_COMMAND_DATA: the explicit command field must carry the "
        "command text verbatim as inert data (REQ-413A5B74FD)"
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


def test_simulate_command_surfaces_command_text_as_explicit_inert_data_field() -> None:
    """REQ-413A5B74FD: the returned structure explicitly carries the command text.

    Deterministic proof, for a variety of inputs (including empty, blank,
    multi-line, and non-ASCII text), that the returned dict exposes the
    command text as its own independent data field: byte-for-byte the
    input string, typed as ``str``, never transformed or executed. The
    existing fields keep their exact prior values, so the structure is a
    strict superset of the previous return dict.
    """
    from shared_tools.fake_terminal import simulate_command

    commands = [
        "",
        "   ",
        "echo FIELD_DATA_11",
        "ls -la | grep pattern && touch /tmp/field-data-proof",
        "multi\nline\ncmd",
        "unicode-\u00fcn\u00efc\u00f8d\u00e9",
    ]

    for command in commands:
        result = simulate_command(command)

        assert isinstance(result, dict)
        assert set(result) == {"stdout", "stderr", "returncode", "command"}, (
            "EXPLICIT_DATA_FIELD: the returned structure must explicitly "
            "surface the command text as an independent data field "
            "(REQ-413A5B74FD)"
        )
        assert isinstance(result["command"], str), (
            "EXPLICIT_DATA_FIELD: the command data field must be a str "
            "holding inert text, not a callable or side effect "
            "(REQ-413A5B74FD)"
        )
        assert result["command"] == command, (
            "EXPLICIT_DATA_FIELD: the command data field must carry the "
            "command text verbatim, byte-for-byte unchanged, as data "
            "rather than executed (REQ-413A5B74FD)"
        )
        assert result["stdout"] == run_command(command), (
            "EXPLICIT_DATA_FIELD: stdout must still mirror run_command "
            "exactly for every command (REQ-413A5B74FD, REQ-0C50BE10F3)"
        )
        assert result["stderr"] == "" and result["returncode"] == 0, (
            "EXPLICIT_DATA_FIELD: the existing fields must keep their "
            "deterministic inert values (REQ-413A5B74FD)"
        )
        assert "[SIMULATED] Executing:" not in result["stdout"], (
            "EXPLICIT_DATA_FIELD: the command text must stay under the "
            "inert label, never an execution marker (REQ-413A5B74FD)"
        )
        assert simulate_command(command) == result, (
            "EXPLICIT_DATA_FIELD: the structured result, including the "
            "explicit command data field, must be deterministic "
            "(REQ-413A5B74FD)"
        )


def test_simulate_command_command_field_is_inert_data_at_runtime(
    monkeypatch, tmp_path
) -> None:
    """Runtime complement: the explicit command field is inert data.

    REQ-413A5B74FD: the deterministic tests must prove the returned
    structure and that the command text is treated as data. The real
    subprocess/shell entry points are armed so that any attempt to reach
    them fails, and the 'command' field of the returned dict must carry
    the exact command text verbatim while producing no filesystem side
    effect -- proof that it is data, not an action.
    """
    import os
    import subprocess

    from shared_tools.fake_terminal import simulate_command

    def subsystem_violation(*_args, **_kwargs):
        raise AssertionError(
            "FAKE_TERMINAL_RUNTIME_SUBSYSTEM_VIOLATION: simulate_command "
            "reached a real subprocess/shell entry point; the command "
            "text must be treated as inert data (REQ-413A5B74FD)"
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

    marker = "FIELD_DATA_PROOF_7C3A"
    side_effect_path = tmp_path / "field_execution_proof.txt"
    command = f"echo {marker} && touch {side_effect_path}"

    result = simulate_command(command)

    assert set(result) == {"stdout", "stderr", "returncode", "command"}, (
        "FIELD_DATA_PROOF: the returned structure must explicitly surface "
        "the command text as an independent data field (REQ-413A5B74FD)"
    )
    assert result["command"] == command, (
        "FIELD_DATA_PROOF: the command field must carry the exact command "
        "text verbatim as inert data (REQ-413A5B74FD)"
    )
    assert marker not in result["stdout"].splitlines(), (
        "FIELD_DATA_PROOF: a bare marker line in stdout would prove the "
        "command was executed by a shell (REQ-413A5B74FD)"
    )
    assert not side_effect_path.exists(), (
        "FIELD_DATA_PROOF: a filesystem side effect would prove real "
        "command execution (REQ-413A5B74FD)"
    )
    assert simulate_command(command) == result, (
        "FIELD_DATA_PROOF: the structured result must be deterministic "
        "(REQ-413A5B74FD)"
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


def test_redact_secrets_normalization_is_stable_across_forms_orders_and_hash_seeds() -> None:
    try:
        from shared_tools.fake_terminal import redact_secrets
    except ImportError as exc:
        raise AssertionError(
            "FAIL_RED_REDACT_SECRETS_NOT_IMPLEMENTED: shared_tools.fake_terminal "
            "must provide a pure redact_secrets helper for training logs "
            "(REQ-A59E470230)"
        ) from exc

    import os
    import subprocess
    import sys
    from pathlib import Path

    secret_key = "sk-live-abc123"
    secret_pw = "hunter2"
    text = (
        f"{secret_pw} opens, {secret_key} middle, {secret_pw} again, "
        f"{secret_key} closes, {secret_pw}"
    )
    expected = (
        "[REDACTED] opens, [REDACTED] middle, [REDACTED] again, "
        "[REDACTED] closes, [REDACTED]"
    )

    # The same logical secret set supplied as different containers, in
    # different orders, with duplicates and empty values mixed in: the
    # helper must normalize them to one identical result in which every
    # repeated occurrence becomes the exact [REDACTED] literal.
    forms = [
        [secret_key, secret_pw, secret_key, "", secret_pw],
        [secret_pw, secret_key],
        [secret_pw, "", secret_key, secret_pw],
        {secret_key, secret_pw, ""},
        (secret_pw, secret_key, secret_pw),
    ]

    for form in forms:
        result = redact_secrets(text, form)
        assert result == expected, (
            "REDACT_SECRETS: every repeated occurrence of a supplied secret "
            "must be replaced with the exact literal [REDACTED] and empty "
            "secret values must be ignored (REQ-A59E470230)"
        )
        assert secret_key not in result and secret_pw not in result, (
            "REDACT_SECRETS: no supplied secret value may survive redaction "
            "(REQ-A59E470230)"
        )
        assert result.count("[REDACTED]") == 5, (
            "REDACT_SECRETS: exactly one [REDACTED] literal must replace "
            "each of the five occurrences (REQ-A59E470230)"
        )

    # Cross-process determinism: identical calls under two different
    # PYTHONHASHSEED values must yield byte-identical output, so the
    # normalized result cannot depend on set/dict iteration order.
    repo_root = Path(__file__).resolve().parent.parent
    snippet = (
        "import shared_tools.fake_terminal as ft\n"
        f"text = {text!r}\n"
        f"secrets = {forms[0]!r}\n"
        "print(ft.redact_secrets(text, secrets), end='')\n"
    )
    for seed in ("1", "42"):
        env = dict(os.environ, PYTHONPATH=str(repo_root), PYTHONHASHSEED=seed)
        completed = subprocess.run(
            [sys.executable, "-c", snippet],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            env=env,
            timeout=60,
        )
        assert completed.returncode == 0, (
            "REDACT_SECRETS: the deterministic redaction call must succeed "
            f"in a fresh interpreter (REQ-A59E470230); stderr: {completed.stderr!r}"
        )
        assert completed.stdout == expected, (
            "REDACT_SECRETS: redaction must be deterministic across Python "
            "hash seeds, not only within one process (REQ-A59E470230)"
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


def test_redact_secrets_overlapping_inputs_are_deterministic_independent_of_set_and_hash_order() -> None:
    try:
        from shared_tools.fake_terminal import redact_secrets
    except ImportError as exc:
        raise AssertionError(
            "FAIL_RED_REDACT_SECRETS_NOT_IMPLEMENTED: shared_tools.fake_terminal "
            "must provide a pure redact_secrets helper for training logs "
            "(REQ-CF0D222BF0)"
        ) from exc

    import itertools
    import os
    import subprocess
    import sys
    from pathlib import Path

    # Overlapping supplied secrets: "token123" contains "token" which
    # contains "tok". The canonical longest-first / lexicographic order must
    # make the longest supplied secret win at every overlapping position,
    # whatever order the values are supplied in.
    secrets = ["tok", "token", "token123"]
    text = "show token123 then token and tok done"
    expected = "show [REDACTED] then [REDACTED] and [REDACTED] done"

    for order in itertools.permutations(secrets):
        result = redact_secrets(text, list(order))
        assert result == expected, (
            "REDACT_SECRETS: overlapping supplied secrets must redact to the "
            "same deterministic result for every supplied order "
            f"(REQ-CF0D222BF0); order={order!r} gave {result!r}"
        )
        assert "tok" not in result and "token" not in result and "token123" not in result, (
            "REDACT_SECRETS: no supplied secret value may survive redaction "
            "(REQ-CF0D222BF0)"
        )

    assert redact_secrets(text, set(secrets)) == expected, (
        "REDACT_SECRETS: overlapping supplied secrets must redact to the "
        "same deterministic result when supplied as an unordered set "
        "(REQ-CF0D222BF0)"
    )

    # Cross-process determinism: the identical call must yield
    # byte-identical output under different PYTHONHASHSEED values, so the
    # overlapping-input result cannot depend on set/hash iteration order.
    repo_root = Path(__file__).resolve().parent.parent
    snippet = (
        "import shared_tools.fake_terminal as ft\n"
        f"text = {text!r}\n"
        f"secrets = {set(secrets)!r}\n"
        "print(ft.redact_secrets(text, secrets), end='')\n"
    )
    outputs = []
    for seed in ("0", "1", "42"):
        env = dict(os.environ, PYTHONPATH=str(repo_root), PYTHONHASHSEED=seed)
        completed = subprocess.run(
            [sys.executable, "-c", snippet],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            env=env,
            timeout=60,
        )
        assert completed.returncode == 0, (
            "REDACT_SECRETS: the deterministic overlapping-secret redaction "
            "call must succeed in a fresh interpreter (REQ-CF0D222BF0); "
            f"stderr: {completed.stderr!r}"
        )
        outputs.append(completed.stdout)

    assert outputs == [expected, expected, expected], (
        "REDACT_SECRETS: overlapping inputs must produce deterministic "
        "output independent of set/hash iteration order, i.e. "
        "byte-identical across Python hash seeds (REQ-CF0D222BF0); "
        f"got {outputs!r}"
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


def test_redact_secrets_redacts_every_boundary_occurrence_for_any_iterable() -> None:
    try:
        from shared_tools.fake_terminal import redact_secrets
    except ImportError as exc:
        raise AssertionError(
            "FAIL_RED_REDACT_SECRETS_NOT_IMPLEMENTED: shared_tools.fake_terminal "
            "must provide a pure redact_secrets helper for training logs "
            "(REQ-85C52948B7)"
        ) from exc

    # REQ-85C52948B7: EVERY non-empty supplied secret value occurring in
    # text must be redacted, including occurrences at the very start and
    # end of the text, and the helper must treat secret values as exact
    # literals regardless of the iterable they are supplied in (here a set,
    # and a second call uses a generator).
    secret_head = "AKIA-super-secret"
    secret_tail = "tail.secret-key"
    text = (
        f"{secret_head} opens the log, mid body, {secret_tail} closes it, "
        f"{secret_tail} again and {secret_head} last"
    )

    result = redact_secrets(text, {secret_head, secret_tail, ""})

    assert secret_head not in result, (
        "REDACT_SECRETS: a non-empty supplied secret at the start of the "
        "text must be redacted (REQ-85C52948B7)"
    )
    assert secret_tail not in result, (
        "REDACT_SECRETS: a non-empty supplied secret (with a regex-special "
        "dot) at the end of the text must be redacted (REQ-85C52948B7)"
    )
    assert result == (
        "[REDACTED] opens the log, mid body, [REDACTED] closes it, "
        "[REDACTED] again and [REDACTED] last"
    ), (
        "REDACT_SECRETS: every occurrence of a supplied secret, wherever it "
        "appears including text boundaries, must become the exact [REDACTED] "
        "literal (REQ-85C52948B7)"
    )
    assert result.count("[REDACTED]") == 4, (
        "REDACT_SECRETS: each of the four boundary/repeated occurrences "
        "must be redacted exactly once (REQ-85C52948B7)"
    )
    assert redact_secrets(text, (v for v in (secret_head, secret_tail))) == result, (
        "REDACT_SECRETS: redaction must be identical for any iterable of "
        "secret values, not just a list (REQ-85C52948B7)"
    )
    assert redact_secrets("", [secret_head, secret_tail]) == "", (
        "REDACT_SECRETS: empty text must be returned unchanged "
        "(REQ-85C52948B7)"
    )
    assert redact_secrets(text, {secret_head, secret_tail, ""}) == result, (
        "REDACT_SECRETS: boundary-occurrence redaction must be deterministic "
        "(REQ-85C52948B7)"
    )


def test_redact_secrets_treats_backslash_and_adjacent_occurrences_as_exact_literals() -> None:
    """REQ-85C52948B7: literal matching holds for backslashes and adjacency.

    Two required facets of the core contract -- "every non-empty supplied
    secret value that occurs in ``text`` must be redacted" as exact literals,
    deterministically, to the exact ``[REDACTED]`` marker -- are locked in:
      * a secret value containing a backslash must match as an exact literal
        (the backslash must not be re-interpreted as a regex escape), so a
        lookalike decoy that differs from the secret is left untouched;
      * adjacent, consecutive occurrences (no separating text) must each be
        replaced by exactly one ``[REDACTED]`` literal.
    """
    try:
        from shared_tools.fake_terminal import redact_secrets
    except ImportError as exc:
        raise AssertionError(
            "FAIL_RED_REDACT_SECRETS_NOT_IMPLEMENTED: shared_tools.fake_terminal "
            "must provide a pure redact_secrets helper for training logs "
            "(REQ-85C52948B7)"
        ) from exc

    # Backslash secret: the value must be treated as an exact literal, so the
    # occurrence is redacted while a lookalike that lacks the backslashes stays.
    backslash_secret = "C:\\temp\\api\\token"
    backslash_text = (
        "path C:\\temp\\api\\token leaked; "
        "decoy C:xtempxapixtoken stays"
    )
    backslash_result = redact_secrets(backslash_text, [backslash_secret])

    assert backslash_secret not in backslash_result, (
        "REDACT_SECRETS: a non-empty supplied secret containing a backslash "
        "must be redacted (REQ-85C52948B7)"
    )
    assert "C:xtempxapixtoken" in backslash_result, (
        "REDACT_SECRETS: a backslash in a supplied secret must match as an "
        "exact literal, so a lookalike decoy that differs from the secret "
        "must stay (REQ-85C52948B7)"
    )
    assert backslash_result == (
        "path [REDACTED] leaked; decoy C:xtempxapixtoken stays"
    ), (
        "REDACT_SECRETS: the backslash-containing secret must collapse to "
        "exactly one [REDACTED] literal (REQ-85C52948B7)"
    )
    assert backslash_result == redact_secrets(backslash_text, [backslash_secret]), (
        "REDACT_SECRETS: backslash-secret redaction must be deterministic "
        "(REQ-85C52948B7)"
    )

    # Adjacent consecutive occurrences (no separating text): every occurrence,
    # including consecutive ones, must become exactly one [REDACTED] literal.
    adjacent_text = "AAAABBBBAAAABBBB"
    adjacent_result = redact_secrets(adjacent_text, ["AAAA", "BBBB"])

    assert "AAAA" not in adjacent_result and "BBBB" not in adjacent_result, (
        "REDACT_SECRETS: no supplied secret value may survive redaction "
        "(REQ-85C52948B7)"
    )
    assert adjacent_result == "[REDACTED][REDACTED][REDACTED][REDACTED]", (
        "REDACT_SECRETS: every occurrence, including adjacent consecutive "
        "ones, must be replaced by exactly one [REDACTED] literal "
        "(REQ-85C52948B7)"
    )
    assert adjacent_result.count("[REDACTED]") == 4, (
        "REDACT_SECRETS: each of the four adjacent occurrences must be "
        "redacted exactly once (REQ-85C52948B7)"
    )
    assert adjacent_result == redact_secrets(adjacent_text, ["AAAA", "BBBB"]), (
        "REDACT_SECRETS: adjacent-occurrence redaction must be deterministic "
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


def test_add_output_additive_identity_and_order_preserving() -> None:
    """REQ-F92FFC55BA: additive output accumulation is a pure concatenation.

    Reinforces the additive contract the acceptance objective calls out:
    the two supplied strings are concatenated (first + second), neither is
    dropped, and their relative order is preserved. The empty-string cases
    confirm add_output acts as an identity on the accumulated side, so no
    input is ever lost. Pure and deterministic: no state is read or written.
    """
    from shared_tools.fake_terminal import add_output

    first = "[SIMULATED] Output A"
    second = "[SIMULATED] Output B"

    # Concatenation: the result is exactly first + second.
    assert add_output(first, second) == first + second, (
        "ADDITIVE_OUTPUT: add_output must return first + second "
        "(REQ-F92FFC55BA)"
    )

    # Order preservation: first precedes second, each kept intact.
    assert add_output(first, second).startswith(first)
    assert add_output(first, second).endswith(second)
    # Additive (order-sensitive): operand order is preserved, not swapped.
    assert add_output(first, second) != add_output(second, first)

    # Additive identity: empty operands contribute nothing; none lost.
    assert add_output(first, "") == first
    assert add_output("", second) == second
    assert add_output("", "") == ""
