# wrapper_strategies.py
#
# Strategies for command wrappers like gamescope, umu-run, etc.

from typing import Any
from bottles.backend.globals import (
    umu_run_available,
    gamescope_available,
    gamemode_available,
    mangohud_available,
    obs_vkc_available,
)
from bottles.backend.utils.steam import SteamUtils
from bottles.backend.wine.strategies.strategist import (
    ExecutionStrategist,
    ExecutionContext,
)
from bottles.backend.logger import Logger

logging = Logger()


class UmuStrategist(ExecutionStrategist):
    """
    Handles umu-run wrapping and environment vars (PROTONPATH, GAMEID, STORE).
    """

    def apply(self, context: ExecutionContext, config: Any):
        params = config.Parameters
        if not (umu_run_available and not context.return_steam_env and params.use_umu):
            return

        proton_root = context.metadata.get("proton_root_path")
        if not proton_root:
            return

        # 1. Environment variables
        context.add_env("PROTONPATH", proton_root)

        umu_id = getattr(params, "umu_id", "umu-default")
        if umu_id == "umu-default":
            try:
                from bottles.backend.utils.umu import UmuDatabase

                found_id = UmuDatabase.get_umu_id(config.Name)
                if found_id:
                    umu_id = found_id
            except Exception as e:
                logging.warning(f"UMU lookup failed: {e}")

        context.add_env("GAMEID", umu_id)
        context.add_env("STORE", getattr(params, "umu_store", "none"))

        # 2. Command wrapping (umu-run [FILE [ARG...]])
        # Note: Logic in winecommand.py suggests removing the runner if umu-run is used
        context.metadata["use_umu_wrap"] = True


class GamescopeStrategist(ExecutionStrategist):
    """
    Handles gamescope wrapping and temporary script generation.
    """

    def apply(self, context: ExecutionContext, config: Any):
        if not (
            gamescope_available
            and context.metadata.get("gamescope_activated")
            and not context.is_minimal
        ):
            return

        context.metadata["use_gamescope_wrap"] = True


class ToolWrapperStrategist(ExecutionStrategist):
    """
    Handles simple wrappers like gamemode, mangohud, and obs-vkcapture.
    """

    def apply(self, context: ExecutionContext, config: Any):
        params = config.Parameters
        if context.is_minimal:
            return

        wrappers = []

        # We check if they should be applied as direct command prefixes
        if gamemode_available and params.gamemode:
            wrappers.append(
                gamemode_available if not context.return_steam_env else "gamemode"
            )

        if (
            mangohud_available
            and params.mangohud
            and not context.metadata.get("gamescope_activated")
        ):
            wrappers.append(
                mangohud_available if not context.return_steam_env else "mangohud"
            )

        if obs_vkc_available and params.obsvkc:
            wrappers.append(obs_vkc_available)

        if wrappers:
            context.metadata["tool_wrappers"] = wrappers
