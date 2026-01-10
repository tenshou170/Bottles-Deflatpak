# journal.py

from datetime import datetime
from gettext import gettext

from gi.repository import Adw, Gtk, Pango, GObject, Gio

from bottles.backend.managers.journal import JournalManager, JournalSeverity


class JournalItem(GObject.Object):
    severity_markup = GObject.Property(type=str)
    timestamp = GObject.Property(type=str)
    message = GObject.Property(type=str)
    is_group = GObject.Property(type=bool, default=False)

    def __init__(self, severity_markup, timestamp, message, is_group=False):
        super().__init__()
        self.severity_markup = severity_markup
        self.timestamp = timestamp
        self.message = message
        self.is_group = is_group


@Gtk.Template(resource_path="/com/usebottles/bottles/dialog-journal.ui")
class JournalDialog(Adw.Window):
    __gtype_name__ = "JournalDialog"

    # region Widgets
    column_view = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    btn_all = Gtk.Template.Child()
    btn_critical = Gtk.Template.Child()
    btn_error = Gtk.Template.Child()
    btn_warning = Gtk.Template.Child()
    btn_info = Gtk.Template.Child()
    label_filter = Gtk.Template.Child()

    # endregion

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.journal = list(JournalManager.get(period="all").items())
        self.liststore = Gio.ListStore(item_type=JournalItem)
        self.selection_model = Gtk.SingleSelection(model=self.liststore)
        self.current_severity = ""

        # connect signals
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.btn_all.connect("clicked", self.filter_results, "")
        self.btn_critical.connect(
            "clicked", self.filter_results, JournalSeverity.CRITICAL
        )
        self.btn_error.connect("clicked", self.filter_results, JournalSeverity.ERROR)
        self.btn_warning.connect(
            "clicked", self.filter_results, JournalSeverity.WARNING
        )
        self.btn_info.connect("clicked", self.filter_results, JournalSeverity.INFO)

        self.column_view.set_model(self.selection_model)
        self.__setup_columns()
        self.populate_tree_view()

    def __setup_columns(self):
        for title, prop in [
            (gettext("Severity"), "severity_markup"),
            (gettext("Timestamp"), "timestamp"),
            (gettext("Message"), "message"),
        ]:
            factory = Gtk.SignalListItemFactory()
            factory.connect("setup", self.__on_column_setup)
            factory.connect("bind", self.__on_column_bind, prop)

            column = Gtk.ColumnViewColumn(title=title, factory=factory)
            if prop == "message":
                column.set_expand(True)
            self.column_view.append_column(column)

    def __on_column_setup(self, factory, list_item):
        label = Gtk.Label(xalign=0, margin_start=6, margin_end=6)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        list_item.set_child(label)

    def __on_column_bind(self, factory, list_item, prop):
        item = list_item.get_item()
        label = list_item.get_child()

        if item.is_group:
            if prop == "timestamp":
                label.set_markup(f"<b>{item.timestamp}</b>")
            else:
                label.set_label("")
            # Could add a style class for the whole row here if we had the row widget
            return

        if prop == "severity_markup":
            label.set_markup(item.severity_markup)
        else:
            label.set_label(getattr(item, prop))

    def populate_tree_view(self, query="", severity=None):
        self.liststore.remove_all()

        if severity is None:
            severity = self.current_severity

        colors = {
            JournalSeverity.CRITICAL: "#db1600",
            JournalSeverity.ERROR: "#db6600",
            JournalSeverity.WARNING: "#dba100",
            JournalSeverity.INFO: "#3283a8",
            JournalSeverity.CRASH: "#db1600",
        }

        last_date_label = None

        for _, value in self.journal:
            if query.lower() not in value["message"].lower():
                continue

            if severity not in ("", value["severity"]):
                continue

            timestamp = value.get("timestamp", "")
            try:
                timestamp_dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                date_label = timestamp_dt.strftime("%Y-%m-%d")
            except (TypeError, ValueError):
                date_label = ""

            if date_label != last_date_label:
                self.liststore.append(
                    JournalItem(
                        severity_markup="",
                        timestamp=date_label,
                        message="",
                        is_group=True,
                    )
                )
                last_date_label = date_label

            self.liststore.append(
                JournalItem(
                    severity_markup='<span foreground="{}"><b>{}</b></span>'.format(
                        colors.get(
                            value["severity"],
                            colors.get(JournalSeverity.INFO, "#3283a8"),
                        ),
                        value["severity"].capitalize(),
                    ),
                    timestamp=timestamp,
                    message=value.get("message", ""),
                    is_group=False,
                )
            )

    def on_search_changed(self, entry):
        self.populate_tree_view(entry.get_text())

    def filter_results(self, _, severity):
        self.current_severity = severity
        self.populate_tree_view(self.search_entry.get_text())

        severity_labels = {
            JournalSeverity.CRITICAL: gettext("Critical"),
            JournalSeverity.ERROR: gettext("Errors"),
            JournalSeverity.WARNING: gettext("Warnings"),
            JournalSeverity.INFO: gettext("Info"),
            JournalSeverity.CRASH: gettext("Crashes"),
        }

        label = severity_labels.get(severity, gettext("All messages"))
        self.label_filter.set_text(label)
