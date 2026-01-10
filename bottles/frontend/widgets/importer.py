# importer.py

from gettext import gettext as _

from gi.repository import Adw, Gtk

from bottles.backend.managers.system import SystemManager
from bottles.backend.utils.threading import RunAsync
from bottles.frontend.utils.gtk import GtkUtils


@Gtk.Template(resource_path="/com/usebottles/bottles/importer-entry.ui")
class ImporterEntry(Adw.ActionRow):
    __gtype_name__ = "ImporterEntry"

    # region Widgets
    label_manager = Gtk.Template.Child()
    btn_import = Gtk.Template.Child()
    btn_browse = Gtk.Template.Child()
    img_lock = Gtk.Template.Child()

    # endregion

    def __init__(self, im_manager, prefix, **kwargs):
        super().__init__(**kwargs)

        # common variables and references
        self.window = im_manager.window
        self.import_manager = im_manager.import_manager
        self.prefix = prefix

        # populate widgets
        self.set_title(prefix.get("Name"))
        self.label_manager.set_text(prefix.get("Manager"))

        if prefix.get("Lock"):
            self.img_lock.set_visible(True)

        self.label_manager.add_css_class("tag-%s" % prefix.get("Manager").lower())

        # connect signals
        self.btn_browse.connect("clicked", self.browse_wineprefix)
        self.btn_import.connect("clicked", self.import_wineprefix)

    def browse_wineprefix(self, widget):
        SystemManager.browse_wineprefix(self.prefix)

    def import_wineprefix(self, widget):
        @GtkUtils.run_in_main_loop
        def set_imported(result, error=False):
            self.btn_import.set_visible(result.ok)
            self.img_lock.set_visible(result.ok)

            if result.ok:
                self.window.show_toast(
                    _('"{0}" imported').format(self.prefix.get("Name"))
                )

            self.set_sensitive(True)

        self.set_sensitive(False)

        RunAsync(
            self.import_manager.import_wineprefix,
            callback=set_imported,
            wineprefix=self.prefix,
        )
