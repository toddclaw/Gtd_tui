"""Rotating file backups for the GTD data file (plain JSON or encrypted blob)."""

from __future__ import annotations

import gzip
import json
import re
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from platformdirs import user_data_dir

from gtd_tui.storage.crypto import MAGIC, is_encrypted

# Minimum reasonable uncompressed size for a valid backup (guards against truncation)
_MIN_VALID_JSON_BYTES = 20

# Supports both uncompressed (.json, .enc) and gzipped (.json.gz, .enc.gz)
_BACKUP_NAME_RE = re.compile(
    r"^gtd_backup_(\d{4}-\d{2}-\d{2}_\d{6})\.(json|enc)(\.gz)?$"
)


@dataclass(frozen=True)
class _BackupFile:
    path: Path
    when: datetime


def _default_backup_dir() -> Path:
    return Path(user_data_dir("gtd_tui")) / "backups"


def _parse_backup(path: Path) -> _BackupFile | None:
    m = _BACKUP_NAME_RE.match(path.name)
    if not m:
        return None
    try:
        when = datetime.strptime(m.group(1), "%Y-%m-%d_%H%M%S")
    except ValueError:
        return None
    return _BackupFile(path=path, when=when)


def _list_backups(backup_dir: Path) -> list[_BackupFile]:
    if not backup_dir.is_dir():
        return []
    out: list[_BackupFile] = []
    for p in backup_dir.iterdir():
        if p.is_file():
            parsed = _parse_backup(p)
            if parsed is not None:
                out.append(parsed)
    out.sort(key=lambda b: b.when, reverse=True)
    return out


def rotate_backups(
    backup_dir: Path,
    *,
    daily_keep: int,
    daily_slots_per_day: int = 1,
    weekly_keep: int = 4,
    monthly_keep: int = 12,
) -> None:
    """Keep tiered backups; delete files that fall outside retention.

    daily_keep: number of calendar days to retain.
    daily_slots_per_day: max backups to keep per calendar day (1 = one per day).
    A keep count of 0 disables that tier. If all tiers are 0, nothing is deleted.
    """
    if daily_keep <= 0 and weekly_keep <= 0 and monthly_keep <= 0:
        return
    files = _list_backups(backup_dir)
    if not files:
        return

    selected: set[Path] = set()
    if daily_keep > 0:
        slots = max(1, daily_slots_per_day)
        days_seen: set[date] = set()
        day_counts: dict[date, int] = {}
        for bf in files:
            d = bf.when.date()
            if slots == 1:
                if d not in days_seen and len(days_seen) < daily_keep:
                    selected.add(bf.path)
                    days_seen.add(d)
            else:
                if d not in days_seen:
                    if len(days_seen) >= daily_keep:
                        continue
                    days_seen.add(d)
                n = day_counts.get(d, 0)
                if n < slots:
                    selected.add(bf.path)
                    day_counts[d] = n + 1

    if weekly_keep > 0:
        weeks_used: set[tuple[int, int]] = set()
        for bf in files:
            if bf.path in selected:
                continue
            iso = bf.when.isocalendar()
            key = (iso.year, iso.week)
            if key not in weeks_used and len(weeks_used) < weekly_keep:
                selected.add(bf.path)
                weeks_used.add(key)

    if monthly_keep > 0:
        months_used: set[tuple[int, int]] = set()
        for bf in files:
            if bf.path in selected:
                continue
            key = (bf.when.year, bf.when.month)
            if key not in months_used and len(months_used) < monthly_keep:
                selected.add(bf.path)
                months_used.add(key)

    for bf in files:
        if bf.path not in selected:
            try:
                bf.path.unlink()
            except OSError:
                pass


def _validate_backup(dest: Path, gzipped: bool, encrypted: bool) -> bool:
    """Verify the backup is readable and has expected structure. Returns True if valid."""
    try:
        if gzipped:
            with gzip.open(dest, "rb") as f:
                raw = f.read()
        else:
            raw = dest.read_bytes()
        if len(raw) < _MIN_VALID_JSON_BYTES:
            return False
        if encrypted:
            return len(raw) >= 4 and raw[:4] == MAGIC
        data = json.loads(raw.decode("utf-8"))
        return isinstance(data, dict) and "tasks" in data
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return False


def create_backup_copy(
    data_file: Path, backup_dir: Path, *, gzip_backups: bool = True
) -> Path | None:
    """Copy *data_file* into *backup_dir* with a timestamped name. Returns new path.

    Validates the backup after writing; on validation failure, removes the backup
    and returns None (avoids keeping truncated or corrupt backups).
    """
    if not data_file.is_file():
        return None
    try:
        raw = data_file.read_bytes()
        if len(raw) < _MIN_VALID_JSON_BYTES:
            return None
        head = raw[:4]
    except OSError:
        return None
    encrypted = is_encrypted(head)
    ext = "enc" if encrypted else "json"
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_dir.mkdir(parents=True, exist_ok=True)
    dest = backup_dir / f"gtd_backup_{stamp}.{ext}"
    if gzip_backups:
        dest = dest.with_suffix(dest.suffix + ".gz")
    try:
        if gzip_backups:
            with open(data_file, "rb") as src, gzip.open(dest, "wb") as dst:
                shutil.copyfileobj(src, dst)
        else:
            shutil.copyfile(data_file, dest)
        dest.chmod(0o600)
        if not _validate_backup(dest, gzipped=gzip_backups, encrypted=encrypted):
            dest.unlink(missing_ok=True)
            return None
    except OSError:
        dest.unlink(missing_ok=True)
        return None
    return dest


def maybe_backup_after_save(
    data_file: Path,
    *,
    enabled: bool,
    backup_directory: str,
    daily_keep: int,
    daily_slots_per_day: int = 1,
    weekly_keep: int,
    monthly_keep: int,
    throttle_minutes: int,
    last_backup_monotonic: float,
    now_monotonic: float,
    gzip_backups: bool = True,
) -> float:
    """If policy allows, copy *data_file* and rotate. Returns updated last-backup time."""
    if not enabled:
        return last_backup_monotonic
    throttle_sec = max(0, throttle_minutes) * 60
    if (
        throttle_sec > 0
        and last_backup_monotonic > 0
        and (now_monotonic - last_backup_monotonic) < throttle_sec
    ):
        return last_backup_monotonic

    bdir = (
        Path(backup_directory).expanduser()
        if backup_directory.strip()
        else _default_backup_dir()
    )
    created = create_backup_copy(data_file, bdir, gzip_backups=gzip_backups)
    if created is None:
        return last_backup_monotonic

    rotate_backups(
        bdir,
        daily_keep=daily_keep,
        daily_slots_per_day=daily_slots_per_day,
        weekly_keep=weekly_keep,
        monthly_keep=monthly_keep,
    )
    return now_monotonic
