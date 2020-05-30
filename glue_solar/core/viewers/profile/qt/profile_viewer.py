# Experimenting with implementing a basic glue viewer for SunPy maps

import os

from glue.utils import defer_draw, decorate_all_methods

from astropy.wcs import WCS
from spectral_cube import SpectralCube
from spectral_cube.wcs_utils import drop_axis, slice_wcs

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Qt5Agg')
from echo import delay_callback
from qtpy.QtWidgets import QWidget, QVBoxLayout, QCheckBox

from glue.core import Component, Data
from glue.core.data_combo_helper import ComponentIDComboHelper, ManualDataComboHelper
from glue.external.echo import (CallbackProperty, SelectionCallbackProperty,
                                keep_in_sync)
from glue.external.echo.qt import (connect_checkable_button,
                                   autoconnect_callbacks_to_qt)
from glue.viewers.matplotlib.layer_artist import MatplotlibLayerArtist
from glue.viewers.matplotlib.state import (MatplotlibDataViewerState,
                                           MatplotlibLayerState,
                                           DeferredDrawCallbackProperty as DDCProperty,
                                           DeferredDrawSelectionCallbackProperty as DDSCProperty)
from glue.viewers.matplotlib.qt.data_viewer import MatplotlibDataViewer
from glue.core.subset import roi_to_subset_state
from glue.utils.qt import load_ui
from glue.config import qt_client

# __all__ = ['SunPyProfileViewerState', 'SunPyProfileLayerState', 'SunPyProfileLayerArtist',
#            'SunPyProfileViewerStateWidget', 'SunPyProfileLayerStateWidget',
#            'SunPyProfileDataViewer', 'SunPyMatplotlibProfileMixin']


def get_identity_wcs(naxis):

    wcs = WCS(naxis=naxis)
    wcs.wcs.ctype = ['X'] * naxis
    wcs.wcs.crval = [0.] * naxis
    wcs.wcs.crpix = [1.] * naxis
    wcs.wcs.cdelt = [1.] * naxis

    return wcs


class SunPyProfileViewerState(MatplotlibDataViewerState):
    x_att_pixel = DDSCProperty(docstring='The component ID giving the pixel component '
                                         'shown on the x axis')
    y_att_pixel = SelectionCallbackProperty(docstring='The component ID giving the pixel component '
                                                       'shown on the y axis')
    x_att = DDSCProperty(docstring='The attribute to use on the x-axis')
    y_att = SelectionCallbackProperty(docstring='The attribute to use on the y-axis')

    # reference_data = DDSCProperty(docstring='The dataset that is used to define the '
    #                                         'available pixel/world components, and '
    #                                         'which defines the coordinate frame in '
    #                                         'which the images are shown')

    def __init__(self, *args, **kwargs):
        super(SunPyProfileViewerState, self).__init__(*args, **kwargs)

        self._x_att_helper = ComponentIDComboHelper(self, 'x_att')
        # self._y_att_helper = ComponentIDComboHelper(self, 'y_att')

        self.add_callback('layers', self._on_layers_change)
        self.add_callback('x_att', self._on_attribute_change)
        # self.add_callback('y_att', self._on_attribute_change)

        # self.add_callback('y_att', self._on_attribute_change)
        # self.add_callback('z_att', self._on_attribute_change)

    def _on_layers_change(self, value):
        # self.layers_data is a shortcut for
        # [layer_state.layer for layer_state in self.layers]
        self._x_att_helper.set_multiple_data(self.layers_data)

        # self._y_att_helper.set_multiple_data(self.layers_data)
        # self._z_att_helper.set_multiple_data(self.layers_data)

    def _on_attribute_change(self, value):
        self.x_axislabel = 'Wavelength'

        self.y_axislabel = 'Data values'


class SunPyProfileLayerState(MatplotlibLayerState):
    fill = CallbackProperty(False, docstring='Whether to show the markers as filled or not')
    color = CallbackProperty(docstring='The color used to display the data')
    alpha = CallbackProperty(docstring='The transparency used to display the data')

    def __init__(self, viewer_state=None, **kwargs):
        super(SunPyProfileLayerState, self).__init__(viewer_state=viewer_state, **kwargs)

        self.color = self.layer.style.color
        self.alpha = self.layer.style.alpha

        self._sync_color = keep_in_sync(self, 'color', self.layer.style, 'color')
        self._sync_alpha = keep_in_sync(self, 'alpha', self.layer.style, 'alpha')


