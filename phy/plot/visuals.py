# -*- coding: utf-8 -*-

"""Common visuals."""


#------------------------------------------------------------------------------
# Imports
#------------------------------------------------------------------------------

import numpy as np
from vispy.gloo import Texture2D

from .base import BaseVisual
from .transform import Range, GPU, NDC
from .utils import _enable_depth_mask, _tesselate_histogram


#------------------------------------------------------------------------------
# Utils
#------------------------------------------------------------------------------

def _check_data_bounds(data_bounds):
    assert len(data_bounds) == 4
    assert data_bounds[0] < data_bounds[2]
    assert data_bounds[1] < data_bounds[3]


def _get_data_bounds(data_bounds, pos):
    """"Prepare data bounds, possibly using min/max of the data."""
    if not len(pos):
        return data_bounds or NDC
    if data_bounds is None:
        m, M = pos.min(axis=0), pos.max(axis=0)
        data_bounds = [m[0], m[1], M[0], M[1]]
    _check_data_bounds(data_bounds)
    return data_bounds


def _get_data_bounds_1D(data_bounds, data):
    """Generate the complete data_bounds 4-tuple from the specified 2-tuple."""
    if data_bounds is None:
        data_bounds = [data.min(), data.max()] if data.size else [-1, 1]
    assert len(data_bounds) == 2
    # Ensure that the data bounds are not degenerate.
    if data_bounds[0] == data_bounds[1]:
        data_bounds = [data_bounds[0] - 1, data_bounds[0] + 1]
    ymin, ymax = data_bounds
    data_bounds = [-1, ymin, 1, ymax]
    _check_data_bounds(data_bounds)
    return data_bounds


def _check_pos_2D(pos):
    """Check position data before GPU uploading."""
    assert pos is not None
    pos = np.asarray(pos)
    assert pos.ndim == 2
    return pos


def _get_pos_depth(pos_tr, depth):
    """Prepare a (N, 3) position-depth array for GPU uploading."""
    n = pos_tr.shape[0]
    pos_tr = np.asarray(pos_tr, dtype=np.float32)
    assert pos_tr.shape == (n, 2)

    # Set the depth.
    if depth is None:
        depth = np.zeros(n, dtype=np.float32)
    depth = np.asarray(depth, dtype=np.float32)
    assert depth.shape == (n,)

    # Set the a_position attribute.
    pos_depth = np.empty((n, 3), dtype=np.float32)
    pos_depth[:, :2] = pos_tr
    pos_depth[:, 2] = depth

    return pos_depth


def _get_hist_max(hist):
    hist_max = hist.max() if hist.size else 1.
    hist_max = float(hist_max)
    hist_max = hist_max if hist_max > 0 else 1.
    assert hist_max > 0
    return hist_max


def _get_attr(attr, default, n):
    """Prepare an attribute for GPU uploading."""
    if not hasattr(default, '__len__'):
        default = [default]
    if attr is None:
        attr = np.tile(default, (n, 1))
    attr = np.asarray(attr, dtype=np.float32)
    if attr.ndim == 1:
        attr = attr[:, np.newaxis]
    assert attr.shape == (n, len(default))
    return attr


def _get_index(n_items, item_size, n):
    """Prepare an index attribute for GPU uploading."""
    index = np.arange(n_items)
    index = np.repeat(index, item_size)
    index = index.astype(np.float32)
    assert index.shape == (n,)
    return index


def _get_texture(arr, default, n_items, from_bounds):
    """Prepare data to be uploaded as a texture, with casting to uint8.
    The from_bounds must be specified.
    """
    if not hasattr(default, '__len__'):  # pragma: no cover
        default = [default]
    n_cols = len(default)
    if arr is None:
        arr = np.tile(default, (n_items, 1))
    assert arr.shape == (n_items, n_cols)
    # Convert to 3D texture.
    arr = arr[np.newaxis, ...].astype(np.float32)
    assert arr.shape == (1, n_items, n_cols)
    # NOTE: we need to cast the texture to [0, 255] (uint8).
    # This is easy as soon as we assume that the signal bounds are in
    # [-1, 1].
    assert len(from_bounds) == 2
    m, M = map(float, from_bounds)
    assert np.all(arr >= m)
    assert np.all(arr <= M)
    arr = 255 * (arr - m) / (M - m)
    assert np.all(arr >= 0)
    assert np.all(arr <= 255)
    arr = arr.astype(np.uint8)
    return arr


#------------------------------------------------------------------------------
# Visuals
#------------------------------------------------------------------------------

