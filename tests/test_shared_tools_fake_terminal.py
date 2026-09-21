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

    result = simulate_command("echo SHOULD_NOT_RUN")

    assert isinstance(result, dict)
    assert result["command"] == "echo SHOULD_NOT_RUN"
    assert result["exit_code"] == 0


def test_simulate_command_stdout_mirrors_run_command() -> None:
    """REQ-0C50BE10F3: simulate_command must mirror run_command's stdout (ACCEPT-001)."""
    from shared_tools.fake_terminal import simulate_command

    command = "echo SHOULD_NOT_RUN"
    result = simulate_command(command)

    assert "stdout" in result, (
        "REQ-0C50BE10F3: stdout must exactly mirror run_command"
    )
    assert result["stdout"] == run_command(command), (
        "REQ-0C50BE10F3: stdout must exactly mirror run_command"
    )


def test_fake_terminal_never_invokes_real_command_execution() -> None:
    """REQ-879DB2129D: fake_terminal must remain a pure command simulator.

    A module can only execute a real command if it holds a reference to the
    primitive that does so, or its compiled code references such a global. We
    therefore assert the imported module neither binds ``subprocess`` (plain,
    aliased, or ``from subprocess import ...``) nor any ``os``
    command-execution primitive (``os.system`` / ``os.popen`` / ``os.exec*``),
    and that no code object in the module references ``subprocess`` as a global.

    Deterministic and entirely in-memory: it inspects only the already-imported
    module's namespace and compiled code objects using value identity. It
    performs no network, environment-variable, file-system (no source read), or
    process-state access.
    """
    import os
    import subprocess
    import types

    import shared_tools.fake_terminal as fake_terminal

    # The stdlib callables that would actually execute a command / spawn a shell.
    shell_primitives = (
        os.system,
        os.popen,
        os.execv,
        os.execve,
        os.execl,
        os.execle,
        os.execlp,
        os.execvp,
        os.execvpe,
    )

    def _violation(detail: str) -> None:
        raise AssertionError(f"REQ-879DB2129D violation: {detail}")

    # (1) Module namespace: no reference to a real command-execution primitive.
    for name, value in vars(fake_terminal).items():
        if value is subprocess or value is os:
            _violation(f"{name!r} is a command-execution module")
        if any(value is primitive for primitive in shell_primitives):
            _violation(f"{name!r} is a real command-execution primitive")
        origin = getattr(value, "__module__", None)
        if isinstance(origin, str) and origin.split(".", 1)[0] == "subprocess":
            _violation(f"{name!r} originates from the subprocess package")

    # (2) Compiled code objects: no reference to the subprocess global.
    def _iter_code(code: "types.CodeType"):
        yield code
        for const in code.co_consts:
            if isinstance(const, types.CodeType):
                yield from _iter_code(const)

    for name, value in vars(fake_terminal).items():
        code = getattr(value, "__code__", None)
        if not isinstance(code, types.CodeType):
            continue
        for frame in _iter_code(code):
            if "subprocess" in frame.co_names:
                _violation(f"{name!r} references the subprocess global")


def test_simulate_command_treats_injection_payload_as_inert_data() -> None:
    """REQ-413A5B74FD: prove structure and that command text is inert data (ACCEPT-001).

    A shell-injection payload must be embedded verbatim in the returned
    ``command`` and ``stdout`` fields, proving the command text is treated as
    inert data, not executed. Deterministic: no network, env-var, file-system,
    or process-state access.
    """
    from shared_tools.fake_terminal import simulate_command

    payload = "touch /tmp/never_created_413a5b74fd && echo INJECTED"

    result = simulate_command(payload)

    # (1) Returned structure: exactly the four expected keys.
    assert isinstance(result, dict)
    assert set(result) == {"command", "exit_code", "simulated", "stdout"}

    # (2) Command text is treated as inert data: embedded verbatim, never executed.
    assert result["command"] == payload
    assert result["exit_code"] == 0
    assert result["simulated"] is True
    assert payload in result["stdout"]


def test_redact_secrets_replaces_nonempty_secret_values() -> None:
    """REQ-85C52948B7: redact_secrets redacts non-empty secrets (ACCEPT-002).

    A pure, deterministic helper for training logs: every non-empty supplied
    secret value that occurs in ``text`` is replaced by the fixed ``[REDACTED]``
    placeholder; empty-string supplied secrets are ignored and never used as
    replacement targets; text containing none of the supplied secrets is
    returned unchanged; and repeated calls with identical input return
    identical output.
    """
    import shared_tools.fake_terminal as fake_terminal

    redact_secrets = getattr(fake_terminal, "redact_secrets", None)
    assert redact_secrets is not None, (
        "REQ-85C52948B7: redact_secrets helper must exist (ACCEPT-002)"
    )

    # (1) Every non-empty supplied secret occurring in the text is absent from
    # the result, with the fixed '[REDACTED]' placeholder present in its place.
    text = "api_key=sk-abc123 user=bob token=sk-abc123"
    secrets = ["sk-abc123", "hunter2"]

    result = redact_secrets(text, secrets)

    assert "sk-abc123" not in result
    assert result.count("[REDACTED]") == 2
    assert result == "api_key=[REDACTED] user=bob token=[REDACTED]"
    # A supplied secret that does not occur in the text leaves no trace.
    assert "hunter2" not in result

    # (2) An empty-string secret in the supplied set is ignored: the text is
    # returned unchanged and no placeholder is inserted.
    assert redact_secrets("hello world", [""]) == "hello world"

    # (3) Text containing none of the supplied secrets is returned unchanged.
    assert redact_secrets("hello world", ["sk-abc123"]) == "hello world"

    # (4) Deterministic: repeated calls with identical input return identical
    # output.
    assert redact_secrets(text, secrets) == result
    assert redact_secrets(text, secrets) == result
