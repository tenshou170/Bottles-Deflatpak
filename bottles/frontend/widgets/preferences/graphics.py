from gettext import gettext as _
from gi.repository import Adw, Gtk

from bottles.backend.globals import (
    gamescope_available,
    vkbasalt_available,
)
from bottles.backend.utils.display import DisplayUtils
from bottles.backend.utils.gpu import GPUUtils, GPUVendors
from bottles.backend.utils.threading import RunAsync
from bottles.frontend.utils.gtk import GtkUtils
from bottles.frontend.windows.display import DisplayDialog
from bottles.frontend.windows.fsr import FsrDialog
from bottles.frontend.windows.gamescope import GamescopeDialog
from bottles.frontend.windows.vkbasalt import VkBasaltDialog


@Gtk.Template(resource_path="/com/usebottles/bottles/preferences-graphics.ui")
class PreferencesGraphics(Adw.PreferencesGroup):
    __gtype_name__ = "PreferencesGraphics"

    btn_manage_gamescope = Gtk.Template.Child()
    btn_manage_vkbasalt = Gtk.Template.Child()
    btn_manage_fsr = Gtk.Template.Child()
    row_nvapi = Gtk.Template.Child()
    row_discrete = Gtk.Template.Child()
    row_vkbasalt = Gtk.Template.Child()
    row_gamescope = Gtk.Template.Child()
    row_wayland = Gtk.Template.Child()
    row_manage_display = Gtk.Template.Child()
    switch_vkbasalt = Gtk.Template.Child()
    switch_wayland = Gtk.Template.Child()
    switch_fsr = Gtk.Template.Child()
    switch_nvapi = Gtk.Template.Child()
    switch_gamescope = Gtk.Template.Child()
    switch_discrete = Gtk.Template.Child()
    spinner_nvapibool = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parent_view = None
        self.config = None
        self.manager = None

    def setup(self, parent_view):
        self.parent_view = parent_view
        self.config = parent_view.config
        self.manager = parent_view.manager

        # region signals
        self.row_manage_display.connect("activated", self.__show_display_settings)
        self.btn_manage_gamescope.connect(
            "clicked", self.parent_view._show_feature_dialog, GamescopeDialog
        )
        self.btn_manage_vkbasalt.connect(
            "clicked", self.parent_view._show_feature_dialog, VkBasaltDialog
        )
        self.btn_manage_fsr.connect(
            "clicked", self.parent_view._show_feature_dialog, FsrDialog
        )
        self.switch_vkbasalt.connect(
            "state-set", self.parent_view._toggle_feature_cb, "vkbasalt"
        )
        self.switch_wayland.connect("state-set", self.__toggle_wayland)
        self.switch_fsr.connect("state-set", self.parent_view._toggle_feature_cb, "fsr")
        self.switch_nvapi.connect("state-set", self.__toggle_nvapi)
        self.switch_gamescope.connect(
            "state-set", self.parent_view._toggle_feature_cb, "gamescope"
        )
        self.switch_discrete.connect(
            "state-set", self.parent_view._toggle_feature_cb, "discrete_gpu"
        )
        # endregion

        # Availability checks
        _not_available = _("This feature is unavailable on your system.")
        if not gamescope_available:
            self.switch_gamescope.set_tooltip_text(_not_available)
            self.btn_manage_gamescope.set_tooltip_text(_not_available)
            self.parent_view._add_unavailable_indicator(self.row_gamescope, None)

        if not vkbasalt_available:
            self.switch_vkbasalt.set_tooltip_text(_not_available)
            self.btn_manage_vkbasalt.set_tooltip_text(_not_available)
            self.parent_view._add_unavailable_indicator(self.row_vkbasalt, None)

        self.switch_gamescope.set_sensitive(gamescope_available)
        self.btn_manage_gamescope.set_sensitive(gamescope_available)
        self.switch_vkbasalt.set_sensitive(vkbasalt_available)
        self.btn_manage_vkbasalt.set_sensitive(vkbasalt_available)

        is_nvidia_gpu = GPUUtils.is_gpu(GPUVendors.NVIDIA)
        self.row_nvapi.set_visible(is_nvidia_gpu)

        is_wayland_session = DisplayUtils.display_server_type() == "wayland"
        self.switch_wayland.set_sensitive(is_wayland_session)

    def set_config(self, config):
        self.config = config
        parameters = self.config.Parameters

        self.switch_vkbasalt.handler_block_by_func(self.parent_view._toggle_feature_cb)
        self.switch_wayland.handler_block_by_func(self.__toggle_wayland)
        self.switch_fsr.handler_block_by_func(self.parent_view._toggle_feature_cb)
        self.switch_nvapi.handler_block_by_func(self.__toggle_nvapi)
        self.switch_gamescope.handler_block_by_func(self.parent_view._toggle_feature_cb)
        self.switch_discrete.handler_block_by_func(self.parent_view._toggle_feature_cb)

        self.switch_vkbasalt.set_active(parameters.vkbasalt)
        self.switch_wayland.set_active(parameters.wayland)
        self.switch_fsr.set_active(parameters.fsr)
        self.switch_nvapi.set_active(parameters.dxvk_nvapi)
        self.switch_gamescope.set_active(parameters.gamescope)
        self.switch_discrete.set_active(parameters.discrete_gpu)

        self.switch_vkbasalt.handler_unblock_by_func(
            self.parent_view._toggle_feature_cb
        )
        self.switch_wayland.handler_unblock_by_func(self.__toggle_wayland)
        self.switch_fsr.handler_unblock_by_func(self.parent_view._toggle_feature_cb)
        self.switch_nvapi.handler_unblock_by_func(self.__toggle_nvapi)
        self.switch_gamescope.handler_unblock_by_func(
            self.parent_view._toggle_feature_cb
        )
        self.switch_discrete.handler_unblock_by_func(
            self.parent_view._toggle_feature_cb
        )

    def __toggle_wayland(self, _widget: Gtk.Widget, state: bool):
        self.parent_view._toggle_feature(state, "wayland")
        self.parent_view.manager.update_config(
            config=self.config, key="Wayland", value=state
        )

    def __toggle_nvapi(self, widget=False, state=False):
        """Install/Uninstall NVAPI from the bottle"""
        self.parent_view.queue.add_task()
        self.set_nvapi_status(pending=True)

        RunAsync(
            task_func=self.parent_view.manager.install_dll_component,
            callback=self.set_nvapi_status,
            config=self.config,
            component="nvapi",
            remove=not state,
        )

        self.parent_view._toggle_feature(state=state, key="dxvk_nvapi")

    @GtkUtils.run_in_main_loop
    def set_nvapi_status(self, status=None, error=None, pending=False):
        """Set the nvapi status"""
        self.switch_nvapi.set_sensitive(not pending)
        if pending:
            self.parent_view.components_group.spinner_nvapi.start()
            self.spinner_nvapibool.start()
            self.parent_view.components_group.spinner_nvapi.set_visible(True)
            self.spinner_nvapibool.set_visible(True)
        else:
            self.parent_view.components_group.spinner_nvapi.stop()
            self.spinner_nvapibool.stop()
            self.parent_view.components_group.spinner_nvapi.set_visible(False)
            self.spinner_nvapibool.set_visible(False)
            self.parent_view.queue.end_task()

    def __show_display_settings(self, widget):
        dialog = DisplayDialog(self.config, self.parent_view.window)
        dialog.present()
