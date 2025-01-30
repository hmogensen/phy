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
        data, params = self.graph_input()

        print(params)

        template_amp_channels = data.template_amp_channels
        template_units = data.template_units
        template_batch_nr = data.template_batch_nr
        template_amplitudes = data.template_amplitudes
        template_clusters = data.template_clusters
        n_templates = len(template_amplitudes)

        # Load sparse matrices
        abs_dist_data = data.abs_dist_sparse
        rel_dist_data = data.rel_dist_sparse
        rows = data.row_dist_indx
        cols = data.col_dist_indx

        assert abs_dist_data.shape == rel_dist_data.shape
        assert len(rows) == len(cols)

        abs_dist_mat = sp.coo_matrix((abs_dist_data, (rows, cols)), shape=(n_templates, n_templates))
        rel_dist_mat = sp.coo_matrix((rel_dist_data, (rows, cols)), shape=(n_templates, n_templates))

        # Convert to CSR format for efficient indexing
        abs_dist_mat = abs_dist_mat.tocsr()
        rel_dist_mat = rel_dist_mat.tocsr()        

        ch_window_width = params.ch_window_width
        unit_thr = params.tempclust.unit_thr
        height_thr = params.tempclust.height_thr
        abs_dist_thr = params.tempclust.abs_dist_thr
        rel_dist_thr = params.tempclust.rel_dist_thr
        batch_delay_thr = params.tempclust.batch_delay_thr

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
                @view.dock.add_button(icon='f6ff')
                def update_graph(checked):
                    emit('update-graph', self)


