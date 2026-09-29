"""Use-case: launch an app, poll for a green button, tap it within a deadline.

Depends only on the DeviceController abstraction plus the detector.

The clock and sleep functions are injected so the polling loop can be tested
without a real Android device.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from domain.cv_green_button_detector import (
    ButtonMatch,
    CvGreenButtonDetector,
)
from domain.device_controller import DeviceController
from domain.errors import DeviceError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Found:
    """Successful outcome: the coordinates that were tapped."""

    x: int
    y: int


@dataclass(frozen=True)
class NotFound:
    """Unsuccessful outcome: no green button appeared before the deadline."""

    timeout: float


Result = Found | NotFound


class GreenButtonTapper:
    """Launches an app and taps its green button within a timeout budget."""

    def __init__(
        self,
        device: DeviceController,
        detector: CvGreenButtonDetector,
        *,
        timeout: float,
        poll_interval: float,
        debug_dump: str | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Wire the collaborators and timing.

        Args:
            device:
                Controller used to launch the package, capture screenshots,
                and send taps.

            detector:
                Green-button detector applied to each screenshot.

            timeout:
                Total search budget in seconds, counted from application
                launch.

            poll_interval:
                Delay between screenshot attempts, in seconds.

            debug_dump:
                Optional path where the final annotated screenshot is written.

            clock:
                Monotonic time source, injected for testing.

            sleep:
                Sleep function, injected for testing.
        """
        self.device: DeviceController = device
        self.detector: CvGreenButtonDetector = detector

        self.timeout: float = timeout
        self.poll_interval: float = poll_interval

        self.debug_dump: str | None = debug_dump

        self._clock: Callable[[], float] = clock
        self._sleep: Callable[[float], None] = sleep

    def run(self, package: str) -> Result:
        """Launch ``package`` and tap its green button within the deadline.

        Device-boundary failures are expected to have already been translated
        into ``DeviceError`` by the concrete ``DeviceController`` adapter (the
        adb adapter raises the ``AdbError`` subclass). This use-case catches
        those errors to log the operation that failed, then re-raises them for
        the composition root to map to an exit code.

        Args:
            package:
                Android application package name to launch.

        Returns:
            ``Found(x, y)`` when the green button was found and tapped.

            ``NotFound(timeout)`` when no green button appeared before the
            configured deadline.

        Raises:
            ValueError:
                If ``package`` is empty.

            DeviceError:
                If an ADB/device operation fails; logged here and re-raised.
        """
        package = package.strip()

        if not package:
            raise ValueError("package name must not be empty")

        logger.info(
            "launching package=%s",
            package,
        )

        try:
            self.device.launch_app(package)

        except DeviceError as exc:
            logger.error(
                "failed to launch package=%s: %s",
                package,
                exc,
            )
            raise

        deadline = self._clock() + self.timeout

        last_screenshot: bytes | None = None

        while self._clock() < deadline:
            try:
                screenshot = self.device.capture_screen()

            except DeviceError as exc:
                logger.error(
                    "failed to capture screen for package=%s: %s",
                    package,
                    exc,
                )
                raise

            last_screenshot = screenshot

            match = self.detector.find(
                screenshot
            )

            if match is not None:
                self._dump(
                    screenshot,
                    match,
                )

                try:
                    self.device.tap(
                        match.x,
                        match.y,
                    )

                except DeviceError as exc:
                    logger.error(
                        (
                            "failed to tap green button "
                            "for package=%s at (%d, %d): %s"
                        ),
                        package,
                        match.x,
                        match.y,
                        exc,
                    )
                    raise

                logger.info(
                    (
                        "green button tapped "
                        "package=%s x=%d y=%d"
                    ),
                    package,
                    match.x,
                    match.y,
                )

                return Found(
                    x=match.x,
                    y=match.y,
                )

            self._sleep(
                self.poll_interval
            )

        if last_screenshot is not None:
            self._dump(
                last_screenshot,
                None,
            )

        logger.info(
            (
                "green button not found "
                "package=%s timeout=%.2fs"
            ),
            package,
            self.timeout,
        )

        return NotFound(
            timeout=self.timeout
        )

    def _dump(
        self,
        screenshot: bytes,
        match: ButtonMatch | None,
    ) -> None:
        """Write annotated screenshot to ``debug_dump`` when configured.

        Args:
            screenshot:
                PNG screenshot to annotate.

            match:
                Detected button region, or ``None`` if nothing matched.
        """
        if self.debug_dump is None:
            return

        Path(
            self.debug_dump
        ).write_bytes(
            self.detector.annotate(
                screenshot,
                match,
            )
        )
