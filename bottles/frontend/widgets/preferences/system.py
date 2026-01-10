import os
from gettext import gettext as _
from gi.repository import Adw, Gtk

from bottles.backend.logger import Logger
from bottles.backend.managers.library import LibraryManager
from bottles.backend.managers.runtime import RuntimeManager
from bottles.backend.managers.system import SystemManager
from bottles.backend.models.enum import Arch
from bottles.backend.utils.threading import RunAsync
from bottles.backend.wine.regkeys import RegKeys
from bottles.frontend.utils.gtk import GtkUtils
from bottles.frontend.windows.dlloverrides import DLLOverridesDialog
from bottles.frontend.windows.drives import DrivesDialog
from bottles.frontend.windows.envvars import EnvironmentVariablesDialog
from bottles.frontend.windows.exclusionpatterns import ExclusionPatternsDialog
from bottles.frontend.windows.sandbox import SandboxDialog

logging = Logger()


@Gtk.Template(resource_path="/com/usebottles/bottles/preferences-system.ui")
class PreferencesSystem(Adw.PreferencesGroup):
    __gtype_name__ = "PreferencesSystem"

    btn_manage_sandbox = Gtk.Template.Child()
    btn_manage_versioning_patterns = Gtk.Template.Child()
    btn_cwd_reset = Gtk.Template.Child()
    btn_cwd = Gtk.Template.Child()
    row_sandbox = Gtk.Template.Child()
    row_runtime = Gtk.Template.Child()
    row_steam_runtime = Gtk.Template.Child()
    row_cwd = Gtk.Template.Child()
    label_cwd = Gtk.Template.Child()
    row_env_variables = Gtk.Template.Child()
    row_overrides = Gtk.Template.Child()
    row_drives = Gtk.Template.Child()
    row_winebridge = Gtk.Template.Child()
    entry_name = Gtk.Template.Child()
    switch_winebridge = Gtk.Template.Child()
    switch_runtime = Gtk.Template.Child()
    switch_steam_runtime = Gtk.Template.Child()
    switch_sandbox = Gtk.Template.Child()
    switch_versioning_compression = Gtk.Template.Child()
    switch_auto_versioning = Gtk.Template.Child()
    switch_versioning_patterns = Gtk.Template.Child()
    combo_windows = Gtk.Template.Child()
    combo_language = Gtk.Template.Child()
    spinner_windows = Gtk.Template.Child()
    str_list_languages = Gtk.Template.Child()
    str_list_windows = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parent_view = None
        self.config = None
        self.manager = None
        self.__valid_name = True

    def setup(self, parent_view):
        self.parent_view = parent_view
        self.config = parent_view.config
        self.manager = parent_view.manager

        # region signals
        self.row_overrides.connect(
            "activated", self.parent_view._show_feature_dialog, DLLOverridesDialog
        )
        self.row_env_variables.connect(
            "activated",
            self.parent_view._show_feature_dialog,
            EnvironmentVariablesDialog,
        )
        self.row_drives.connect(
            "activated", self.parent_view._show_feature_dialog, DrivesDialog
        )
        self.btn_manage_sandbox.connect(
            "clicked", self.parent_view._show_feature_dialog, SandboxDialog
        )
        self.btn_manage_versioning_patterns.connect(
            "clicked", self.parent_view._show_feature_dialog, ExclusionPatternsDialog
        )
        self.btn_cwd.connect("clicked", self._choose_cwd)
        self.btn_cwd_reset.connect("clicked", self._reset_cwd)
        self.switch_winebridge.connect(
            "state-set", self.parent_view._toggle_feature_cb, "winebridge"
        )
        self.switch_sandbox.connect(
            "state-set", self.parent_view._toggle_feature_cb, "sandbox"
        )
        self.switch_versioning_compression.connect(
            "state-set", self.parent_view._toggle_versioning_compression
        )
        self.switch_auto_versioning.connect(
            "state-set", self.parent_view._toggle_feature_cb, "versioning_automatic"
        )
        self.switch_versioning_patterns.connect(
            "state-set",
            self.parent_view._toggle_feature_cb,
            "versioning_exclusion_patterns",
        )
        self.combo_windows.connect("notify::selected", self._set_windows)
        self.combo_language.connect("notify::selected-item", self._set_language)
        self.entry_name.connect("changed", self.__check_entry_name)
        self.entry_name.connect("apply", self.__save_name)
        # endregion

        if RuntimeManager.get_runtimes("steam"):
            self.row_steam_runtime.set_visible(True)
            self.switch_steam_runtime.connect(
                "state-set", self.parent_view._toggle_feature_cb, "use_steam_runtime"
            )

    def set_config(self, config):
        self.config = config
        parameters = self.config.Parameters

        # temporary lock functions connected to the widgets
        self.switch_winebridge.handler_block_by_func(
            self.parent_view._toggle_feature_cb
        )
        self.switch_sandbox.handler_block_by_func(self.parent_view._toggle_feature_cb)
        self.switch_versioning_compression.handler_block_by_func(
            self.parent_view._toggle_versioning_compression
        )
        self.switch_auto_versioning.handler_block_by_func(
            self.parent_view._toggle_feature_cb
        )
        self.switch_versioning_patterns.handler_block_by_func(
            self.parent_view._toggle_feature_cb
        )
        if RuntimeManager.get_runtimes("steam"):
            self.switch_steam_runtime.handler_block_by_func(
                self.parent_view._toggle_feature_cb
            )
        self.combo_windows.handler_block_by_func(self._set_windows)
        self.combo_language.handler_block_by_func(self._set_language)

        self.switch_winebridge.set_active(parameters.winebridge)
        self.switch_sandbox.set_active(parameters.sandbox)
        self.switch_versioning_compression.set_active(parameters.versioning_compression)
        self.switch_auto_versioning.set_active(parameters.versioning_automatic)
        self.switch_versioning_patterns.set_active(
            parameters.versioning_exclusion_patterns
        )
        if RuntimeManager.get_runtimes("steam"):
            self.switch_steam_runtime.set_active(parameters.use_steam_runtime)

        self._update_working_directory_row()
        self.entry_name.set_text(config.Name)
        self.row_cwd.set_subtitle(
            _('Directory that contains the data of "{}".'.format(config.Name))
        )

        self.combo_language.set_selected(
            SystemManager.get_languages(
                from_locale=self.config.Language, get_index=True
            )
        )

        # region Windows Versions
        self.windows_versions = {
            "win11": "Windows 11",
            "win10": "Windows 10",
            "win81": "Windows 8.1",
            "win8": "Windows 8",
            "win7": "Windows 7",
            "win2008r2": "Windows 2008 R2",
            "win2008": "Windows 2008",
            "vista": "Windows Vista",
            "winxp": "Windows XP",
        }
        if self.config.Arch == Arch.WIN32:
            self.windows_versions["win98"] = "Windows 98"
            self.windows_versions["win95"] = "Windows 95"

        self.str_list_windows.splice(0, self.str_list_windows.get_n_items())
        for windows_version in self.windows_versions:
            self.str_list_windows.append(self.windows_versions[windows_version])

        for index, windows_version in enumerate(self.windows_versions):
            if windows_version == self.config.Windows:
                self.combo_windows.set_selected(index)
        # endregion

        self._set_steam_rules()

        # unblock
        self.switch_winebridge.handler_unblock_by_func(
            self.parent_view._toggle_feature_cb
        )
        self.switch_sandbox.handler_unblock_by_func(self.parent_view._toggle_feature_cb)
        self.switch_versioning_compression.handler_unblock_by_func(
            self.parent_view._toggle_versioning_compression
        )
        self.switch_auto_versioning.handler_unblock_by_func(
            self.parent_view._toggle_feature_cb
        )
        self.switch_versioning_patterns.handler_unblock_by_func(
            self.parent_view._toggle_feature_cb
        )
        if RuntimeManager.get_runtimes("steam"):
            self.switch_steam_runtime.handler_unblock_by_func(
                self.parent_view._toggle_feature_cb
            )
        self.combo_windows.handler_unblock_by_func(self._set_windows)
        self.combo_language.handler_unblock_by_func(self._set_language)

    def _set_windows(self, *_args):
        @GtkUtils.run_in_main_loop
        def update(result, error=False):
            self.spinner_windows.stop()
            self.spinner_windows.set_visible(False)
            self.combo_windows.set_sensitive(True)
            self.parent_view.queue.end_task()

        self.parent_view.queue.add_task()
        self.spinner_windows.start()
        self.spinner_windows.set_visible(True)
        self.combo_windows.set_sensitive(False)
        rk = RegKeys(self.config)

        version_keys = list(self.windows_versions.keys())
        windows_version = version_keys[self.combo_windows.get_selected()]

        self.parent_view.config = self.manager.update_config(
            config=self.config, key="Windows", value=windows_version
        ).data["config"]
        self.config = self.parent_view.config

        RunAsync(rk.lg_set_windows, callback=update, version=windows_version)

    def _set_language(self, *_args):
        index = self.combo_language.get_selected()
        language = SystemManager.get_languages(from_index=index)
        self.parent_view.config = self.manager.update_config(
            config=self.config,
            key="Language",
            value=language[0],
        ).data["config"]
        self.config = self.parent_view.config

    def _set_steam_rules(self):
        status = self.config.Environment != "Steam"
        self.parent_view.graphics_group.row_discrete.set_visible(status)
        self.parent_view.graphics_group.row_discrete.set_sensitive(status)
        self.parent_view.components_group.combo_dxvk.set_visible(status)
        self.parent_view.components_group.combo_dxvk.set_sensitive(status)
        self.row_sandbox.set_visible(status)
        self.row_sandbox.set_sensitive(status)

    def __check_entry_name(self, *_args):
        if self.entry_name.get_text() != self.config.Name:
            is_duplicate = self.entry_name.get_text() in self.manager.local_bottles
            if is_duplicate:
                self.parent_view.window.show_toast(
                    _("This bottle name is already in use.")
                )
                self.__valid_name = False
                self.entry_name.add_css_class("error")
                return
        self.__valid_name = True
        self.entry_name.remove_css_class("error")

    def __save_name(self, *_args):
        if not self.__valid_name:
            self.entry_name.set_text(self.config.Name)
            self.__valid_name = True
            return

        new_name = self.entry_name.get_text()
        old_name = self.config.Name

        library_manager = LibraryManager()
        entries = library_manager.get_library()

        for uuid, entry in entries.items():
            bottle = entry.get("bottle")
            if bottle.get("name") == old_name:
                logging.info(f"Updating library entry for {entry.get('name')}")
                entries[uuid]["bottle"]["name"] = new_name
                break

        library_manager._LibraryManager__library = entries
        library_manager.save_library()

        self.manager.update_config(config=self.config, key="Name", value=new_name)
        self.manager.update_bottles(silent=True)
        self.parent_view.window.page_library.update()
        self.parent_view.details.view_bottle.label_name.set_text(self.config.Name)

    def _choose_cwd(self, widget):
        def set_path(_dialog, response):
            if response != Gtk.ResponseType.ACCEPT:
                return
            path = dialog.get_file().get_path()
            self.manager.update_config(config=self.config, key="WorkingDir", value=path)
            self._update_working_directory_row(path)

        dialog = Gtk.FileChooserNative.new(
            title=_("Select Working Directory"),
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            parent=self.parent_view.window,
        )
        dialog.set_modal(True)
        dialog.connect("response", set_path)
        dialog.show()

    def _reset_cwd(self, *_args):
        self.manager.update_config(config=self.config, key="WorkingDir", value="")
        self._update_working_directory_row()

    def _update_working_directory_row(self, working_dir=None):
        working_dir = working_dir if working_dir is not None else self.config.WorkingDir
        has_custom_dir = bool(working_dir)
        if has_custom_dir:
            basename = os.path.basename(os.path.normpath(working_dir)) or working_dir
            self.label_cwd.set_label(basename)
            self.label_cwd.set_tooltip_text(working_dir)
        else:
            self.label_cwd.set_label(_("(Default)"))
            self.label_cwd.set_tooltip_text(None)
        self.btn_cwd_reset.set_visible(has_custom_dir)
