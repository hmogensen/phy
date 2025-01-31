from phy import IPlugin
from phy.cluster.views import ManualClusteringView 
from PyQt5.QtWidgets import QListView
from PyQt5.QtGui import QStandardItemModel, QStandardItem
import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QListView)
from PyQt5.QtCore import QStringListModel

#class MergeTemplateView(ManualClusteringView):
#class MergeTemplateView(object):
class MergeTemplateView(QListView):
    def __init__(self, controller):
        super(MergeTemplateView, self).__init__()
        self.controller = controller
        self._init_ui()

    def _init_ui(self):
        # Create main layout
        layout = QVBoxLayout()
        
        # Create button layout
        button_layout = QHBoxLayout()
        
        # Create buttons
        self.add_button = QPushButton('Add Item', self)
        self.remove_button = QPushButton('Remove Item', self)
        self.merge_button = QPushButton('Merge', self)
        self.merge_button.setEnabled(False)
        self.unmerge_button = QPushButton('Unmerge', self)
        self.unmerge_button.setEnabled(False)

        # Add buttons to button layout
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.merge_button)
        button_layout.addWidget(self.unmerge_button)
        
        # Create list view and model
        self.list_view = QListView()
        self.model = QStringListModel()
        self.items = []
        self.model.setStringList(self.items)
        self.list_view.setModel(self.model)
        self.list_view.setSelectionMode(QListView.MultiSelection)
        
        # Connect button signals to slots
        self.add_button.clicked.connect(self.add_item)
        self.remove_button.clicked.connect(self.remove_item)
        self.merge_button.clicked.connect(self.merge_templates)
        self.unmerge_button.clicked.connect(self.unmerge_cluster)
        self.list_view.selectionModel().selectionChanged.connect(self.update_merge_buttons)        

        # Add layouts and widgets to main layout
        layout.addLayout(button_layout)
        layout.addWidget(self.list_view)
        
        
        # Set the main layout
        self.setLayout(layout)

        for i in self.controller.model.template_clusters.data:
            self.items.append(str(i))
            self.model.setStringList(self.items)
        
        # Set window properties
        self.setGeometry(300, 300, 400, 500)
        self.setWindowTitle('List Widget')
        
    def add_item(self):
        # Add a dummy item to the list
        count = len(self.items)
        self.items.append(f'Item {count + 1}')
        self.model.setStringList(self.items)
        
    def remove_item(self):
        # Remove the last item if the list is not empty
        if self.items:
            self.items.pop()
            self.model.setStringList(self.items)

    def update_merge_buttons(self):
        selected_indexes = self.list_view.selectionModel().selectedIndexes()
        self.merge_button.setEnabled(len(selected_indexes) >= 2)
        self.unmerge_button.setEnabled(len(selected_indexes) == 1)
    
    def merge_templates(self):
        selected_indexes = self.list_view.selectionModel().selectedIndexes()
        selected_items = [self.items[index.row()] for index in selected_indexes]
        print("Merge items:", selected_items)

    def unmerge_cluster(self):
        selected_indx = self.list_view.selectionModel().selectedIndexes()[0]
        print("Unmerge items: ", self.items[selected_indx.row()])


    # def attach(self, gui):
    #     # super(MergeTemplateView, self).attach(gui)
    #     gui.add_view(self) # position = None

class MergeTemplateViewPlugin(IPlugin):
    def attach_to_controller(self, controller):
        def create_merge_template_view():
            return MergeTemplateView(controller)
        
        controller.view_creator["MergeTemplateView"] = create_merge_template_view
