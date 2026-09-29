"""Error raised by the adb adapter."""

from domain.errors import DeviceError


class AdbError(DeviceError):
    """adb returned a non-zero status or produced unexpected output."""
