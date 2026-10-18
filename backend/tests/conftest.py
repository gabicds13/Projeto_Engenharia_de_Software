"""Fixtures compartilhadas dos testes do BFF."""
from __future__ import annotations

import os

import pytest

# Garante configuração determinística antes de importar a app.
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("USE_MOCKS", "true")
os.environ.setdefault("JWT_SECRET", "test-secret")


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import create_app

    return TestClient(create_app())
