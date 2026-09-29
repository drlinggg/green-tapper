"""Domain-level errors for the device boundary."""


class DeviceError(RuntimeError):
    """A device operation failed at the ``DeviceController`` boundary.

    Adapters raise subclasses of this error (e.g. ``AdbError``).
    """
