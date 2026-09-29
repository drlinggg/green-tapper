"""Green-button detection: pure computer vision — bytes in, coordinates out.

No adb, no I/O. OpenCV/NumPy are the domain's own image-processing tools.
"""
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class GreenSpec:
    """Tunable definition of what counts as a "green button".

    Hue uses OpenCV's 0-179 scale. Defaults target a broad Material-ish green and
    reject greyish/dark pixels via the S/V minimums.
    """

    hue_range: tuple[int, int] = (35, 85)
    sat_min: int = 80
    val_min: int = 60
    min_area_frac: float = 0.001  # ignore specks smaller than 0.1% of the screen
    aspect_range: tuple[float, float] = (0.2, 8.0)
    min_solidity: float = 0.8  # convex-fill ratio; rejects text and thin bars
    close_kernel: int = 5  # side of the square morphological-close kernel, in pixels


@dataclass(frozen=True)
class AnnotationStyle:
    """Drawing settings for the ``--debug-dump`` overlay (colors are BGR)."""

    mask_overlay_bgr: tuple[int, int, int] = (0, 0, 255)  # red tint over green pixels
    bbox_bgr: tuple[int, int, int] = (255, 0, 0)  # blue box and center dot
    original_weight: float = 0.6  # blend weight of the original screenshot
    overlay_weight: float = 0.4  # blend weight of the mask overlay
    bbox_thickness: int = 3  # pixels
    center_radius: int = 6  # pixels


@dataclass(frozen=True)
class ButtonMatch:
    """A detected button: bbox center to tap, plus its bounding box and area."""

    x: int  # pixels
    y: int  # pixels
    bbox: tuple[int, int, int, int]  # x, y, w, h — pixels
    area: int  # pixels²


class CvGreenButtonDetector:
    """Finds the most button-like green region in a screenshot."""

    def __init__(
        self, spec: GreenSpec | None = None, style: AnnotationStyle | None = None
    ) -> None:
        """Configure detection thresholds and debug-overlay style.

        Args:
            spec: Thresholds defining what counts as a green button; defaults to
                ``GreenSpec()``.
            style: Debug-overlay drawing settings; defaults to ``AnnotationStyle()``.
        """
        self.spec: GreenSpec = spec if spec is not None else GreenSpec()
        self.style: AnnotationStyle = style if style is not None else AnnotationStyle()

    def find(self, png_bytes: bytes) -> ButtonMatch | None:
        """Locate the most button-like green region in a screenshot.

        Deterministic: among the regions passing the spec (green hue range,
        minimum area, aspect ratio, convex-fill solidity), the largest by area
        wins, with ties broken by top-left position.

        Args:
            png_bytes: Screenshot encoded as PNG bytes.

        Returns:
            A ``ButtonMatch`` with the bbox center to tap, or ``None`` if no
            region matched.
        """
        image = self._decode(png_bytes)
        if image is None:
            return None

        height, width = image.shape[:2]
        min_area = self.spec.min_area_frac * width * height
        low_aspect, high_aspect = self.spec.aspect_range

        candidates: list[tuple[float, int, int, int, int]] = []
        contours, _ = cv2.findContours(
            self._green_mask(image), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            aspect = w / h if h else 0.0
            if not (low_aspect <= aspect <= high_aspect):
                continue
            hull_area = cv2.contourArea(cv2.convexHull(contour))
            solidity = area / hull_area if hull_area else 0.0
            if solidity < self.spec.min_solidity:
                continue
            candidates.append((area, x, y, w, h))

        if not candidates:
            return None

        candidates.sort(key=lambda candidate: (-candidate[0], candidate[1], candidate[2]))
        area, x, y, w, h = candidates[0]
        return ButtonMatch(x=x + w // 2, y=y + h // 2, bbox=(x, y, w, h), area=int(area))

    def annotate(self, png_bytes: bytes, match: ButtonMatch | None) -> bytes:
        """Draw the green mask and the chosen bbox onto the screenshot.

        Used by ``--debug-dump`` to make detection decisions inspectable.

        Args:
            png_bytes: Original screenshot as PNG bytes.
            match: The region that was selected, or ``None`` if nothing matched.

        Returns:
            A PNG image (bytes) with the mask and bounding box overlaid.
        """
        image = self._decode(png_bytes)
        if image is None:
            return png_bytes
        style = self.style
        highlighted = image.copy()
        highlighted[self._green_mask(image) > 0] = style.mask_overlay_bgr
        blended = cv2.addWeighted(
            image, style.original_weight, highlighted, style.overlay_weight, 0.0
        )
        if match is not None:
            x, y, w, h = match.bbox
            cv2.rectangle(
                blended, (x, y), (x + w, y + h), style.bbox_bgr, thickness=style.bbox_thickness
            )
            cv2.circle(
                blended,
                (match.x, match.y),
                radius=style.center_radius,
                color=style.bbox_bgr,
                thickness=cv2.FILLED,
            )
        _, buffer = cv2.imencode(".png", blended)
        return buffer.tobytes()

    @staticmethod
    def _decode(png_bytes: bytes) -> np.ndarray | None:
        """Decode PNG bytes into a BGR image, or ``None`` if empty/unreadable."""
        if not png_bytes:
            return None

        return cv2.imdecode(np.frombuffer(png_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)

    def _green_mask(self, image: np.ndarray) -> np.ndarray:
        """Build a cleaned binary mask of green pixels for ``image`` (BGR)."""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        low_hue, high_hue = self.spec.hue_range
        channel_max = int(np.iinfo(np.uint8).max)
        lower = np.array([low_hue, self.spec.sat_min, self.spec.val_min], dtype=np.uint8)
        upper = np.array([high_hue, channel_max, channel_max], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)
        kernel = np.ones((self.spec.close_kernel, self.spec.close_kernel), dtype=np.uint8)
        return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
