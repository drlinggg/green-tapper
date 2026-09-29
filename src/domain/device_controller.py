"""Port (hexagonal architecture): the abstraction the domain depends on.

Declared as an abstract base class. The core depends on this interface, never on
concrete adapters (adb, CLI); adapters subclass it, so dependencies point inward
(dependency inversion).
"""
from abc import ABC, abstractmethod


class DeviceController(ABC):
    """Controls a device: launch an app, capture the screen, tap a point.

    Concrete controllers (e.g. adb-based) implement these operations.
    """

    @abstractmethod
    def launch_app(self, package: str) -> None:
        """Launch an application by package name.

        Args:
            package: Android application package name (e.g. ``com.example.app``).
        """
        raise NotImplementedError

    @abstractmethod
    def capture_screen(self) -> bytes:
        """Capture the current screen.

        Returns:
            The screenshot encoded as PNG bytes.
        """
        raise NotImplementedError

    @abstractmethod
    def tap(self, x: int, y: int) -> None:
        """Tap a point on the screen.

        Args:
            x: Horizontal coordinate in display pixels.
            y: Vertical coordinate in display pixels.
        """
        raise NotImplementedError
