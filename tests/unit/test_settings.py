"""Unit tests for Settings.from_env: fail-fast when a required variable is
missing, no silent fallbacks.

Structured Arrange–Act–Assert.
"""
from pathlib import Path

import pytest

from settings import ConfigError, Settings


def test_from_env_reads_required_vars(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Arrange
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("ADB_HOST", "10.0.0.5")
    monkeypatch.setenv("ADB_PORT", "5555")
    monkeypatch.delenv("ANDROID_SERIAL", raising=False)
    # Act
    settings = Settings.from_env(dotenv_path=tmp_path / "absent.env")
    # Assert
    assert settings.debug is False
    assert settings.adb_host == "10.0.0.5"
    assert settings.adb_port == 5555
    assert settings.serial is None


def test_missing_required_var_fails_fast(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Arrange
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("ADB_PORT", "5037")
    monkeypatch.delenv("ADB_HOST", raising=False)
    # Act / Assert
    with pytest.raises(ConfigError):
        Settings.from_env(dotenv_path=tmp_path / "absent.env")


def test_non_integer_port_fails_fast(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Arrange
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("ADB_HOST", "127.0.0.1")
    monkeypatch.setenv("ADB_PORT", "not-a-number")
    # Act / Assert
    with pytest.raises(ConfigError):
        Settings.from_env(dotenv_path=tmp_path / "absent.env")


def test_non_boolean_debug_fails_fast(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Arrange
    monkeypatch.setenv("DEBUG", "maybe")
    monkeypatch.setenv("ADB_HOST", "127.0.0.1")
    monkeypatch.setenv("ADB_PORT", "5037")
    # Act / Assert
    with pytest.raises(ConfigError):
        Settings.from_env(dotenv_path=tmp_path / "absent.env")


def test_reads_values_from_dotenv_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Arrange
    for name in ("DEBUG", "ADB_HOST", "ADB_PORT", "ANDROID_SERIAL"):
        monkeypatch.delenv(name, raising=False)
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "# a comment\n"
        "\n"
        "malformed-line-without-equals\n"
        'DEBUG="true"\n'
        "ADB_HOST=192.168.1.9\n"
        "ADB_PORT=5555\n"
        "ANDROID_SERIAL=emulator-5554\n",
        encoding="utf-8",
    )
    # Act
    settings = Settings.from_env(dotenv_path=dotenv)
    # Assert
    assert settings.debug is True
    assert settings.adb_host == "192.168.1.9"
    assert settings.adb_port == 5555
    assert settings.serial == "emulator-5554"
