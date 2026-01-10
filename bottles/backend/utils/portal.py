# portal.py

import gi


class PortalUtils:
    """
    Utility class for interacting with XDG Desktop Portals safely.
    """

    @staticmethod
    def get_portal():
        """
        Safely attempt to get an Xdp.Portal instance.
        Returns:
            Xdp.Portal or None if not available.
        """
        try:
            gi.require_version("Xdp", "1.0")
            from gi.repository import Xdp  # type: ignore

            return Xdp.Portal()
        except (ImportError, ValueError):
            return None

    @staticmethod
    def is_available() -> bool:
        """
        Check if the XDP namespace and portal service are available.
        """
        portal = PortalUtils.get_portal()
        return portal is not None
