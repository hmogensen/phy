from phy import IPlugin
import numpy as np
import networkx as nx
from phy.plot.plot import PlotCanvasMpl
from functools import partial
from phylib.utils import Bunch, connect, unconnect, emit
from phy.cluster.views import ManualClusteringView 
import scipy.sparse as sp

class GraphView(ManualClusteringView):
    plot_canvas_class = PlotCanvasMpl

    def __init__(self, graph_input):
        super(GraphView, self).__init__()
        self.graph_input = graph_input

    def attach(self, gui):
        super(GraphView, self).attach(gui)
        on_update = partial(self.on_graph_update)
        connect(on_update, event='update-graph') # Todo: unconnect?

    def on_graph_update(self, state):
        data = self.graph_input()
        settings = data.params

        template_amp_channels = data.template_amp_channels
        template_units = data.template_units
        template_batch_nr = data.template_batch_nr
        template_amplitudes = data.template_amplitudes
        template_clusters = data.template_clusters
        n_templates = len(template_amplitudes)

        # Load sparse matrices
        abs_dist_data = np.load(settings["fname_abs_dist_sparse"])
        rel_dist_data = np.load(settings["fname_rel_dist_sparse"])
        rows = np.load(settings["fname_rows_dist_indx"])
        cols = np.load(settings["fname_cols_dist_indx"])

        assert abs_dist_data.shape == rel_dist_data.shape
        assert len(rows) == len(cols)

        abs_dist_mat = sp.coo_matrix((abs_dist_data, (rows, cols)), shape=(n_templates, n_templates))
        rel_dist_mat = sp.coo_matrix((rel_dist_data, (rows, cols)), shape=(n_templates, n_templates))

        # Convert to CSR format for efficient indexing
        abs_dist_mat = abs_dist_mat.tocsr()
        rel_dist_mat = rel_dist_mat.tocsr()        

        ch_window_width = settings['ch_window_width']
        unit_thr = settings['unit_thr']
        height_thr = settings['height_thr']
        abs_dist_thr = settings['abs_dist_thr']
        rel_dist_thr = settings['rel_dist_thr']
        batch_delay_thr = settings['batch_delay_thr']

        n_batches = len(template_amplitudes)

        batch_pos = np.linspace(-0.3, 0.3, n_batches)
        channel_pos = np.linspace(-0.3, 0.3, ch_window_width)[::-1]

        if template_clusters is None:
            template_clusters = np.arange(template_units.size)

        indx = np.where((template_units > unit_thr) & (template_amplitudes > height_thr))[0]
        
        abs_dist_mat_condensed = abs_dist_mat[indx][:, indx].todense()
        rel_dist_mat_condensed = rel_dist_mat[indx][:, indx].todense()

        p = np.argwhere((abs_dist_mat_condensed > 0) & 
                        (((abs_dist_mat_condensed < abs_dist_thr)) 
                         | (rel_dist_mat_condensed < rel_dist_thr)))
        p = indx[p]
        
        ga = nx.Graph()
        for i in range(p.shape[0]):
            w = np.abs(template_batch_nr[p[i][0]] - template_batch_nr[p[i][1]])
            if w <= batch_delay_thr:
                ga.add_edge(p[i][0], p[i][1], weight=w)
        
        self.canvas.clear()
        pos = nx.spring_layout(ga)
        labels = nx.get_edge_attributes(ga, 'weight')
        pos = nx.spring_layout(ga)
        for k in pos.keys():
            pos[k][0] = batch_pos[template_batch_nr[k]]
            pos[k][1] = channel_pos[template_amp_channels[k] - 1]
        
        node_colors = template_clusters
        
        self.canvas.ax.set_title("Template clusters")
        nx.draw_networkx(ga, pos)
        nx.draw_networkx_edge_labels(ga, pos, edge_labels=labels)
        nx.draw_networkx_nodes(ga, pos)  # node_color=node_colors
        self.canvas.show()


class GraphViewPlugin(IPlugin):
    def attach_to_controller(self, controller):
        def create_graph_view():
            return GraphView(graph_input=controller.get_graph_data)

        if controller.graph_model is not None:
            controller.view_creator["GraphView"] = create_graph_view


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
