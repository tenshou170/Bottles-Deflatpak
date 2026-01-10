# vmtouch.py

# SPDX-License-Identifier: GPL-3.0-only

from gi.repository import Adw, GLib, Gtk


@Gtk.Template(resource_path="/com/usebottles/bottles/dialog-vmtouch.ui")
class VmtouchDialog(Adw.Window):
    __gtype_name__ = "VmtouchDialog"

    # region Widgets
    switch_cache_cwd = Gtk.Template.Child()
    btn_save = Gtk.Template.Child()
    btn_cancel = Gtk.Template.Child()

    # endregion

    def __init__(self, window, config, **kwargs):
        super().__init__(**kwargs)
        self.set_transient_for(window)

        # common variables and references
        self.window = window
        self.manager = window.manager
        self.config = config

        # connect signals
        self.btn_save.connect("clicked", self.__save)

        self.__update(config)

    def __update(self, config):
        self.switch_cache_cwd.set_active(config.Parameters.vmtouch_cache_cwd)

    def __idle_save(self, *_args):
        settings = {"vmtouch_cache_cwd": self.switch_cache_cwd.get_active()}

        for setting in settings.keys():
            self.manager.update_config(
                config=self.config,
                key=setting,
                value=settings[setting],
                scope="Parameters",
            )

        self.destroy()

    def __save(self, *_args):
        GLib.idle_add(self.__idle_save)
