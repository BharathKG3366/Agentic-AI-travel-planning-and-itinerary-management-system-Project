from __future__ import annotations

import os
from datetime import date, timedelta

import pytest


@pytest.fixture(autouse=True)
def isolated_memory(tmp_path, monkeypatch):
    monkeypatch.setenv("VOYAGEWISE_DB_PATH", str(tmp_path / "test_voyagewise.sqlite3"))
    # Keep tests independent of any real user credentials.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("SERPAPI_KEY", raising=False)
    monkeypatch.delenv("RAPIDAPI_KEY", raising=False)


@pytest.fixture
def future_date():
    return date.today() + timedelta(days=12)
