"""Unit tests for the adbutils adapter: patch the adbutils client so the exact
shell commands and device resolution run without a real ADB server.

Structured Arrange–Act–Assert.
"""
import io
from unittest.mock import MagicMock

import pytest

from adapters.adbutils_device_controller import AdbutilsDeviceController
from adapters.errors import AdbError

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class _FakeImage:
    """Stand-in for the PIL image returned by ``adbutils.Device.screenshot``."""

    def save(self, buffer: io.BytesIO, format: str) -> None:  # noqa: A002 - adbutils API name
        buffer.write(_PNG_SIGNATURE + b"PNGDATA")


def _patch_devices(
    monkeypatch: pytest.MonkeyPatch, devices: list[MagicMock]
) -> None:
    """Patch ``AdbClient`` so ``device_list`` returns ``devices``."""
    client = MagicMock()
    client.device_list.return_value = devices
    monkeypatch.setattr(
        "adapters.adbutils_device_controller.AdbClient",
        MagicMock(return_value=client),
    )


def _controller_serving(
    monkeypatch: pytest.MonkeyPatch, device: MagicMock, serial: str | None = None
) -> AdbutilsDeviceController:
    """Build a controller whose ADB client resolves to a single ``device``."""
    _patch_devices(monkeypatch, [device])
    return AdbutilsDeviceController(serial=serial)


def test_launch_app_sends_monkey_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    device = MagicMock()
    controller = _controller_serving(monkeypatch, device)
    # Act
    controller.launch_app("com.example.app")
    # Assert
    device.shell.assert_called_once_with(
        ["monkey", "-p", "com.example.app", "-c", "android.intent.category.LAUNCHER", "1"]
    )


def test_capture_screen_returns_png_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    device = MagicMock()
    device.screenshot.return_value = _FakeImage()
    controller = _controller_serving(monkeypatch, device)
    # Act
    data = controller.capture_screen()
    # Assert
    assert data.startswith(_PNG_SIGNATURE)


def test_capture_screen_rejects_non_png(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    bad_image = MagicMock()
    bad_image.save.side_effect = lambda buffer, **_: buffer.write(b"not-a-png")
    device = MagicMock()
    device.screenshot.return_value = bad_image
    controller = _controller_serving(monkeypatch, device)
    # Act / Assert
    with pytest.raises(AdbError):
        controller.capture_screen()


def test_tap_sends_input_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    device = MagicMock()
    controller = _controller_serving(monkeypatch, device)
    # Act
    controller.tap(5, 7)
    # Assert
    device.shell.assert_called_once_with(["input", "tap", "5", "7"])


def test_no_devices_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    _patch_devices(monkeypatch, [])
    controller = AdbutilsDeviceController()
    # Act / Assert
    with pytest.raises(AdbError):
        controller.launch_app("com.example.app")


def test_multiple_devices_without_serial_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    first, second = MagicMock(), MagicMock()
    first.serial, second.serial = "dev-A", "dev-B"
    _patch_devices(monkeypatch, [first, second])
    controller = AdbutilsDeviceController()  # no serial from CLI or env
    # Act / Assert
    with pytest.raises(AdbError):
        controller.tap(1, 2)


def test_unknown_serial_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    other = MagicMock()
    other.serial = "other-serial"
    controller = _controller_serving(monkeypatch, other, serial="wanted-serial")
    # Act / Assert
    with pytest.raises(AdbError):
        controller.capture_screen()


def test_serial_selects_matching_device(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    wanted, other = MagicMock(), MagicMock()
    wanted.serial, other.serial = "wanted-serial", "other-serial"
    _patch_devices(monkeypatch, [other, wanted])
    controller = AdbutilsDeviceController(serial="wanted-serial")
    # Act
    controller.tap(1, 2)
    # Assert
    wanted.shell.assert_called_once_with(["input", "tap", "1", "2"])
    other.shell.assert_not_called()
