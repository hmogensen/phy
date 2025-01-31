from phy import IPlugin, connect
from phy.cluster.views import WaveformView
from phylib.utils import Bunch, connect, unconnect, emit
from phy.cluster.views.base import ManualClusteringView

class ExportPlotPlugin(IPlugin):
    def attach_to_controller(self, controller):
        @connect
        def on_view_attached(view, gui):
            if isinstance(view, ManualClusteringView):
                @view.dock.add_button(icon='f0c7')
                def export_plot(checked):
                    emit(view.export_data_event_name, self)
