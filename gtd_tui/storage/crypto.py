"""Encryption/decryption for the GTD data file — BACKLOG-23.

File format (binary):
    [4-byte magic][1-byte version][32-byte salt][12-byte nonce]
    [ciphertext][16-byte GCM tag]

Key derivation: scrypt with N=2**17, r=8, p=1.
Cipher: AES-256-GCM (authenticated encryption).
"""

from __future__ import annotations

import os
import struct

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC: bytes = b"GTDE"
VERSION: int = 1

_SALT_LEN = 32
_NONCE_LEN = 12
_TAG_LEN = 16  # appended by AESGCM automatically
_HEADER_LEN = 4 + 1 + _SALT_LEN + _NONCE_LEN  # magic + version + salt + nonce


class DecryptionError(Exception):
    """Raised when decryption fails (wrong password or corrupt data)."""


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = Scrypt(salt=salt, length=32, n=2**17, r=8, p=1)
    return kdf.derive(password.encode())


def encrypt_data(plaintext: bytes, password: str) -> bytes:
    """Encrypt *plaintext* with *password*. Returns the full binary blob."""
    salt = os.urandom(_SALT_LEN)
    nonce = os.urandom(_NONCE_LEN)
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, None)
    header = MAGIC + struct.pack("B", VERSION) + salt + nonce
    return header + ciphertext_with_tag


def decrypt_data(blob: bytes, password: str) -> bytes:
    """Decrypt *blob* with *password*. Raises DecryptionError on failure."""
    if len(blob) < _HEADER_LEN + _TAG_LEN:
        raise DecryptionError("Data too short to be a valid encrypted file")
    if blob[:4] != MAGIC:
        raise DecryptionError("Missing magic header")
    offset = 4
    _version = struct.unpack("B", blob[offset : offset + 1])[0]
    offset += 1
    salt = blob[offset : offset + _SALT_LEN]
    offset += _SALT_LEN
    nonce = blob[offset : offset + _NONCE_LEN]
    offset += _NONCE_LEN
    ciphertext_with_tag = blob[offset:]
    try:
        key = _derive_key(password, salt)
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext_with_tag, None)
    except Exception as exc:
        raise DecryptionError("Incorrect password or corrupt data") from exc


def is_encrypted(data: bytes) -> bool:
    """Return True if *data* starts with the GTD encryption magic header."""
    return len(data) >= 4 and data[:4] == MAGIC
