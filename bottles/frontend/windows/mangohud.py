# mangohud.py

from gi.repository import Adw, GLib, Gtk

from bottles.backend.logger import Logger

logging = Logger()


@Gtk.Template(resource_path="/com/usebottles/bottles/dialog-mangohud.ui")
class MangoHudDialog(Adw.Window):
    __gtype_name__ = "MangoHudDialog"

    # Region Widgets
    btn_save = Gtk.Template.Child()
    display_on_game_start = Gtk.Template.Child()

    def __init__(self, window, config, **kwargs):
        super().__init__(**kwargs)
        self.set_transient_for(window)

        # Common variables and references
        self.window = window
        self.manager = window.manager
        self.config = config

        # Connect signals
        self.btn_save.connect("clicked", self.__save)

        self.__update(config)

    def __update(self, config):
        parameters = config.Parameters
        self.display_on_game_start.set_active(parameters.mangohud_display_on_game_start)

    def __idle_save(self, *_args):
        settings = {
            "mangohud_display_on_game_start": self.display_on_game_start.get_active(),
        }

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
