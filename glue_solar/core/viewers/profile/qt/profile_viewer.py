# Experimenting with implementing a basic glue viewer for SunPy maps

import os
import copy

from glue.utils import defer_draw, decorate_all_methods

from astropy.wcs import WCS

import numpy as np

from echo import delay_callback
from echo import (CallbackProperty, SelectionCallbackProperty,
                  keep_in_sync)
from echo.qt import (connect_checkable_button,
                     autoconnect_callbacks_to_qt)


from qtpy.QtWidgets import QWidget, QVBoxLayout, QCheckBox
from glue.core.data_derived import DerivedData, IndexedData
from glue.core.data_combo_helper import ComponentIDComboHelper, ManualDataComboHelper

from glue.viewers.matplotlib.layer_artist import MatplotlibLayerArtist
from glue.viewers.matplotlib.state import (MatplotlibDataViewerState,
                                           MatplotlibLayerState,
                                           DeferredDrawCallbackProperty as DDCProperty,
                                           DeferredDrawSelectionCallbackProperty as DDSCProperty)
from glue.viewers.matplotlib.qt.data_viewer import MatplotlibDataViewer
from glue.core.subset import roi_to_subset_state
from glue.utils.qt import load_ui
from glue.config import qt_client
from astropy.wcs.wcsapi import SlicedLowLevelWCS

# __all__ = ['SunPyProfileViewerState', 'SunPyProfileLayerState', 'SunPyProfileLayerArtist',
#            'SunPyProfileViewerStateWidget', 'SunPyProfileLayerStateWidget',
#            'SunPyProfileDataViewer', 'SunPyMatplotlibProfileMixin']


class SunPyProfileViewerState(MatplotlibDataViewerState):
    x_att_pixel = DDSCProperty(docstring='The component ID giving the pixel component '
                                         'shown on the x axis')

    x_att = DDSCProperty(docstring='The attribute to use on the x-axis')

    reference_data = DDSCProperty(docstring='The dataset that is used to define the '
                                            'available pixel/world components, and '
                                            'which defines the coordinate frame in '
                                            'which the images are shown')

    def __init__(self, *args, **kwargs):
        super(SunPyProfileViewerState, self).__init__(*args, **kwargs)

        self.ref_data_helper = ManualDataComboHelper(self, 'reference_data')

        self.add_callback('layers', self._layers_changed)
        self.add_callback('reference_data', self._reference_data_changed)
        self.add_callback('x_att', self._on_attribute_change)

        self.x_att_helper = ComponentIDComboHelper(self, 'x_att',
                                                   numeric=False, datetime=False, categorical=False,
                                                   pixel_coord=True)

    def _update_combo_ref_data(self):
        self.ref_data_helper.set_multiple_data(self.layers_data)

    @property
    def _display_world(self):
        return getattr(self.reference_data, 'coords', None) is not None

    def _on_attribute_change(self, value):
        self.x_axislabel = 'Wavelength'

        self.y_axislabel = 'Data values'

    @defer_draw
    def _layers_changed(self, *args):
        self._update_combo_ref_data()

    @defer_draw
    def _reference_data_changed(self, *args):
        # This signal can get emitted if just the choices but not the actual
        # reference data change, so we check here that the reference data has
        # actually changed

        if self.reference_data is not getattr(self, '_last_reference_data', None):
            self._last_reference_data = self.reference_data

            with delay_callback(self, 'x_att'):

                if self.reference_data is None:
                    self.x_att_helper.set_multiple_data([])
                else:
                    self.x_att_helper.set_multiple_data([self.reference_data])
                    if self._display_world:
                        self.x_att_helper.world_coord = True
                        self.x_att = self.reference_data.world_component_ids[0]
                    else:
                        self.x_att_helper.world_coord = False
                        self.x_att = self.reference_data.pixel_component_ids[0]


