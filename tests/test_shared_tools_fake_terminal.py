import inspect
import types

import shared_tools.fake_terminal as _ft_module
from shared_tools.fake_terminal import format_output, run_command, simulate_command


# Intentionally broad: any reference to subprocess/os/spawn/exec/eval or common
# execution-oriented names in co_names is a compliance tripwire.
_PROHIBITED_GLOBALS = frozenset({
    "subprocess", "os", "system", "Popen", "popen", "call", "run",
    "check_call", "check_output", "getoutput", "getstatusoutput",
    "spawn", "exec", "eval", "execfile", "shell",
})


def test_run_command_is_deterministic_and_non_executing() -> None:
    command = "echo SHOULD_NOT_RUN"

    result = run_command(command)

    assert result == (
        "[SIMULATED] Executing: echo SHOULD_NOT_RUN\n"
        "[SIMULATED] Output placeholder"
    )


def test_format_output_wraps_terminal_fence() -> None:
    assert format_output("line one\nline two") == "```terminal\nline one\nline two\n```"


def test_simulate_command_structured_simulation_req_f92ffc55ba() -> None:
    """simulate_command structured simulation (REQ-F92FFC55BA) returns dict with stdout mirroring run_command."""
    from shared_tools.fake_terminal import simulate_command

    command = "echo SHOULD_NOT_RUN"

    result = simulate_command(command)

    assert isinstance(result, dict)
    assert result["stdout"] == run_command(command)
    # command text is inert data: no real execution, deterministic fake output
    assert simulate_command("rm -rf /")["stdout"].startswith("[SIMULATED] Executing:")


def test_simulate_command_structured_simulation_req_0c50be10f3() -> None:
    """ACCEPT-001 / REQ-0C50BE10F3: structured command simulation returns a
    dict whose stdout mirrors run_command and whose command string is inert.
    """
    command = "ls -la"
    result = simulate_command(command)

    assert isinstance(result, dict)
    assert set(result.keys()) == {"stdout"}
    assert result["stdout"] == run_command(command)
    assert result["stdout"] == (
        f"[SIMULATED] Executing: {command}\n"
        "[SIMULATED] Output placeholder"
    )
    # command string is inert: dangerous-looking input still yields only simulated wrapper output
    assert simulate_command("rm -rf /")["stdout"].startswith("[SIMULATED] Executing:")


def test_simulate_command_structured_simulation_req_413a5b74fd() -> None:
    """ACCEPT-001 / REQ-413A5B74FD: structured command simulation returns a
    dict with exactly stdout mirroring run_command, and command text is inert data.
    """
    import os

    command = "ls -la"
    result = simulate_command(command)

    assert isinstance(result, dict)
    assert set(result.keys()) == {"stdout"}
    assert result["stdout"] == run_command(command)

    # Inert command text: an injection payload that would create a canary file
    # if executed is treated purely as data; output stays the simulated wrapper.
    canary = "/tmp/opencode/simulate_command_injection_canary"
    assert not os.path.exists(canary), "canary already exists before test"
    injection = f"touch {canary}"
    injected = simulate_command(injection)
    assert isinstance(injected, dict)
    assert set(injected.keys()) == {"stdout"}
    assert injected["stdout"] == run_command(injection)
    assert injected["stdout"].startswith("[SIMULATED] Executing:")
    assert not os.path.exists(canary), "simulate_command executed the injection payload"


def _iter_code_objects(code: types.CodeType):
    yield code
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            yield from _iter_code_objects(const)


def _module_top_level_code(module: types.ModuleType) -> types.CodeType | None:
    spec = getattr(module, "__spec__", None)
    loader = getattr(spec, "loader", None)
    if loader is not None and hasattr(loader, "get_code"):
        try:
            code = loader.get_code(module.__name__)
            if isinstance(code, types.CodeType):
                return code
        except Exception:
            return None
    return None


def test_fake_terminal_code_objects_reference_no_subprocess_or_os_shell_execution_globals() -> None:
    """REQ-879DB2129D: compiled code objects must not reference subprocess/os/shell globals."""
    seen: set[int] = set()

    def visit(code: types.CodeType) -> None:
        for co in _iter_code_objects(code):
            if id(co) in seen:
                continue
            seen.add(id(co))
            offenders = sorted(set(co.co_names) & _PROHIBITED_GLOBALS)
            assert not offenders, (
                f"{co.co_name} references prohibited execution globals: {offenders}"
            )

    module_code = _module_top_level_code(_ft_module)
    if module_code is not None:
        visit(module_code)

    for obj in vars(_ft_module).values():
        if inspect.isfunction(obj):
            visit(obj.__code__)
        elif inspect.isclass(obj):
            for attr in vars(obj).values():
                if inspect.isfunction(attr):
                    visit(attr.__code__)
