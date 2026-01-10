import time

from gi.repository import Adw, Gtk

from bottles.backend.utils.threading import RunAsync


@Gtk.Template(resource_path="/com/usebottles/bottles/dialog-upgrade-versioning.ui")
class UpgradeVersioningDialog(Adw.Window):
    __gtype_name__ = "UpgradeVersioningDialog"

    # region Widgets
    btn_cancel = Gtk.Template.Child()
    btn_proceed = Gtk.Template.Child()
    btn_upgrade = Gtk.Template.Child()
    stack_switcher = Gtk.Template.Child()
    progressbar = Gtk.Template.Child()

    # endregion

    def __init__(self, parent, **kwargs):
        super().__init__(**kwargs)
        self.set_transient_for(parent.window)

        # common variables and references
        self.parent = parent
        self.config = parent.config

        # connect signals
        self.btn_upgrade.connect("clicked", self.__upgrade)
        self.btn_proceed.connect("clicked", self.__proceed)

    def __upgrade(self, widget):
        """
        This function take the new bottle name from the entry
        and create a new duplicate of the bottle. It also change the
        stack_switcher page when the process is finished.
        """
        self.stack_switcher.set_visible_child_name("page_upgrading")
        self.btn_upgrade.set_visible(False)
        self.btn_cancel.set_visible(False)
        self.btn_cancel.set_label("Close")

        RunAsync(self.pulse)
        RunAsync(
            self.parent.manager.versioning_manager.update_system,
            self.finish,
            self.config,
        )

    def __proceed(self, widget):
        self.stack_switcher.set_visible_child_name("page_info")
        self.btn_proceed.set_visible(False)
        self.btn_upgrade.set_visible(True)

    def finish(self, result, error=False):
        self.btn_cancel.set_visible(True)
        self.parent.manager.update_bottles()
        self.stack_switcher.set_visible_child_name("page_finish")

    def pulse(self):
        # This function update the progress bar every half second.
        while True:
            time.sleep(0.5)
            self.progressbar.pulse()
