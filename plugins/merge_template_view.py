import numpy as np
from phy import IPlugin
from phy.cluster.views import ManualClusteringView 
from PyQt5.QtWidgets import (QListView, QTableView, QApplication, QWidget, 
                           QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy)
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import QStringListModel

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.cm import rainbow

_N_COLUMNS = 3

class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=4, height=4):
        fig = Figure(figsize=(width, height))
        self.axes = fig.add_subplot(111)
        
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)
        
        FigureCanvas.setSizePolicy(self,
                                 QSizePolicy.Expanding,
                                 QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)


class MergeTemplateView(QWidget):
    
    def __init__(self, controller): #:TemplateController):
        super(MergeTemplateView, self).__init__()
        self.controller = controller
        self._init_ui()


    def _clear_table(self):
        self.model.removeRows(0, self.model.rowCount())


    def _reload_table(self):
        spike_templates = self.controller.model.spike_templates
        unique_templates = np.unique(spike_templates[spike_templates > 0])
        template_clusters = self.controller.graph_model.template_clusters
        assert len(template_clusters) == len(unique_templates)

        unique_template_clusters = np.unique(template_clusters)
        for tc in unique_template_clusters:   
            indx = np.nonzero(tc == template_clusters)[0]
            n_templates = len(indx)
            assert n_templates > 0
            n_spikes = 0
            for i in indx:
                n_spikes += np.count_nonzero(spike_templates == i)

            row_items = [
                QStandardItem(str(tc)),
                QStandardItem(str(n_templates)),
                QStandardItem(str(n_spikes))
            ]
            assert len(row_items) == _N_COLUMNS
            self.model.appendRow(row_items)


    def _init_ui(self):
        main_layout = QHBoxLayout()
        
        self.plot_canvas = PlotCanvas(self, width=4, height=4)
        main_layout.addWidget(self.plot_canvas)
        
        right_layout = QVBoxLayout()
        
        button_layout = QHBoxLayout()
        
        self.merge_button = QPushButton('Merge', self)
        self.merge_button.setEnabled(False)
        self.unmerge_button = QPushButton('Unmerge', self)
        self.unmerge_button.setEnabled(False)

        button_layout.addWidget(self.merge_button)
        button_layout.addWidget(self.unmerge_button)
        
        self.list_view = QTableView()
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["tc_id", "n_clusters", "n_spikes"])
        
        self.list_view.setModel(self.model)
        self.list_view.setSelectionMode(QListView.ExtendedSelection)
        self.list_view.setSelectionBehavior(QTableView.SelectRows)
        
        self.merge_button.clicked.connect(self.merge_action)
        self.unmerge_button.clicked.connect(self.unmerge_cluster)
        self.list_view.selectionModel().selectionChanged.connect(self.update_merge_buttons)        

        right_layout.addLayout(button_layout)
        right_layout.addWidget(self.list_view)
        
        main_layout.addLayout(right_layout)
        
        self.setLayout(main_layout)

        self._reload_table()
        
        self.setGeometry(300, 300, 800, 500)
        self.setWindowTitle('Merge Template View')
        

    def update_merge_buttons(self):
        selected_indexes = self.list_view.selectionModel().selectedIndexes()
        n_rows = len(selected_indexes)/_N_COLUMNS
        self.merge_button.setEnabled(n_rows >= 2)
        self.unmerge_button.setEnabled(n_rows == 1)
        self.update_plot()

    
    def merge_action(self):
        selected_indx = self.list_view.selectionModel().selectedIndexes()
        selected_rows = sorted(set(index.row() for index in selected_indx))
        merge_clusters = [int(self.model.item(row, 0).text()) for row in selected_rows]
        template_clusters = self.controller.graph_model.template_clusters.copy()
        min_cluster = min(merge_clusters)
        for cluster in merge_clusters:
            template_clusters[template_clusters == cluster] = min_cluster
        unique_clusters = np.unique(template_clusters)
        mapping = {old: new for new, old in enumerate(unique_clusters)}
        for old, new in mapping.items():
            template_clusters[template_clusters == old] = new
        self.controller.graph_model.set_template_clusters(template_clusters)
        self._clear_table()
        self._reload_table()
 

    def unmerge_cluster(self):
        selected_indx = self.list_view.selectionModel().selectedIndexes()
        selected_rows = sorted(set(index.row() for index in selected_indx))
        unmerge_cluster_row = [int(self.model.item(row, 0).text()) for row in selected_rows]
        assert len(unmerge_cluster_row) == 1 # Can be modified to allow for selecting and unmerging several 
                                         # templates at the same time. In this case also change setEnabled state 
                                         # in callback update_merge_buttons
        unmerge_cluster_row = unmerge_cluster_row[0]
        template_clusters = self.controller.graph_model.template_clusters.copy()
        unmerge_template_indx = np.where(template_clusters == unmerge_cluster_row)[0]
        shift_template_indx = template_clusters > unmerge_cluster_row
        template_clusters[shift_template_indx] += len(unmerge_template_indx)
        for i, indx in enumerate(unmerge_template_indx, start=1):
            template_clusters[indx] = unmerge_cluster_row + i
        self.controller.graph_model.set_template_clusters(template_clusters)
        self._clear_table()
        self._reload_table()


    def update_plot(self):
        self.plot_canvas.axes.clear()

        selected_indexes = self.list_view.selectionModel().selectedIndexes()
        selected_rows = sorted(set(index.row() for index in selected_indexes))
        template_cluster_ids = [int(self.model.item(row, 0).text()) for row in selected_rows]
        template_clusters = self.controller.graph_model.template_clusters
        template_channel_ranges = self.controller.graph_model.template_channel_ranges

        colors = rainbow(np.linspace(0, 1, len(template_cluster_ids)))
        for i_color, i_template_cluster in enumerate(template_cluster_ids):
            indx = np.nonzero(i_template_cluster == template_clusters)
            color = colors[i_color]
            for i_template in indx:
                i_template = i_template[0]
                templ = self.controller.model.get_template(i_template)
                data = templ["template"]
                for index, i_channel in enumerate(range(template_channel_ranges[0][i_template], template_channel_ranges[1][i_template])):
                    if index >= data.shape[1]:
                        print(f"Warning: index {index} out of bounds for matrix {data.shape}")
                        continue
                    y = 500.0*i_channel + data[:, index]
                    self.plot_canvas.axes.plot(y, color=color)
        self.plot_canvas.axes.grid(True)
        self.plot_canvas.draw()


class MergeTemplateViewPlugin(IPlugin):
    def attach_to_controller(self, controller):
        def create_merge_template_view():
            return MergeTemplateView(controller)
        
        controller.view_creator["MergeTemplateView"] = create_merge_template_view
