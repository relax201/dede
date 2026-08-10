"""Unit tests — security helpers"""

from __future__ import annotations

import os

import pytest

# Ensure settings can load during import
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-chars!!")
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost:5432/tasi")

from app.core.security import Role, create_access_token, decode_token, has_min_role, hash_password, verify_password


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("S3cure!Pass")
    assert verify_password("S3cure!Pass", hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_roundtrip() -> None:
    token = create_access_token("user-123", Role.ANALYST)
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "analyst"


def test_rbac_hierarchy() -> None:
    assert has_min_role(Role.ADMIN, Role.ANALYST)
    assert has_min_role(Role.ANALYST, Role.USER)
    assert not has_min_role(Role.USER, Role.ADMIN)
