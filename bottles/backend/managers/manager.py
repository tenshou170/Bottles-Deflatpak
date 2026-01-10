# manager.py
#
# Copyright 2025 mirkobrombin <brombin94@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, in version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import time
import concurrent.futures
from gettext import gettext as _
from threading import Event
from typing import Any, Callable, Dict, List, Optional, Tuple

from bottles.backend.globals import Paths
from bottles.backend.logger import Logger
from bottles.backend.managers.component import ComponentManager
from bottles.backend.managers.data import DataManager, UserDataKeys
from bottles.backend.managers.dependency import DependencyManager
from bottles.backend.managers.importer import ImportManager
from bottles.backend.managers.installer import InstallerManager
from bottles.backend.managers.registry_rule import RegistryRuleManager
from bottles.backend.managers.repository import RepositoryManager
from bottles.backend.managers.steam import SteamManager
from bottles.backend.managers.versioning import VersioningManager
from bottles.backend.managers.system import SystemManager
from bottles.backend.managers.discovery import DiscoveryManager
from bottles.backend.managers.bottle_manager import BottleManager
from bottles.backend.models.config import BottleConfig
from bottles.backend.models.process import (
    ProcessFinishedPayload,
    ProcessStartedPayload,
)
from bottles.backend.models.result import Result
from bottles.backend.state import SignalManager, Signals
from bottles.backend.utils.connection import ConnectionUtils
from bottles.backend.utils.gsettings_stub import GSettingsStub
from bottles.backend.utils.singleton import Singleton

logging = Logger()


