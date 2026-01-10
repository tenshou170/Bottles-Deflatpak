# bottle_preferences.py

from gettext import gettext as _

from gi.repository import Adw, Gdk, Gtk

from bottles.backend.logger import Logger
from bottles.backend.models.config import BottleConfig
from bottles.backend.utils.threading import RunAsync
from bottles.frontend.utils.gtk import GtkUtils
from bottles.frontend.widgets.preferences.graphics import PreferencesGraphics
from bottles.frontend.widgets.preferences.performance import PreferencesPerformance
from bottles.frontend.widgets.preferences.system import PreferencesSystem
from bottles.frontend.widgets.preferences.components import PreferencesComponents

logging = Logger()


# noinspection PyUnusedLocal
@Gtk.Template(resource_path="/com/usebottles/bottles/details-preferences.ui")
class PreferencesView(Adw.PreferencesPage):
    __gtype_name__ = "DetailsPreferences"

    # region Widgets
    system_group = Gtk.Template.Child()
    components_group = Gtk.Template.Child()
    graphics_group = Gtk.Template.Child()
    performance_group = Gtk.Template.Child()
    # endregion

    def __init__(self, details, config, **kwargs):
        super().__init__(**kwargs)

        # common variables and references
        self.window = details.window
        self.manager = details.window.manager
        self.config = config
        self.queue = details.queue
        self.details = details

        self.graphics_group.setup(self)
        self.performance_group.setup(self)
        self.system_group.setup(self)
        self.components_group.setup(self)

    def _create_unavailable_popover(self, command: str | None) -> Gtk.Popover:
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(6)
        box.set_margin_end(6)

        unavailable_label = Gtk.Label(
            label=_("This feature is unavailable on your system."),
            xalign=0,
            wrap=True,
        )
        box.append(unavailable_label)

        if command:
            command_label = Gtk.Label(label=_("To add it, please run:"))
            command_label.set_xalign(0)
            box.append(command_label)

            command_box = Gtk.Box(spacing=6)
            command_box.set_hexpand(True)

            command_entry = Gtk.Entry()
            command_entry.set_editable(False)
            command_entry.set_hexpand(True)
            command_entry.set_text(command)
            command_entry.add_css_class("monospace")
            command_entry.set_width_chars(len(command))
            command_entry.set_focusable(False)

            btn_copy_command = Gtk.Button()
            btn_copy_command.set_icon_name("edit-copy-symbolic")
            btn_copy_command.set_tooltip_text(_("Copy command"))
            btn_copy_command.connect(
                "clicked", self._copy_command_to_clipboard, command
            )

            command_box.append(command_entry)
            command_box.append(btn_copy_command)
            box.append(command_box)

        popover.set_child(box)
        return popover

    def _add_unavailable_indicator(self, row: Adw.ActionRow, command: str | None):
        if not row:
            return

        popover = self._create_unavailable_popover(command)
        menu_button = Gtk.MenuButton()
        menu_button.set_valign(Gtk.Align.CENTER)
        menu_button.set_icon_name("dialog-warning-symbolic")
        menu_button.set_has_frame(False)
        menu_button.set_popover(popover)
        menu_button.set_tooltip_text(_("This feature is unavailable on your system."))

        row.add_suffix(menu_button)

    def _copy_command_to_clipboard(self, _widget, command: str):
        display = Gdk.Display.get_default()
        if not display:
            return

        clipboard = Gdk.Display.get_clipboard(display)
        clipboard.set_content(Gdk.ContentProvider.new_for_value(command))
        self.window.show_toast(_("Copied to clipboard"))

    def update_combo_components(self):
        self.components_group.update_combos()

    def set_config(self, config: BottleConfig):
        self.config = config
        self.graphics_group.set_config(config)
        self.performance_group.set_config(config)
        self.system_group.set_config(config)
        self.components_group.set_config(config)

    def _show_feature_dialog(self, _widget: Gtk.Widget, dialog: Adw.Window) -> None:
        """Present dialog of a specific feature."""
        window = dialog(window=self.window, config=self.config)
        window.present()

    def _toggle_feature(self, state: bool, key: str) -> None:
        """Toggle a specific feature."""
        self.config = self.manager.update_config(
            config=self.config, key=key, value=state, scope="Parameters"
        ).data["config"]

    def _toggle_feature_cb(self, _widget: Gtk.Widget, state: bool, key: str) -> None:
        self._toggle_feature(state=state, key=key)

    def _toggle_versioning_compression(self, widget, state):
        """Toggle the versioning compression for current bottle"""

        def update():
            self.config = self.manager.update_config(
                config=self.config,
                key="versioning_compression",
                value=state,
                scope="Parameters",
            ).data["config"]

        def handle_response(_widget, response_id):
            if response_id == "ok":
                RunAsync(
                    self.manager.versioning_manager.re_initialize, config=self.config
                )
            _widget.destroy()

        if self.manager.versioning_manager.is_initialized(self.config):
            dialog = Adw.MessageDialog.new(
                self.window,
                _("Are you sure you want to delete all snapshots?"),
                _("This will delete all snapshots but keep your files."),
            )
            dialog.add_response("cancel", _("_Cancel"))
            dialog.add_response("ok", _("_Delete"))
            dialog.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
            dialog.connect("response", handle_response)
            dialog.present()
        else:
            update()

    def _dll_component_task_func(self, state, title, spinner_name, task):
        self.window.show_toast(_("Updating {}, please wait…").format(title))
        self.queue.add_task()

        # We need to find the spinner in the children
        spinner = None
        if hasattr(self.graphics_group, f"spinner_{spinner_name}"):
            spinner = getattr(self.graphics_group, f"spinner_{spinner_name}")
        elif hasattr(self.components_group, f"spinner_{spinner_name}"):
            spinner = getattr(self.components_group, f"spinner_{spinner_name}")

        if spinner:
            spinner.start()
            spinner.set_visible(True)

        def callback(result, error=False):
            if spinner:
                spinner.stop()
                spinner.set_visible(False)
            self.queue.end_task()
            if error:
                self.window.show_toast(_("Error updating {}").format(title))
            else:
                self.window.show_toast(_("{} updated successfully").format(title))

        RunAsync(task, callback=callback)
