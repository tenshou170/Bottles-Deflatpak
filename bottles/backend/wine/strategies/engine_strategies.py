# engine_strategies.py
#
# Strategies for engine-level configurations (Sync, Runtimes, etc.)

from typing import Any
from bottles.backend.globals import ntsync_available
from bottles.backend.managers.runtime import RuntimeManager
from bottles.backend.utils.steam import SteamUtils
from bottles.backend.wine.strategies.strategist import (
    ExecutionStrategist,
    ExecutionContext,
)
from bottles.backend.logger import Logger

logging = Logger()


class SyncStrategist(ExecutionStrategist):
    """
    Handles Esync, Fsync, and NTsync environment variables.
    """

    def apply(self, context: ExecutionContext, config: Any):
        params = config.Parameters

        if params.sync == "esync":
            context.add_env("WINEESYNC", "1")
        elif params.sync == "fsync":
            context.add_env("WINEFSYNC", "1")

        if ntsync_available:
            # Check context metadata for runner info set by RunnerStrategist
            if context.metadata.get("is_proton"):
                context.add_env("PROTON_USE_NTSYNC", "1")


class RuntimeStrategist(ExecutionStrategist):
    """
    Handles Bottles and Steam Runtimes.
    """

    def apply(self, context: ExecutionContext, config: Any):
        params = config.Parameters
        if context.return_steam_env or context.is_terminal:
            return

        # 1. Bottles Runtime
        if params.use_runtime or params.use_eac_runtime or params.use_be_runtime:
            runtime_env = RuntimeManager.get_runtime_env("bottles")
            if runtime_env:
                if params.use_runtime:
                    logging.info("Using Bottles runtime")
                    context.concat_env("LD_LIBRARY_PATH", ":".join(runtime_env))

                # Anti-leak runtimes
                if not context.is_minimal:
                    eac = RuntimeManager.get_eac()
                    be = RuntimeManager.get_be()
                    if eac:
                        logging.info("Using EasyAntiCheat runtime")
                        context.add_env("PROTON_EAC_RUNTIME", eac)
                        context.concat_env(
                            "WINEDLLOVERRIDES",
                            "easyanticheat_x86,easyanticheat_x64=b,n",
                            sep=";",
                        )
                    if be:
                        logging.info("Using BattlEye runtime")
                        context.add_env("PROTON_BATTLEYE_RUNTIME", be)
                        context.concat_env(
                            "WINEDLLOVERRIDES", "beclient,beclient_x64=b,n", sep=";"
                        )
            else:
                logging.warning("Bottles runtime was requested but not found")

        # 2. Steam Runtime (Command wrapping)
        if params.use_steam_runtime:
            rs = RuntimeManager.get_runtimes("steam")
            picked = None
            runner_runtime = getattr(
                config, "RunnerRuntime", []
            )  # This might be context metadata or config

            if rs:
                if "sniper" in rs and "sniper" in runner_runtime:
                    picked = rs["sniper"]
                elif "soldier" in rs and "soldier" in runner_runtime:
                    picked = rs["soldier"]
                elif "scout" in rs:
                    picked = rs["scout"]

            if picked:
                logging.info(f"Using Steam runtime {picked['name']}")
                context.metadata["steam_runtime_entry"] = picked["entry_point"]
            else:
                logging.warning(
                    "Steam runtime requested but no valid combination found"
                )
