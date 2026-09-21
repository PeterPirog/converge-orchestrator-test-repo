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


def test_redact_secrets_contract_exact_literal_empty_ignored_repeated() -> None:
    """REQ-A59E470230: redact_secrets deterministic redaction contract (ACCEPT-002).

    Pins the exact-literal, empty-ignored, and repeated-occurrence behavior:
    every non-empty supplied secret is replaced by the exact literal
    ``[REDACTED]``, empty-string supplied secrets are ignored, and all repeated
    occurrences of a secret are redacted. Pure and deterministic: it inspects
    only the already-imported helper and performs no subprocess, os.system /
    os.popen / os.exec*, network, environment-variable, file-system, or
    process-state access.
    """
    import shared_tools.fake_terminal as fake_terminal

    redact_secrets = getattr(fake_terminal, "redact_secrets", None)
    assert redact_secrets is not None, (
        "REQ-A59E470230: redact_secrets helper must exist (ACCEPT-002)"
    )

    # (a) A non-empty secret is replaced by the exact literal '[REDACTED]'.
    fixture = "redaction-test-value"
    text = f"prefix {fixture} suffix"
    result = redact_secrets(text, [fixture])
    assert result == "prefix [REDACTED] suffix", (
        "REQ-A59E470230: non-empty secret must be replaced by the exact "
        "literal '[REDACTED]'"
    )
    assert fixture not in result

    # (b) An empty-string secret is ignored: text is left unchanged and no
    # placeholder is inserted.
    empty_only = redact_secrets("hello world", [""])
    assert empty_only == "hello world", (
        "REQ-A59E470230: an empty-string secret must be ignored"
    )
    assert "[REDACTED]" not in empty_only, (
        "REQ-A59E470230: an empty-string secret must insert no placeholder"
    )

    # (c) Two occurrences of the same secret both become '[REDACTED]'.
    repeated_text = f"a={fixture} b={fixture}"
    repeated_result = redact_secrets(repeated_text, [fixture])
    assert repeated_result == "a=[REDACTED] b=[REDACTED]", (
        "REQ-A59E470230: every repeated occurrence of a secret must be "
        "replaced by '[REDACTED]'"
    )
    assert repeated_result.count("[REDACTED]") == 2
    assert fixture not in repeated_result

    # (d) Deterministic: identical input across repeated calls yields identical
    # output.
    for _ in range(3):
        assert redact_secrets(repeated_text, [fixture]) == repeated_result, (
            "REQ-A59E470230: repeated calls with identical input must return "
            "identical output"
        )


def test_redact_secrets_overlapping_secrets_order_independent() -> None:
    """REQ-CF0D222BF0: overlapping secrets redact identically in any order (ACCEPT-002).

    Supplying overlapping secret values (one occurring within the other) must
    yield identical redacted output regardless of the supplied iteration order.
    Pure and deterministic: it inspects only the already-imported helper and
    performs no subprocess, os.system / os.popen / os.exec*, network,
    environment-variable, file-system, or process-state access.
    """
    import shared_tools.fake_terminal as fake_terminal

    redact_secrets = getattr(fake_terminal, "redact_secrets", None)
    assert redact_secrets is not None, (
        "REQ-CF0D222BF0: redact_secrets helper must exist (ACCEPT-002)"
    )

    # Overlapping secrets: 'bc' occurs within 'abc'.
    first = redact_secrets("abc", ["abc", "bc"])
    second = redact_secrets("abc", ["bc", "abc"])

    assert first == second, (
        "REQ-CF0D222BF0: overlapping inputs must produce deterministic output "
        "independent of set/hash iteration order"
    )


