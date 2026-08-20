"""
sandbox.py

Best-effort local sandboxing for running untrusted student Python code with
plain `subprocess` (no Docker). This is NOT a true security boundary -- a
determined student could still find ways to abuse the host if they inspect
the source. It is meant to catch accidental problems (infinite loops, huge
memory use, obviously destructive calls) in a classroom setting, not to
survive a malicious attacker.

LIMITATIONS (documented, not hidden):
- True filesystem/network isolation is only reliably achieved with an OS-level
  sandbox: Docker/Podman containers, gVisor, firejail, or a VM. This module
  does not provide that.
- `resource` limits (RLIMIT_CPU, RLIMIT_AS, etc.) only work on POSIX systems
  (Linux/macOS). On Windows they are skipped and we rely on the wall-clock
  timeout only.
- We cannot fully block outbound network access from a plain subprocess on
  most OSes without OS-level firewalling; we only strip proxy/network-ish
  environment variables and rely on the timeout + code review by the teacher.

RECOMMENDATION FOR PRODUCTION / COLLEGE SERVER DEPLOYMENT:
Run student code inside a locked-down Docker container per submission:
  - `--network none`
  - `--read-only` filesystem with a small writable tmpfs
  - `--memory` / `--cpus` limits
  - a non-root user
  - `--pids-limit` to stop fork bombs
This module exposes `build_subprocess_kwargs()` and `preexec_fn` so swapping
the executor for a `docker run ...` wrapper later is a small change.
"""

import os
import sys
import tempfile

IS_POSIX = os.name == "posix"

# Resource limits (POSIX only)
CPU_TIME_LIMIT_SECONDS = 5           # RLIMIT_CPU
MAX_MEMORY_BYTES = 256 * 1024 * 1024  # 256 MB, RLIMIT_AS
MAX_OUTPUT_BYTES = 1 * 1024 * 1024    # truncate captured stdout/stderr at 1 MB
WALL_CLOCK_TIMEOUT_SECONDS = 6


def make_restricted_env():
    """A minimal environment with network/proxy-ish and sensitive vars stripped."""
    keep_keys = {"PATH", "SYSTEMROOT", "PATHEXT"} if not IS_POSIX else {"PATH"}
    env = {k: v for k, v in os.environ.items() if k in keep_keys}
    # Explicitly make sure nothing sensitive leaks through
    for sensitive in ("AWS_SECRET_ACCESS_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                       "DATABASE_URL", "SECRET_KEY"):
        env.pop(sensitive, None)
    return env


def make_temp_workdir():
    """A fresh, empty temp directory the student process runs inside."""
    return tempfile.mkdtemp(prefix="submission_")


def preexec_fn_factory():
    """
    Returns a function to run in the child process (POSIX only) right after
    fork(), before exec(). Sets CPU time + address-space (memory) limits.
    Returns None on non-POSIX platforms (Windows) since `resource` isn't
    available there.
    """
    if not IS_POSIX:
        return None

    def _limit_resources():
        import resource
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (CPU_TIME_LIMIT_SECONDS, CPU_TIME_LIMIT_SECONDS))
        except Exception:
            pass
        try:
            resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY_BYTES, MAX_MEMORY_BYTES))
        except Exception:
            pass
        try:
            # Limit number of child processes / fork bombs
            resource.setrlimit(resource.RLIMIT_NPROC, (32, 32))
        except Exception:
            pass

    return _limit_resources
