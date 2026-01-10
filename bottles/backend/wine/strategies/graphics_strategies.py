# graphics_strategies.py
#
# Strategies for graphics-related configurations (DXVK, VKD3D, FSR, etc.)

import os
from typing import Any
from bottles.backend.managers.system import SystemManager
from bottles.backend.managers.discovery import DiscoveryManager
from bottles.backend.utils.display import DisplayUtils
from bottles.backend.utils.path import PathUtils
from bottles.backend.utils.gpu import GPUUtils
from bottles.backend.wine.strategies.strategist import (
    ExecutionStrategist,
    ExecutionContext,
)


class GraphicsStrategist(ExecutionStrategist):
    """
    Handles environment variables for DXVK, VKD3D, LatencyFleX, MangoHud, vkBasalt, and OBS.
    """

    def apply(self, context: ExecutionContext, config: Any):
        params = config.Parameters
        bottle_path = PathUtils.get_bottle_path(config)

        if context.return_steam_env:
            return

        # 1. DXVK & VKD3D
        if params.dxvk:
            context.add_env("WINE_LARGE_ADDRESS_AWARE", "1")
            context.add_env(
                "DXVK_STATE_CACHE_PATH",
                os.path.join(bottle_path, "cache", "dxvk_state"),
            )
            context.add_env("STAGING_SHARED_MEMORY", "1")
            context.add_env("__GL_SHADER_DISK_CACHE", "1")
            context.add_env(
                "__GL_SHADER_DISK_CACHE_PATH",
                os.path.join(bottle_path, "cache", "gl_shader"),
            )
            context.add_env(
                "MESA_SHADER_CACHE_DIR",
                os.path.join(bottle_path, "cache", "mesa_shader"),
            )

        if params.vkd3d:
            context.add_env(
                "VKD3D_SHADER_CACHE_PATH",
                os.path.join(bottle_path, "cache", "vkd3d_shader"),
            )

        # 2. LatencyFleX
        if params.latencyflex:
            lf_path = PathUtils.get_latencyflex_path(config.LatencyFleX)
            lf_layer_path = os.path.join(
                lf_path, "layer/usr/share/vulkan/implicit_layer.d"
            )
            context.concat_env("VK_ADD_LAYER_PATH", lf_layer_path)
            context.add_env("LFX", "1")
            context.concat_env(
                "LD_LIBRARY_PATH",
                os.path.join(lf_path, "layer/usr/lib/x86_64-linux-gnu"),
            )
        else:
            context.add_env("DISABLE_LFX", "1")

        # 3. MangoHud & vkBasalt
        if params.mangohud and not context.is_minimal:
            # Note: handle_gamescope might override this or be needed
            context.add_env("MANGOHUD", "1")
            context.add_env("MANGOHUD_DLSYM", "1")
            if not params.mangohud_display_on_game_start:
                context.add_env("MANGOHUD_CONFIG", "no_display")

        if params.vkbasalt and not context.is_minimal:
            vkbasalt_conf_path = os.path.join(bottle_path, "vkBasalt.conf")
            if os.path.isfile(vkbasalt_conf_path):
                context.add_env("VKBASALT_CONFIG_FILE", vkbasalt_conf_path)
            context.add_env("ENABLE_VKBASALT", "1")

        # 4. OBS
        if params.obsvkc and not context.is_minimal:
            context.add_env("OBS_VKCAPTURE", "1")
            if DisplayUtils.display_server_type() == "x11":
                context.add_env("OBS_USE_EGL", "1")

        # 5. DXVK-NVAPI
        if params.dxvk_nvapi:
            context.add_env("DXVK_NVAPIHACK", "0")
            context.add_env("DXVK_ENABLE_NVAPI", "1")

        # 6. FSR
        if params.fsr:
            context.add_env("WINE_FULLSCREEN_FSR", "1")
            context.add_env(
                "WINE_FULLSCREEN_FSR_STRENGTH", str(params.fsr_sharpening_strength)
            )
            if params.fsr_quality_mode:
                context.add_env(
                    "WINE_FULLSCREEN_FSR_MODE", str(params.fsr_quality_mode)
                )


class GPUStrategist(ExecutionStrategist):
    """
    Handles Discrete GPU selection and ICD mapping.
    """

    def apply(self, context: ExecutionContext, config: Any):
        if context.return_steam_env:
            return

        gpu = GPUUtils().get_gpu()
        params = config.Parameters

        if params.discrete_gpu:
            discrete = gpu.get("prime", {}).get("discrete")
            if discrete:
                for k, v in discrete.get("envs", {}).items():
                    context.add_env(k, v)
                context.concat_env("VK_ICD_FILENAMES", discrete.get("icd"))

        # Fallback ICD
        if "VK_ICD_FILENAMES" not in context.env:
            prime = gpu.get("prime", {})
            if prime.get("integrated"):
                context.concat_env("VK_ICD_FILENAMES", prime["integrated"]["icd"])
            elif gpu.get("vendors"):
                first = list(gpu["vendors"].keys())[0]
                context.concat_env("VK_ICD_FILENAMES", gpu["vendors"][first]["icd"])
