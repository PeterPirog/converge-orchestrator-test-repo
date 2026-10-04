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


def test_simulate_command_structured_simulation_req_0c50be10f3() -> None:
    """ACCEPT-001 (REQ-0C50BE10F3): simulate_command returns deterministic structured output.

    The simulated output field mirrors run_command byte-for-byte, and hostile
    command strings are treated as inert data, producing only wrapper output.
    """
    from shared_tools.fake_terminal import simulate_command

    command = "ls -la"
    result = simulate_command(command)

    assert isinstance(result, dict)
    assert result["command"] == command
    assert result["simulated"] is True
    assert result["output"] == run_command(command)
    assert result["output"] == (
        "[SIMULATED] Executing: ls -la\n"
        "[SIMULATED] Output placeholder"
    )

    # Hostile input must be inert data, not executed.
    hostile = "rm -rf /"
    hostile_result = simulate_command(hostile)
    assert isinstance(hostile_result, dict)
    assert hostile_result["command"] == hostile
    assert hostile_result["simulated"] is True
    assert hostile_result["output"].startswith("[SIMULATED] Executing:")

    # Determinism
    assert simulate_command(command) == result
    assert simulate_command(hostile) == hostile_result


def test_fake_terminal_is_pure_in_process_simulator() -> None:
    """AST + namespace guard: fake_terminal.py performs no process execution."""
    import ast
    import inspect
    import pathlib

    import shared_tools.fake_terminal as fake_terminal

    source_path = pathlib.Path(inspect.getfile(fake_terminal))
    module_source = source_path.read_text(encoding="utf-8")
    syntax_tree = ast.parse(module_source)

    banned_modules = {"subprocess", "pty", "shell"}
    banned_names = {
        "system", "popen", "Popen",
        "spawn", "spawnl", "spawnle", "spawnlp", "spawnlpe",
        "spawnv", "spawnve", "spawnvp", "spawnvpe",
        "exec", "execl", "execle", "execlp", "execlpe",
        "execv", "execve", "execvp", "execvpe",
        "fork", "kill", "CreateProcess",
        "run", "call", "check_call", "check_output",
    }

    for node in ast.walk(syntax_tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                assert root not in banned_modules, f"banned import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            assert root not in banned_modules, f"banned import from: {node.module}"
            for alias in node.names:
                assert alias.name not in banned_names, f"banned name import: {alias.name}"
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                assert func.id not in banned_names, f"banned call: {func.id}"
            elif isinstance(func, ast.Attribute):
                assert func.attr not in banned_names, f"banned attribute call: {func.attr}"
                if isinstance(func.value, ast.Name):
                    assert not (func.value.id == "os" and func.attr == "system"), "banned os.system call"
                    assert func.value.id not in banned_modules, f"banned module call: {func.value.id}"

    exported = {name for name in dir(fake_terminal) if not name.startswith("_")}
    assert not (exported & banned_names), f"banned names in public API: {exported & banned_names}"


def test_redact_secrets_non_empty_occurrences_req_85c52948b7() -> None:
    """ACCEPT-002 (REQ-85C52948B7): redact_secrets replaces every non-empty
    secret value in text with the fixed literal '[REDACTED]'.

    Empty and None secret values are ignored deterministically; repeated calls
    with identical inputs return identical output.
    """
    import shared_tools.fake_terminal as fake_terminal

    redact_secrets = getattr(fake_terminal, "redact_secrets", None)
    assert redact_secrets is not None, "REQ-85C52948B7 redact_secrets helper missing"

    text = "password=abc123 token=xyz789"
    secrets = ["abc123", "", "xyz789", None]
    result = redact_secrets(text, secrets)

    assert result == "password=[REDACTED] token=[REDACTED]"
    assert "abc123" not in result
    assert "xyz789" not in result
    assert redact_secrets(text, secrets) == result


def test_simulate_command_structured_simulation_req_413a5b74fd() -> None:
    """ACCEPT-001 (REQ-413A5B74FD): command text is inert data in simulate_command."""
    import os

    from shared_tools.fake_terminal import simulate_command

    payload = "touch /tmp/never_created_413a5b74fd && echo INJECTED"
    canary = "/tmp/never_created_413a5b74fd"

    # Deterministic pre-call clear: remove any leftover canary from an aborted run.
    if os.path.exists(canary):
        os.remove(canary)

    result = simulate_command(payload)

    assert isinstance(result, dict)
    assert set(result) == {"command", "simulated", "output"}
    assert result["command"] == payload
    assert result["simulated"] is True
    assert result["output"] == run_command(payload)
    assert result["output"].startswith("[SIMULATED] Executing:")
    assert not os.path.exists(canary)


def test_redact_secrets_repeated_occurrences_req_a59e470230() -> None:
    """ACCEPT-002 (REQ-A59E470230): redact_secrets replaces every repeated
    occurrence of each secret with the exact literal '[REDACTED]'.

    Empty strings and ``None`` entries are ignored and never alter the text.
    Repeated occurrences of the same secret are all redacted deterministically.
    """
    from shared_tools.fake_terminal import redact_secrets

    text = (
        "alpha=secret_one beta=secret_two "
        "gamma=secret_one delta=secret_two "
        "epsilon=secret_one"
    )
    secrets = ["secret_one", None, "", "secret_two", ""]
    result = redact_secrets(text, secrets)

    assert result == (
        "alpha=[REDACTED] beta=[REDACTED] "
        "gamma=[REDACTED] delta=[REDACTED] "
        "epsilon=[REDACTED]"
    )
    assert result.count("[REDACTED]") == 5
    assert "secret_one" not in result
    assert "secret_two" not in result
    assert redact_secrets(text, secrets) == result


def test_redact_secrets_overlapping_inputs_iteration_order_req_cf0d222bf0() -> None:
    """ACCEPT-002 (REQ-CF0D222BF0): overlapping secrets produce deterministic output.

    The same overlapping secret contents, passed as an ordered list, a reversed
    list, or a set, must redact to identical output regardless of the iteration
    order of the collection.
    """
    from shared_tools.fake_terminal import redact_secrets

    text = "start=abcdef end=xyz"
    secrets = ["abc", "bcd"]

    result_forward = redact_secrets(text, secrets)
    result_reverse = redact_secrets(text, list(reversed(secrets)))
    result_set = redact_secrets(text, set(secrets))

    assert result_forward == result_reverse == result_set, (
        "REQ-CF0D222BF0 overlapping-secret output depends on iteration order"
    )


def test_redact_secrets_io_purity_req_0320ab815a(monkeypatch, tmp_path) -> None:
    """ACCEPT-002 (REQ-0320AB815A): redact_secrets reads zero external state.

    Output is derived solely from the ``text`` and ``secrets`` arguments.
    Environment variables, files, network sockets, and process state are not
    consulted, so seeding them with a secret must not alter the result.
    """
    import builtins
    import os
    import socket
    import urllib.request

    from shared_tools.fake_terminal import redact_secrets

    text = "user=alice pass=hunter2"
    secrets = ["hunter2"]
    baseline = redact_secrets(text, secrets)

    canary_secret = "ENV_FILE_SEED_0320AB815A"
    monkeypatch.setenv("REDACT_CANARY_0320AB815A", canary_secret)
    canary_path = tmp_path / "secrets.txt"
    canary_path.write_text(canary_secret, encoding="utf-8")

    calls = []

    def wrap(original, label):
        def wrapper(*args, **kwargs):
            calls.append(label)
            return original(*args, **kwargs)

        return wrapper

    monkeypatch.setattr(os, "getenv", wrap(os.getenv, "os.getenv"))
    monkeypatch.setattr(os.environ, "get", wrap(os.environ.get, "os.environ.get"))
    monkeypatch.setattr(os, "getpid", wrap(os.getpid, "os.getpid"))
    monkeypatch.setattr(builtins, "open", wrap(builtins.open, "builtins.open"))
    monkeypatch.setattr(socket, "socket", wrap(socket.socket, "socket.socket"))
    monkeypatch.setattr(
        urllib.request, "urlopen", wrap(urllib.request.urlopen, "urllib.request.urlopen")
    )

    result = redact_secrets(text, secrets)

    assert result == baseline
    assert canary_secret not in result
    assert calls == []


def test_redact_secrets_no_stdout_stderr_logging_req_5c3f7ab352(capsys) -> None:
    """ACCEPT-002 (REQ-5C3F7AB352): redact_secrets never logs input text or secret values.

    The helper performs only in-process string replacement. Even when a secret
    occurs repeatedly or empty/``None`` secrets are present, the original text
    and every non-empty secret value must never appear on stdout or stderr.
    """
    from shared_tools.fake_terminal import redact_secrets

    secret = "hunter2"
    text = f"user=alice pass={secret} token={secret}"
    secrets = [secret, "", None]

    result = redact_secrets(text, secrets)

    expected = "user=alice pass=[REDACTED] token=[REDACTED]"
    assert result == expected

    captured = capsys.readouterr()
    assert text not in captured.out, "input text leaked to stdout"
    assert secret not in captured.out, "secret value leaked to stdout"
    assert text not in captured.err, "input text leaked to stderr"
    assert secret not in captured.err, "secret value leaked to stderr"

    assert redact_secrets(text, secrets) == result
