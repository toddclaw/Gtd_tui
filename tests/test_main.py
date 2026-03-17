"""Tests for __main__ CLI entry point."""

from __future__ import annotations

import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# _detect_password
# ---------------------------------------------------------------------------


def test_detect_password_returns_none_when_no_file(tmp_path: Path) -> None:
    """Returns None immediately when the data file does not exist."""
    from gtd_tui.__main__ import _detect_password

    result = _detect_password(tmp_path / "missing.json")
    assert result is None


def test_detect_password_returns_none_for_plaintext_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Returns None for an unencrypted file without prompting."""
    from gtd_tui.__main__ import _detect_password
    from gtd_tui.storage.file import save_data

    data_file = tmp_path / "data.json"
    save_data([], [], data_file=data_file)

    called = []
    monkeypatch.setattr("getpass.getpass", lambda prompt="": called.append(prompt))

    result = _detect_password(data_file)

    assert result is None
    assert called == [], "getpass should not be called for plaintext files"


def test_detect_password_correct_password_returns_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Returns the password string when the correct password is supplied."""
    from gtd_tui.__main__ import _detect_password
    from gtd_tui.storage.file import save_data

    data_file = tmp_path / "data.json"
    save_data([], [], data_file=data_file, password="secret")
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "secret")

    result = _detect_password(data_file)

    assert result == "secret"


def test_detect_password_wrong_password_exits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exits with code 1 when the password is wrong."""
    from gtd_tui.__main__ import _detect_password
    from gtd_tui.storage.file import save_data

    data_file = tmp_path / "data.json"
    save_data([], [], data_file=data_file, password="correct")
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "wrong")

    with pytest.raises(SystemExit) as exc_info:
        _detect_password(data_file)

    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# _cmd_encrypt
# ---------------------------------------------------------------------------


def test_cmd_encrypt_exits_when_file_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exits with code 1 when the data file does not exist."""
    from gtd_tui.__main__ import _cmd_encrypt

    with pytest.raises(SystemExit) as exc_info:
        _cmd_encrypt(tmp_path / "missing.json")

    assert exc_info.value.code == 1


def test_cmd_encrypt_exits_when_already_encrypted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exits with code 1 when the file is already encrypted."""
    from gtd_tui.__main__ import _cmd_encrypt
    from gtd_tui.storage.file import save_data

    data_file = tmp_path / "data.json"
    save_data([], [], data_file=data_file, password="existing")
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "new")

    with pytest.raises(SystemExit) as exc_info:
        _cmd_encrypt(data_file)

    assert exc_info.value.code == 1


def test_cmd_encrypt_exits_when_passwords_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exits with code 1 when the two password prompts do not match."""
    from gtd_tui.__main__ import _cmd_encrypt
    from gtd_tui.storage.file import save_data

    data_file = tmp_path / "data.json"
    save_data([], [], data_file=data_file)

    prompts: list[str] = ["first", "second"]
    monkeypatch.setattr("getpass.getpass", lambda prompt="": prompts.pop(0))

    with pytest.raises(SystemExit) as exc_info:
        _cmd_encrypt(data_file)

    assert exc_info.value.code == 1


def test_cmd_encrypt_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Encrypts the file so that subsequent load requires the password."""
    from gtd_tui.__main__ import _cmd_encrypt
    from gtd_tui.gtd.operations import add_task
    from gtd_tui.storage.file import load_tasks, save_data

    data_file = tmp_path / "data.json"
    tasks = add_task([], "Test task")
    save_data(tasks, [], data_file=data_file)

    monkeypatch.setattr("getpass.getpass", lambda prompt="": "mypassword")

    _cmd_encrypt(data_file)

    captured = capsys.readouterr()
    assert "encrypted" in captured.out.lower()
    # File should now require password to load
    loaded = load_tasks(data_file, password="mypassword")
    assert any(t.title == "Test task" for t in loaded)


# ---------------------------------------------------------------------------
# _cmd_decrypt
# ---------------------------------------------------------------------------


def test_cmd_decrypt_exits_when_file_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exits with code 1 when the data file does not exist."""
    from gtd_tui.__main__ import _cmd_decrypt

    with pytest.raises(SystemExit) as exc_info:
        _cmd_decrypt(tmp_path / "missing.json")

    assert exc_info.value.code == 1


def test_cmd_decrypt_exits_when_not_encrypted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exits with code 1 when the file is already plaintext."""
    from gtd_tui.__main__ import _cmd_decrypt
    from gtd_tui.storage.file import save_data

    data_file = tmp_path / "data.json"
    save_data([], [], data_file=data_file)

    with pytest.raises(SystemExit) as exc_info:
        _cmd_decrypt(data_file)

    assert exc_info.value.code == 1


def test_cmd_decrypt_exits_on_wrong_password(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exits with code 1 when the supplied password is wrong."""
    from gtd_tui.__main__ import _cmd_decrypt
    from gtd_tui.storage.file import save_data

    data_file = tmp_path / "data.json"
    save_data([], [], data_file=data_file, password="correct")
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "wrong")

    with pytest.raises(SystemExit) as exc_info:
        _cmd_decrypt(data_file)

    assert exc_info.value.code == 1


def test_cmd_decrypt_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Decrypts the file so that subsequent load needs no password."""
    from gtd_tui.__main__ import _cmd_decrypt
    from gtd_tui.gtd.operations import add_task
    from gtd_tui.storage.file import load_tasks, save_data

    data_file = tmp_path / "data.json"
    tasks = add_task([], "Encrypted task")
    save_data(tasks, [], data_file=data_file, password="mypassword")

    monkeypatch.setattr("getpass.getpass", lambda prompt="": "mypassword")

    _cmd_decrypt(data_file)

    captured = capsys.readouterr()
    assert "decrypted" in captured.out.lower()
    # File should now load without a password
    loaded = load_tasks(data_file)
    assert any(t.title == "Encrypted task" for t in loaded)


# ---------------------------------------------------------------------------
# Existing summary tests
# ---------------------------------------------------------------------------


def test_summary_flag_prints_today_tasks(tmp_path: Path, capsys) -> None:
    """--summary prints today's tasks to stdout and exits with code 0."""
    from gtd_tui.__main__ import _print_summary
    from gtd_tui.gtd.operations import add_task
    from gtd_tui.storage.file import save_data

    data_file = tmp_path / "data.json"
    tasks = add_task([], "Morning run")
    save_data(tasks, [], data_file=data_file)

    _print_summary(data_file=data_file)

    captured = capsys.readouterr()
    assert "Morning run" in captured.out
    assert "Today" in captured.out


def test_summary_empty_list(tmp_path: Path, capsys) -> None:
    """--summary with no tasks prints Today (0) and no task lines."""
    from gtd_tui.__main__ import _print_summary
    from gtd_tui.storage.file import save_data

    data_file = tmp_path / "data.json"
    save_data([], [], data_file=data_file)

    _print_summary(data_file=data_file)

    captured = capsys.readouterr()
    assert "Today" in captured.out
    assert "Morning run" not in captured.out
