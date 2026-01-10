# sandbox.py

from gi.repository import Adw, Gtk


@Gtk.Template(resource_path="/com/usebottles/bottles/dialog-sandbox.ui")
class SandboxDialog(Adw.Window):
    __gtype_name__ = "SandboxDialog"

    # region Widgets
    switch_net = Gtk.Template.Child()
    switch_sound = Gtk.Template.Child()

    # endregion

    def __init__(self, window, config, **kwargs):
        super().__init__(**kwargs)
        self.set_transient_for(window)

        # common variables and references
        self.window = window
        self.manager = window.manager
        self.config = config
        self.__update(config)

        # connect signals
        self.switch_net.connect("state-set", self.__set_flag, "share_net")
        self.switch_sound.connect("state-set", self.__set_flag, "share_sound")

    def __set_flag(self, widget, state, flag):
        self.config = self.manager.update_config(
            config=self.config, key=flag, value=state, scope="Sandbox"
        ).data["config"]

    def __update(self, config):
        self.switch_net.set_active(config.Sandbox.share_net)
        self.switch_sound.set_active(config.Sandbox.share_sound)
