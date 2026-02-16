import os
import sys
import ctypes
from contextlib import contextmanager

# Load libc for fflush
try:
    libc = ctypes.CDLL(None)
except Exception:
    try:
        if sys.platform.startswith("darwin"):
            libc = ctypes.CDLL("libc.dylib")
        else:
            libc = ctypes.CDLL("libc.so.6")
    except Exception:
        libc = None


def flush_c_streams():
    """Flush C-level stdout and stderr."""
    if libc:
        try:
            # defined in stdio.h. usually text stream pointers are exported.
            # simpler to just fflush(NULL) which flushes all open output streams.
            libc.fflush(None)
        except Exception:
            pass


@contextmanager
def suppress_stdout_stderr():
    """
    Context manager to suppress stdout and stderr at the file descriptor level.
    This suppresses output from C extensions and subprocesses as well.
    Ensures C-level buffers are flushed to capture/suppress all output correctly.
    """
    # Flush Python buffers first
    sys.stdout.flush()
    sys.stderr.flush()

    # Flush C buffers before redirection (so we don't suppress previous desired output)
    flush_c_streams()

    # Open /dev/null
    with open(os.devnull, "w") as devnull:
        # Save existing file descriptors
        try:
            # Check if stdout/stderr have fileno
            stdout_fd = sys.stdout.fileno()
            stderr_fd = sys.stderr.fileno()
        except AttributeError, ValueError:
            yield
            return

        saved_stdout_fd = os.dup(stdout_fd)
        saved_stderr_fd = os.dup(stderr_fd)

        try:
            # Redirect stdout/stderr to /dev/null
            os.dup2(devnull.fileno(), stdout_fd)
            os.dup2(devnull.fileno(), stderr_fd)
            yield

            # Flush buffers again while redirected to ensure output goes to /dev/null
            sys.stdout.flush()
            sys.stderr.flush()
            flush_c_streams()

        finally:
            # Restore file descriptors
            os.dup2(saved_stdout_fd, stdout_fd)
            os.dup2(saved_stderr_fd, stderr_fd)
            os.close(saved_stdout_fd)
            os.close(saved_stderr_fd)
