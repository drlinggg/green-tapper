"""CLI argument parsing — the driving adapter's input concern."""
import argparse

from settings import ExitCode, Settings


class CliParser:
    """Builds the ``green-tapper`` command-line argument parser."""

    def __init__(self, settings: Settings) -> None:
        """Store the settings used as CLI defaults.

        Args:
            settings: Resolved settings; environment/.env values become defaults.
        """
        self.settings: Settings = settings

    def build(self) -> argparse.ArgumentParser:
        """Build the argument parser.

        Returns:
            A configured ``argparse.ArgumentParser``.
        """
        parser = argparse.ArgumentParser(
            prog="python src/main.py",
            description="Launch an Android app and tap its green button (adb, no UI automators).",
            epilog=self._exit_codes_epilog(),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "package",
            help="Android application package name, e.g. com.example.app",
        )
        parser.add_argument(
            "--serial",
            default=self.settings.serial,
            help="Target device serial when several are attached",
        )
        parser.add_argument(
            "--adb-host",
            default=self.settings.adb_host,
            help="adb server host",
        )
        parser.add_argument(
            "--adb-port",
            type=int,
            default=self.settings.adb_port,
            help="adb server port",
        )
        parser.add_argument(
            "--timeout",
            type=float,
            default=self.settings.timeout,
            help="Search budget in seconds",
        )
        parser.add_argument(
            "--poll-interval",
            type=float,
            default=self.settings.poll_interval,
            help="Delay between screenshots",
        )
        parser.add_argument(
            "--debug-dump",
            metavar="PATH",
            help="Save the green mask and chosen bbox for inspection",
        )
        return parser

    @staticmethod
    def _exit_codes_epilog() -> str:
        """Render the exit-code reference shown at the bottom of ``--help``."""
        descriptions: dict[ExitCode, str] = {
            ExitCode.OK: "green button tapped",
            ExitCode.NOT_FOUND: "green button not found within the timeout",
            ExitCode.CONFIG: "bad configuration or arguments",
            ExitCode.DEVICE: "device / ADB failure",
            ExitCode.INTERRUPTED: "interrupted (SIGINT/SIGTERM)",
        }
        lines = "\n".join(
            f"  {int(code):<3} {description}"
            for code, description in descriptions.items()
        )
        return f"exit codes:\n{lines}"
