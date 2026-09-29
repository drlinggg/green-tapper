"""Unit tests for the CLI parser: settings become defaults and the exit-code
reference is shown in help.

Structured Arrange–Act–Assert.
"""
from cli.parser import CliParser
from settings import ExitCode, Settings


def _settings() -> Settings:
    """Return settings with recognisable, non-default values."""
    return Settings(
        debug=False,
        adb_host="10.0.0.1",
        adb_port=5555,
        serial="emulator-5554",
        timeout=7.5,
        poll_interval=0.25,
    )


def test_settings_become_argument_defaults() -> None:
    # Arrange
    parser = CliParser(_settings()).build()
    # Act
    args = parser.parse_args(["com.example.app"])
    # Assert
    assert args.package == "com.example.app"
    assert args.adb_host == "10.0.0.1"
    assert args.adb_port == 5555
    assert args.serial == "emulator-5554"
    assert args.timeout == 7.5
    assert args.poll_interval == 0.25


def test_flags_override_defaults() -> None:
    # Arrange
    parser = CliParser(_settings()).build()
    # Act
    args = parser.parse_args(["com.example.app", "--adb-port", "5037", "--timeout", "3"])
    # Assert
    assert args.adb_port == 5037
    assert args.timeout == 3.0


def test_help_lists_every_exit_code() -> None:
    # Arrange
    parser = CliParser(_settings()).build()
    # Act
    help_text = parser.format_help()
    # Assert
    assert "exit codes:" in help_text
    for code in ExitCode:
        assert str(int(code)) in help_text
