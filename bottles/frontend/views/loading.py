# loading.py

from gettext import gettext as _

from gi.repository import Adw, Gtk

from bottles.backend.models.result import Result
from bottles.backend.state import SignalManager, Signals
from bottles.frontend.params import APP_ID
from bottles.frontend.utils.gtk import GtkUtils


@Gtk.Template(resource_path="/com/usebottles/bottles/loading.ui")
class LoadingView(Adw.Bin):
    __gtype_name__ = "LoadingView"
    __fetched = 0

    # region widgets
    label_fetched = Gtk.Template.Child()
    label_downloading = Gtk.Template.Child()
    btn_go_offline = Gtk.Template.Child()
    loading_status_page = Gtk.Template.Child()
    # endregion

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.loading_status_page.set_icon_name(APP_ID)
        self.btn_go_offline.connect("clicked", self.go_offline)

    @GtkUtils.run_in_main_loop
    def add_fetched(self, res: Result):
        total: int = res.data
        self.__fetched += 1
        self.label_downloading.set_text(
            _("Downloading ~{0} of packages…").format("20kb")
        )
        self.label_fetched.set_text(
            _("Fetched {0} of {1} packages").format(self.__fetched, total)
        )

    def go_offline(self, _widget):
        SignalManager.send(Signals.ForceStopNetworking, Result(status=True))
