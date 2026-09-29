"""Application entry point and composition root.

`Application` is the only place that knows about both the domain and the
concrete adapters; the domain does not depend on it. Run via ``python src/main.py``
(the package modules live under ``src`` on the path).
"""
import logging
import signal
import sys
from types import FrameType

from adapters.adbutils_device_controller import AdbutilsDeviceController
from cli.parser import CliParser
from domain.cv_green_button_detector import CvGreenButtonDetector, GreenSpec
from domain.device_controller import DeviceController
from domain.errors import DeviceError
from domain.green_button_tapper import Found, GreenButtonTapper
from settings import ConfigError, ExitCode, Settings

log = logging.getLogger(__name__)


class Application:
    """Composition root: wires the concrete adapters into the domain use-case."""

    def run(self, argv: list[str] | None = None) -> int:
        """Parse args, build collaborators, tap the green button, return the code.

        Args:
            argv: Argument list to parse; defaults to ``sys.argv`` when ``None``.

        Returns:
            An :class:`~settings.ExitCode`: ``OK`` tapped, ``NOT_FOUND`` no green
            button, ``CONFIG`` bad configuration/arguments, ``DEVICE`` ADB failure.
        """
        try:
            settings = Settings.from_env()
        except ConfigError as exc:
            print(f"Configuration error: {exc}", file=sys.stderr)
            return ExitCode.CONFIG

        settings.configure_logging()
        arguments = CliParser(settings).build().parse_args(argv)

        try:
            device: DeviceController = AdbutilsDeviceController(
                serial=arguments.serial,
                host=arguments.adb_host,
                port=arguments.adb_port,
            )
        except DeviceError as exc:
            log.error("failed to connect to the ADB server: %s", exc)
            return ExitCode.DEVICE

        detector = CvGreenButtonDetector(GreenSpec())
        tapper = GreenButtonTapper(
            device,
            detector,
            timeout=arguments.timeout,
            poll_interval=arguments.poll_interval,
            debug_dump=arguments.debug_dump,
        )

        log.debug(
            "target=%s timeout=%.1fs poll=%.1fs adb=%s:%d serial=%s",
            arguments.package, arguments.timeout, arguments.poll_interval,
            arguments.adb_host, arguments.adb_port, arguments.serial,
        )

        try:
            result = tapper.run(arguments.package)
        except ValueError as exc:
            print(f"Invalid argument: {exc}", file=sys.stderr)
            return ExitCode.CONFIG
        except DeviceError as exc:
            log.error("device operation failed: %s", exc)
            return ExitCode.DEVICE

        if isinstance(result, Found):
            print(f"Tapped the green button at ({result.x}, {result.y}).")
            return ExitCode.OK
        print(f"Green button not found within {arguments.timeout:.0f} seconds.")
        return ExitCode.NOT_FOUND


def _raise_keyboard_interrupt(signum: int, frame: FrameType | None) -> None:
    """Translate a termination signal into ``KeyboardInterrupt``.

    Lets a ``SIGTERM`` (sent by Kubernetes/Docker on shutdown) unwind the polling
    loop the same way ``Ctrl+C`` (``SIGINT``) does.
    """
    raise KeyboardInterrupt


def main(argv: list[str] | None = None) -> int:
    """Entry point; run via ``python src/main.py``.

    Installs a ``SIGTERM`` handler so container shutdown exits gracefully, then
    delegates to :meth:`Application.run`.

    Args:
        argv: Argument list to parse; defaults to ``sys.argv`` when ``None``.

    Returns:
        The :class:`~settings.ExitCode` from :meth:`Application.run`, or
        ``INTERRUPTED`` when interrupted by ``SIGINT``/``SIGTERM``.
    """
    signal.signal(signal.SIGTERM, _raise_keyboard_interrupt)
    try:
        return Application().run(argv)
    except KeyboardInterrupt:
        log.info("interrupted, shutting down")
        return ExitCode.INTERRUPTED


if __name__ == "__main__":
    sys.exit(main())
