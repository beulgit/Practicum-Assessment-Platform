"""
runner.py
Executes a Python program (as text) against a single stdin input, safely
(as far as plain subprocess allows -- see sandbox.py for caveats), and
returns stdout / stderr / timing / timeout information.
"""

import subprocess
import sys
import os
import shutil
import time
import dataclasses
from typing import Optional

from execution.sandbox import (
    make_restricted_env,
    make_temp_workdir,
    preexec_fn_factory,
    WALL_CLOCK_TIMEOUT_SECONDS,
    MAX_OUTPUT_BYTES,
)


@dataclasses.dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    returncode: Optional[int]
    execution_time: float
    timed_out: bool
    error_type: Optional[str] = None


def _classify_error(stderr: str, returncode: Optional[int] = None) -> Optional[str]:
    # On POSIX, subprocess reports a negative returncode equal to -signum
    # when the child was killed by a signal. SIGXCPU (24) fires when our
    # RLIMIT_CPU is exceeded, SIGKILL (9) is used for hard termination.
    if returncode is not None and returncode < 0:
        sig = -returncode
        if sig in (24, 9, 25):  # SIGXCPU, SIGKILL, SIGVTALRM
            return "Timeout"
        return f"Terminated by signal {sig}"
    if not stderr:
        return None
    known = [
        "SyntaxError", "IndentationError", "NameError", "TypeError", "ValueError",
        "IndexError", "KeyError", "ZeroDivisionError", "AttributeError",
        "ImportError", "ModuleNotFoundError", "RecursionError", "FileNotFoundError",
        "OverflowError", "MemoryError",
    ]
    for err in known:
        if err in stderr:
            return err
    return "RuntimeError"


def run_student_code(code: str, stdin_data: str,
                      timeout: int = WALL_CLOCK_TIMEOUT_SECONDS) -> ExecutionResult:
    """
    Runs `code` as a standalone Python script, feeding `stdin_data` on stdin.
    Executes in an isolated temp directory with a restricted environment and
    (on POSIX) CPU/memory rlimits. See execution/sandbox.py for the documented
    limitations of this approach.
    """
    workdir = make_temp_workdir()
    script_path = os.path.join(workdir, "submission.py")
    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)

        env = make_restricted_env()
        preexec_fn = preexec_fn_factory()

        start = time.time()
        timed_out = False
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "submission.py"],  # -I: isolated mode, ignores PYTHONPATH etc.
                input=stdin_data,
                cwd=workdir,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
                preexec_fn=preexec_fn,
            )
            stdout, stderr, returncode = proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired as e:
            timed_out = True
            stdout = (e.stdout or "") if isinstance(e.stdout, str) else ""
            stderr = (e.stderr or "") if isinstance(e.stderr, str) else ""
            returncode = None
        elapsed = time.time() - start

        stdout = stdout[:MAX_OUTPUT_BYTES]
        stderr = stderr[:MAX_OUTPUT_BYTES]

        error_type = "Timeout" if timed_out else _classify_error(stderr, returncode)
        if error_type == "Timeout" and not timed_out:
            # Killed by CPU rlimit (SIGXCPU) rather than the wall-clock timeout.
            timed_out = True

        return ExecutionResult(
            stdout=stdout,
            stderr=stderr,
            returncode=returncode,
            execution_time=round(elapsed, 4),
            timed_out=timed_out,
            error_type=error_type,
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
