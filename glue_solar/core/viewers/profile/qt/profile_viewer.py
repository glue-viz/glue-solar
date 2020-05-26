# Experimenting with implementing a basic glue viewer for SunPy maps

# from glue.core.subset import roi_to_subset_state
# from glue.core.coordinates import Coordinates, LegacyCoordinates
# from glue.core.coordinate_helpers import dependent_axes
#
# from glue.viewers.profile.layer_artist import ProfileLayerArtist
# from glue.viewers.image.layer_artist import ImageLayerArtist, ImageSubsetLayerArtist
# from glue.viewers.image.compat import update_image_viewer_state
#
# from glue.viewers.image.frb_artist import imshow
# from glue.viewers.image.composite_array import CompositeArray

import os

from astropy.wcs import WCS

import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib import pyplot as plt
from qtpy.QtWidgets import QWidget, QVBoxLayout, QCheckBox

from glue.core.data_combo_helper import ComponentIDComboHelper

from glue.external.echo import (CallbackProperty, SelectionCallbackProperty,
                                keep_in_sync)
from glue.external.echo.qt import (connect_checkable_button,
                                   autoconnect_callbacks_to_qt)

from glue.viewers.common.layer_artist import LayerArtist
from glue.viewers.common.state import ViewerState, LayerState
from glue.viewers.common.qt.data_viewer import DataViewer

from glue.utils.qt import load_ui

from glue.config import qt_client

__all__ = ['SunPyViewerState', '']


def get_identity_wcs(naxis):

    wcs = WCS(naxis=naxis)
    wcs.wcs.ctype = ['X'] * naxis
    wcs.wcs.crval = [0.] * naxis
    wcs.wcs.crpix = [1.] * naxis
    wcs.wcs.cdelt = [1.] * naxis

    return wcs


class SunPyViewerState(ViewerState):
    x_att_pixel = SelectionCallbackProperty(docstring='The component ID giving the pixel component '
                                                      'shown on the x axis')
    y_att_pixel = SelectionCallbackProperty(docstring='The component ID giving the pixel component '
                                                      'shown on the y axis')
    x_att = SelectionCallbackProperty(docstring='The attribute to use on the x-axis')
    y_att = SelectionCallbackProperty(docstring='The attribute to use on the y-axis')

    def __init__(self, *args, **kwargs):
        super(SunPyViewerState, self).__init__(*args, **kwargs)
        self._x_att_helper = ComponentIDComboHelper(self, 'x_att', numeric=False, datetime=False,
                                                    categorical=False, pixel_coord=True)
        self._y_att_helper = ComponentIDComboHelper(self, 'y_att', numeric=False, datetime=False,
                                                    categorical=False, pixel_coord=True)
        self.add_callback('layers', self._on_layers_change)

        self.layers_data = [layer_state.layer for layer_state in self.layers]

    def _on_layers_change(self, value):
        # self.layers_data is a shortcut for
        # [layer_state.layer for layer_state in self.layers]

        self._x_att_helper.set_multiple_data(self.layers_data)
        self._y_att_helper.set_multiple_data(self.layers_data)

    @property
    def layers_data(self):
        return self._layers_data

    @layers_data.setter
    def layers_data(self, value):
        self._layers_data = value


class SunPyLayerState(LayerState):
    fill = CallbackProperty(False, docstring='Whether to show the markers as filled or not')
    color = CallbackProperty(docstring='The color used to display the data')
    alpha = CallbackProperty(docstring='The transparency used to display the data')

    def __init__(self, viewer_state=None, **kwargs):
        super(SunPyLayerState, self).__init__(viewer_state=viewer_state, **kwargs)

        self.color = self.layer.style.color
        self.alpha = self.layer.style.alpha

        self._sync_color = keep_in_sync(self, 'color', self.layer.style, 'color')
        self._sync_alpha = keep_in_sync(self, 'alpha', self.layer.style, 'alpha')


class SunPyLayerArtist(LayerArtist):

    _layer_state_cls = SunPyLayerState

    def __init__(self, axes, *args, **kwargs):

        super(SunPyLayerArtist, self).__init__(*args, **kwargs)

        self.axes = axes

        self.artist = self.axes.plot([], [], 'o', color=self.state.layer.style.color)[0]

        self.state.add_callback('fill', self._on_fill_change)
        self.state.add_callback('visible', self._on_visible_change)
        self.state.add_callback('zorder', self._on_zorder_change)
        self.state.add_callback('color', self._on_color_change)
        self.state.add_callback('alpha', self._on_alpha_change)

        self._viewer_state.add_callback('x_att', self._on_attribute_change)
        self._viewer_state.add_callback('y_att', self._on_attribute_change)

    def _on_fill_change(self, value=None):
        if self.state.fill:
            self.artist.set_markerfacecolor(self.state.layer.style.color)
        else:
            self.artist.set_markerfacecolor('none')
        self.redraw()

    def _on_visible_change(self, value=None):
        self.artist.set_visible(self.state.visible)
        self.redraw()

    def _on_zorder_change(self, value=None):
        self.artist.set_zorder(self.state.zorder)
        self.redraw()

    def _on_color_change(self, value=None):
        self.artist.set_color(self.state.color)
        self.redraw()

    def _on_alpha_change(self, value=None):
        self.artist.set_alpha(self.state.alpha)
        self.redraw()

    def _on_attribute_change(self, value=None):

        if self._viewer_state.x_att is None or self._viewer_state.y_att is None:
            return

        x = self.state.layer[self._viewer_state.x_att]
        y = self.state.layer[self._viewer_state.y_att]

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
        self._on_fill_change()
        self._on_attribute_change()


class SunPyViewerStateWidget(QWidget):

    def __init__(self, viewer_state=None, session=None):

        super(SunPyViewerStateWidget, self).__init__()

        self.ui = load_ui('viewer_state.ui', self,
                          directory=os.path.dirname(__file__))

        self.viewer_state = viewer_state
        self._connections = autoconnect_callbacks_to_qt(self.viewer_state, self.ui)


class SunPyLayerStateWidget(QWidget):

    def __init__(self, layer_artist):

        super(SunPyLayerStateWidget, self).__init__()

        self.checkbox = QCheckBox('Fill markers')
        layout = QVBoxLayout()
        layout.addWidget(self.checkbox)
        self.setLayout(layout)

        self.layer_state = layer_artist.state
        connect_checkable_button(self.layer_state, 'fill', self.checkbox)


class SunPyDataViewer(DataViewer):

    LABEL = 'SunPy 1D Viewer'
    _state_cls = SunPyViewerState
    _options_cls = SunPyViewerStateWidget
    _layer_style_widget_cls = SunPyLayerStateWidget
    _data_artist_cls = SunPyLayerArtist
    _subset_artist_cls = SunPyLayerArtist

    def __init__(self, *args, **kwargs):
        super(SunPyDataViewer, self).__init__(*args, **kwargs)
        self.axes = plt.subplot(1, 1, 1)
        # self.setCentralWidget(self.axes.figure.canvas)

    def get_layer_artist(self, cls, layer=None, layer_state=None):
        return cls(self.axes, self.state, layer=layer, layer_state=layer_state)


qt_client.add(SunPyDataViewer)
