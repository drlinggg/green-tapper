"""Unit tests for the composition root: exit-code mapping, graceful shutdown, and
error handling wired around a fake device controller (no real phone).

Structured Arrange–Act–Assert.
"""
import pytest

import main as main_module
from adapters.errors import AdbError
from domain.device_controller import DeviceController
from settings import ConfigError, ExitCode, Settings


class _FakeController(DeviceController):
    """In-memory DeviceController replaying scripted screenshots."""

    def __init__(self, screens: list[bytes]) -> None:
        self._screens = list(screens)
        self.launched: str | None = None
        self.taps: list[tuple[int, int]] = []

    def launch_app(self, package: str) -> None:
        self.launched = package

    def capture_screen(self) -> bytes:
        if len(self._screens) > 1:
            return self._screens.pop(0)
        return self._screens[0]

    def tap(self, x: int, y: int) -> None:
        self.taps.append((x, y))


@pytest.fixture
def _adb_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the required environment variables for a real ``Settings.from_env``."""
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("ADB_HOST", "127.0.0.1")
    monkeypatch.setenv("ADB_PORT", "5037")
    monkeypatch.delenv("ANDROID_SERIAL", raising=False)


def _install_controller(monkeypatch: pytest.MonkeyPatch, controller: DeviceController) -> None:
    """Replace the concrete adapter so the composition root wires ``controller``."""
    monkeypatch.setattr(main_module, "AdbutilsDeviceController", lambda **_: controller)


def test_run_taps_and_returns_ok(
    monkeypatch: pytest.MonkeyPatch,
    _adb_env: None,
    green_button_png: tuple[bytes, tuple[int, int]],
) -> None:
    # Arrange
    png, _ = green_button_png
    controller = _FakeController([png])
    _install_controller(monkeypatch, controller)
    # Act
    code = main_module.Application().run(
        ["com.example.app", "--timeout", "2", "--poll-interval", "0"]
    )
    # Assert
    assert code == ExitCode.OK
    assert controller.launched == "com.example.app"
    assert len(controller.taps) == 1


def test_run_returns_not_found(
    monkeypatch: pytest.MonkeyPatch, _adb_env: None, no_green_png: bytes
) -> None:
    # Arrange
    _install_controller(monkeypatch, _FakeController([no_green_png]))
    # Act
    code = main_module.Application().run(
        ["com.example.app", "--timeout", "0.01", "--poll-interval", "0"]
    )
    # Assert
    assert code == ExitCode.NOT_FOUND


def test_run_returns_config_on_bad_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    def _raise() -> Settings:
        raise ConfigError("ADB_HOST is not set")

    monkeypatch.setattr(Settings, "from_env", staticmethod(_raise))
    # Act
    code = main_module.Application().run(["com.example.app"])
    # Assert
    assert code == ExitCode.CONFIG


def test_run_returns_device_on_connect_failure(
    monkeypatch: pytest.MonkeyPatch, _adb_env: None
) -> None:
    # Arrange
    def _raise(**_: object) -> DeviceController:
        raise AdbError("cannot reach ADB server")

    monkeypatch.setattr(main_module, "AdbutilsDeviceController", _raise)
    # Act
    code = main_module.Application().run(["com.example.app"])
    # Assert
    assert code == ExitCode.DEVICE


def test_run_returns_device_on_runtime_failure(
    monkeypatch: pytest.MonkeyPatch, _adb_env: None
) -> None:
    # Arrange
    controller = _FakeController([b""])
    controller.launch_app = _raising_launch  # type: ignore[method-assign]
    _install_controller(monkeypatch, controller)
    # Act
    code = main_module.Application().run(["com.example.app", "--timeout", "1"])
    # Assert
    assert code == ExitCode.DEVICE


def test_run_returns_config_on_empty_package(
    monkeypatch: pytest.MonkeyPatch, _adb_env: None
) -> None:
    # Arrange
    _install_controller(monkeypatch, _FakeController([b""]))
    # Act
    code = main_module.Application().run(["   ", "--timeout", "1"])
    # Assert
    assert code == ExitCode.CONFIG


def test_main_maps_interrupt_to_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    def _interrupt(_argv: list[str] | None = None) -> int:
        raise KeyboardInterrupt

    monkeypatch.setattr(main_module.Application, "run", lambda self, argv=None: _interrupt(argv))
    # Act
    code = main_module.main(["com.example.app"])
    # Assert
    assert code == ExitCode.INTERRUPTED


def _raising_launch(package: str) -> None:
    """Module-level helper so it can be bound as a bound-method replacement."""
    raise AdbError("device offline")
