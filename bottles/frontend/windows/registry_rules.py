from gettext import gettext as _

from gi.repository import Adw, Gtk

from bottles.backend.managers.registry_rule import RegistryRuleManager
from bottles.backend.models.registry_rule import RegistryRule


@Gtk.Template(resource_path="/com/usebottles/bottles/registry-rule-entry.ui")
class RegistryRuleEntry(Adw.ActionRow):
    __gtype_name__ = "RegistryRuleEntry"

    # region Widgets
    btn_apply = Gtk.Template.Child()
    btn_delete = Gtk.Template.Child()
    btn_edit = Gtk.Template.Child()
    # endregion

    def __init__(self, parent, rule: RegistryRule, config, manager, **kwargs):
        super().__init__(**kwargs)

        self.parent = parent
        self.window = parent.window
        self.rule = rule
        self.config = config
        self.manager = manager

        self.set_title(rule.name)
        self._set_subtitle()

        if not self.config:
            self.btn_apply.set_visible(False)

        self.btn_apply.connect("clicked", self.__apply)
        self.btn_delete.connect("clicked", self.__delete)
        self.btn_edit.connect("clicked", self.__edit)

    def _set_subtitle(self):
        details = []
        if self.rule.description:
            details.append(self.rule.description)
        if self.rule.triggers:
            details.append(_("Triggers: {}".format(", ".join(self.rule.triggers))))
        if self.rule.run_once:
            details.append(_("Run once"))

        subtitle = " \u2022 ".join(details) if details else _("No description provided")
        self.set_subtitle(subtitle)

    def __apply(self, *_args):
        if not self.config:
            return
        RegistryRuleManager.apply_rules(self.config, rule_names=[self.rule.name])
        self.window.show_toast(_("Applied {} to this bottle").format(self.rule.name))

    def __delete(self, *_args):
        RegistryRuleManager.delete_rule(self.manager, self.config, self.rule.name)
        self.parent.remove_entry(self)
        self.window.show_toast(_("{} removed").format(self.rule.name))

    def __edit(self, *_args):
        self.parent.populate_form(self.rule)
