"""Unit tests for the polling use-case, using a fake device and detector so the
loop, the timeout, and the "not found" path run without a real phone.

Structured Arrange–Act–Assert.
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from domain.cv_green_button_detector import ButtonMatch
from domain.device_controller import DeviceController
from domain.errors import DeviceError
from domain.green_button_tapper import Found, GreenButtonTapper, NotFound


class FakeDevice(DeviceController):
    """Records launches and taps; replays a scripted sequence of screenshots."""

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


class FakeDetector:
    """Returns scripted detection results, one per ``find`` call."""

    def __init__(self, results: list[ButtonMatch | None]) -> None:
        self._results = list(results)

    def find(self, png_bytes: bytes) -> ButtonMatch | None:
        return self._results.pop(0) if self._results else None

    def annotate(self, png_bytes: bytes, match: ButtonMatch | None) -> bytes:
        return b"annotated"


class StepClock:
    """A monotonic clock that advances by a fixed step on every call."""

    def __init__(self, step: float = 1.0) -> None:
        self._now = 0.0
        self._step = step

    def __call__(self) -> float:
        value = self._now
        self._now += self._step
        return value


def _no_sleep(_seconds: float) -> None:
    pass


def test_taps_center_when_found() -> None:
    # Arrange
    match = ButtonMatch(x=42, y=99, bbox=(0, 0, 10, 10), area=100)
    device = FakeDevice(screens=[b"splash", b"ready"])
    detector = FakeDetector(results=[None, match])
    tapper = GreenButtonTapper(
        device, detector, timeout=100.0, poll_interval=0.5, clock=StepClock(), sleep=_no_sleep
    )
    # Act
    result = tapper.run("com.example.app")
    # Assert
    assert result == Found(x=42, y=99)
    assert device.launched == "com.example.app"
    assert device.taps == [(42, 99)]


def test_not_found_within_timeout_never_taps() -> None:
    # Arrange
    device = FakeDevice(screens=[b"blank"])
    detector = FakeDetector(results=[])  # always None
    tapper = GreenButtonTapper(
        device, detector, timeout=2.0, poll_interval=0.5, clock=StepClock(step=1.0), sleep=_no_sleep
    )
    # Act
    result = tapper.run("com.example.app")
    # Assert
    assert isinstance(result, NotFound)
    assert result.timeout == 2.0
    assert device.taps == []


def test_writes_debug_dump_when_requested(tmp_path: Path) -> None:
    # Arrange
    dump_path = tmp_path / "dump.png"
    match = ButtonMatch(x=10, y=20, bbox=(0, 0, 5, 5), area=25)
    device = FakeDevice(screens=[b"ready"])
    detector = FakeDetector(results=[match])
    tapper = GreenButtonTapper(
        device,
        detector,
        timeout=100.0,
        poll_interval=0.5,
        debug_dump=str(dump_path),
        clock=StepClock(),
        sleep=_no_sleep,
    )
    # Act
    tapper.run("com.example.app")
    # Assert
    assert dump_path.read_bytes() == b"annotated"  # FakeDetector.annotate output


def test_empty_package_raises_value_error() -> None:
    # Arrange
    device = MagicMock(spec=DeviceController)
    tapper = GreenButtonTapper(
        device,
        FakeDetector(results=[]),
        timeout=1.0,
        poll_interval=0.5,
        clock=StepClock(),
        sleep=_no_sleep,
    )
    # Act / Assert
    with pytest.raises(ValueError):
        tapper.run("   ")
    device.launch_app.assert_not_called()


def test_launch_failure_is_logged_and_reraised() -> None:
    # Arrange
    device = MagicMock(spec=DeviceController)
    device.launch_app.side_effect = DeviceError("device offline")
    tapper = GreenButtonTapper(
        device,
        FakeDetector(results=[]),
        timeout=1.0,
        poll_interval=0.5,
        clock=StepClock(),
        sleep=_no_sleep,
    )
    # Act / Assert
    with pytest.raises(DeviceError):
        tapper.run("com.example.app")


def test_capture_failure_is_logged_and_reraised() -> None:
    # Arrange
    device = MagicMock(spec=DeviceController)
    device.capture_screen.side_effect = DeviceError("screencap failed")
    tapper = GreenButtonTapper(
        device,
        FakeDetector(results=[]),
        timeout=100.0,
        poll_interval=0.5,
        clock=StepClock(),
        sleep=_no_sleep,
    )
    # Act / Assert
    with pytest.raises(DeviceError):
        tapper.run("com.example.app")


def test_tap_failure_is_logged_and_reraised() -> None:
    # Arrange
    match = ButtonMatch(x=1, y=2, bbox=(0, 0, 2, 2), area=4)
    device = MagicMock(spec=DeviceController)
    device.capture_screen.return_value = b"png"
    device.tap.side_effect = DeviceError("input tap failed")
    tapper = GreenButtonTapper(
        device,
        FakeDetector(results=[match]),
        timeout=100.0,
        poll_interval=0.5,
        clock=StepClock(),
        sleep=_no_sleep,
    )
    # Act / Assert
    with pytest.raises(DeviceError):
        tapper.run("com.example.app")
