import numpy as np
from functools import partial
import sys
from PyQt5.QtWidgets import QFileDialog, QApplication
import json

from .histogram import HistogramView, _compute_histogram, _first_not_null
from phy.utils.color import selected_cluster_color
from phylib.utils import Bunch, connect, unconnect, emit

class TriggerHistogramView(HistogramView):
    def __init__(self, cluster_stat=None, trigger_stat=None):
        super(TriggerHistogramView, self).__init__(cluster_stat=cluster_stat)
        self.trigger_stat = trigger_stat

    def get_clusters_data(self, load_all=None):
        bunchs = []
        trigger_times = self.trigger_stat()
        for i, cluster_id in enumerate(self.cluster_ids):
            bunch = self.cluster_stat(cluster_id, trigger_times)
            if not bunch.data.size:
                continue
            bmin, bmax = bunch.data.min(), bunch.data.max()
            # Update self.x_max if it was not set before.
            self.x_min = _first_not_null(self.x_min, bunch.get('x_min', None), bmin)
            self.x_max = _first_not_null(self.x_max, bunch.get('x_max', None), bmax)
            self.x_min, self.x_max = sorted((self.x_min, self.x_max))
            assert self.x_min is not None
            assert self.x_max is not None
            assert self.x_min <= self.x_max

            # Compute the histogram.
            bunch.histogram = _compute_histogram(
                bunch.data, x_min=self.x_min, x_max=self.x_max, n_bins=self.n_bins)
            bunch.ylim = bunch.histogram.max()

            bunch.color = selected_cluster_color(i)
            bunch.index = 0
            bunch.cluster_id = cluster_id
            bunchs.append(bunch)
        return bunchs
    

class PeristimHistView(TriggerHistogramView):
    """Histogram view showing the peristimulus time histogram (PSTH)."""
    x_min = -0.5  # window starts 500ms before stimulus by default
    x_max = 0.5   # window ends 500ms after stimulus by default
    n_bins = 100  # 10ms bins by default
    alias_char = 'psth'  # provide `:psthn` (set number of bins) and `:psthm` (set max bin) snippets
    bin_unit = 'ms'  # user-provided bin values in milliseconds, but stored in seconds
    listen_to_triggers = True

    export_data_event_name = 'export-plot-psth'

    default_shortcuts = {
        'change_window_size': 'ctrl+wheel',
    }

    default_snippets = {
        'set_n_bins': '%sn' % alias_char,
        'set_bin_size (%s)' % bin_unit: '%sb' % alias_char,
        'set_x_min (%s)' % bin_unit: '%smin' % alias_char,
        'set_x_max (%s)' % bin_unit: '%smax' % alias_char,
    }
    
    def attach(self, gui):
        super(PeristimHistView, self).attach(gui)
        on_export_plot = partial(self.export_plot)
        connect(on_export_plot, event=self.export_data_event_name) # Todo: unconnect?

    def export_plot(self, state):
        filename, _ = QFileDialog.getSaveFileName(
            caption="Save clusters",
            filter="JSON files (*.json)"
        )
        if filename:
            bunchs = self.get_clusters_data()
            
            # Convert NumPy arrays to lists in the bunches data
            serializable_bunchs = []
            for bunch in bunchs:
                serializable_bunch = {}
                for key, value in bunch.items():
                    if isinstance(value, np.ndarray):
                        serializable_bunch[key] = value.tolist()
                    elif isinstance(value, tuple) and len(value) == 4:  # Handle RGBA color tuples
                        serializable_bunch[key] = list(value)
                    else:
                        serializable_bunch[key] = value
                serializable_bunchs.append(serializable_bunch)
            
            # Save to JSON file
            with open(filename, 'w') as f:
                json.dump(serializable_bunchs, f, indent=2)