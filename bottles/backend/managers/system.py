# system.py
#
# Specific manager for app directories and cache management.

import os
import shutil
from datetime import datetime
from glob import glob
from typing import Any, Optional, Callable

import icoextract  # type: ignore [import-untyped]

from bottles.backend.globals import Paths
from bottles.backend.logger import Logger
from bottles.backend.managers.template import TemplateManager
from bottles.backend.models.config import BottleConfig
from bottles.backend.models.result import Result
from bottles.backend.params import APP_ID
from bottles.backend.state import SignalManager, Signals
from bottles.backend.utils.file import FileUtils
from bottles.backend.utils.generic import get_mime
from bottles.backend.utils.imagemagick import ImageMagickUtils
from bottles.backend.utils.path import PathUtils
from bottles.backend.utils.portal import PortalUtils

logging = Logger()


class SystemManager:
    def __init__(self, settings: Any, steam_manager: Any):
        self.settings = settings
        self.steam_manager = steam_manager

    def check_app_dirs(self):
        """
        Checks for the existence of the bottles' directories, and creates them
        if they don't exist.
        """
        dirs = [
            (Paths.runners, "Runners"),
            (Paths.runtimes, "Runtimes"),
            (Paths.winebridge, "WineBridge"),
            (Paths.bottles, "Bottles"),
            (Paths.dxvk, "Dxvk"),
            (Paths.vkd3d, "Vkd3d"),
            (Paths.nvapi, "Nvapi"),
            (Paths.templates, "Templates"),
            (Paths.temp, "Temp"),
            (Paths.latencyflex, "LatencyFleX"),
        ]

        for path, name in dirs:
            if not os.path.isdir(path):
                logging.info(f"{name} path doesn't exist, creating now.")
                os.makedirs(path, exist_ok=True)

        if (
            self.settings.get_boolean("steam-proton-support")
            and self.steam_manager.is_steam_supported
        ):
            if not os.path.isdir(Paths.steam):
                logging.info("Steam path doesn't exist, creating now.")
                os.makedirs(Paths.steam, exist_ok=True)

    def _clear_temp(self, force: bool = False):
        """Clears the temp directory if user setting allows it. Use the force
        parameter to force clearing the directory.
        """
        if self.settings.get_boolean("temp") or force:
            try:
                shutil.rmtree(Paths.temp)
                os.makedirs(Paths.temp, exist_ok=True)
                logging.info("Temp directory cleaned successfully!")
            except FileNotFoundError:
                self.check_app_dirs()

    def get_cache_details(self) -> dict:
        self.check_app_dirs()
        file_utils = FileUtils()

        temp_size_bytes = file_utils.get_path_size(Paths.temp, human=False)
        templates = []
        templates_size_bytes = 0

        for template in TemplateManager.get_templates():
            template_uuid = template.get("uuid", "")
            template_path = os.path.join(Paths.templates, template_uuid)

            size_bytes = file_utils.get_path_size(template_path, human=False)
            templates_size_bytes += size_bytes

            templates.append(
                {
                    "uuid": template_uuid,
                    "env": template.get("env", ""),
                    "created": template.get("created", ""),
                    "size": file_utils.get_human_size(size_bytes),
                    "size_bytes": size_bytes,
                }
            )

        total_size_bytes = temp_size_bytes + templates_size_bytes

        return {
            "temp": {
                "path": Paths.temp,
                "size": file_utils.get_human_size(temp_size_bytes),
                "size_bytes": temp_size_bytes,
            },
            "templates": templates,
            "templates_size": file_utils.get_human_size(templates_size_bytes),
            "templates_size_bytes": templates_size_bytes,
            "total_size": file_utils.get_human_size(total_size_bytes),
            "total_size_bytes": total_size_bytes,
        }

    def clear_temp_cache(self) -> Result[None]:
        try:
            self._clear_temp(force=True)
        except Exception as ex:
            logging.error(f"Failed to clear temp cache: {ex}")
            return Result(False, message=str(ex))

        return Result(True)

    def clear_template_cache(self, template_uuid: str) -> Result[None]:
        self.check_app_dirs()
        try:
            TemplateManager.delete_template(template_uuid)
        except Exception as ex:
            logging.error(f"Failed to clear template cache: {ex}")
            return Result(False, message=str(ex))

        return Result(True)

    def clear_templates_cache(self) -> Result[None]:
        self.check_app_dirs()
        try:
            for template in TemplateManager.get_templates():
                TemplateManager.delete_template(template.get("uuid", ""))
        except Exception as ex:
            logging.error(f"Failed to clear templates cache: {ex}")
            return Result(False, message=str(ex))

        return Result(True)

    def clear_all_caches(self) -> Result[None]:
        temp_result = self.clear_temp_cache()
        if not temp_result.ok:
            return temp_result

        templates_result = self.clear_templates_cache()
        if not templates_result.ok:
            return templates_result

        return Result(True)

    @staticmethod
    def get_bottle_path(config: BottleConfig) -> str:
        return PathUtils.get_bottle_path(config)

    @staticmethod
    def get_temp_path(dest: str) -> str:
        return f"{Paths.temp}/{dest}"

    @staticmethod
    def get_template_path(template: str) -> str:
        return f"{Paths.templates}/{template}"

    @staticmethod
    def get_exe_parent_dir(config: BottleConfig, executable_path: str):
        """Get parent directory of the executable."""
        if "\\" in executable_path:
            p = "\\".join(executable_path.split("\\")[:-1])
            p = p.replace("C:\\", "\\drive_c\\").replace("\\", "/")
            return PathUtils.get_bottle_path(config) + p
        return os.path.dirname(executable_path)

    @staticmethod
    def move_file_to_bottle(
        file_path: str, config: BottleConfig, fn_update: Optional[Callable] = None
    ) -> str | bool:
        logging.info(f"Adding file {file_path} to the bottle …")
        bottle_path = PathUtils.get_bottle_path(config)

        if not os.path.exists(f"{bottle_path}/storage"):
            os.makedirs(f"{bottle_path}/storage")

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        file_new_path = f"{bottle_path}/storage/{file_name}"

        logging.info(f"Copying file {file_path} to the bottle …")
        try:
            if file_size == 0:
                with open(file_new_path, "wb"):
                    pass
                if fn_update:
                    fn_update(1)
                return file_new_path

            chunk_size = 64 * 1024
            bytes_copied = 0
            with open(file_path, "rb") as f_in:
                with open(file_new_path, "wb") as f_out:
                    while True:
                        chunk = f_in.read(chunk_size)
                        if not chunk:
                            break
                        f_out.write(chunk)
                        bytes_copied += len(chunk)

                        if fn_update:
                            fn_update(bytes_copied / file_size)

                    if fn_update:
                        fn_update(1)
            return file_new_path
        except (OSError, IOError):
            logging.error(f"Could not copy file {file_path} to the bottle.")
            return False

    @staticmethod
    def extract_icon(config: BottleConfig, program_name: str, program_path: str) -> str:
        from bottles.backend.wine.winepath import WinePath

        winepath = WinePath(config)
        icon = f"{APP_ID}-program"
        bottle_icons_path = os.path.join(PathUtils.get_bottle_path(config), "icons")

        try:
            if winepath.is_windows(program_path):
                program_path = winepath.to_unix(program_path)

            ico_dest_temp = os.path.join(bottle_icons_path, f"_{program_name}.png")
            ico_dest = os.path.join(bottle_icons_path, f"{program_name}.png")
            ico = icoextract.IconExtractor(program_path)
            os.makedirs(bottle_icons_path, exist_ok=True)

            if os.path.exists(ico_dest_temp):
                os.remove(ico_dest_temp)

            if os.path.exists(ico_dest):
                os.remove(ico_dest)

            ico.export_icon(ico_dest_temp)
            if get_mime(ico_dest_temp) == "image/vnd.microsoft.icon":
                if not ico_dest_temp.endswith(".ico"):
                    shutil.move(ico_dest_temp, f"{ico_dest_temp}.ico")
                    ico_dest_temp = f"{ico_dest_temp}.ico"
                im = ImageMagickUtils(ico_dest_temp)
                im.convert(ico_dest)
                icon = ico_dest
            else:
                shutil.move(ico_dest_temp, ico_dest)
                icon = ico_dest
        except:  # pylint: disable=bare-except
            pass

        return icon

    @staticmethod
    def create_desktop_entry(
        config: BottleConfig,
        program: dict,
        skip_icon: bool = False,
        custom_icon: str = "",
        use_xdp: bool = False,
    ) -> bool:
        if not use_xdp:
            try:
                os.makedirs(Paths.applications, exist_ok=True)
            except OSError:
                return False

        is_devel = "Devel" in APP_ID
        cmd_legacy = "bottles" if not is_devel else "bottles-devel"
        cmd_cli = "bottles-cli" if not is_devel else "bottles-devel-cli"
        icon = f"{APP_ID}-program"

        if not skip_icon and not custom_icon:
            icon = SystemManager.extract_icon(
                config, program.get("name"), program.get("path")
            )
        elif custom_icon:
            icon = custom_icon

        if not use_xdp:
            file_name_template = "%s/%s--%s--%s.desktop"
            existing_files = glob(
                file_name_template
                % (Paths.applications, config.Name, program.get("name"), "*")
            )
            desktop_file = file_name_template % (
                Paths.applications,
                config.Name,
                program.get("name"),
                datetime.now().timestamp(),
            )

            if existing_files:
                for file in existing_files:
                    os.remove(file)

            with open(desktop_file, "w") as f:
                f.write("[Desktop Entry]\n")
                f.write(f"Name={program.get('name')}\n")
                f.write(
                    f"Exec={cmd_cli} run -p \"{program.get('name')}\" -b \"{config.get('Name')}\" -- %u\n"
                )
                f.write("Type=Application\n")
                f.write("Terminal=false\n")
                f.write("Categories=Application;\n")
                f.write(f"Icon={icon}\n")
                f.write(f"Comment=Launch {program.get('name')} using Bottles.\n")
                f.write(f"StartupWMClass={program.get('name')}\n")
                # Actions
                f.write("Actions=Configure;\n")
                f.write("[Desktop Action Configure]\n")
                f.write("Name=Configure in Bottles\n")
                f.write(f"Exec={cmd_legacy} -b \"{config.get('Name')}\"\n")

            return True
        if PortalUtils.is_available():
            portal = PortalUtils.get_portal()
            if portal:
                pass

        return False

    @staticmethod
    def open_filemanager(
        config: Optional[BottleConfig] = None,
        path_type: str = "bottle",
        component: str = "",
        custom_path: str = "",
    ):
        from bottles.backend.managers.discovery import DiscoveryManager

        logging.info("Opening the file manager in the path …")
        path = ""

        if path_type == "bottle" and config is None:
            raise NotImplementedError("bottle type need a valid Config")

        if path_type == "bottle":
            bottle_path = PathUtils.get_bottle_path(config)
            if config.Environment == "Steam":
                bottle_path = config.Path
            path = f"{bottle_path}/drive_c"
        elif component != "":
            if path_type in ["runner", "runner:proton"]:
                path = PathUtils.get_runner_path(component)
            elif path_type == "dxvk":
                path = PathUtils.get_dxvk_path(component)
            elif path_type == "vkd3d":
                path = PathUtils.get_vkd3d_path(component)
            elif path_type == "nvapi":
                path = PathUtils.get_nvapi_path(component)
            elif path_type == "latencyflex":
                path = PathUtils.get_latencyflex_path(component)
            elif path_type == "runtime":
                path = Paths.runtimes
            elif path_type == "winebridge":
                path = Paths.winebridge

        if path_type == "custom" and custom_path != "":
            path = custom_path

        path = f"file://{path}"
        SignalManager.send(Signals.GShowUri, Result(data=path))

    @staticmethod
    def get_languages(
        from_name=None,
        from_locale=None,
        from_index=None,
        get_index=False,
        get_locales=False,
    ):
        from gettext import gettext as _

        locales = [
            "sys",
            "bg_BG",
            "cs_CZ",
            "da_DK",
            "de_DE",
            "el_GR",
            "en_US",
            "es_ES",
            "et_EE",
            "fi_FI",
            "fr_FR",
            "hr_HR",
            "hu_HU",
            "it_IT",
            "lt_LT",
            "lv_LV",
            "nl_NL",
            "no_NO",
            "pl_PL",
            "pt_PT",
            "ro_RO",
            "ru_RU",
            "sk_SK",
            "sl_SI",
            "sv_SE",
            "tr_TR",
            "zh_CN",
            "ja_JP",
            "zh_TW",
            "ko_KR",
        ]
        names = [
            _("System"),
            _("Bulgarian"),
            _("Czech"),
            _("Danish"),
            _("German"),
            _("Greek"),
            _("English"),
            _("Spanish"),
            _("Estonian"),
            _("Finnish"),
            _("French"),
            _("Croatian"),
            _("Hungarian"),
            _("Italian"),
            _("Lithuanian"),
            _("Latvian"),
            _("Dutch"),
            _("Norwegian"),
            _("Polish"),
            _("Portuguese"),
            _("Romanian"),
            _("Russian"),
            _("Slovak"),
            _("Slovenian"),
            _("Swedish"),
            _("Turkish"),
            _("Chinese"),
            _("Japanese"),
            _("Taiwanese"),
            _("Korean"),
        ]

        if from_name and from_locale:
            raise ValueError("Cannot pass both from_name, from_locale and from_index.")

        if from_name:
            if from_name not in names:
                raise ValueError("Given name not in list.")
            i = names.index(from_name)
            if get_index:
                return i
            return from_name, locales[i]

        if from_locale:
            if from_locale not in locales:
                raise ValueError("Given locale not in list.")
            i = locales.index(from_locale)
            if get_index:
                return i
            return from_locale, names[i]

        if isinstance(from_index, int):
            if from_index not in range(0, len(locales)):
                raise ValueError("Given index not in range.")
            return locales[from_index], names[from_index]

        if get_locales:
            return locales

        return names

    @staticmethod
    def browse_wineprefix(wineprefix: dict):
        path = wineprefix.get("Path")
        if not path:
            return
        SystemManager.open_filemanager(custom_path=path, path_type="custom")
