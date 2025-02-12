from phy import IPlugin, connect
from phylib.io.sc_params_dialog import ScParamsDialog
from phylib.io.sc_params import ScParams


def _edit_parameters(params:ScParams):
    updated_params, accepted = ScParamsDialog.edit_params(params)
    if accepted:
        return updated_params
    return None

class ScSettingsMenuPlugin(IPlugin):
    def attach_to_controller(self, controller):
        @connect
        def on_gui_ready(sender, gui):
            gui.file_actions.separator()
            @gui.file_actions.add()
            def sc_settings():
                params = controller.sc_params
                if updated_params := _edit_parameters(params):
                    for key in updated_params:
                        params[key] = updated_params[key]
