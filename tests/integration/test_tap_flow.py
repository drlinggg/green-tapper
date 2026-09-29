"""Integration: the real detector wired into the polling use-case, driven by a
mocked device that serves generated PNG screenshots (no real phone).

Structured Arrange–Act–Assert.
"""
from unittest.mock import MagicMock

import pytest

from domain.cv_green_button_detector import CvGreenButtonDetector
from domain.device_controller import DeviceController
from domain.green_button_tapper import Found, GreenButtonTapper


class _AdvancingClock:
    """Monotonic clock that advances one second per call (keeps the loop finite)."""

    def __init__(self) -> None:
        self._now = 0.0

    def __call__(self) -> float:
        self._now += 1.0
        return self._now


@pytest.mark.integration
def test_launch_detect_tap_flow(green_button_png: tuple[bytes, tuple[int, int]]) -> None:
    # Arrange
    png, (center_x, center_y) = green_button_png
    device = MagicMock(spec=DeviceController)
    device.capture_screen.side_effect = [b"", png]  # splash frame, then the button
    tapper = GreenButtonTapper(
        device,
        CvGreenButtonDetector(),  # real computer vision, not a fake
        timeout=100.0,
        poll_interval=0.5,
        clock=_AdvancingClock(),
        sleep=lambda _seconds: None,
    )
    # Act
    result = tapper.run("com.example.app")
    # Assert
    assert isinstance(result, Found)
    assert abs(result.x - center_x) <= 3
    assert abs(result.y - center_y) <= 3
    device.launch_app.assert_called_once_with("com.example.app")
    device.tap.assert_called_once_with(result.x, result.y)
