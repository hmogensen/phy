from phy import IPlugin, connect
from phy.cluster.views import WaveformView
from phylib.utils import Bunch, connect, unconnect, emit
from plugins.graph_view import GraphView
from phy.cluster.views.trigger_histogram import PeristimHistView

class ExportPlotPlugin(IPlugin):
    def attach_to_controller(self, controller):
        @connect
        def on_view_attached(view, gui):
            if isinstance(view, PeristimHistView):
                @view.dock.add_button(icon='f105') # TODO: Change to suitable icon
                def export_plot(checked):
                    emit(view.export_data_event_name, self)