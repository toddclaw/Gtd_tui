"""Tests for single-instance lockfile."""

from __future__ import annotations

from pathlib import Path

from gtd_tui.storage.lockfile import (
    lockfile_path,
    release_lock,
    try_acquire_lock,
)


def test_try_acquire_lock_success(tmp_path: Path) -> None:
    assert try_acquire_lock(tmp_path)
    assert lockfile_path(tmp_path).exists()


def test_try_acquire_lock_fails_when_held(tmp_path: Path) -> None:
    assert try_acquire_lock(tmp_path)
    assert not try_acquire_lock(tmp_path)


def test_release_lock_removes_file(tmp_path: Path) -> None:
    try_acquire_lock(tmp_path)
    assert lockfile_path(tmp_path).exists()
    release_lock(tmp_path)
    assert not lockfile_path(tmp_path).exists()


def test_release_lock_idempotent(tmp_path: Path) -> None:
    release_lock(tmp_path)
    release_lock(tmp_path)


def test_acquire_after_release(tmp_path: Path) -> None:
    assert try_acquire_lock(tmp_path)
    release_lock(tmp_path)
    assert try_acquire_lock(tmp_path)
