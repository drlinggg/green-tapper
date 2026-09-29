"""Application-wide settings: read deployment config from the environment (and an
optional .env file), plus logging setup.

No fallbacks: a missing required variable fails fast at startup (main builds
Settings before doing anything else). Only deploy-varying config lives here;
fixed constants (timeout, poll interval, CV thresholds) live in code.
"""
import logging
import os
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path


class ConfigError(RuntimeError):
    """A required environment variable is missing or malformed."""


class ExitCode(IntEnum):
    """Process exit codes returned by the application."""

    OK = 0
    NOT_FOUND = 2
    CONFIG = 3
    DEVICE = 4
    INTERRUPTED = 130


@dataclass(frozen=True)
class Settings:
    """Deployment settings resolved from required environment variables."""

    debug: bool
    adb_host: str
    adb_port: int
    serial: str | None = None
    timeout: float = 10.0  # seconds
    poll_interval: float = 0.5  # seconds, between screenshots

    @classmethod
    def from_env(cls, dotenv_path: Path | None = None) -> "Settings":
        """Build settings from the environment (loading .env first).

        Args:
            dotenv_path: Path to the .env file; defaults to ``./.env``.

        Returns:
            A populated ``Settings`` instance.

        Raises:
            ConfigError: If a required variable is missing or malformed.
        """
        cls._load_dotenv(dotenv_path or Path(".env"))
        return cls(
            debug=cls._require_bool("DEBUG"),
            adb_host=cls._require("ADB_HOST"),
            adb_port=cls._require_int("ADB_PORT"),
            serial=os.environ.get("ANDROID_SERIAL") or None,
        )

    def configure_logging(self) -> None:
        """Configure the root logger from this instance's ``debug`` flag.

        Modules obtain their own logger via ``logging.getLogger(__name__)``.
        """
        logging.basicConfig(
            level=logging.DEBUG if self.debug else logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )

    @staticmethod
    def _load_dotenv(path: Path) -> None:
        """Load variables from a .env file into ``os.environ`` (no overwrite).

        Comments and malformed lines are ignored.

        Args:
            path: Path to the .env file; a missing file is a no-op.
        """
        if not path.is_file():
            return
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

    @staticmethod
    def _require(name: str) -> str:
        """Return a required environment variable.

        Args:
            name: Environment variable name.

        Returns:
            The variable's value.

        Raises:
            ConfigError: If the variable is unset or empty.
        """
        value = os.environ.get(name)
        if not value:
            raise ConfigError(f"required environment variable {name} is not set")
        return value

    @classmethod
    def _require_bool(cls, name: str) -> bool:
        """Return a required boolean variable (``1/true`` → True, ``0/false`` → False).

        Args:
            name: Environment variable name.

        Returns:
            The parsed boolean.

        Raises:
            ConfigError: If the variable is unset, empty, or not a recognised
                boolean (``1``/``true``/``0``/``false``).
        """
        raw = cls._require(name).strip().lower()
        if raw in {"1", "true"}:
            return True
        if raw in {"0", "false"}:
            return False
        raise ConfigError(
            f"environment variable {name} must be a boolean (true/false), got {raw!r}"
        )

    @classmethod
    def _require_int(cls, name: str) -> int:
        """Return a required integer variable.

        Args:
            name: Environment variable name.

        Returns:
            The parsed integer.

        Raises:
            ConfigError: If the variable is unset, empty, or not an integer.
        """
        raw = cls._require(name)
        try:
            return int(raw)
        except ValueError as error:
            raise ConfigError(
                f"environment variable {name} must be an integer, got {raw!r}"
            ) from error
