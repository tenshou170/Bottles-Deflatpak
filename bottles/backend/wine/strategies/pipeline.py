# pipeline.py
#
# Orchestrates execution strategies to build the final Wine command and environment.

from typing import Any, List
from bottles.backend.wine.strategies.strategist import (
    ExecutionContext,
    ExecutionStrategist,
)
from bottles.backend.wine.strategies.base_strategies import (
    BaseWineStrategist,
    RunnerStrategist,
    WaylandStrategist,
)
from bottles.backend.wine.strategies.graphics_strategies import (
    GraphicsStrategist,
    GPUStrategist,
)
from bottles.backend.wine.strategies.engine_strategies import (
    SyncStrategist,
    RuntimeStrategist,
)
from bottles.backend.wine.strategies.wrapper_strategies import (
    UmuStrategist,
    GamescopeStrategist,
    ToolWrapperStrategist,
)
from bottles.backend.logger import Logger

logging = Logger()


class WineExecutionPipeline:
    def __init__(self, config: Any, **context_kwargs):
        self.config = config
        self.context = ExecutionContext(**context_kwargs)
        self.strategists: List[ExecutionStrategist] = [
            BaseWineStrategist(),
            RunnerStrategist(),
            WaylandStrategist(),
            GraphicsStrategist(),
            GPUStrategist(),
            SyncStrategist(),
            RuntimeStrategist(),
            UmuStrategist(),
            GamescopeStrategist(),
            ToolWrapperStrategist(),
        ]

    def run(self) -> ExecutionContext:
        """
        Run the pipeline to populate the context with env and metadata.
        """
        for strategist in self.strategists:
            try:
                strategist.apply(self.context, self.config)
            except Exception as e:
                logging.exception(
                    f"Error in execution strategist {strategist.__class__.__name__}: {e}"
                )

        return self.context

    def generate_command(self, base_command: str) -> str:
        """
        Assemble the final command string using the context and strategists.
        """
        ctx = self.context

        # 1. Base command (with or without runner depending on UMU)
        cmd = base_command

        # Determine runner
        runner_path = ctx.metadata.get("runner_path")
        if not ctx.return_clean_env and runner_path:
            # Note: This reproduces the 'f"{runner} {command}"' logic from get_cmd
            # But we need to handle UMU wrap which removes the runner
            if ctx.metadata.get("use_umu_wrap"):
                pass  # Runner will be handled by umu-run if needed
            else:
                cmd = f"{runner_path} {cmd}"

        # 2. Wrappers
        if ctx.metadata.get("use_umu_wrap"):
            cmd = f"umu-run {cmd}"

        wrappers = ctx.metadata.get("tool_wrappers", [])
        for wrapper in reversed(wrappers):
            cmd = f"{wrapper} {cmd}"

        # 3. Gamescope (Heavy lifting)
        if ctx.metadata.get("use_gamescope_wrap"):
            import tempfile
            import stat
            import os

            gamescope_run = tempfile.NamedTemporaryFile(mode="w", suffix=".sh").name
            file_content = ["#!/usr/bin/env sh\n"]
            file_content.append(f"{cmd} $@")

            # Re-check mangohud for gamescope
            params = self.config.Parameters
            if ctx.metadata.get("mangohud_available") and params.mangohud:
                file_content.append(" &\nmangoapp")

            with open(gamescope_run, "w") as f:
                f.write("".join(file_content))

            st = os.stat(gamescope_run)
            os.chmod(gamescope_run, st.st_mode | stat.S_IEXEC)

            # Build gamescope command
            # This requires _get_gamescope_cmd logic from WineCommand
            # For now we'll assume it's passed in metadata or we duplicate it
            gamescope_bin = ctx.metadata.get("gamescope_bin", "gamescope")
            gamescope_args = ctx.metadata.get("gamescope_args", "")
            cmd = f"{gamescope_bin} {gamescope_args} -- {gamescope_run}"

        # 4. Runtime
        steam_runtime = ctx.metadata.get("steam_runtime_entry")
        if steam_runtime:
            cmd = f"{steam_runtime} {cmd}"

        return cmd
