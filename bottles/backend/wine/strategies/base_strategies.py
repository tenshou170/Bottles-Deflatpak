# base_strategies.py
#
# Core execution strategies for Wine and Runners.

import os
from typing import Any
from bottles.backend.managers.system import SystemManager
from bottles.backend.managers.discovery import DiscoveryManager
from bottles.backend.utils.steam import SteamUtils
from bottles.backend.utils.path import PathUtils
from bottles.backend.wine.strategies.strategist import (
    ExecutionStrategist,
    ExecutionContext,
)
from bottles.backend.logger import Logger

logging = Logger()


class BaseWineStrategist(ExecutionStrategist):
    """
    Handles core Wine environment variables: PREFIX, ARCH, DEBUG, LC_ALL, etc.
    """

    def apply(self, context: ExecutionContext, config: Any):
        params = config.Parameters

        # Core identification
        context.add_env("BOTTLE", config.Path)

        if not context.return_steam_env:
            bottle_path = PathUtils.get_bottle_path(config)
            context.add_env("WINEPREFIX", bottle_path)
            context.add_env("WINEARCH", config.Arch)

            # Debug level
            debug_level = "fixme-all"
            if params.fixme_logs:
                debug_level = "+fixme-all"
            context.add_env("WINEDEBUG", debug_level)

        # Language
        if config.Language != "sys":
            context.add_env("LC_ALL", config.Language)


class RunnerStrategist(ExecutionStrategist):
    """
    Handles Runner discovery, library paths, and Proton-specific configurations.
    """

    def apply(self, context: ExecutionContext, config: Any):
        runner_path = PathUtils.get_runner_path(config.Runner)
        if config.Environment == "Steam":
            runner_path = config.RunnerPath

        is_proton = SteamUtils.is_proton(runner_path)
        proton_root_path = runner_path if is_proton else None

        if is_proton:
            # For Proton, we need to point to the distribution directory for binaries
            runner_path = SteamUtils.get_dist_directory(runner_path)

        context.metadata["runner_path"] = runner_path
        context.metadata["proton_root_path"] = proton_root_path
        context.metadata["is_proton"] = is_proton

        if self._needs_steam_virtual_gamepad_workaround(config.Runner):
            context.add_env("SteamVirtualGamepadInfo", "")

        # Library paths
        ld_paths = []
        if config.Arch == "win64":
            runner_libs = [
                "lib",
                "lib64",
                "lib/wine/x86_64-unix",
                "lib32/wine/x86_64-unix",
                "lib64/wine/x86_64-unix",
                "lib/wine/i386-unix",
                "lib32/wine/i386-unix",
                "lib64/wine/i386-unix",
            ]
        else:
            runner_libs = [
                "lib",
                "lib/wine/i386-unix",
                "lib32/wine/i386-unix",
                "lib64/wine/i386-unix",
            ]

        if not config.Runner.startswith("sys-"):
            for lib in runner_libs:
                path = os.path.join(runner_path, lib)
                if os.path.exists(path):
                    ld_paths.append(path)

            if ld_paths:
                context.concat_env("LD_LIBRARY_PATH", ":".join(ld_paths))

        # GStreamer (if not using system one)
        if (
            "BOTTLES_USE_SYSTEM_GSTREAMER" not in context.env
            and not context.return_steam_env
        ):
            gst_libs = (
                ["lib64/gstreamer-1.0", "lib/gstreamer-1.0", "lib32/gstreamer-1.0"]
                if config.Arch == "win64"
                else ["lib/gstreamer-1.0", "lib32/gstreamer-1.0"]
            )
            gst_env_path = []
            for lib in gst_libs:
                path = os.path.join(runner_path, lib)
                if os.path.exists(path):
                    gst_env_path.append(path)
            if gst_env_path:
                context.add_env("GST_PLUGIN_SYSTEM_PATH", ":".join(gst_env_path))

    def _needs_steam_virtual_gamepad_workaround(self, runner_name: str) -> bool:
        import re

        if not runner_name:
            return False
        normalized = runner_name.lower()
        if not any(
            prefix in normalized
            for prefix in ("ge-proton", "proton-ge", "wine-ge", "soda")
        ):
            return False
        match = re.search(r"(\d+)", normalized)
        if not match:
            return False
        try:
            major = int(match.group(1))
        except ValueError:
            return False
        return major <= 8


class WaylandStrategist(ExecutionStrategist):
    """
    Handles Wayland-specific environment variables.
    """

    def apply(self, context: ExecutionContext, config: Any):
        params = config.Parameters
        from bottles.backend.utils.display import DisplayUtils

        if not getattr(params, "wayland", False):
            return
        if DisplayUtils.display_server_type() != "wayland":
            return

        wayland_display = os.environ.get("WAYLAND_DISPLAY")
        if "WAYLAND_DISPLAY" not in context.env and wayland_display:
            context.add_env("WAYLAND_DISPLAY", wayland_display)

        if "WAYLAND_DISPLAY" in context.env or wayland_display:
            if "DISPLAY" in context.env:
                del context.env["DISPLAY"]
