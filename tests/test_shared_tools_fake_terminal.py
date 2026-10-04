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
