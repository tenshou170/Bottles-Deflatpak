# discovery.py
#
# Specific manager for runners, components, dependencies and installers discovery.

import os
import subprocess
import concurrent.futures
from glob import glob
from typing import Any, Dict, List, Optional, Tuple

from bottles.backend.globals import Paths
from bottles.backend.logger import Logger
from bottles.backend.models.config import BottleConfig
from bottles.backend.utils import yaml
from bottles.backend.utils.generic import sort_by_version
from bottles.backend.utils.steam import SteamUtils
from bottles.backend.utils.threading import RunAsync
from bottles.backend.utils.wine import WineUtils
from bottles.backend.utils.path import PathUtils
from bottles.backend.state import EventManager, Events
from bottles.backend.models.result import Result

logging = Logger()


class DiscoveryManager:
    def __init__(
        self,
        settings: Any,
        utils_conn: Any,
        component_manager: Any,
        dependency_manager: Any,
        installer_manager: Any,
        steam_manager: Any,
    ):
        self.settings = settings
        self.utils_conn = utils_conn
        self.component_manager = component_manager
        self.dependency_manager = dependency_manager
        self.installer_manager = installer_manager
        self.steam_manager = steam_manager

        # component lists
        self.runtimes_available: List[str] = []
        self.winebridge_available: List[str] = []
        self.runners_available: List[str] = []
        self.dxvk_available: List[str] = []
        self.vkd3d_available: List[str] = []
        self.nvapi_available: List[str] = []
        self.latencyflex_available: List[str] = []

        self.supported_runtimes: Dict = {}
        self.supported_winebridge: Dict = {}
        self.supported_wine_runners: Dict = {}
        self.supported_proton_runners: Dict = {}
        self.supported_dxvk: Dict = {}
        self.supported_vkd3d: Dict = {}
        self.supported_nvapi: Dict = {}
        self.supported_latencyflex: Dict = {}
        self.supported_dependencies: Dict = {}
        self.supported_installers: Dict = {}

    @RunAsync.run_async
    def organize_components(self):
        """Get components catalog and organizes into supported_ lists."""
        EventManager.wait(Events.ComponentsFetching)
        catalog = self.component_manager.fetch_catalog()
        if len(catalog) == 0:
            EventManager.done(Events.ComponentsOrganizing)
            logging.info("No components found.")
            return

        self.supported_wine_runners = catalog["wine"]
        self.supported_proton_runners = catalog["proton"]
        self.supported_runtimes = catalog["runtimes"]
        self.supported_winebridge = catalog["winebridge"]
        self.supported_dxvk = catalog["dxvk"]
        self.supported_vkd3d = catalog["vkd3d"]
        self.supported_nvapi = catalog["nvapi"]
        self.supported_latencyflex = catalog["latencyflex"]
        EventManager.done(Events.ComponentsOrganizing)

    @RunAsync.run_async
    def organize_dependencies(self):
        """Organizes dependencies into supported_dependencies."""
        EventManager.wait(Events.DependenciesFetching)
        catalog = self.dependency_manager.fetch_catalog()
        if len(catalog) == 0:
            EventManager.done(Events.DependenciesOrganizing)
            logging.info("No dependencies found!")
            return

        self.supported_dependencies = catalog
        EventManager.done(Events.DependenciesOrganizing)

    @RunAsync.run_async
    def organize_installers(self):
        """Organizes installers into supported_installers."""
        EventManager.wait(Events.InstallersFetching)
        catalog = self.installer_manager.fetch_catalog()
        if len(catalog) == 0:
            EventManager.done(Events.InstallersOrganizing)
            logging.info("No installers found!")
            return

        self.supported_installers = catalog
        EventManager.done(Events.InstallersOrganizing)

    def check_runners(self, install_latest: bool = True) -> bool:
        runners = glob(f"{Paths.runners}/*/")
        self.runners_available = []
        runners_available_list = []

        # lock winemenubuilder.exe in parallel
        def lock_winemenubuilder(runner):
            if not SteamUtils.is_proton(runner):
                winemenubuilder_paths = [
                    f"{runner}lib64/wine/x86_64-windows/winemenubuilder.exe",
                    f"{runner}lib/wine/x86_64-windows/winemenubuilder.exe",
                    f"{runner}lib32/wine/i386-windows/winemenubuilder.exe",
                    f"{runner}lib/wine/i386-windows/winemenubuilder.exe",
                ]
                for winemenubuilder in winemenubuilder_paths:
                    if os.path.isfile(winemenubuilder):
                        os.rename(winemenubuilder, f"{winemenubuilder}.lock")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(lock_winemenubuilder, runners)

        # check system wine
        if (wine_path := WineUtils.find_system_wine()) is not None:
            version = (
                subprocess.Popen(
                    f"{wine_path} --version", stdout=subprocess.PIPE, shell=True
                )
                .communicate()[0]
                .decode("utf-8")
            )
            version = "sys-" + version.split("\n")[0].split(" ")[0]
            runners_available_list.append(version)

        # check bottles runners
        for runner in runners:
            _runner = os.path.basename(os.path.normpath(runner))
            runners_available_list.append(_runner)

        # check system-wide steam compatibility tools (Proton) in parallel
        def check_ct_path(ct_path):
            found_protons = []
            for proton in glob(f"{ct_path}/*/"):
                if SteamUtils.is_proton(proton):
                    found_protons.append(os.path.basename(os.path.normpath(proton)))
            return found_protons

        ct_paths = SteamUtils.get_compatibility_tools_paths()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for protons in executor.map(check_ct_path, ct_paths):
                for _proton in protons:
                    if _proton not in runners_available_list:
                        runners_available_list.append(_proton)

        runners_available_list = self._sort_runners(runners_available_list, "")

        runners_order = {
            "soda": [],
            "caffe": [],
            "vaniglia": [],
            "lutris": [],
            "others": [],
            "sys-": [],
        }

        for i in runners_available_list:
            for r in runners_order:
                if i.startswith(r):
                    runners_order[r].append(i)
                    break
            else:
                runners_order["others"].append(i)

        self.runners_available = [x for l in list(runners_order.values()) for x in l]

        if len(self.runners_available) > 0:
            logging.info(
                "Runners found:\n - {0}".format("\n - ".join(self.runners_available))
            )

        tmp_runners = [x for x in self.runners_available if not x.startswith("sys-")]

        if len(tmp_runners) == 0 and install_latest:
            logging.warning("No managed runners found.")

            if self.utils_conn.check_connection():
                try:
                    if not self.settings.get_boolean("release-candidate"):
                        tmp_runners = []
                        for runner in self.supported_wine_runners.items():
                            if runner[1]["Channel"] not in ["rc", "unstable"]:
                                tmp_runners.append(runner)
                                break
                        runner_name = next(iter(tmp_runners))[0]
                    else:
                        tmp_runners = self.supported_wine_runners
                        runner_name = next(iter(tmp_runners))
                    self.component_manager.install("runner", runner_name)
                except StopIteration:
                    return False
            else:
                return False

        return True

    def check_runtimes(self, install_latest: bool = True) -> bool:
        self.runtimes_available = []
        runtimes = os.listdir(Paths.runtimes)

        if len(runtimes) == 0:
            if install_latest and self.utils_conn.check_connection():
                logging.warning("No runtime found.")
                try:
                    version = next(iter(self.supported_runtimes))
                    return self.component_manager.install("runtime", version)
                except StopIteration:
                    return False
            return False

        runtime = runtimes[0]
        manifest = os.path.join(Paths.runtimes, runtime, "manifest.yml")

        if os.path.exists(manifest):
            with open(manifest, "r") as f:
                data = yaml.load(f)
                version = data.get("version")
                if version:
                    version = f"runtime-{version}"
                    self.runtimes_available = [version]
                    return True
        return False

    def _winebridge_status(self) -> Tuple[Optional[str], Optional[str], bool]:
        def _is_newer(candidate: str, current: str) -> bool:
            versions = [candidate, current]
            try:
                sorted_versions = sort_by_version(list(versions))
            except ValueError:
                sorted_versions = sorted(versions, reverse=True)
            return sorted_versions[0] == candidate and candidate != current

        self.winebridge_available = []
        winebridge = os.listdir(Paths.winebridge)
        latest_supported = None

        if self.supported_winebridge:
            try:
                latest_supported = sort_by_version(
                    list(self.supported_winebridge.keys())
                )[0]
            except ValueError:
                latest_supported = sorted(
                    list(self.supported_winebridge.keys()), reverse=True
                )[0]

        version_file = os.path.join(Paths.winebridge, "VERSION")
        installed_identifier = None
        if os.path.exists(version_file):
            with open(version_file, "r") as f:
                version = f.read().strip()
                if version:
                    installed_identifier = f"winebridge-{version}"
                    self.winebridge_available = [installed_identifier]

        missing_installation = len(winebridge) == 0 or not installed_identifier
        needs_latest = False
        if latest_supported:
            needs_latest = missing_installation or _is_newer(
                latest_supported, installed_identifier
            )

        return latest_supported, installed_identifier, needs_latest

    def winebridge_update_status(self) -> dict:
        latest_supported, installed_identifier, needs_latest = self._winebridge_status()
        return {
            "latest_supported": latest_supported,
            "installed_identifier": installed_identifier,
            "needs_latest": needs_latest,
            "missing": not installed_identifier,
        }

    def check_winebridge(
        self, install_latest: bool = True, update: bool = False
    ) -> bool:
        latest_supported, installed_identifier, needs_latest = self._winebridge_status()

        can_install = install_latest or update
        if can_install and needs_latest and latest_supported:
            if not self.utils_conn.check_connection():
                return False
            logging.warning("WineBridge installation/update required.")
            res = self.component_manager.install("winebridge", latest_supported)
            if res.ok:
                self.winebridge_available = [latest_supported]
                return True
            return False

        if needs_latest and not can_install:
            return False

        return bool(self.winebridge_available)

    def check_dxvk(self, install_latest: bool = True) -> bool:
        res = self._check_component("dxvk", install_latest)
        if res:
            self.dxvk_available = res
        return res is not False

    def check_vkd3d(self, install_latest: bool = True) -> bool:
        res = self._check_component("vkd3d", install_latest)
        if res:
            self.vkd3d_available = res
        return res is not False

    def check_nvapi(self, install_latest: bool = True) -> bool:
        res = self._check_component("nvapi", install_latest)
        if res:
            self.nvapi_available = res
        return res is not False

    def check_latencyflex(self, install_latest: bool = True) -> bool:
        res = self._check_component("latencyflex", install_latest)
        if res:
            self.latencyflex_available = res
        return res is not False

    def get_offline_components(
        self, component_type: str, extra_name_check: str = ""
    ) -> list:
        components = {
            "dxvk": {
                "available": self.dxvk_available,
                "supported": self.supported_dxvk,
            },
            "vkd3d": {
                "available": self.vkd3d_available,
                "supported": self.supported_vkd3d,
            },
            "nvapi": {
                "available": self.nvapi_available,
                "supported": self.supported_nvapi,
            },
            "latencyflex": {
                "available": self.latencyflex_available,
                "supported": self.supported_latencyflex,
            },
            "runner": {
                "available": self.runners_available,
                "supported": self.supported_wine_runners,
            },
            "runner:proton": {
                "available": self.runners_available,
                "supported": self.supported_proton_runners,
            },
        }
        if component_type not in components:
            logging.warning(f"Unknown component type found: {component_type}")
            raise ValueError("Component type not supported.")

        component_list = components[component_type]
        offline_components = list(
            set(component_list["available"]).difference(
                component_list["supported"].keys()
            )
        )

        if component_type == "runner":
            offline_components = [
                runner
                for runner in offline_components
                if not runner.startswith("sys-")
                and not SteamUtils.is_proton(PathUtils.get_runner_path(runner))
            ]
        elif component_type == "runner:proton":
            offline_components = [
                runner
                for runner in offline_components
                if SteamUtils.is_proton(PathUtils.get_runner_path(runner))
            ]

        if (
            extra_name_check
            and extra_name_check not in component_list["available"]
            and extra_name_check not in component_list["supported"]
        ):
            offline_components.append(extra_name_check)

        try:
            return sort_by_version(offline_components)
        except ValueError:
            return sorted(offline_components, reverse=True)

    def _check_component(
        self, component_type: str, install_latest: bool = True
    ) -> bool | list:
        components = {
            "dxvk": {
                "available": self.dxvk_available,
                "supported": self.supported_dxvk,
                "path": Paths.dxvk,
            },
            "vkd3d": {
                "available": self.vkd3d_available,
                "supported": self.supported_vkd3d,
                "path": Paths.vkd3d,
            },
            "nvapi": {
                "available": self.nvapi_available,
                "supported": self.supported_nvapi,
                "path": Paths.nvapi,
            },
            "latencyflex": {
                "available": self.latencyflex_available,
                "supported": self.supported_latencyflex,
                "path": Paths.latencyflex,
            },
            "runtime": {
                "available": self.runtimes_available,
                "supported": self.supported_runtimes,
                "path": Paths.runtimes,
            },
        }

        if component_type not in components:
            logging.warning(f"Unknown component type found: {component_type}")
            raise ValueError("Component type not supported.")

        component = components[component_type]
        component["available"] = os.listdir(component["path"])

        if len(component["available"]) > 0:
            logging.info(
                "{0}s found:\n - {1}".format(
                    component_type.capitalize(), "\n - ".join(component["available"])
                )
            )

        if len(component["available"]) == 0 and install_latest:
            logging.warning(f"No {component_type} found.")

            if self.utils_conn.check_connection():
                try:
                    if not self.settings.get_boolean("release-candidate"):
                        tmp_components = []
                        for cpnt in component["supported"].items():
                            if cpnt[1]["Channel"] not in ["rc", "unstable"]:
                                tmp_components.append(cpnt)
                                break
                        component_version = next(iter(tmp_components))[0]
                    else:
                        tmp_components = component["supported"]
                        component_version = next(iter(tmp_components))
                    self.component_manager.install(component_type, component_version)
                    component["available"] = [component_version]
                except StopIteration:
                    return False
            else:
                return False

        try:
            return sort_by_version(component["available"])
        except ValueError:
            return sorted(component["available"], reverse=True)

    def _sort_runners(self, runner_list: list, prefix: str) -> List[str]:
        """
        Return a sorted list of runners for a given prefix.
        """
        try:
            return sort_by_version(runner_list)
        except ValueError:
            return sorted(runner_list, reverse=True)

    def get_latest_runner(self, runner_prefix: str = "soda") -> str:
        """Return the latest available runner for a given prefix."""
        runners = [
            runner
            for runner in self.runners_available
            if runner.startswith(runner_prefix)
        ]
        if len(runners) > 0:
            return runners[0]
        return ""

    @staticmethod
    def get_runner_path(runner: str) -> str:
        return PathUtils.get_runner_path(runner)

    @staticmethod
    def get_dxvk_path(dxvk: str) -> str:
        return PathUtils.get_dxvk_path(dxvk)

    @staticmethod
    def get_vkd3d_path(vkd3d: str) -> str:
        return PathUtils.get_vkd3d_path(vkd3d)

    @staticmethod
    def get_nvapi_path(nvapi: str) -> str:
        return PathUtils.get_nvapi_path(nvapi)

    @staticmethod
    def get_latencyflex_path(latencyflex: str) -> str:
        return PathUtils.get_latencyflex_path(latencyflex)