class ScatterVisual(BaseVisual):
    shader_name = 'scatter'
    gl_primitive_type = 'points'
    _default_marker_size = 10.
    _supported_marker_types = (
        'arrow',
        'asterisk',
        'chevron',
        'clover',
        'club',
        'cross',
        'diamond',
        'disc',
        'ellipse',
        'hbar',
        'heart',
        'infinity',
        'pin',
        'ring',
        'spade',
        'square',
        'tag',
        'triangle',
        'vbar',
    )

    def __init__(self, marker_type=None):
        super(ScatterVisual, self).__init__()
        # Default bounds.
        self.data_bounds = NDC
        self.n_points = None

        # Set the marker type.
        self.marker_type = marker_type or 'disc'
        assert self.marker_type in self._supported_marker_types

        # Enable transparency.
        _enable_depth_mask()

    def get_shaders(self):
        v, f = super(ScatterVisual, self).get_shaders()
        # Replace the marker type in the shader.
        f = f.replace('%MARKER_TYPE', self.marker_type)
        return v, f

    def get_transforms(self):
        return [Range(from_bounds=self.data_bounds), GPU()]

    def set_data(self,
                 pos=None,
                 depth=None,
                 colors=None,
                 marker_type=None,
                 size=None,
                 data_bounds=None,
                 ):
        pos = _check_pos_2D(pos)
        n = pos.shape[0]
        assert pos.shape == (n, 2)

        # Set the data bounds from the data.
        self.data_bounds = _get_data_bounds(data_bounds, pos)

        pos_tr = self.apply_cpu_transforms(pos)
        self.program['a_position'] = _get_pos_depth(pos_tr, depth)
        self.program['a_size'] = _get_attr(size, self._default_marker_size, n)
        self.program['a_color'] = _get_attr(colors, (1, 1, 1, 1), n)


class PlotVisual(BaseVisual):
    shader_name = 'plot'
    gl_primitive_type = 'line_strip'

    def __init__(self):
        super(PlotVisual, self).__init__()
        self.data_bounds = NDC
        _enable_depth_mask()

    def get_transforms(self):
        return [Range(from_bounds=self.data_bounds),
                GPU(),
                Range(from_bounds=NDC,
                      to_bounds='signal_bounds'),
                ]

    def set_data(self,
                 data=None,
                 depth=None,
                 data_bounds=None,
                 signal_bounds=None,
                 signal_colors=None,
                 ):
        pos = _check_pos_2D(data)
        n_signals, n_samples = data.shape
        n = n_signals * n_samples

        # Generate the x coordinates.
        x = np.linspace(-1., 1., n_samples)
        x = np.tile(x, n_signals)
        assert x.shape == (n,)

        # Generate the (n, 2) pos array.
        pos = np.empty((n, 2), dtype=np.float32)
        pos[:, 0] = x
        pos[:, 1] = data.ravel()

        # Set the transformed position.
        pos_tr = self.apply_cpu_transforms(pos)
        self.program['a_position'] = _get_pos_depth(pos_tr, depth)

        # Generate the signal index.
        self.program['a_signal_index'] = _get_index(n_signals, n_samples, n)

        # Generate the complete data_bounds 4-tuple from the specified 2-tuple.
        self.data_bounds = _get_data_bounds_1D(data_bounds, data)

        # Signal bounds (positions).
        signal_bounds = _get_texture(signal_bounds, NDC, n_signals, [-1, 1])
        self.program['u_signal_bounds'] = Texture2D(signal_bounds)

        # Signal colors.
        signal_colors = _get_texture(signal_colors, (1,) * 4,
                                     n_signals, [0, 1])
        self.program['u_signal_colors'] = Texture2D(signal_colors)

        # Number of signals.
        self.program['n_signals'] = n_signals


class HistogramVisual(BaseVisual):
    shader_name = 'histogram'
    gl_primitive_type = 'triangles'

    def __init__(self):
        super(HistogramVisual, self).__init__()
        self.n_bins = 0
        self.hist_max = 1

    def get_transforms(self):
        return [Range(from_bounds=[0, 0, self.n_bins, self.hist_max],
                      to_bounds=[0, 0, 1, 1]),
                GPU(),
                Range(from_bounds='hist_bounds',   # (0, 0, 1, v)
                      to_bounds=NDC),
                ]

    def set_data(self,
                 hist=None,
                 hist_lims=None,
                 hist_colors=None,
                 ):
        hist = _check_pos_2D(hist)
        n_hists, n_bins = hist.shape
        n = 6 * n_hists * n_bins
        # Store n_bins for get_transforms().
        self.n_bins = n_bins

        # Generate hist_max.
        self.hist_max = _get_hist_max(hist)

        # Set the transformed position.
        pos = np.vstack(_tesselate_histogram(row) for row in hist)
        pos_tr = self.apply_cpu_transforms(pos)
        pos_tr = np.asarray(pos_tr, dtype=np.float32)
        assert pos_tr.shape == (n, 2)
        self.program['a_position'] = pos_tr

        # Generate the hist index.
        self.program['a_hist_index'] = _get_index(n_hists, n_bins * 6, n)

        # Hist colors.
        self.program['u_hist_colors'] = _get_texture(hist_colors,
                                                     (1, 1, 1, 1),
                                                     n_hists, [0, 1])

        # Hist bounds.
        hist_bounds = np.c_[np.zeros((n_hists, 2)),
                            np.ones(n_hists),
                            hist_lims] if hist_lims is not None else None
        hist_bounds = _get_texture(hist_bounds, [0, 0, 1, self.hist_max],
                                   n_hists, [0, 10])
        self.program['u_hist_bounds'] = Texture2D(hist_bounds)
        self.program['n_hists'] = n_hists


class TextVisual(BaseVisual):
    shader_name = 'text'
    gl_primitive_type = 'points'

    def get_transforms(self):
        pass

    def set_data(self):
        pass