class Manager(metaclass=Singleton):
    """
    Coordinator manager for Bottles.
    Delegates specialized tasks to sub-managers while maintaining backward compatibility.
    """

    _playtime_signals_connected: bool = False

    @property
    def runtimes_available(self) -> List[str]:
        return self.discovery_manager.runtimes_available

    @runtimes_available.setter
    def runtimes_available(self, value: List[str]):
        self.discovery_manager.runtimes_available = value

    @property
    def winebridge_available(self) -> List[str]:
        return self.discovery_manager.winebridge_available

    @winebridge_available.setter
    def winebridge_available(self, value: List[str]):
        self.discovery_manager.winebridge_available = value

    @property
    def runners_available(self) -> List[str]:
        return self.discovery_manager.runners_available

    @runners_available.setter
    def runners_available(self, value: List[str]):
        self.discovery_manager.runners_available = value

    @property
    def dxvk_available(self) -> List[str]:
        return self.discovery_manager.dxvk_available

    @dxvk_available.setter
    def dxvk_available(self, value: List[str]):
        self.discovery_manager.dxvk_available = value

    @property
    def vkd3d_available(self) -> List[str]:
        return self.discovery_manager.vkd3d_available

    @vkd3d_available.setter
    def vkd3d_available(self, value: List[str]):
        self.discovery_manager.vkd3d_available = value

    @property
    def nvapi_available(self) -> List[str]:
        return self.discovery_manager.nvapi_available

    @nvapi_available.setter
    def nvapi_available(self, value: List[str]):
        self.discovery_manager.nvapi_available = value

    @property
    def latencyflex_available(self) -> List[str]:
        return self.discovery_manager.latencyflex_available

    @latencyflex_available.setter
    def latencyflex_available(self, value: List[str]):
        self.discovery_manager.latencyflex_available = value

    @property
    def local_bottles(self) -> Dict[str, BottleConfig]:
        return self.bottle_manager.local_bottles

    @local_bottles.setter
    def local_bottles(self, value: Dict[str, BottleConfig]):
        self.bottle_manager.local_bottles = value

    @property
    def supported_runtimes(self) -> Dict:
        return self.discovery_manager.supported_runtimes

    @supported_runtimes.setter
    def supported_runtimes(self, value: Dict):
        self.discovery_manager.supported_runtimes = value

    @property
    def supported_winebridge(self) -> Dict:
        return self.discovery_manager.supported_winebridge

    @supported_winebridge.setter
    def supported_winebridge(self, value: Dict):
        self.discovery_manager.supported_winebridge = value

    @property
    def supported_wine_runners(self) -> Dict:
        return self.discovery_manager.supported_wine_runners

    @supported_wine_runners.setter
    def supported_wine_runners(self, value: Dict):
        self.discovery_manager.supported_wine_runners = value

    @property
    def supported_proton_runners(self) -> Dict:
        return self.discovery_manager.supported_proton_runners

    @supported_proton_runners.setter
    def supported_proton_runners(self, value: Dict):
        self.discovery_manager.supported_proton_runners = value

    @property
    def supported_dxvk(self) -> Dict:
        return self.discovery_manager.supported_dxvk

    @supported_dxvk.setter
    def supported_dxvk(self, value: Dict):
        self.discovery_manager.supported_dxvk = value

    @property
    def supported_vkd3d(self) -> Dict:
        return self.discovery_manager.supported_vkd3d

    @supported_vkd3d.setter
    def supported_vkd3d(self, value: Dict):
        self.discovery_manager.supported_vkd3d = value

    @property
    def supported_nvapi(self) -> Dict:
        return self.discovery_manager.supported_nvapi

    @supported_nvapi.setter
    def supported_nvapi(self, value: Dict):
        self.discovery_manager.supported_nvapi = value

    @property
    def supported_latencyflex(self) -> Dict:
        return self.discovery_manager.supported_latencyflex

    @supported_latencyflex.setter
    def supported_latencyflex(self, value: Dict):
        self.discovery_manager.supported_latencyflex = value

    @property
    def supported_dependencies(self) -> Dict:
        return self.discovery_manager.supported_dependencies

    @supported_dependencies.setter
    def supported_dependencies(self, value: Dict):
        self.discovery_manager.supported_dependencies = value

    @property
    def supported_installers(self) -> Dict:
        return self.discovery_manager.supported_installers

    @supported_installers.setter
    def supported_installers(self, value: Dict):
        self.discovery_manager.supported_installers = value

    def __init__(
        self,
        g_settings: Optional[Any] = None,
        check_connection: bool = True,
        is_cli: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)

        times = {"start": time.time()}

        # common variables
        self.is_cli = is_cli
        self.settings = g_settings or GSettingsStub
        self.utils_conn = ConnectionUtils(
            force_offline=self.is_cli or self.settings.get_boolean("force-offline")
        )
        self.data_mgr = DataManager()
        _offline = True

        if check_connection:
            _offline = not self.utils_conn.check_connection()

        # validating user-defined Paths.bottles
        if user_bottles_path := self.data_mgr.get(UserDataKeys.CustomBottlesPath):
            if os.path.exists(user_bottles_path):
                Paths.bottles = user_bottles_path
            else:
                logging.error(
                    f"Custom bottles path {user_bottles_path} does not exist! "
                    f"Falling back to default path."
                )

        # sub-managers
        self.repository_manager = RepositoryManager(get_index=not _offline)
        if self.repository_manager.aborted_connections > 0:
            self.utils_conn.status = False
            _offline = True

        times["RepositoryManager"] = time.time()
        self.versioning_manager = VersioningManager(self)
        times["VersioningManager"] = time.time()
        self.component_manager = ComponentManager(self, _offline)
        self.installer_manager = InstallerManager(self, _offline)
        self.dependency_manager = DependencyManager(self, _offline)
        self.import_manager = ImportManager(self)
        times["ImportManager"] = time.time()
        self.steam_manager = SteamManager()
        times["SteamManager"] = time.time()

        # Initialize sub-managers
        self.system_manager = SystemManager(self.settings, self.steam_manager)
        self.discovery_manager = DiscoveryManager(
            self.settings,
            self.utils_conn,
            self.component_manager,
            self.dependency_manager,
            self.installer_manager,
            self.steam_manager,
        )
        self.bottle_manager = BottleManager(
            self.settings,
            self.discovery_manager,
            self.dependency_manager,
            self.steam_manager,
            self.versioning_manager,
            self.system_manager,
        )

        # React to runtime changes in playtime preference when available
        if hasattr(self.settings, "connect"):
            try:
                self.settings.connect(
                    "changed::playtime-enabled", self._on_playtime_enabled_changed
                )
            except (AttributeError, TypeError, Exception):
                pass

        # Subscribe to playtime signals (connect once per process)
        if not Manager._playtime_signals_connected:
            SignalManager.connect(Signals.ProgramStarted, self._on_program_started)
            SignalManager.connect(Signals.ProgramFinished, self._on_program_finished)
            Manager._playtime_signals_connected = True

        if not self.is_cli:
            times.update(self.checks(install_latest=False, first_run=True).data)
        else:
            logging.set_silent()

        if "BOOT_TIME" in os.environ:
            _temp_times = times.copy()
            last = 0
            times_str = "Boot times:"
            for f, t in _temp_times.items():
                if last == 0:
                    last = int(round(t))
                    continue
                t = int(round(t))
                times_str += f"\n\t - {f} took: {t - last}s"
                last = t
            logging.info(times_str)

    def checks(
        self,
        install_latest=False,
        first_run=False,
        progress_callback: Optional[Callable[..., None]] = None,
    ) -> Result:
        logging.info("Performing Bottles checks\u2026")

        rv = Result(status=True, data={})

        steps: List[Tuple[Optional[str], str, Callable[[], bool | None]]] = [
            ("check_app_dirs", _("Preparing folders\u2026"), self.check_app_dirs),
            (
                "check_dxvk",
                _("Setting up DXVK\u2026"),
                lambda: self.check_dxvk(install_latest),
            ),
            (
                "check_vkd3d",
                _("Setting up VKD3D\u2026"),
                lambda: self.check_vkd3d(install_latest),
            ),
            (
                "check_nvapi",
                _("Setting up NVAPI\u2026"),
                lambda: self.check_nvapi(install_latest),
            ),
            (
                "check_latencyflex",
                _("Setting up LatencyFleX\u2026"),
                lambda: self.check_latencyflex(install_latest),
            ),
            (
                "check_runtimes",
                _("Preparing runtimes\u2026"),
                lambda: self.check_runtimes(install_latest),
            ),
            (
                "check_winebridge",
                _("Preparing WineBridge\u2026"),
                lambda: self.check_winebridge(install_latest),
            ),
            (
                "check_runners",
                _("Preparing runners\u2026"),
                lambda: self.check_runners(install_latest),
            ),
        ]

        if first_run:
            steps.extend(
                [
                    (
                        None,
                        _("Organizing components\u2026"),
                        self.organize_components,
                    ),
                    (
                        None,
                        _("Cleaning temporary files\u2026"),
                        lambda: self._clear_temp(force=False),
                    ),
                ]
            )

        steps.extend(
            [
                (
                    None,
                    _("Organizing dependencies\u2026"),
                    self.organize_dependencies,
                ),
                (
                    None,
                    _("Organizing installers\u2026"),
                    self.organize_installers,
                ),
                ("check_bottles", _("Loading bottles\u2026"), self.check_bottles),
            ]
        )

        total_steps = len(steps)

        for index, (data_key, description, func) in enumerate(steps, start=1):
            # This is a legacy sequential fallback for now, but we want to parallelize
            # the heavy lifting while maintaining the logic order where needed.
            pass

        # Optimized execution
        def run_step(step_idx, step_data):
            d_key, desc, st_func = step_data
            if progress_callback:
                progress_callback(
                    description=desc,
                    current_step=step_idx,
                    total_steps=total_steps,
                    completed=False,
                )

            res = st_func()

            if progress_callback:
                progress_callback(
                    description=desc,
                    current_step=step_idx,
                    total_steps=total_steps,
                    completed=True,
                )
            return d_key, res

        # 1. Essential prep
        self.check_app_dirs()
        rv.data["check_app_dirs"] = time.time()

        # 2. Parallel component checks
        parallel_steps = [
            (
                "check_dxvk",
                _("Setting up DXVK\u2026"),
                lambda: self.check_dxvk(install_latest),
            ),
            (
                "check_vkd3d",
                _("Setting up VKD3D\u2026"),
                lambda: self.check_vkd3d(install_latest),
            ),
            (
                "check_nvapi",
                _("Setting up NVAPI\u2026"),
                lambda: self.check_nvapi(install_latest),
            ),
            (
                "check_latencyflex",
                _("Setting up LatencyFleX\u2026"),
                lambda: self.check_latencyflex(install_latest),
            ),
            (
                "check_runtimes",
                _("Preparing runtimes\u2026"),
                lambda: self.check_runtimes(install_latest),
            ),
            (
                "check_winebridge",
                _("Preparing WineBridge\u2026"),
                lambda: self.check_winebridge(install_latest),
            ),
            (
                "check_runners",
                _("Preparing runners\u2026"),
                lambda: self.check_runners(install_latest),
            ),
            ("check_bottles", _("Loading bottles\u2026"), self.check_bottles),
        ]

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=len(parallel_steps)
        ) as executor:
            futures = [
                executor.submit(run_step, i + 2, step)
                for i, step in enumerate(parallel_steps)
            ]
            for future in concurrent.futures.as_completed(futures):
                d_key, res = future.result()
                if res is False:
                    rv.set_status(False)
                if d_key:
                    rv.data[d_key] = time.time()

        # 3. Post-discovery organization (these are mostly async)
        org_steps = []
        if first_run:
            org_steps.extend(
                [
                    (None, _("Organizing components\u2026"), self.organize_components),
                    (
                        None,
                        _("Cleaning temporary files\u2026"),
                        lambda: self._clear_temp(force=False),
                    ),
                ]
            )

        org_steps.extend(
            [
                (None, _("Organizing dependencies\u2026"), self.organize_dependencies),
                (None, _("Organizing installers\u2026"), self.organize_installers),
            ]
        )

        for i, step in enumerate(org_steps, start=len(parallel_steps) + 2):
            _key, res = run_step(i, step)
            if res is False:
                rv.set_status(False)

        return rv

    def _on_playtime_enabled_changed(self, _settings, _key) -> None:
        enabled = self.settings.get_boolean("playtime-enabled")
        if not enabled:
            if (
                getattr(self.bottle_manager, "playtime_tracker", None)
                and self.bottle_manager.playtime_tracker.enabled
            ):
                self._launch_to_session.clear()
                self.bottle_manager.playtime_tracker.disable_tracking()
            return

        if (
            getattr(self.bottle_manager, "playtime_tracker", None)
            and self.bottle_manager.playtime_tracker.enabled
        ):
            return

        self.bottle_manager._initialize_playtime_tracker()

    # Playtime signal handlers
    _launch_to_session: Dict[str, int] = {}

    def playtime_start(
        self,
        *,
        bottle_id: str,
        bottle_name: str,
        bottle_path: str,
        program_name: str,
        program_path: str,
    ) -> Result[int]:
        try:
            sid = self.bottle_manager.playtime_tracker.start_session(
                bottle_id=bottle_id,
                bottle_name=bottle_name,
                bottle_path=bottle_path,
                program_name=program_name,
                program_path=program_path,
            )
            return Result(True, data=sid)
        except Exception as e:
            logging.exception(e)
            return Result(False, message=str(e))

    def playtime_finish(
        self,
        session_id: int,
        *,
        status: str = "success",
        ended_at: Optional[int] = None,
    ) -> Result[None]:
        try:
            if status == "success":
                self.bottle_manager.playtime_tracker.mark_exit(
                    session_id, status="success", ended_at=ended_at
                )
            else:
                self.bottle_manager.playtime_tracker.mark_failure(
                    session_id, status=status
                )
            return Result(True)
        except Exception as e:
            logging.exception(e)
            return Result(False, message=str(e))

    def _on_program_started(self, data: Optional[Result] = None) -> None:
        try:
            if not data or not data.data:
                return
            payload: ProcessStartedPayload = data.data  # type: ignore
            logging.debug(
                f"Playtime signal: started launch_id={payload.launch_id} bottle={payload.bottle_name} program={payload.program_name}"
            )
            res = self.playtime_start(
                bottle_id=payload.bottle_id,
                bottle_name=payload.bottle_name,
                bottle_path=payload.bottle_path,
                program_name=payload.program_name,
                program_path=payload.program_path,
            )
            if not res.ok:
                return
            sid = int(res.data or -1)
            self._launch_to_session[payload.launch_id] = sid

            config = self._get_payload_config(payload)
            if config:
                RegistryRuleManager.apply_rules(config, trigger="start_program")
        except Exception as e:
            logging.debug(f"Failed to handle program started signal: {e}")

    def _on_program_finished(self, data: Optional[Result] = None) -> None:
        try:
            if not data or not data.data:
                return
            payload: ProcessFinishedPayload = data.data  # type: ignore
            sid = self._launch_to_session.pop(payload.launch_id, -1)
            if sid and sid > 0:
                status = payload.status
                ended_at = int(payload.ended_at or time.time())
                logging.debug(
                    f"Playtime signal: finished launch_id={payload.launch_id} status={status} sid={sid}"
                )
                self.playtime_finish(sid, status=status, ended_at=ended_at)

            config = self._get_payload_config(payload)
            if config:
                RegistryRuleManager.apply_rules(config, trigger="stop_program")
        except Exception as e:
            logging.debug(f"Failed to handle program finished signal: {e}")

    def _get_payload_config(self, payload) -> Optional[BottleConfig]:
        config = self.local_bottles.get(payload.bottle_name)
        if isinstance(config, BottleConfig):
            return config

        try:
            config_path = os.path.join(payload.bottle_path, "bottle.yml")
            loaded = BottleConfig.load(config_path)
            if loaded.status:
                return loaded.data
        except (TypeError, ValueError, AttributeError):
            pass
        return None

    # System Manager Delegation
    def check_app_dirs(self):
        self.system_manager.check_app_dirs()

    def _clear_temp(self, force: bool = False):
        self.system_manager._clear_temp(force)

    def get_cache_details(self) -> dict:
        return self.system_manager.get_cache_details()

    def clear_temp_cache(self) -> Result[None]:
        return self.system_manager.clear_temp_cache()

    def clear_template_cache(self, template_uuid: str) -> Result[None]:
        return self.system_manager.clear_template_cache(template_uuid)

    def clear_templates_cache(self) -> Result[None]:
        return self.system_manager.clear_templates_cache()

    def clear_all_caches(self) -> Result[None]:
        return self.system_manager.clear_all_caches()

    # Discovery Manager Delegation
    def organize_components(self):
        self.discovery_manager.organize_components()

    def organize_dependencies(self):
        self.discovery_manager.organize_dependencies()

    def organize_installers(self):
        self.discovery_manager.organize_installers()

    def check_runners(self, install_latest: bool = True) -> bool:
        return self.discovery_manager.check_runners(install_latest)

    def check_runtimes(self, install_latest: bool = True) -> bool:
        return self.discovery_manager.check_runtimes(install_latest)

    def winebridge_update_status(self) -> dict:
        return self.discovery_manager.winebridge_update_status()

    def check_winebridge(
        self, install_latest: bool = True, update: bool = False
    ) -> bool:
        return self.discovery_manager.check_winebridge(install_latest, update)

    def check_dxvk(self, install_latest: bool = True) -> bool:
        return self.discovery_manager.check_dxvk(install_latest)

    def check_vkd3d(self, install_latest: bool = True) -> bool:
        return self.discovery_manager.check_vkd3d(install_latest)

    def check_nvapi(self, install_latest: bool = True) -> bool:
        return self.discovery_manager.check_nvapi(install_latest)

    def check_latencyflex(self, install_latest: bool = True) -> bool:
        return self.discovery_manager.check_latencyflex(install_latest)

    def get_offline_components(
        self, component_type: str, extra_name_check: str = ""
    ) -> list:
        return self.discovery_manager.get_offline_components(
            component_type, extra_name_check
        )

    def get_latest_runner(self) -> str:
        return self.discovery_manager.get_latest_runner()

    # Bottle Manager Delegation
    def get_programs(self, config: BottleConfig) -> List[dict]:
        return self.bottle_manager.get_programs(config)

    def check_bottles(self, silent: bool = False):
        self.bottle_manager.check_bottles(silent)

    def update_bottles(self, silent: bool = False):
        self.bottle_manager.check_bottles(silent)
        SignalManager.send(Signals.ManagerLocalBottlesLoaded)

    def update_config(
        self,
        config: BottleConfig,
        key: str,
        value: Any,
        scope: str = "",
        remove: bool = False,
        fallback: bool = False,
    ) -> Result:
        return self.bottle_manager.update_config(
            config, key, value, scope, remove, fallback
        )

    def apply_audio_driver(self, driver: str) -> Result[None]:
        return self.bottle_manager.apply_audio_driver(driver)

    def create_bottle_from_config(self, config: BottleConfig) -> bool:
        return self.bottle_manager.create_bottle_from_config(config)

    def create_bottle(
        self,
        name,
        environment: str,
        path: str = "",
        runner: str = False,
        dxvk: bool = False,
        vkd3d: bool = False,
        nvapi: bool = False,
        latencyflex: bool = False,
        versioning: bool = False,
        sandbox: bool = False,
        fn_logger: callable = None,
        arch: str = "win64",
        custom_environment: Optional[str] = None,
        cancel_event: Optional[Event] = None,
    ) -> Result:
        return self.bottle_manager.create_bottle(
            name,
            environment,
            path,
            runner,
            dxvk,
            vkd3d,
            nvapi,
            latencyflex,
            versioning,
            sandbox,
            fn_logger,
            arch,
            custom_environment,
            cancel_event,
        )

    def delete_bottle(self, config: BottleConfig) -> bool:
        return self.bottle_manager.delete_bottle(config)

    def repair_bottle(self, config: BottleConfig) -> Result:
        res = self.bottle_manager.repair_bottle(config)
        return Result(res)

    def install_dll_component(
        self, config: BottleConfig, component: str, state: bool = True, **kwargs
    ) -> Result:
        return self.bottle_manager.install_dll_component(
            config, component, state, **kwargs
        )

    def remove_dependency(self, config: BottleConfig, dependency: list) -> Result:
        return self.bottle_manager.remove_dependency(config, dependency)
