"""Symmetric encryption for Strava tokens at rest."""

from __future__ import annotations

from cryptography.fernet import Fernet


def encrypt_token(plaintext: str, key: str) -> str:
    """Encrypt a token string using Fernet symmetric encryption."""
    f = Fernet(key.encode() if isinstance(key, str) else key)
    return f.encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str, key: str) -> str:
    """Decrypt a Fernet-encrypted token string."""
    f = Fernet(key.encode() if isinstance(key, str) else key)
    return f.decrypt(ciphertext.encode()).decode()
