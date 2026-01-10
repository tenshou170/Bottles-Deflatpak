from bottles.backend.utils.path import PathUtils
# program.py
#
# Widget for rendering program entries in the library and details views.

from gi.repository import Adw, Gtk

from bottles.backend.managers.library import LibraryManager
from bottles.backend.models.result import Result
from bottles.backend.managers.system import SystemManager
from bottles.frontend.utils.gtk import GtkUtils
from bottles.frontend.utils.playtime import PlaytimeService
from bottles.frontend.utils.program_controller import ProgramController
from bottles.frontend.windows.launchoptions import LaunchOptionsDialog
from bottles.frontend.windows.playtimegraph import PlaytimeGraphDialog
from bottles.frontend.windows.rename import RenameDialog


# noinspection PyUnusedLocal
@Gtk.Template(resource_path="/com/usebottles/bottles/program-entry.ui")
class ProgramEntry(Adw.ActionRow):
    __gtype_name__ = "ProgramEntry"

    btn_menu = Gtk.Template.Child()
    btn_run = Gtk.Template.Child()
    btn_stop = Gtk.Template.Child()
    btn_launch_options = Gtk.Template.Child()
    btn_playtime_stats = Gtk.Template.Child()
    btn_launch_steam = Gtk.Template.Child()
    btn_uninstall = Gtk.Template.Child()
    btn_remove = Gtk.Template.Child()
    btn_hide = Gtk.Template.Child()
    btn_unhide = Gtk.Template.Child()
    btn_rename = Gtk.Template.Child()
    btn_browse = Gtk.Template.Child()
    btn_add_steam = Gtk.Template.Child()
    btn_add_entry = Gtk.Template.Child()
    btn_add_library = Gtk.Template.Child()
    btn_launch_terminal = Gtk.Template.Child()
    pop_actions = Gtk.Template.Child()

    def __init__(
        self,
        window,
        config,
        program,
        is_steam=False,
        check_boot=True,
        is_running=None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        # common variables and references
        self.window = window
        self.view_bottle = window.page_details.view_bottle
        self.manager = window.manager
        self.config = config
        self.program = program
        self.controller = ProgramController(window, config, program)

        self.set_title(self.program["name"])

        if is_steam:
            self.set_subtitle("Steam")
            for w in [self.btn_run, self.btn_stop, self.btn_menu]:
                w.set_visible(False)
                w.set_sensitive(False)
            self.btn_launch_steam.set_visible(True)
            self.btn_launch_steam.set_sensitive(True)
            self.set_activatable_widget(self.btn_launch_steam)

        if program.get("removed"):
            self.add_css_class("removed")

        if program.get("auto_discovered"):
            self.btn_remove.set_visible(False)

        self.btn_hide.set_visible(not program.get("removed"))
        self.btn_unhide.set_visible(program.get("removed"))

        if self.manager.steam_manager.is_steam_supported:
            self.btn_add_steam.set_visible(True)

        library_manager = LibraryManager()
        for _uuid, entry in library_manager.get_library().items():
            if entry.get("id") == program.get("id"):
                self.btn_add_library.set_visible(False)

        self.btn_run.connect("clicked", self.run_executable)
        self.btn_launch_steam.connect("clicked", self.run_steam)
        self.btn_launch_terminal.connect("clicked", self.run_executable, True)
        self.btn_stop.connect("clicked", self.stop_process)
        self.btn_launch_options.connect("clicked", self.show_launch_options_view)
        self.btn_playtime_stats.connect("clicked", self.show_playtime_stats)
        self.btn_uninstall.connect("clicked", self.uninstall_program)
        self.btn_hide.connect("clicked", self.toggle_visibility)
        self.btn_unhide.connect("clicked", self.toggle_visibility)
        self.btn_rename.connect("clicked", self.rename_program)
        self.btn_browse.connect("clicked", self.browse_program_folder)
        self.btn_add_entry.connect("clicked", self.add_entry)
        self.btn_add_library.connect("clicked", self.add_to_library)
        self.btn_add_steam.connect("clicked", self.add_to_steam)
        self.btn_remove.connect("clicked", self.remove_program)

        if not program.get("removed") and not is_steam:
            if is_running is True:
                self.__start_watcher(True)
            elif is_running is False:
                pass
            elif check_boot:
                self.controller.is_process_alive(self.__start_watcher)

        # Update subtitle with playtime info
        if not is_steam:
            self.__update_subtitle()

    def __update_subtitle(self):
        """Update the subtitle with playtime information."""
        try:
            if not hasattr(self.manager, "playtime_service"):
                self.manager.playtime_service = PlaytimeService(self.manager)

            service = self.manager.playtime_service
            if not service.is_enabled():
                return

            bottle_path = PathUtils.get_bottle_path(self.config)
            program_path = self.program.get("path", "")
            if not program_path:
                return

            record = service.get_program_playtime(
                bottle_id=self.config.Name,
                bottle_path=bottle_path,
                program_name=self.program.get("name", "Unknown"),
                program_path=program_path,
            )
            self.set_subtitle(service.format_subtitle(record))
        except Exception:
            pass

    def show_launch_options_view(self, _widget=False):
        def update(_widget, config):
            self.config = config
            self.controller.config = config
            self.update_programs()

        dialog = LaunchOptionsDialog(self, self.config, self.program)
        dialog.present()
        dialog.connect("options-saved", update)

    def show_playtime_stats(self, _widget=False):
        """Show the playtime statistics dialog for this program."""
        from bottles.backend.managers.playtime import _compute_program_id

        self.pop_actions.popdown()

        program_path = self.program.get("path", "")
        bottle_path = PathUtils.get_bottle_path(self.config)
        program_id = _compute_program_id(self.config.Name, bottle_path, program_path)

        dialog = PlaytimeGraphDialog(
            self,
            program_name=self.program.get("name", "Unknown"),
            program_id=program_id,
            bottle_id=self.config.Name,
        )
        dialog.present()

    @GtkUtils.run_in_main_loop
    def __reset_buttons(self, result: bool | Result = False, _error=False):
        status = False
        if isinstance(result, Result):
            status = result.status
        elif isinstance(result, bool):
            status = result

        self.btn_run.set_visible(status)
        self.btn_stop.set_visible(not status)
        self.btn_run.set_sensitive(status)
        self.btn_stop.set_sensitive(not status)

    def __start_watcher(self, _result=False, _error=False):
        if (isinstance(_result, Result) and not _result.status) or (
            isinstance(_result, bool) and not _result
        ):
            return

        self.__reset_buttons()
        self.controller.wait_for_process(self.__reset_buttons)

    def run_executable(self, _widget, with_terminal=False):
        self.pop_actions.popdown()
        self.controller.run(with_terminal, self.__reset_buttons)
        self.__reset_buttons()

    def run_steam(self, _widget):
        self.controller.run_steam()
        self.pop_actions.popdown()

    def stop_process(self, widget):
        self.controller.stop(self.__reset_buttons)

    @GtkUtils.run_in_main_loop
    def update_programs(self, _result=False, _error=False):
        self.view_bottle.update_programs(config=self.config)

    def uninstall_program(self, _widget):
        self.controller.uninstall(self.update_programs)

    def toggle_visibility(self, _widget=None, update=True):
        self.controller.toggle_visibility(
            lambda: self.update_programs() if update else None
        )
        status = self.program.get("removed")
        self.btn_hide.set_visible(not status)
        self.btn_unhide.set_visible(status)

    def remove_program(self, _widget=None):
        self.controller.remove(self.update_programs)

    def rename_program(self, _widget):
        def on_save(new_name):
            self.controller.rename(new_name, self.update_programs)

        dialog = RenameDialog(self.window, on_save=on_save, name=self.program["name"])
        dialog.present()

    def browse_program_folder(self, _widget):
        self.controller.browse_folder()
        self.pop_actions.popdown()

    def add_entry(self, _widget):
        self.controller.add_desktop_entry()

    def add_to_library(self, _widget):
        self.btn_add_library.set_visible(False)
        self.controller.add_to_library(self.window.update_library)

    def add_to_steam(self, _widget):
        self.controller.add_to_steam()

    def update_playtime(self, playtime_service):
        if not playtime_service or not playtime_service.is_enabled():
            return

        program_path = self.program.get("path", "")
        if not program_path:
            return

        try:
            record = playtime_service.get_program_playtime(
                self.config.Name, self.config.Path, self.program["name"], program_path
            )
            self.set_subtitle(playtime_service.format_subtitle(record))
        except Exception:
            pass
