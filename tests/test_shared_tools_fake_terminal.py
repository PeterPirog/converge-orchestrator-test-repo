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
