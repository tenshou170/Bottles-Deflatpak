# rename.py

from gi.repository import Adw, Gtk


@Gtk.Template(resource_path="/com/usebottles/bottles/dialog-rename.ui")
class RenameDialog(Adw.Window):
    __gtype_name__ = "RenameDialog"

    # region Widgets
    entry_name = Gtk.Template.Child()
    btn_cancel = Gtk.Template.Child()
    btn_save = Gtk.Template.Child()
    ev_controller = Gtk.EventControllerKey.new()

    # endregion

    def __init__(self, window, name, on_save, **kwargs):
        super().__init__(**kwargs)

        self.set_transient_for(window)

        # common variables and references
        self.window = window
        self.manager = window.manager
        self.on_save = on_save

        # set widget defaults
        self.entry_name.set_text(name)
        self.entry_name.add_controller(self.ev_controller)

        # connect signals
        self.ev_controller.connect("key-released", self.on_change)
        self.btn_cancel.connect("clicked", self.__close_window)
        self.btn_save.connect("clicked", self.__on_save)

    def __on_save(self, *_args):
        text = self.entry_name.get_text()
        self.on_save(new_name=text)
        self.destroy()

    def __close_window(self, *_args):
        self.destroy()

    def on_change(self, *_args):
        self.btn_save.set_sensitive(len(self.entry_name.get_text()) > 0)
