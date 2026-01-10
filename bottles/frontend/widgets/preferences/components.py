import re
from gi.repository import Adw, Gtk

from bottles.backend.logger import Logger
from bottles.backend.models.result import Result
from bottles.backend.runner import Runner
from bottles.backend.utils.threading import RunAsync
from bottles.frontend.utils.gtk import GtkUtils
from bottles.frontend.windows.protonalert import ProtonAlertDialog

logging = Logger()


@Gtk.Template(resource_path="/com/usebottles/bottles/preferences-components.ui")
class PreferencesComponents(Adw.PreferencesGroup):
    __gtype_name__ = "PreferencesComponents"

    combo_runner = Gtk.Template.Child()
    combo_dxvk = Gtk.Template.Child()
    combo_vkd3d = Gtk.Template.Child()
    combo_nvapi = Gtk.Template.Child()
    combo_latencyflex = Gtk.Template.Child()
    spinner_dxvk = Gtk.Template.Child()
    spinner_vkd3d = Gtk.Template.Child()
    spinner_nvapi = Gtk.Template.Child()
    spinner_latencyflex = Gtk.Template.Child()
    spinner_runner = Gtk.Template.Child()
    str_list_runner = Gtk.Template.Child()
    str_list_dxvk = Gtk.Template.Child()
    str_list_vkd3d = Gtk.Template.Child()
    str_list_nvapi = Gtk.Template.Child()
    str_list_latencyflex = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parent_view = None
        self.config = None
        self.manager = None

    def setup(self, parent_view):
        self.parent_view = parent_view
        self.config = parent_view.config
        self.manager = parent_view.manager

        # region signals
        self.combo_runner.connect("notify::selected", self._set_runner)
        self.combo_dxvk.connect("notify::selected", self._set_dxvk)
        self.combo_vkd3d.connect("notify::selected", self._set_vkd3d)
        self.combo_nvapi.connect("notify::selected", self._set_nvapi)
        self.combo_latencyflex.connect("notify::selected", self._set_latencyflex)
        # endregion

    def update_combos(self):
        self.combo_runner.handler_block_by_func(self._set_runner)
        self.combo_dxvk.handler_block_by_func(self._set_dxvk)
        self.combo_vkd3d.handler_block_by_func(self._set_vkd3d)
        self.combo_nvapi.handler_block_by_func(self._set_nvapi)
        self.combo_latencyflex.handler_block_by_func(self._set_latencyflex)

        for string_list in [
            self.str_list_runner,
            self.str_list_dxvk,
            self.str_list_vkd3d,
            self.str_list_nvapi,
            self.str_list_latencyflex,
        ]:
            string_list.splice(0, string_list.get_n_items())

        self.str_list_dxvk.append("Disabled")
        self.str_list_vkd3d.append("Disabled")
        self.str_list_latencyflex.append("Disabled")

        for dxvk in self.manager.dxvk_available:
            self.str_list_dxvk.append(dxvk)
        for vkd3d in self.manager.vkd3d_available:
            self.str_list_vkd3d.append(vkd3d)
        for runner in self.manager.runners_available:
            self.str_list_runner.append(runner)
        for nvapi in self.manager.nvapi_available:
            self.str_list_nvapi.append(nvapi)
        for latencyflex in self.manager.latencyflex_available:
            self.str_list_latencyflex.append(latencyflex)

        self.combo_runner.handler_unblock_by_func(self._set_runner)
        self.combo_dxvk.handler_unblock_by_func(self._set_dxvk)
        self.combo_vkd3d.handler_unblock_by_func(self._set_vkd3d)
        self.combo_nvapi.handler_unblock_by_func(self._set_nvapi)
        self.combo_latencyflex.handler_unblock_by_func(self._set_latencyflex)

    def set_config(self, config):
        self.config = config
        parameters = self.config.Parameters

        self.combo_runner.handler_block_by_func(self._set_runner)
        self.combo_dxvk.handler_block_by_func(self._set_dxvk)
        self.combo_vkd3d.handler_block_by_func(self._set_vkd3d)
        self.combo_nvapi.handler_block_by_func(self._set_nvapi)
        self.combo_latencyflex.handler_block_by_func(self._set_latencyflex)

        _dxvk = self.config.DXVK
        if parameters.dxvk:
            if _dxvk in self.manager.dxvk_available:
                if _i_dxvk := self.manager.dxvk_available.index(_dxvk) + 1:
                    self.combo_dxvk.set_selected(_i_dxvk)
        else:
            self.combo_dxvk.set_selected(0)

        _vkd3d = self.config.VKD3D
        if parameters.vkd3d:
            if _vkd3d in self.manager.vkd3d_available:
                if _i_vkd3d := self.manager.vkd3d_available.index(_vkd3d) + 1:
                    self.combo_vkd3d.set_selected(_i_vkd3d)
        else:
            self.combo_vkd3d.set_selected(0)

        _nvapi = self.config.NVAPI
        if _nvapi in self.manager.nvapi_available:
            if _i_nvapi := self.manager.nvapi_available.index(_nvapi):
                self.combo_nvapi.set_selected(_i_nvapi)

        _latencyflex = self.config.LatencyFleX
        if parameters.latencyflex:
            if _latencyflex in self.manager.latencyflex_available:
                if (
                    _i_latencyflex := self.manager.latencyflex_available.index(
                        _latencyflex
                    )
                    + 1
                ):
                    self.combo_latencyflex.set_selected(_i_latencyflex)
        else:
            self.combo_latencyflex.set_selected(0)

        _runner = self.config.Runner
        if _runner in self.manager.runners_available:
            if _i_runner := self.manager.runners_available.index(_runner):
                self.combo_runner.set_selected(_i_runner)

        self.combo_runner.handler_unblock_by_func(self._set_runner)
        self.combo_dxvk.handler_unblock_by_func(self._set_dxvk)
        self.combo_vkd3d.handler_unblock_by_func(self._set_vkd3d)
        self.combo_nvapi.handler_unblock_by_func(self._set_nvapi)
        self.combo_latencyflex.handler_unblock_by_func(self._set_latencyflex)

    def _set_runner(self, *_args):
        def set_widgets_status(status=True):
            self.combo_runner.set_sensitive(status)
            self.parent_view.graphics_group.switch_nvapi.set_sensitive(status)
            self.combo_dxvk.set_sensitive(status)
            self.combo_nvapi.set_sensitive(status)
            self.combo_vkd3d.set_sensitive(status)

            if status:
                self.spinner_runner.stop()
                self.spinner_runner.set_visible(False)
            else:
                self.spinner_runner.start()
                self.spinner_runner.set_visible(True)

        @GtkUtils.run_in_main_loop
        def update(result: Result[dict], error=False):
            if isinstance(result, Result) and isinstance(result.data, dict):
                self.parent_view.details.update_runner_label(runner)
                if "config" in result.data:
                    self.parent_view.config = result.data["config"]
                    self.config = self.parent_view.config

                if self.config.Parameters.use_steam_runtime:
                    self.parent_view.system_group.switch_steam_runtime.handler_block_by_func(
                        self.parent_view._toggle_feature_cb
                    )
                    self.parent_view.system_group.switch_steam_runtime.set_active(True)
                    self.parent_view.system_group.switch_steam_runtime.handler_unblock_by_func(
                        self.parent_view._toggle_feature_cb
                    )

            set_widgets_status(True)
            self.parent_view.set_config(self.config)
            self.parent_view.queue.end_task()

        set_widgets_status(False)
        runner = self.manager.runners_available[self.combo_runner.get_selected()]

        def run_task(status=True):
            if not status:
                update(Result(True))
                return
            self.parent_view.queue.add_task()
            RunAsync(
                Runner.runner_update,
                callback=update,
                config=self.config,
                manager=self.manager,
                runner=runner,
            )

        if re.search("^(GE-)?Proton", runner):
            dialog = ProtonAlertDialog(self.parent_view.window, run_task)
            dialog.show()
        else:
            run_task()

    def _set_dxvk(self, *_args):
        self.set_dxvk_status(pending=True)
        self.parent_view.queue.add_task()

        if self.combo_dxvk.get_selected() == 0:
            if self.combo_vkd3d.get_selected() != 0:
                self.combo_vkd3d.set_selected(0)

            RunAsync(
                task_func=self.manager.install_dll_component,
                callback=self.set_dxvk_status,
                config=self.config,
                component="dxvk",
                remove=True,
            )
            self.parent_view.config = self.manager.update_config(
                config=self.config, key="dxvk", value=False, scope="Parameters"
            ).data["config"]
        else:
            dxvk = self.manager.dxvk_available[self.combo_dxvk.get_selected() - 1]
            self.parent_view.config = self.manager.update_config(
                config=self.config, key="DXVK", value=dxvk
            ).data["config"]

            RunAsync(
                task_func=self._dll_component_task_func,
                callback=self.set_dxvk_status,
                config=self.parent_view.config,
                component="dxvk",
            )
            self.parent_view.config = self.manager.update_config(
                config=self.parent_view.config,
                key="dxvk",
                value=True,
                scope="Parameters",
            ).data["config"]
        self.config = self.parent_view.config

    def _set_vkd3d(self, *_args):
        self.set_vkd3d_status(pending=True)
        self.parent_view.queue.add_task()

        if self.combo_vkd3d.get_selected() == 0:
            RunAsync(
                task_func=self.manager.install_dll_component,
                callback=self.set_vkd3d_status,
                config=self.config,
                component="vkd3d",
                remove=True,
            )
            self.parent_view.config = self.manager.update_config(
                config=self.config, key="vkd3d", value=False, scope="Parameters"
            ).data["config"]
        else:
            if self.combo_dxvk.get_selected() == 0:
                self.combo_dxvk.set_selected(1)

            vkd3d = self.manager.vkd3d_available[self.combo_vkd3d.get_selected() - 1]
            self.parent_view.config = self.manager.update_config(
                config=self.config, key="VKD3D", value=vkd3d
            ).data["config"]

            RunAsync(
                task_func=self._dll_component_task_func,
                callback=self.set_vkd3d_status,
                config=self.parent_view.config,
                component="vkd3d",
            )
            self.parent_view.config = self.manager.update_config(
                config=self.parent_view.config,
                key="vkd3d",
                value=True,
                scope="Parameters",
            ).data["config"]
        self.config = self.parent_view.config

    def _set_nvapi(self, *_args):
        self.parent_view.graphics_group.set_nvapi_status(pending=True)
        self.parent_view.queue.add_task()

        self.parent_view.graphics_group.switch_nvapi.set_active(True)

        nvapi = self.manager.nvapi_available[self.combo_nvapi.get_selected()]
        self.parent_view.config = self.manager.update_config(
            config=self.config, key="NVAPI", value=nvapi
        ).data["config"]

        RunAsync(
            task_func=self._dll_component_task_func,
            callback=self.parent_view.graphics_group.set_nvapi_status,
            config=self.parent_view.config,
            component="nvapi",
        )
        self.parent_view.config = self.manager.update_config(
            config=self.parent_view.config,
            key="dxvk_nvapi",
            value=True,
            scope="Parameters",
        ).data["config"]
        self.config = self.parent_view.config

    def _set_latencyflex(self, *_args):
        self.parent_view.queue.add_task()
        if self.combo_latencyflex.get_selected() == 0:
            RunAsync(
                task_func=self.manager.install_dll_component,
                callback=self.set_latencyflex_status,
                config=self.config,
                component="latencyflex",
                remove=True,
            )
            self.parent_view.config = self.manager.update_config(
                config=self.config, key="latencyflex", value=False, scope="Parameters"
            ).data["config"]
        else:
            latencyflex = self.manager.latencyflex_available[
                self.combo_latencyflex.get_selected() - 1
            ]
            self.parent_view.config = self.manager.update_config(
                config=self.config, key="LatencyFleX", value=latencyflex
            ).data["config"]

            RunAsync(
                task_func=self._dll_component_task_func,
                callback=self.set_latencyflex_status,
                config=self.parent_view.config,
                component="latencyflex",
            )
            self.parent_view.config = self.manager.update_config(
                config=self.parent_view.config,
                key="latencyflex",
                value=True,
                scope="Parameters",
            ).data["config"]
        self.config = self.parent_view.config

    def _dll_component_task_func(self, *args, **kwargs):
        self.manager.install_dll_component(
            config=kwargs["config"], component=kwargs["component"], remove=True
        )
        self.manager.install_dll_component(
            config=kwargs["config"], component=kwargs["component"]
        )

    @GtkUtils.run_in_main_loop
    def set_dxvk_status(self, status=None, error=None, pending=False):
        self.combo_dxvk.set_sensitive(not pending)
        if pending:
            self.spinner_dxvk.start()
            self.spinner_dxvk.set_visible(True)
        else:
            self.spinner_dxvk.stop()
            self.spinner_dxvk.set_visible(False)
            self.parent_view.queue.end_task()

    @GtkUtils.run_in_main_loop
    def set_vkd3d_status(self, status=None, error=None, pending=False):
        self.combo_vkd3d.set_sensitive(not pending)
        if pending:
            self.spinner_vkd3d.start()
            self.spinner_vkd3d.set_visible(True)
        else:
            self.spinner_vkd3d.stop()
            self.spinner_vkd3d.set_visible(False)
            self.parent_view.queue.end_task()

    @GtkUtils.run_in_main_loop
    def set_latencyflex_status(self, status=None, error=None, pending=False):
        self.combo_latencyflex.set_sensitive(not pending)
        if pending:
            self.spinner_latencyflex.start()
            self.spinner_latencyflex.set_visible(True)
        else:
            self.spinner_latencyflex.stop()
            self.spinner_latencyflex.set_visible(False)
            self.parent_view.queue.end_task()
