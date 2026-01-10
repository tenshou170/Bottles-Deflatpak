from gettext import gettext as _
from gi.repository import Adw, Gtk

from bottles.backend.globals import (
    gamemode_available,
    mangohud_available,
    obs_vkc_available,
    vmtouch_available,
)
from bottles.backend.utils.threading import RunAsync
from bottles.frontend.windows.mangohud import MangoHudDialog
from bottles.frontend.windows.vmtouch import VmtouchDialog


@Gtk.Template(resource_path="/com/usebottles/bottles/preferences-performance.ui")
class PreferencesPerformance(Adw.PreferencesGroup):
    __gtype_name__ = "PreferencesPerformance"

    btn_manage_mangohud = Gtk.Template.Child()
    btn_manage_vmtouch = Gtk.Template.Child()
    row_mangohud = Gtk.Template.Child()
    row_gamemode = Gtk.Template.Child()
    row_vmtouch = Gtk.Template.Child()
    row_obsvkc = Gtk.Template.Child()
    row_use_umu = Gtk.Template.Child()
    switch_mangohud = Gtk.Template.Child()
    switch_obsvkc = Gtk.Template.Child()
    switch_use_umu = Gtk.Template.Child()
    switch_gamemode = Gtk.Template.Child()
    switch_vmtouch = Gtk.Template.Child()
    combo_sync = Gtk.Template.Child()

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
        self.btn_manage_mangohud.connect(
            "clicked", self.parent_view._show_feature_dialog, MangoHudDialog
        )
        self.btn_manage_vmtouch.connect(
            "clicked", self.parent_view._show_feature_dialog, VmtouchDialog
        )
        self.switch_mangohud.connect(
            "state-set", self.parent_view._toggle_feature_cb, "mangohud"
        )
        self.switch_obsvkc.connect(
            "state-set", self.parent_view._toggle_feature_cb, "obsvkc"
        )
        self.switch_use_umu.connect(
            "state-set", self.parent_view._toggle_feature_cb, "use_umu"
        )
        self.switch_gamemode.connect(
            "state-set", self.parent_view._toggle_feature_cb, "gamemode"
        )
        self.switch_vmtouch.connect(
            "state-set", self.parent_view._toggle_feature_cb, "vmtouch"
        )
        self.combo_sync.connect("notify::selected", self.__set_sync_type)
        # endregion

        # Availability checks
        _not_available = _("This feature is unavailable on your system.")
        if not gamemode_available:
            self.switch_gamemode.set_tooltip_text(_not_available)
            self.parent_view._add_unavailable_indicator(self.row_gamemode, None)

        if not mangohud_available:
            self.switch_mangohud.set_tooltip_text(_not_available)
            self.btn_manage_mangohud.set_tooltip_text(_not_available)
            self.parent_view._add_unavailable_indicator(self.row_mangohud, None)

        if not obs_vkc_available:
            self.switch_obsvkc.set_tooltip_text(_not_available)
            self.parent_view._add_unavailable_indicator(self.row_obsvkc, None)

        if not vmtouch_available:
            self.switch_vmtouch.set_tooltip_text(_not_available)
            self.parent_view._add_unavailable_indicator(self.row_vmtouch, None)

        self.switch_gamemode.set_sensitive(gamemode_available)
        self.switch_mangohud.set_sensitive(mangohud_available)
        self.btn_manage_mangohud.set_sensitive(mangohud_available)
        self.switch_obsvkc.set_sensitive(obs_vkc_available)
        self.switch_vmtouch.set_sensitive(vmtouch_available)

    def set_config(self, config):
        self.config = config
        parameters = self.config.Parameters

        self.switch_mangohud.handler_block_by_func(self.parent_view._toggle_feature_cb)
        self.switch_obsvkc.handler_block_by_func(self.parent_view._toggle_feature_cb)
        self.switch_use_umu.handler_block_by_func(self.parent_view._toggle_feature_cb)
        self.switch_gamemode.handler_block_by_func(self.parent_view._toggle_feature_cb)
        self.switch_vmtouch.handler_block_by_func(self.parent_view._toggle_feature_cb)
        self.combo_sync.handler_block_by_func(self.__set_sync_type)

        self.switch_mangohud.set_active(parameters.mangohud)
        self.switch_obsvkc.set_active(parameters.obsvkc)
        self.switch_use_umu.set_active(parameters.use_umu)
        self.switch_gamemode.set_active(parameters.gamemode)
        self.switch_vmtouch.set_active(parameters.vmtouch)

        sync_type = parameters.sync
        if sync_type == "wine":
            self.combo_sync.set_selected(0)
        elif sync_type == "esync":
            self.combo_sync.set_selected(1)
        elif sync_type == "fsync":
            self.combo_sync.set_selected(2)

        self.switch_mangohud.handler_unblock_by_func(
            self.parent_view._toggle_feature_cb
        )
        self.switch_obsvkc.handler_unblock_by_func(self.parent_view._toggle_feature_cb)
        self.switch_use_umu.handler_unblock_by_func(self.parent_view._toggle_feature_cb)
        self.switch_gamemode.handler_unblock_by_func(
            self.parent_view._toggle_feature_cb
        )
        self.switch_vmtouch.handler_unblock_by_func(self.parent_view._toggle_feature_cb)
        self.combo_sync.handler_unblock_by_func(self.__set_sync_type)

        # Umu-launcher is only available for Proton runners
        is_proton = "proton" in self.config.Runner.lower()
        self.row_use_umu.set_visible(is_proton)

    def __set_sync_type(self, *_args):
        # Set the sync type (wine, esync, fsync)
        sync_types = ["wine", "esync", "fsync"]
        selected = self.combo_sync.get_selected()
        sync_type = sync_types[selected]

        self.parent_view.queue.add_task()
        self.combo_sync.set_sensitive(False)

        def callback(result, error=False):
            self.combo_sync.set_sensitive(True)
            self.parent_view.queue.end_task()

        RunAsync(
            self.manager.update_config,
            callback=callback,
            config=self.config,
            key="sync",
            value=sync_type,
            scope="Parameters",
        )