def test_req_0320ab815a_redact_secrets_never_reads_external_state() -> None:
    """REQ-0320AB815A: redact_secrets reads no external state (ACCEPT-002).

    Proven deterministically: the module namespace and the helper's
    compiled code objects are scanned for external-state references, and
    the helper's code object is executed in a namespace exposing only the
    pure builtins ``sorted`` and ``len`` — any environment, file, network,
    or process capability would raise ``NameError``. No real I/O, network,
    or subprocess is performed; the in-process environment change is
    restored immediately.
    """
    import io
    import os
    import pathlib
    import shutil
    import socket
    import subprocess
    import sys
    import tempfile
    import types
    import urllib

    import shared_tools.fake_terminal as fake_terminal

    redact_secrets = getattr(fake_terminal, "redact_secrets", None)
    assert redact_secrets is not None, (
        "REQ-0320AB815A: redact_secrets helper must exist (ACCEPT-002)"
    )

    def _violation(detail: str) -> None:
        raise AssertionError(f"REQ-0320AB815A violation: {detail}")

    # (1) The module namespace exposes no external-state capability.
    forbidden_objects = (os, sys, socket, subprocess, pathlib, shutil,
                         tempfile, io, urllib, open, os.getenv, os.environ)
    for name, value in vars(fake_terminal).items():
        if any(value is item for item in forbidden_objects):
            _violation(f"{name!r} is an external-state module or object")
        if isinstance(value, io.IOBase):
            _violation(f"{name!r} is an open file handle")
        origin = getattr(value, "__module__", None)
        if isinstance(origin, str) and origin.split(".", 1)[0] in {
            "os", "sys", "socket", "subprocess", "pathlib", "shutil",
            "tempfile", "io", "urllib", "http"}:
            _violation(f"{name!r} originates from {origin!r}")

    # (2) No code object of the helper references an external-state global.
    forbidden = frozenset({
        "os", "sys", "subprocess", "socket", "open", "io", "pathlib",
        "shutil", "tempfile", "urllib", "http", "requests", "asyncio",
        "getenv", "environ", "exec", "eval", "compile", "input",
        "breakpoint", "exit", "quit", "__import__"})

    def _iter_code(code: "types.CodeType"):
        yield code
        for const in code.co_consts:
            if isinstance(const, types.CodeType):
                yield from _iter_code(const)

    code = getattr(redact_secrets, "__code__", None)
    assert isinstance(code, types.CodeType), (
        "REQ-0320AB815A: redact_secrets must be a plain Python function"
    )
    referenced = set()
    for frame in _iter_code(code):
        referenced.update(frame.co_names)
    leaked = referenced & forbidden
    assert not leaked, (
        "REQ-0320AB815A violation: redact_secrets references external-state "
        f"global(s): {sorted(leaked)}"
    )

    # (3) Purity sandbox: with only the pure builtins available, the body
    # still returns the exact deterministic redaction for the fixed input.
    fixed_text = "api_key=sk-abc123 user=bob token=sk-abc123"
    fixed_secrets = ["sk-abc123", ""]
    expected = "api_key=[REDACTED] user=bob token=[REDACTED]"
    sandbox = types.FunctionType(code, {"sorted": sorted, "len": len})
    try:
        sandbox_result = sandbox(fixed_text, fixed_secrets)
    except NameError as exc:
        _violation(
            f"redact_secrets requires external capability {exc.name!r}; it "
            "must not read environment variables, files, network resources, "
            "or process state"
        )
    assert sandbox_result == expected, (
        "REQ-0320AB815A: fixed input must yield the exact deterministic "
        "redaction output"
    )
    assert sandbox(fixed_text, fixed_secrets) == sandbox_result, (
        "REQ-0320AB815A: repeated identical input must return identical "
        "output"
    )

    # (4) Environment invariance: the real helper's output is identical even
    # while a canary environment variable is present (in-process change,
    # restored immediately).
    env_name = "REQ_0320AB815A_PURITY_CANARY"
    canary = "req0320ab815a-canary-must-never-appear"
    prior = os.environ.get(env_name)
    os.environ[env_name] = canary
    try:
        under_env = redact_secrets(fixed_text, fixed_secrets)
    finally:
        if prior is None:
            os.environ.pop(env_name, None)
        else:
            os.environ[env_name] = prior
    assert under_env == expected, (
        "REQ-0320AB815A: output must not depend on environment variables"
    )
    assert canary not in under_env, (
        "REQ-0320AB815A: redact_secrets must not read environment variables"
    )


def test_redact_secrets_duplicate_values_in_list() -> None:
    """REQ-5C3F7AB352: duplicate secret values in the input list (ACCEPT-002).

    Repeated values in the supplied secrets list must produce byte-identical
    output to passing the secret once, and duplicate empty-string entries are
    ignored. Pure and deterministic: no network, environment-variable,
    file-system, subprocess, or process-state access.
    """
    import shared_tools.fake_terminal as fake_terminal

    redact_secrets = getattr(fake_terminal, "redact_secrets", None)
    assert redact_secrets is not None, (
        "REQ-5C3F7AB352: redact_secrets helper must exist (ACCEPT-002)"
    )

    # (1) Repeated values: ['tok','tok','tok'] is byte-identical to ['tok'].
    text = "a=tok b=tok c=other"
    once = redact_secrets(text, ["tok"])
    tripled = redact_secrets(text, ["tok", "tok", "tok"])
    assert tripled == once, (
        "REQ-5C3F7AB352: duplicate secret values must produce byte-identical "
        "output to passing the secret once"
    )
    assert tripled == "a=[REDACTED] b=[REDACTED] c=other"
    assert tripled.count("[REDACTED]") == 2
    assert "tok" not in tripled

    # (2) Duplicate empty-string entries are ignored: text unchanged, no
    # placeholder inserted.
    clean = redact_secrets("hello world", ["", ""])
    assert clean == "hello world", (
        "REQ-5C3F7AB352: duplicate empty-string secrets must be ignored"
    )
    assert "[REDACTED]" not in clean
