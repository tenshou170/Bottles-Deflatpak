from gettext import gettext as _
from typing import Optional

from gi.repository import Gtk, GObject, Gio

from bottles.backend.models.config import BottleConfig
from bottles.backend.utils.threading import RunAsync
from bottles.backend.wine.winebridge import WineBridge
from bottles.backend.wine.winedbg import WineDbg
from bottles.frontend.utils.gtk import GtkUtils


class ProcessItem(GObject.Object):
    pid = GObject.Property(type=str)
    name = GObject.Property(type=str)
    threads = GObject.Property(type=str)

    def __init__(self, pid, name, threads):
        super().__init__()
        self.pid = pid
        self.name = name
        self.threads = threads


@Gtk.Template(resource_path="/com/usebottles/bottles/details-taskmanager.ui")
class TaskManagerView(Gtk.ScrolledWindow):
    __gtype_name__ = "TaskManagerView"

    # region Widgets
    columnview_processes = Gtk.Template.Child()
    actions = Gtk.Template.Child()
    btn_update = Gtk.Template.Child()
    btn_kill = Gtk.Template.Child()

    # endregion

    def __init__(self, details, config, **kwargs):
        super().__init__(**kwargs)

        # common variables and references
        self.window = details.window
        self.manager = details.window.manager
        self.config = config

        self.btn_update.connect("clicked", self.sensitive_update)
        self.btn_kill.connect("clicked", self.kill_process)

        # Apply model to columnview_processes
        self.liststore_processes = Gio.ListStore(item_type=ProcessItem)
        self.selection_model = Gtk.SingleSelection(model=self.liststore_processes)
        self.columnview_processes.set_model(self.selection_model)
        self.selection_model.connect("selection-changed", self.show_kill_btn)

        self.__setup_columns()

        self.update()

    def __setup_columns(self):
        for title, prop in [
            (_("PID"), "pid"),
            (_("Name"), "name"),
            (_("Threads"), "threads"),
        ]:
            factory = Gtk.SignalListItemFactory()
            factory.connect("setup", self.__on_column_setup)
            factory.connect("bind", self.__on_column_bind, prop)

            column = Gtk.ColumnViewColumn(title=title, factory=factory)
            if prop == "name":
                column.set_expand(True)
            self.columnview_processes.append_column(column)

    def __on_column_setup(self, factory, list_item):
        label = Gtk.Label(xalign=0, margin_start=6, margin_end=6)
        list_item.set_child(label)

    def __on_column_bind(self, factory, list_item, prop):
        item = list_item.get_item()
        label = list_item.get_child()
        label.set_label(getattr(item, prop))

        self.update()

    def set_config(self, config):
        self.config = config

    def show_kill_btn(self, *args):
        item = self.selection_model.get_selected_item()
        if item is None:
            self.btn_kill.set_sensitive(False)
            return
        self.btn_kill.set_sensitive(True)

    def update(self, widget=False, config: Optional[BottleConfig] = None):
        """
        This function scan for new processed and update the
        liststore_processes with the new data
        """
        self.liststore_processes.remove_all()

        def fetch_processes(config: Optional[BottleConfig] = None):
            if config is None:
                config = BottleConfig()
            self.config = config
            if not config.Runner:
                return []

            winebridge = WineBridge(config)

            if winebridge.is_available():
                processes = winebridge.get_procs()
            else:
                winedbg = WineDbg(config)
                processes = winedbg.get_processes()
            return processes

        def update_processes(processes: list, *_args):
            if len(processes) > 0:
                for process in processes:
                    item = ProcessItem(
                        pid=str(process.get("pid")),
                        name=process.get("name", "n/a"),
                        threads=str(process.get("threads", "0")),
                    )
                    self.liststore_processes.append(item)

        RunAsync(task_func=fetch_processes, callback=update_processes, config=config)

    def sensitive_update(self, widget):
        @GtkUtils.run_in_main_loop
        def reset(result, error):
            self.btn_update.set_sensitive(True)

        self.btn_update.set_sensitive(False)
        RunAsync(
            task_func=self.update, callback=reset, widget=False, config=self.config
        )

    def kill_process(self, widget):
        winebridge = WineBridge(self.config)
        item = self.selection_model.get_selected_item()

        if item is None:
            self.btn_kill.set_sensitive(False)
            return

        pid = item.pid
        self.btn_kill.set_sensitive(False)

        @GtkUtils.run_in_main_loop
        def reset(result, error):
            # We need to find the item in the liststore, but selection might have changed
            # however, for kill_process we can just refresh the whole list or find by pid
            self.update()

        if winebridge.is_available():
            RunAsync(task_func=winebridge.kill_proc, callback=reset, pid=pid)
        else:
            winedbg = WineDbg(self.config)
            RunAsync(task_func=winedbg.kill_process, callback=reset, pid=pid)
