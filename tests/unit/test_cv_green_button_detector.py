"""Black-box unit tests for the CV core: PNG in, coordinates out.

Structured Arrange–Act–Assert.
"""

from domain.cv_green_button_detector import CvGreenButtonDetector

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def test_finds_green_button_center(green_button_png: tuple[bytes, tuple[int, int]]) -> None:
    # Arrange
    png, (center_x, center_y) = green_button_png
    detector = CvGreenButtonDetector()
    # Act
    match = detector.find(png)
    # Assert
    assert match is not None
    assert abs(match.x - center_x) <= 3
    assert abs(match.y - center_y) <= 3


def test_returns_none_without_green(no_green_png: bytes) -> None:
    # Arrange
    detector = CvGreenButtonDetector()
    # Act
    match = detector.find(no_green_png)
    # Assert
    assert match is None


def test_picks_largest_of_several(two_buttons_png: tuple[bytes, tuple[int, int]]) -> None:
    # Arrange
    png, (center_x, center_y) = two_buttons_png
    detector = CvGreenButtonDetector()
    # Act
    match = detector.find(png)
    # Assert
    assert match is not None
    assert abs(match.x - center_x) <= 3
    assert abs(match.y - center_y) <= 3


def test_annotate_returns_valid_png(green_button_png: tuple[bytes, tuple[int, int]]) -> None:
    # Arrange
    png, _ = green_button_png
    detector = CvGreenButtonDetector()
    # Act
    annotated = detector.annotate(png, detector.find(png))
    # Assert
    assert annotated.startswith(_PNG_SIGNATURE)


def test_ignores_thin_green_status_bar(status_bar_png: bytes) -> None:
    # Arrange
    detector = CvGreenButtonDetector()
    # Act
    match = detector.find(status_bar_png)
    # Assert
    assert match is None  # a full-width thin bar fails the aspect-ratio filter


def test_finds_button_on_dark_theme(dark_theme_png: tuple[bytes, tuple[int, int]]) -> None:
    # Arrange
    png, (center_x, center_y) = dark_theme_png
    detector = CvGreenButtonDetector()
    # Act
    match = detector.find(png)
    # Assert
    assert match is not None
    assert abs(match.x - center_x) <= 3
    assert abs(match.y - center_y) <= 3


def test_find_returns_none_on_empty_bytes() -> None:
    # Arrange
    detector = CvGreenButtonDetector()
    # Act / Assert
    assert detector.find(b"") is None


def test_annotate_without_match_returns_valid_png(no_green_png: bytes) -> None:
    # Arrange
    detector = CvGreenButtonDetector()
    # Act
    annotated = detector.annotate(no_green_png, None)
    # Assert
    assert annotated.startswith(_PNG_SIGNATURE)


def test_annotate_returns_input_on_empty_bytes() -> None:
    # Arrange
    detector = CvGreenButtonDetector()
    # Act / Assert
    assert detector.annotate(b"", None) == b""
