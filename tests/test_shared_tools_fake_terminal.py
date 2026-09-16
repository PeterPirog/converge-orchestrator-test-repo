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


def test_redact_secrets_redacts_every_non_empty_supplied_secret() -> None:
    """REQ-85C52948B7: deterministic secret redaction for training logs.

    Every non-empty supplied secret value that occurs in the text must be
    redacted (no longer present in the returned text), empty supplied
    values must be ignored, and the redaction must be deterministic.
    """
    from shared_tools import fake_terminal

    assert hasattr(fake_terminal, "redact_secrets"), (
        "RED-REQ-85C52948B7-redact_secrets_not_implemented"
    )

    redact_secrets = fake_terminal.redact_secrets

    text = "api_key=sk-abc123 user=bob token=sk-abc123"
    secrets = ["sk-abc123", "hunter2", ""]

    result = redact_secrets(text, secrets)

    # Every non-empty supplied secret that occurs in the text is redacted.
    assert "sk-abc123" not in result
    # A supplied secret that does not occur in the text leaves no trace.
    assert "hunter2" not in result
    # Empty supplied values are not secrets and must be ignored.
    assert redact_secrets("plain text", [""]) == "plain text"
    # Redaction is deterministic for identical input.
    assert result == redact_secrets(text, secrets)


def test_redact_secrets_repeated_occurrences_and_empty_ignored() -> None:
    """REQ-A59E470230 (ACCEPT-002): exact-literal redaction of repeated secrets.

    Every occurrence of every non-empty supplied secret must be replaced
    with the exact literal "[REDACTED]", empty supplied secret values must
    be ignored, and the redaction must be deterministic.
    """
    from shared_tools import fake_terminal

    redact_secrets = fake_terminal.redact_secrets

    text = "token=alpha99 retry alpha99 token=alpha99 pass=beta77 end"
    secrets = ["alpha99", "", "beta77"]

    result = redact_secrets(text, secrets)

    # Every occurrence of every non-empty secret is replaced, all of them.
    assert result == (
        "token=[REDACTED] retry [REDACTED] token=[REDACTED] pass=[REDACTED] end"
    )
    assert result.count("[REDACTED]") == 4
    assert "alpha99" not in result
    assert "beta77" not in result
    # Empty supplied values are ignored: "" must not inject the literal.
    assert redact_secrets("a b c", [""]) == "a b c"
    # Deterministic: identical inputs give identical outputs...
    assert redact_secrets(text, secrets) == result
    # ...with a normalized order independent of the supplied iteration order.
    assert redact_secrets(text, ["beta77", "", "alpha99"]) == result


def test_redact_secrets_overlapping_inputs_deterministic() -> None:
    """REQ-CF0D222BF0 (ACCEPT-002): deterministic redaction of overlapping secrets.

    Overlapping secrets are supplied secret values where one is a substring
    of another (here "secret123" inside "secret1234"). redact_secrets must
    collapse such inputs to a single deterministic output, and that output
    must be independent of the iteration order the supplied collection
    happens to expose (list order, reversed list order, or an unordered set).

    The deterministic contract is: longer secrets are replaced first, ties
    broken lexicographically. So "secret1234" is redacted as a whole unit,
    leaving "api=[REDACTED] end". A shorter-first ordering would instead
    corrupt the text to "api=[REDACTED]4 end", which is what this test
    guards against.
    """
    from shared_tools import fake_terminal

    redact_secrets = fake_terminal.redact_secrets

    text = "api=secret1234 end"
    expected = "api=[REDACTED] end"

    # The same two overlapping secrets fed in every plausible iteration
    # order must all produce the identical, correct result.
    orderings = (
        ["secret123", "secret1234"],   # shorter first
        ["secret1234", "secret123"],   # longer first
        {"secret123", "secret1234"},   # unordered set
    )

    for order in orderings:
        result = redact_secrets(text, order)
        assert result == expected, (
            "REQ-CF0D222BF0: overlapping secret redaction must be deterministic "
            f"independent of iteration order (got={result!r}, order={list(order)!r})"
        )