class SunPyProfileLayerState(MatplotlibLayerState):
    color = DDCProperty(docstring='The color used to display the data')
    alpha = DDCProperty(docstring='The transparency used to display the data')

    attribute = DDSCProperty(docstring='The attribute shown in the layer')

    def __init__(self, layer=None, viewer_state=None, **kwargs):
        super(SunPyProfileLayerState, self).__init__(layer=layer, viewer_state=viewer_state, **kwargs)

        self.attribute_att_helper = ComponentIDComboHelper(self, 'attribute',
                                                           numeric=True, categorical=False)

        self.color = self.layer.style.color
        self.alpha = self.layer.style.alpha

        self._sync_color = keep_in_sync(self, 'color', self.layer.style, 'color')
        self._sync_alpha = keep_in_sync(self, 'alpha', self.layer.style, 'alpha')

        self.add_callback('layer', self._update_attribute)

        if layer is not None:
            self._update_attribute()

    def _update_attribute(self, *args):
        if self.layer is not None:
            self.attribute_att_helper.set_multiple_data([self.layer])


class SunPyProfileLayerArtist(MatplotlibLayerArtist):
    _layer_state_cls = SunPyProfileLayerState

    def __init__(self, axes, *args, **kwargs):

        super(SunPyProfileLayerArtist, self).__init__(axes, *args, **kwargs)

        self.axes = axes

        self.artist = self.axes.plot([], [], '-', mec='none', color=self.state.layer.style.color)[0]

        self.state.add_callback('visible', self._on_visual_change)
        self.state.add_callback('zorder', self._on_visual_change)
        self.state.add_callback('color', self._on_visual_change)
        self.state.add_callback('alpha', self._on_visual_change)

        self._viewer_state.add_callback('x_att', self._on_attribute_change)

    def _on_visual_change(self, value=None):

        self.artist.set_visible(self.state.visible)
        self.artist.set_zorder(self.state.zorder)

        self.artist.set_alpha(self.state.alpha)

        self.redraw()

    def _on_attribute_change(self, value=None):

        if extracted_indices is not None:
            print('extracted_indices', extracted_indices)

        xi = extracted_indices[0]
        yi = extracted_indices[1]
        zi = extracted_indices[2]

        if self._viewer_state is not None:
            print('self._viewer_state', self._viewer_state)

        print('self.layer', self.layer)

        x_labels = self.layer.coordinate_components

        wcs = self.layer.coords
        print('wcs', wcs)

        data_raw = self.layer.data
        print('data_raw', data_raw)

        xid = x_labels[-1]
        x = np.array(data_raw[xid], dtype=float)
        print('x.shape', x.shape)

        x = x[xi, yi, :]
        print('x', x)

        print('x_labels', x_labels)

        y_labels = self.layer.data.main_components

        yid = self.layer.data.main_components[0]
        y = np.array(data_raw[yid], dtype=float)
        print('y.shape', y.shape)

        y = y[xi, yi, :]
        print('y', y)

        print('y_labels', y_labels)

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

    def __init__(self, viewer_state, session=None):

        super(SunPyProfileViewerStateWidget, self).__init__()

        self.ui = load_ui('viewer_state.ui', self,
                          directory=os.path.dirname(__file__))

        self._connections = autoconnect_callbacks_to_qt(viewer_state, self.ui)
        self.viewer_state = viewer_state

        self.session = session

        print('self.session', self.session)
        print('self.session.data_collection', self.session.data_collection)

        for dataset in self.session.data_collection:
            if isinstance(dataset, IndexedData):
                print(dataset.indices)
                self.indices = dataset.indices

        global extracted_indices
        extracted_indices = copy.deepcopy(self.indices)


class SunPyProfileLayerStateWidget(QWidget):

    def __init__(self, layer_artist):

        super(SunPyProfileLayerStateWidget, self).__init__()

        layout = QVBoxLayout()
        # layout.addWidget(self.checkbox)
        self.setLayout(layout)

        self.layer_state = layer_artist.state


class SunPyMatplotlibProfileMixin(object):

    def setup_callbacks(self):
        self.state.add_callback('x_att', self._update_axes)

    def _update_axes(self, *args):

        if self.state.x_att is not None:
            self.state.x_axislabel = 'Wavelength'

        self.state.y_axislabel = 'Data values'

        self.axes.figure.canvas.draw_idle()


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

    def __init__(self, session, parent=None, state=None):
        MatplotlibDataViewer.__init__(self, session, parent=parent, wcs=True, state=state)
        SunPyMatplotlibProfileMixin.setup_callbacks(self)


qt_client.add(SunPyProfileDataViewer)
