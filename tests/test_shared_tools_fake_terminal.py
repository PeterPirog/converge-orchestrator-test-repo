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
