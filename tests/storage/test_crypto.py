"""Unit tests for gtd_tui.storage.crypto — BACKLOG-23."""
from __future__ import annotations

import pytest

from gtd_tui.storage.crypto import (
    MAGIC,
    DecryptionError,
    decrypt_data,
    encrypt_data,
    is_encrypted,
)


def test_encrypt_decrypt_round_trip() -> None:
    plaintext = b'{"tasks": [], "folders": []}'
    password = "hunter2"
    ciphertext = encrypt_data(plaintext, password)
    result = decrypt_data(ciphertext, password)
    assert result == plaintext


def test_encrypted_output_is_binary_and_not_plaintext() -> None:
    plaintext = b'{"tasks": [], "folders": []}'
    ciphertext = encrypt_data(plaintext, "password")
    assert ciphertext != plaintext
    assert b"tasks" not in ciphertext


def test_magic_header_present() -> None:
    plaintext = b'{"tasks": [], "folders": []}'
    ciphertext = encrypt_data(plaintext, "password")
    assert ciphertext[:4] == MAGIC


def test_is_encrypted_true_for_encrypted_data() -> None:
    plaintext = b'{"tasks": [], "folders": []}'
    ciphertext = encrypt_data(plaintext, "password")
    assert is_encrypted(ciphertext) is True


def test_is_encrypted_false_for_plaintext_json() -> None:
    plaintext = b'{"tasks": [], "folders": []}'
    assert is_encrypted(plaintext) is False


def test_is_encrypted_false_for_empty_bytes() -> None:
    assert is_encrypted(b"") is False


def test_wrong_password_raises_decryption_error() -> None:
    plaintext = b'{"tasks": [], "folders": []}'
    ciphertext = encrypt_data(plaintext, "correct_password")
    with pytest.raises(DecryptionError):
        decrypt_data(ciphertext, "wrong_password")


def test_corrupt_data_raises_decryption_error() -> None:
    plaintext = b'{"tasks": [], "folders": []}'
    ciphertext = bytearray(encrypt_data(plaintext, "password"))
    # Flip a byte in the ciphertext portion (after the header)
    ciphertext[50] ^= 0xFF
    with pytest.raises(DecryptionError):
        decrypt_data(bytes(ciphertext), "password")


def test_each_encrypt_produces_different_ciphertext() -> None:
    """Random salt and nonce mean two encryptions are never identical."""
    plaintext = b'{"tasks": [], "folders": []}'
    ct1 = encrypt_data(plaintext, "password")
    ct2 = encrypt_data(plaintext, "password")
    assert ct1 != ct2


def test_decrypt_truncated_data_raises_decryption_error() -> None:
    """Truncated blobs (missing GCM tag or nonce) must not crash silently."""
    plaintext = b'{"tasks": [], "folders": []}'
    ciphertext = encrypt_data(plaintext, "password")
    with pytest.raises(DecryptionError):
        decrypt_data(ciphertext[:20], "password")
