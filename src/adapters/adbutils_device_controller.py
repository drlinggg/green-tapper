"""Driven adapter: implements DeviceController via adbutils.

adbutils communicates with a running ADB server and is used only for basic
ADB primitives: application launch, screenshot capture, and tap.
"""

import io
import logging

from adbutils import AdbClient, AdbDevice

from adapters.errors import AdbError
from domain.device_controller import DeviceController

logger = logging.getLogger(__name__)


class AdbutilsDeviceController(DeviceController):
    """Drives an Android device through the ADB server via adbutils."""

    def __init__(
        self,
        serial: str | None = None,
        host: str = "127.0.0.1",
        port: int = 5037,
    ) -> None:
        """Configure connection to the ADB server.

        Args:
            serial:
                Target device serial.

                If specified, that exact device is used.

                If ``None`` and exactly one device is attached, that device is
                used. If several devices are attached, resolution fails fast so
                the caller must disambiguate with a serial.

            host:
                ADB server host.

                Use ``127.0.0.1`` when running directly on the host.

                When running inside Docker while the ADB server is running
                on the host, ``host.docker.internal`` may be used instead.

            port:
                ADB server port. The standard port is 5037.
        """
        self.serial: str | None = (
            str(serial).strip()
            if serial is not None
            else None
        )

        try:
            self._client: AdbClient = AdbClient(
                host=host,
                port=port,
            )
        except Exception as exc:
            raise AdbError(
                f"failed to create ADB client for {host}:{port}: {exc}"
            ) from exc

        logger.debug(
            "adb client created host=%s port=%d serial=%s",
            host,
            port,
            self.serial,
        )

    def launch_app(self, package: str) -> None:
        """Launch an Android package through the standard ``monkey`` command.

        Args:
            package:
                Android application package name to launch.

        Raises:
            AdbError:
                If the device cannot be resolved or the ADB command fails.
        """
        try:
            device = self._resolve_device()

            logger.debug(
                "launch_app package=%s serial=%s",
                package,
                device.serial,
            )

            device.shell(
                [
                    "monkey",
                    "-p",
                    package,
                    "-c",
                    "android.intent.category.LAUNCHER",
                    "1",
                ]
            )

        except AdbError:
            raise

        except Exception as exc:
            raise AdbError(
                f"failed to launch package {package!r}: {exc}"
            ) from exc

    def tap(self, x: int, y: int) -> None:
        """Send a tap through Android's standard ``input tap`` command.

        Args:
            x:
                Horizontal coordinate in display pixels.

            y:
                Vertical coordinate in display pixels.

        Raises:
            AdbError:
                If the device cannot be resolved or the ADB command fails.
        """
        try:
            device = self._resolve_device()

            logger.debug(
                "tap x=%d y=%d serial=%s",
                x,
                y,
                device.serial,
            )

            device.shell(
                [
                    "input",
                    "tap",
                    str(x),
                    str(y),
                ]
            )

        except AdbError:
            raise

        except Exception as exc:
            raise AdbError(
                f"failed to tap coordinates ({x}, {y}): {exc}"
            ) from exc

    def capture_screen(self) -> bytes:
        """Capture the current Android screen and return it as PNG bytes.

        Author:
            Andrei Banakh

        Telegram:
            t.me/abanakh

        Date:
            2026-09-29

        ``adbutils.Device.screenshot()`` is intentionally used as the
        high-level screenshot primitive instead of manually implementing
        screenshot transport, Base64 transfer, file pulling, or chunking.

        During development, screenshot capture over a physical USB connection
        between macOS and a Samsung Galaxy A35 was unreliable. Large ADB
        transfers could return an incomplete PNG and then cause the device to
        disappear from the ADB device list.

        The same behaviour was reproduced with the official ADB client, so the
        issue was not specific to ppadb, adbutils, or this application.

        Screenshot capture works reliably after pairing the device through
        Android Wireless Debugging. Therefore, for the tested macOS +
        Samsung Galaxy A35 environment, the device should be paired and
        connected through Wi-Fi debugging before this method is used.

        The pairing flow is:

            Developer options
            -> Wireless debugging
            -> Pair device with pairing code

        After pairing, connect the Mac to the Wi-Fi ADB endpoint. If no
        explicit serial is supplied and exactly one device is attached, that
        device is selected automatically.

        Raises:
            AdbError:
                If the device cannot be resolved, screenshot capture fails,
                or the resulting image cannot be encoded as PNG.
        """
        try:
            device = self._resolve_device()

            logger.debug(
                "capture_screen serial=%s",
                device.serial,
            )

            image = device.screenshot(
                error_ok=False,
            )

            buffer = io.BytesIO()
            image.save(
                buffer,
                format="PNG",
            )

            screenshot = buffer.getvalue()

            if not screenshot:
                raise AdbError(
                    "screenshot returned empty PNG data"
                )

            if not screenshot.startswith(
                b"\x89PNG\r\n\x1a\n"
            ):
                raise AdbError(
                    "screenshot returned invalid PNG data"
                )

            return screenshot

        except AdbError:
            raise

        except Exception as exc:
            raise AdbError(
                f"failed to capture screen: {exc}"
            ) from exc

    def _resolve_device(self) -> AdbDevice:
        """Resolve the device to drive, failing fast when it is ambiguous.

        If ``serial`` was explicitly supplied, that exact device is selected.

        Otherwise resolution requires exactly one attached device: if several
        are attached and no serial was given, an ``AdbError`` is raised and the
        caller must disambiguate with ``--serial`` (or ``ANDROID_SERIAL``).

        Raises:
            AdbError:
                If querying devices fails, no devices are available, the
                explicitly requested serial is not connected, or several
                devices are attached without a serial.
        """
        try:
            devices = self._client.device_list()

        except Exception as exc:
            raise AdbError(
                f"failed to query ADB devices: {exc}"
            ) from exc

        if not devices:
            raise AdbError(
                "no devices/emulators attached to the ADB server"
            )

        if self.serial is not None:
            for device in devices:
                if str(device.serial).strip() == self.serial:
                    return device

            raise AdbError(
                f"device {self.serial!r} is not attached"
            )

        if len(devices) > 1:
            attached = ", ".join(str(device.serial) for device in devices)
            raise AdbError(
                "multiple devices attached and no serial specified; "
                f"set --serial or ANDROID_SERIAL (attached: {attached})"
            )

        return devices[0]
