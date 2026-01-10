# program_controller.py
#
# Controller class to delegate business logic from ProgramEntry widget.

import webbrowser
from gettext import gettext as _

from bottles.backend.logger import Logger
from bottles.backend.managers.library import LibraryManager
from bottles.backend.managers.system import SystemManager
from bottles.backend.runner import Runner
from bottles.backend.utils.threading import RunAsync
from bottles.backend.wine.executor import WineExecutor
from bottles.backend.wine.uninstaller import Uninstaller
from bottles.backend.wine.winedbg import WineDbg
from bottles.frontend.utils.gtk import GtkUtils

logging = Logger()


class ProgramController:
    def __init__(self, window, config, program):
        self.window = window
        self.config = config
        self.program = program
        self.manager = window.manager
        self.executable = program.get("executable", "")

    def run(self, with_terminal=False, callback=None):
        def _run():
            WineExecutor.run_program(self.config, self.program, with_terminal)
            return True

        self.window.show_toast(_('Launching "{0}"…').format(self.program["name"]))
        RunAsync(_run, callback=callback)

    def stop(self, callback=None):
        self.window.show_toast(_('Stopping "{0}"…').format(self.program["name"]))
        winedbg = WineDbg(self.config)
        winedbg.kill_process(self.executable)
        if callback:
            callback(True)

    def run_steam(self):
        self.manager.steam_manager.launch_app(self.config.CompatData)
        self.window.show_toast(
            _('Launching "{0}" with Steam…').format(self.program["name"])
        )

    def uninstall(self, callback=None):
        uninstaller = Uninstaller(self.config)
        RunAsync(
            task_func=uninstaller.from_name,
            callback=callback,
            name=self.program["name"],
        )

    def toggle_visibility(self, callback=None):
        status = not self.program.get("removed")
        msg = _('"{0}" hidden').format(self.program["name"])
        if not status:
            msg = _('"{0}" showed').format(self.program["name"])

        self.program["removed"] = status
        self.save_program()
        self.window.show_toast(msg)
        if callback:
            callback()

    def remove(self, callback=None):
        self.manager.update_config(
            config=self.config,
            key=self.program["id"],
            scope="External_Programs",
            value=None,
            remove=True,
        )
        self.window.show_toast(_('"{0}" removed').format(self.program["name"]))
        if callback:
            callback()

    def rename(self, new_name, callback=None):
        if new_name == self.program["name"]:
            return
        old_name = self.program["name"]
        self.program["name"] = new_name
        self.save_program()

        def async_work():
            library_manager = LibraryManager()
            entries = library_manager.get_library()

            for uuid, entry in entries.items():
                if entry.get("id") == self.program["id"]:
                    entries[uuid]["name"] = new_name
                    library_manager.download_thumbnail(uuid, self.config)
                    break

            library_manager._LibraryManager__library = entries
            library_manager.save_library()

        @GtkUtils.run_in_main_loop
        def ui_update(_result, _error):
            self.window.page_library.update()
            self.window.show_toast(
                _('"{0}" renamed to "{1}"').format(old_name, new_name)
            )
            if callback:
                callback()

        RunAsync(async_work, callback=ui_update)

    def add_desktop_entry(self):
        @GtkUtils.run_in_main_loop
        def update(result, _error=False):
            if not result:
                webbrowser.open("https://docs.usebottles.com/bottles/programs")
                return

            self.window.show_toast(
                _('Desktop Entry created for "{0}"').format(self.program["name"])
            )

        RunAsync(
            SystemManager.create_desktop_entry,
            callback=update,
            config=self.config,
            program={
                "name": self.program["name"],
                "executable": self.program["executable"],
                "path": self.program["path"],
            },
        )

    def add_to_library(self, callback=None):
        def update(_result, _error=False):
            self.window.update_library()
            self.window.show_toast(
                _('"{0}" added to your library').format(self.program["name"])
            )
            if callback:
                callback()

        def add_to_library_task():
            self.save_program()
            library_manager = LibraryManager()
            library_manager.add_to_library(
                {
                    "bottle": {"name": self.config.Name, "path": self.config.Path},
                    "name": self.program["name"],
                    "id": str(self.program["id"]),
                    "icon": SystemManager.extract_icon(
                        self.config, self.program["name"], self.program["path"]
                    ),
                },
                self.config,
            )

        RunAsync(add_to_library_task, update)

    def add_to_steam(self):
        def update(result, _error=False):
            if result.ok:
                self.window.show_toast(
                    _('"{0}" added to your Steam library').format(self.program["name"])
                )

        RunAsync(
            self.manager.steam_manager.add_shortcut,
            update,
            program_name=self.program["name"],
            program_path=self.program["path"],
        )

    def save_program(self):
        res = self.manager.update_config(
            config=self.config,
            key=self.program["id"],
            value=self.program,
            scope="External_Programs",
        )
        self.config = res.data["config"]
        return self.config

    def browse_folder(self):
        SystemManager.open_filemanager(
            config=self.config, path_type="custom", custom_path=self.program["folder"]
        )

    def is_process_alive(self, callback):
        winedbg = WineDbg(self.config)
        RunAsync(
            winedbg.is_process_alive,
            callback=callback,
            name=self.executable,
        )

    def wait_for_process(self, callback, timeout=5):
        winedbg = WineDbg(self.config)
        RunAsync(
            winedbg.wait_for_process,
            callback=callback,
            name=self.executable,
            timeout=timeout,
        )
