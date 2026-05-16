import pytest


@pytest.fixture(autouse=True)
def _fast_test_settings(monkeypatch):
    # Ensure logging doesn't try to load .env in CI.
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    yield
