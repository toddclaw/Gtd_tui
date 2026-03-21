"""Tests for rotating data-file backups."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from gtd_tui.gtd.task import Task
from gtd_tui.storage.crypto import MAGIC, encrypt_data
from gtd_tui.storage.file import save_data
from gtd_tui.storage.rotating_backup import (
    create_backup_copy,
    maybe_backup_after_save,
    rotate_backups,
)


def _touch_backup(backup_dir: Path, when: datetime, *, encrypted: bool = False) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = when.strftime("%Y-%m-%d_%H%M%S")
    path = backup_dir / f"gtd_backup_{stamp}.{'enc' if encrypted else 'json'}"
    payload = b'{"tasks":[]}' if not encrypted else encrypt_data(b'{"tasks":[]}', "pw")
    path.write_bytes(payload)
    return path


def test_create_backup_copy_plain_json(tmp_path: Path) -> None:
    data = tmp_path / "data.json"
    save_data([], [], data_file=data)
    dest = create_backup_copy(data, tmp_path / "bk", gzip_backups=False)
    assert dest is not None
    assert dest.suffix == ".json"
    assert dest.read_text() == data.read_text()


def test_create_backup_copy_plain_json_gzipped(tmp_path: Path) -> None:
    import gzip

    data = tmp_path / "data.json"
    save_data([], [], data_file=data)
    dest = create_backup_copy(data, tmp_path / "bk", gzip_backups=True)
    assert dest is not None
    assert dest.suffix == ".gz"
    assert dest.stem.endswith(".json")
    with gzip.open(dest, "rt") as f:
        assert f.read() == data.read_text()


def test_create_backup_copy_encrypted(tmp_path: Path) -> None:
    data = tmp_path / "data.json"
    save_data([], [], data_file=data, password="secret")
    assert data.read_bytes()[:4] == MAGIC
    dest = create_backup_copy(data, tmp_path / "bk", gzip_backups=False)
    assert dest is not None
    assert dest.suffix == ".enc"
    assert dest.read_bytes() == data.read_bytes()


def test_rotate_keeps_daily_and_drops_old(tmp_path: Path) -> None:
    """daily_keep=N: keep 1 backup per day for the N most recent days."""
    bdir = tmp_path / "backups"
    base = datetime(2026, 1, 15, 12, 0, 0)
    paths = [_touch_backup(bdir, base - timedelta(days=i)) for i in range(10)]
    rotate_backups(bdir, daily_keep=3, weekly_keep=0, monthly_keep=0)
    remaining = sorted(bdir.glob("gtd_backup_*"))
    assert len(remaining) == 3
    assert set(remaining) == set(paths[:3])


def test_rotate_weekly_tier(tmp_path: Path) -> None:
    bdir = tmp_path / "backups"
    # Same calendar day different times — only one daily slot
    d0 = datetime(2026, 3, 1, 10, 0, 0)
    _touch_backup(bdir, d0)
    _touch_backup(bdir, d0.replace(hour=11))
    # Different ISO weeks
    _touch_backup(bdir, datetime(2026, 3, 10, 10, 0, 0))
    _touch_backup(bdir, datetime(2026, 3, 20, 10, 0, 0))
    rotate_backups(bdir, daily_keep=1, weekly_keep=2, monthly_keep=0)
    assert len(list(bdir.glob("gtd_backup_*"))) == 3


def test_maybe_backup_throttle(tmp_path: Path) -> None:
    data = tmp_path / "data.json"
    save_data([Task(title="a")], [], data_file=data)
    bdir = tmp_path / "bk"
    last = 0.0
    last = maybe_backup_after_save(
        data,
        enabled=True,
        backup_directory=str(bdir),
        daily_keep=7,
        weekly_keep=0,
        monthly_keep=0,
        throttle_minutes=60,
        last_backup_monotonic=last,
        now_monotonic=100.0,
        gzip_backups=False,
        daily_slots_per_day=1,
    )
    assert last == 100.0
    assert len(list(bdir.glob("*"))) == 1
    last2 = maybe_backup_after_save(
        data,
        enabled=True,
        backup_directory=str(bdir),
        daily_keep=7,
        weekly_keep=0,
        monthly_keep=0,
        throttle_minutes=60,
        last_backup_monotonic=last,
        now_monotonic=101.0,
        gzip_backups=False,
        daily_slots_per_day=1,
    )
    assert last2 == 100.0
    assert len(list(bdir.glob("*"))) == 1


def test_maybe_backup_disabled(tmp_path: Path) -> None:
    data = tmp_path / "data.json"
    save_data([], [], data_file=data)
    bdir = tmp_path / "bk"
    t = maybe_backup_after_save(
        data,
        enabled=False,
        backup_directory=str(bdir),
        daily_keep=7,
        weekly_keep=4,
        monthly_keep=12,
        throttle_minutes=0,
        last_backup_monotonic=0.0,
        now_monotonic=1.0,
    )
    assert t == 0.0
    assert not bdir.exists()
