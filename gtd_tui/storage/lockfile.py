"""Single-instance lockfile to prevent concurrent gtd-tui processes on the same DB."""

from __future__ import annotations

import os
from pathlib import Path


def lockfile_path(data_dir: Path) -> Path:
    """Return the lockfile path for the given data directory."""
    return data_dir / ".gtd_tui.lock"


def try_acquire_lock(data_dir: Path) -> bool:
    """Create the lockfile atomically if it does not exist.

    Return True if acquired, False if another process holds it.
    Uses O_CREAT|O_EXCL for atomic create-if-not-exists.
    """
    path = lockfile_path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(
            str(path),
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
        )
        try:
            os.write(fd, str(os.getpid()).encode())
        finally:
            os.close(fd)
        return True
    except FileExistsError:
        return False
    except OSError:
        return False


def release_lock(data_dir: Path) -> None:
    """Remove the lockfile. Idempotent."""
    path = lockfile_path(data_dir)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
