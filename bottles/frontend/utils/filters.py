from gettext import gettext as _

from gi.repository import Gtk


def add_executable_filters(dialog):
    filter = Gtk.FileFilter()
    filter.set_name(_("Supported Executables"))
    # TODO: Investigate why `filter.add_mime_type(...)` does not show filter in all distributions.
    # Intended MIME types are:
    #   - `application/x-ms-dos-executable`
    #   - `application/x-msi`
    filter.add_pattern("*.exe")
    filter.add_pattern("*.msi")

    dialog.add_filter(filter)


def add_yaml_filters(dialog):
    filter = Gtk.FileFilter()
    filter.set_name("YAML")
    # TODO: Investigate why `filter.add_mime_type(...)` does not show filter in all distributions.
    # Intended MIME types are:
    #   - `application/yaml`
    filter.add_pattern("*.yml")
    filter.add_pattern("*.yaml")

    dialog.add_filter(filter)


def add_all_filters(dialog):
    filter = Gtk.FileFilter()
    filter.set_name(_("All Files"))
    filter.add_pattern("*")

    dialog.add_filter(filter)
