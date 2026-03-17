from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from platformdirs import user_data_dir

from gtd_tui.app import GtdApp
from gtd_tui.gtd.dates import format_date
from gtd_tui.gtd.operations import today_tasks, upcoming_tasks
from gtd_tui.storage.crypto import DecryptionError, decrypt_data, is_encrypted
from gtd_tui.storage.file import load_folders, load_tasks, save_data

_DEFAULT_DATA_FILE = Path(user_data_dir("gtd_tui")) / "data.json"


def _detect_password(data_file: Path) -> str | None:
    """Return a password if the file is encrypted, else None.

    Prompts via getpass; exits with code 1 on wrong password.
    """
    if not data_file.exists():
        return None
    raw = data_file.read_bytes()
    if not is_encrypted(raw):
        return None
    password = getpass.getpass("Password: ")
    try:
        decrypt_data(raw, password)
    except DecryptionError:
        print("Incorrect password", file=sys.stderr)
        sys.exit(1)
    return password


def _print_summary(data_file: Path | None = None, password: str | None = None) -> None:
    """Print a plain-text summary of today's tasks to stdout and exit."""
    tasks = load_tasks(data_file, password=password)
    today = today_tasks(tasks)
    upcoming = upcoming_tasks(tasks)

    print(f"Today ({len(today)}):")
    for t in today:
        print(f"  - {t.title}")
        if t.notes:
            print(f"    {t.notes}")

    if upcoming:
        print(f"\nUpcoming ({len(upcoming)}):")
        for t in upcoming:
            date_str = format_date(t.scheduled_date) if t.scheduled_date else ""
            print(f"  - {t.title}  {date_str}")
            if t.notes:
                print(f"    {t.notes}")


def _cmd_encrypt(data_file: Path) -> None:
    """One-time migration: encrypt a plaintext data file."""
    if not data_file.exists():
        print(f"Data file not found: {data_file}", file=sys.stderr)
        sys.exit(1)
    raw = data_file.read_bytes()
    if is_encrypted(raw):
        print("File is already encrypted.", file=sys.stderr)
        sys.exit(1)
    password = getpass.getpass("New password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        sys.exit(1)
    tasks = load_tasks(data_file)
    folders = load_folders(data_file)
    save_data(tasks, folders, data_file, password=password)
    print("File encrypted successfully.")


def _cmd_decrypt(data_file: Path) -> None:
    """One-time migration: decrypt an encrypted data file back to plaintext."""
    if not data_file.exists():
        print(f"Data file not found: {data_file}", file=sys.stderr)
        sys.exit(1)
    raw = data_file.read_bytes()
    if not is_encrypted(raw):
        print("File is already plaintext.", file=sys.stderr)
        sys.exit(1)
    password = getpass.getpass("Password: ")
    try:
        decrypt_data(raw, password)  # validate password before proceeding
    except DecryptionError:
        print("Incorrect password", file=sys.stderr)
        sys.exit(1)
    tasks = load_tasks(data_file, password=password)
    folders = load_folders(data_file, password=password)
    save_data(tasks, folders, data_file, password=None)
    print("File decrypted successfully.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="gtd_tui", description="GTD TUI")
    parser.add_argument(
        "-s",
        "--summary",
        action="store_true",
        help="Print a summary of today's tasks and exit (no TUI)",
    )
    parser.add_argument(
        "--encrypt",
        action="store_true",
        help="Encrypt the data file with a password and exit",
    )
    parser.add_argument(
        "--decrypt",
        action="store_true",
        help="Decrypt the data file back to plaintext and exit",
    )
    args = parser.parse_args()

    data_file = _DEFAULT_DATA_FILE

    if args.encrypt:
        _cmd_encrypt(data_file)
        sys.exit(0)

    if args.decrypt:
        _cmd_decrypt(data_file)
        sys.exit(0)

    password = _detect_password(data_file)

    if args.summary:
        _print_summary(password=password)
        sys.exit(0)

    GtdApp(password=password).run()


if __name__ == "__main__":
    main()
