# path.py
#
# Robust path normalization and translation utilities.
# Handles host-to-wine and wine-to-host path mapping by inspecting bottle configuration.

import os
import re

from bottles.backend.globals import Paths
from bottles.backend.logger import Logger
from bottles.backend.models.config import BottleConfig

logging = Logger()


class PathUtils:
    @staticmethod
    def get_bottle_path(config: BottleConfig) -> str:
        if config.Environment == "Steam":
            return os.path.join(Paths.steam, config.CompatData)

        if config.Custom_Path:
            return config.Path

        return os.path.join(Paths.bottles, config.Path)

    @staticmethod
    def get_runner_path(runner: str) -> str:
        if runner.startswith("sys-"):
            return runner

        # Check standard runners path first
        standard_path = f"{Paths.runners}/{runner}"
        if os.path.exists(standard_path):
            return standard_path

        # Check Steam compatibility tools paths
        from bottles.backend.utils.steam import SteamUtils

        for ct_path in SteamUtils.get_compatibility_tools_paths():
            ct_runner_path = os.path.join(ct_path, runner)
            if os.path.exists(ct_runner_path):
                return ct_runner_path

        return standard_path

    @staticmethod
    def get_dxvk_path(dxvk: str) -> str:
        return f"{Paths.dxvk}/{dxvk}/"

    @staticmethod
    def get_vkd3d_path(vkd3d: str) -> str:
        return f"{Paths.vkd3d}/{vkd3d}/"

    @staticmethod
    def get_nvapi_path(nvapi: str) -> str:
        return f"{Paths.nvapi}/{nvapi}/"

    @staticmethod
    def get_latencyflex_path(latencyflex: str) -> str:
        return f"{Paths.latencyflex}/{latencyflex}/"

    @staticmethod
    def to_windows(bottle_path: str, unix_path: str) -> str:
        """
        Convert a host Unix path to a Wine Windows path for a specific bottle.
        Inspects dosdevices symlinks to determine the correct drive letter.
        """
        if not unix_path:
            return ""

        # Normalize host path
        unix_path = os.path.abspath(unix_path)

        # 1. Check if it's inside the bottle's Drive C
        drive_c_path = os.path.join(bottle_path, "drive_c")
        if unix_path.startswith(drive_c_path):
            relative = os.path.relpath(unix_path, drive_c_path)
            return f"C:\\{relative.replace('/', '\\')}"

        # 2. Check dosdevices for other mapped drives
        dosdevices_path = os.path.join(bottle_path, "dosdevices")
        if os.path.exists(dosdevices_path):
            try:
                # Sort entries to prefer standard drives (C:, D:) over higher letters if possible
                # though usually they are unique.
                entries = sorted(os.listdir(dosdevices_path))
                for entry in entries:
                    # Skip 'c:' as it's handled above or points to drive_c
                    if entry == "c:":
                        continue

                    # Entry is usually 'd:', 'e:', etc. or 'e::' (raw device)
                    if not entry.endswith(":"):
                        continue

                    link_path = os.path.join(dosdevices_path, entry)
                    if os.path.islink(link_path):
                        target = os.path.realpath(link_path)
                        if unix_path.startswith(target):
                            drive_letter = entry.rstrip(":").upper()
                            relative = os.path.relpath(unix_path, target)
                            if relative == ".":
                                return f"{drive_letter}:\\"
                            return f"{drive_letter}:\\{relative.replace('/', '\\')}"
            except Exception as e:
                logging.error(f"Error scanning dosdevices in {bottle_path}: {e}")

        # 3. Fallback to Z: drive
        return f"Z:\\{unix_path.lstrip('/').replace('/', '\\')}"

    @staticmethod
    def to_unix(bottle_path: str, windows_path: str) -> str:
        """
        Convert a Wine Windows path to a host Unix path for a specific bottle.
        """
        if not windows_path:
            return ""

        # Normalize separators
        windows_path = windows_path.replace("\\", "/")

        # Extract drive letter
        match = re.match(r"^([a-z]):/(.*)", windows_path, re.IGNORECASE)
        if not match:
            # Fallback for paths without drive letters
            return windows_path

        drive = match.group(1).lower()
        relative = match.group(2)

        # 1. Drive C
        if drive == "c":
            return os.path.join(bottle_path, "drive_c", relative)

        # 2. Other drives via dosdevices
        dosdevices_path = os.path.join(bottle_path, "dosdevices")
        link_path = os.path.join(dosdevices_path, f"{drive}:")
        if os.path.islink(link_path):
            target = os.path.realpath(link_path)
            return os.path.join(target, relative)

        # 3. Z: drive (root)
        if drive == "z":
            return f"/{relative}"

        return windows_path
