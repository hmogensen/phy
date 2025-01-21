"""Show how to add custom buttons in a view's title bar."""

from phy import IPlugin, connect
from phy.cluster.views import WaveformView
from phylib.utils import Bunch, connect, unconnect, emit
from plugins.graph_view import GraphView

class UpdateGraphViewBtnPlugin(IPlugin):
    def attach_to_controller(self, controller):
        @connect
        def on_view_attached(view, gui):
            if isinstance(view, GraphView):
                @view.dock.add_button(icon='f105')
                def update_graph(checked):
                    emit('update-graph', self)

# <viewBox="0 0 576 512">
# <path d="M0 80C0 53.5 21.5 32 48 32l96 0c26.5 0 48 21.5 48 48l0 16 192 0 0-16c0-26.5 21.5-48 48-48l96 0c26.5 0 48 21.5 48 48l0 96c0 26.5-21.5 48-48 48l-96 0c-26.5 0-48-21.5-48-48l0-16-192 0 0 16c0 1.7-.1 3.4-.3 5L272 288l96 0c26.5 0 48 21.5 48 48l0 96c0 26.5-21.5 48-48 48l-96 0c-26.5 0-48-21.5-48-48l0-96c0-1.7 .1-3.4 .3-5L144 224l-96 0c-26.5 0-48-21.5-48-48L0 80z"/>
