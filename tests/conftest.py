"""Shared fixtures: PNG screenshots generated programmatically so the detector
can be tested offline against known ground-truth coordinates.
"""
import cv2
import numpy as np
import pytest

_GREEN_BGR = (0, 200, 0)
_BLUE_BGR = (200, 0, 0)


def _encode_png(image: np.ndarray) -> bytes:
    """Encode a BGR image as PNG bytes."""
    _, buffer = cv2.imencode(".png", image)
    return buffer.tobytes()


def _canvas(width: int = 400, height: int = 800) -> np.ndarray:
    """Return a white BGR canvas of the given size."""
    return np.full((height, width, 3), 255, dtype=np.uint8)


@pytest.fixture
def green_button_png() -> tuple[bytes, tuple[int, int]]:
    """A white screen with one green button; returns (png, expected center)."""
    image = _canvas()
    cv2.rectangle(image, (100, 600), (300, 680), _GREEN_BGR, thickness=-1)
    return _encode_png(image), (200, 640)


@pytest.fixture
def no_green_png() -> bytes:
    """A white screen with only a blue rectangle (no green)."""
    image = _canvas()
    cv2.rectangle(image, (100, 600), (300, 680), _BLUE_BGR, thickness=-1)
    return _encode_png(image)


@pytest.fixture
def two_buttons_png() -> tuple[bytes, tuple[int, int]]:
    """Two green buttons; returns (png, center of the larger one)."""
    image = _canvas()
    cv2.rectangle(image, (60, 100), (160, 160), _GREEN_BGR, thickness=-1)   # smaller
    cv2.rectangle(image, (100, 600), (320, 700), _GREEN_BGR, thickness=-1)  # larger
    return _encode_png(image), (210, 650)


@pytest.fixture
def status_bar_png() -> bytes:
    """A white screen with only a thin, full-width green status bar."""
    image = _canvas()
    cv2.rectangle(image, (0, 0), (400, 10), _GREEN_BGR, thickness=-1)
    return _encode_png(image)


@pytest.fixture
def dark_theme_png() -> tuple[bytes, tuple[int, int]]:
    """A dark screen with one green button; returns (png, expected center)."""
    image = np.full((800, 400, 3), 30, dtype=np.uint8)
    cv2.rectangle(image, (100, 600), (300, 680), _GREEN_BGR, thickness=-1)
    return _encode_png(image), (200, 640)
