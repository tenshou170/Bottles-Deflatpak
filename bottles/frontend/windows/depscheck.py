# depscheck.py

from gi.repository import Adw, Gtk


@Gtk.Template(resource_path="/com/usebottles/bottles/dialog-deps-check.ui")
class DependenciesCheckDialog(Adw.Window):
    __gtype_name__ = "DependenciesCheckDialog"

    # region widgets
    btn_quit = Gtk.Template.Child()

    # endregion

    def __init__(self, window, **kwargs):
        super().__init__(**kwargs)
        self.set_transient_for(window)
        self.window = window

        self.btn_quit.connect("clicked", self.__quit)

    def __quit(self, *_args):
        self.window.proper_close()