class SunPyProfileLayerArtist(MatplotlibLayerArtist):
    _layer_state_cls = SunPyProfileLayerState

    def __init__(self, axes, *args, **kwargs):

        super(SunPyProfileLayerArtist, self).__init__(axes, *args, **kwargs)

        self.axes = axes

        # self.reference_data

        print('1', self.layer)
        print('2', type(self.layer))

        print('3', self.layer.data)
        print('4', type(self.layer.data))

        print('5', self.layer.meta)
        print('6', type(self.layer.meta))

        self.artist = self.axes.plot([], [], '-', mec='none', color=self.state.layer.style.color)[0]

        self.state.add_callback('fill', self._on_visual_change)
        self.state.add_callback('visible', self._on_visual_change)
        self.state.add_callback('zorder', self._on_visual_change)
        self.state.add_callback('color', self._on_visual_change)
        self.state.add_callback('alpha', self._on_visual_change)

        self._viewer_state.add_callback('x_att', self._on_attribute_change)
        # self._viewer_state.add_callback('y_att', self._on_attribute_change)
        # self._viewer_state.add_callback('z_att', self._on_attribute_change)

    def _on_visual_change(self, value=None):

        self.artist.set_visible(self.state.visible)
        self.artist.set_zorder(self.state.zorder)
        # self.artist.set_markeredgecolor(self.state.color)
        # if self.state.fill:
        #     self.artist.set_markerfacecolor(self.state.color)
        # else:
        #     self.artist.set_markerfacecolor('blue')
        self.artist.set_alpha(self.state.alpha)

        self.redraw()

    def _on_attribute_change(self, value=None):

        # if self._viewer_state.x_att is None:
        #     return

        # x = self.state.layer[self._viewer_state.x_att]
        # print('self._viewer_state.x_att', self._viewer_state.x_att)

        print('self.layer', self.layer)

        x_labels = self.layer.coordinate_components
        # x = self._viewer_state.x_att

        wcs = self.layer.coords
        print('wcs', wcs)

        data_raw = self.layer.data
        print('data_raw', data_raw)

        xid = x_labels[-1]

        x = np.array(data_raw[xid], dtype=float)
        print('x.shape', x.shape)

        x = x[0]
        print('x', x)

        wcs_axis_dropped = drop_axis(wcs=wcs,dropax=0)
        print('wcs_axis_dropped', wcs_axis_dropped)

        print('x_labels', x_labels)

        y_labels = self.layer.data.main_components

        yid = self.layer.data.main_components[0]
        y = np.array(data_raw[yid], dtype=float)
        print('y.shape', y.shape)

        y = y[0]
        print('y', y)

        print('len(y)', len(y))
        print('y_labels', y_labels)

        # y = self.state.layer[self._viewer_state.y_att]

        self.artist.set_data(x, y)

        self.axes.set_xlim(np.nanmin(x), np.nanmax(x))
        self.axes.set_ylim(np.nanmin(y), np.nanmax(y))

        self.redraw()

    def clear(self):
        self.artist.set_visible(False)

    def remove(self):
        self.artist.remove()

    def redraw(self):
        self.axes.figure.canvas.draw_idle()

    def update(self):
        self._on_attribute_change()
        self._on_visual_change()


class SunPyProfileViewerStateWidget(QWidget):

    def __init__(self, viewer_state=None, session=None):

        super(SunPyProfileViewerStateWidget, self).__init__()

        self.ui = load_ui('viewer_state.ui', self,
                          directory=os.path.dirname(__file__))

        self.viewer_state = viewer_state
        self._connections = autoconnect_callbacks_to_qt(self.viewer_state, self.ui)


class SunPyProfileLayerStateWidget(QWidget):

    def __init__(self, layer_artist):

        super(SunPyProfileLayerStateWidget, self).__init__()

        # self.checkbox = QCheckBox('Fill markers')
        layout = QVBoxLayout()
        # layout.addWidget(self.checkbox)
        self.setLayout(layout)

        self.layer_state = layer_artist.state
        # connect_checkable_button(self.layer_state, 'fill', self.checkbox)


class SunPyMatplotlibProfileMixin(object):

    def setup_callbacks(self):
        self.state.add_callback('x_att', self._update_axes)
        self.state.add_callback('y_att', self._update_axes)

    def _update_axes(self, *args):

        if self.state.x_att is not None:
            self.state.x_axislabel = 'Wavelength'

        self.state.y_axislabel = 'Data values'

        self.axes.figure.canvas.draw_idle()

    # def apply_roi(self, roi, override_mode=None):

        # Force redraw to get rid of ROI. We do this because applying the
        # subset state below might end up not having an effect on the viewer,
        # for example there may not be any layers, or the active subset may not
        # be one of the layers. So we just explicitly redraw here to make sure
        # a redraw will happen after this method is called.

        # self.redraw()
        #
        # if len(self.layers) == 0:
        #     return
        #
        # subset_state = roi_to_subset_state(roi, x_att=self.state.x_att)
        # self.apply_subset_state(subset_state, override_mode=override_mode)


@decorate_all_methods(defer_draw)
class SunPyProfileDataViewer(SunPyMatplotlibProfileMixin, MatplotlibDataViewer):

    LABEL = 'SunPy 1D Profile'
    _state_cls = SunPyProfileViewerState
    _options_cls = SunPyProfileViewerStateWidget
    _layer_style_widget_cls = SunPyProfileLayerStateWidget
    _data_artist_cls = SunPyProfileLayerArtist
    _subset_artist_cls = SunPyProfileLayerArtist

    large_data_size = 1e8

    allow_duplicate_data = True

    tools = ['select:xrange', 'profile-analysis']

    def __init__(self, session, parent=None, wcs=None, state=None):
        MatplotlibDataViewer.__init__(self, session, parent=parent, wcs=wcs, state=state)
        SunPyMatplotlibProfileMixin.setup_callbacks(self)


qt_client.add(SunPyProfileDataViewer)
