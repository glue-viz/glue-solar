"""Refresh regressions; run with WP1 and the prototype root on sys.path."""
from types import SimpleNamespace

import numpy as np
import pytest
from glue.core import Data, DataCollection
from glue.core.link_helpers import LinkSame
from glue_qt.app import GlueApplication
from glue_qt.viewers.image import ImageViewer

from wp4_common import add_time, nearest, observation_key, slit_x, sync_slices


def test_nearest_validates_times_and_keeps_documented_clamping():
    reference = np.array(['2020-01-01T00:00:10', '2020-01-01T00:00:20'], dtype='datetime64[s]')
    query = reference[0] + np.array([-20, 5, 30], dtype='timedelta64[s]')
    np.testing.assert_array_equal(nearest(query, reference), [0, 0, 1])
    for bad in (reference[::-1], reference[:0], np.array(['NaT'], dtype='datetime64[s]')):
        with pytest.raises(ValueError):
            nearest(query, bad)
    with pytest.raises(ValueError):
        nearest(np.array(['NaT'], dtype='datetime64[s]'), reference)


def test_slit_requires_explicit_decimation():
    positions = np.array([150., 160.])  # outside this image is a valid result, not evidence of decimation
    cube = SimpleNamespace(data=np.zeros((2, 20, 20)), extra_coords={
        'slit x position': SimpleNamespace(wcs=SimpleNamespace(pixel_to_world_values=lambda pixel: positions)),
    })
    np.testing.assert_array_equal(slit_x(cube), positions)
    np.testing.assert_array_equal(slit_x(cube, pixel_stride=10), positions / 10)
    with pytest.raises(ValueError):
        slit_x(cube, pixel_stride=0)


def test_pairing_requires_observation_start():
    data = Data(x=[1]); other = Data(x=[2])
    data.meta.update(OBSID=123, STARTOBS='2020-01-01T00:00:00')
    other.meta.update(OBSID=123, STARTOBS='2020-01-02T00:00:00')
    assert observation_key(data) != observation_key(other)
    other.meta.clear()
    assert observation_key(other) is None


def test_current_time_component_is_not_duplicated(monkeypatch):
    import wp4_common
    data = Data(flux=np.zeros((2, 3, 4)), Time=np.zeros((2, 3, 4)))
    cube = SimpleNamespace(data=np.zeros((2, 3, 4)), shape=(2, 3, 4))
    monkeypatch.setattr(wp4_common, 'cube_times', lambda cube: np.array(['2020-01-01', '2020-01-02'], dtype='datetime64[D]'))
    before = list(data.components)
    add_time(data, cube)
    assert data.components == before


def test_slider_sync_cleans_up_closed_viewers(qtbot):
    data = Data(flux=np.zeros((3, 4, 5)))
    app = GlueApplication(DataCollection([data])); qtbot.addWidget(app)
    first = app.new_data_viewer(ImageViewer, data=data)
    hook = sync_slices(app)
    second = app.new_data_viewer(ImageViewer, data=data)
    first.state.slices = (2, 0, 0)
    assert second.state.slices[0] == 2
    second.close(warn=False)
    assert second.state not in hook(None)
    first.state.slices = (1, 0, 0)
    first.close(warn=False)
    assert hook(None) == {}


def test_blink_close_restores_original_visibility(qtbot):
    from wp5_blink import BlinkTool
    datasets = [Data(label=str(i), flux=np.ones((3, 3))) for i in range(3)]
    dc = DataCollection(datasets)
    for other in datasets[1:]:
        dc.add_link([LinkSame(x, y) for x, y in zip(datasets[0].pixel_component_ids, other.pixel_component_ids)])
    app = GlueApplication(dc); qtbot.addWidget(app)
    viewer = app.new_data_viewer(ImageViewer, data=datasets[0])
    for data in datasets[1:]:
        viewer.add_data(data)
    viewer.layers[2].state.visible = False
    tool = viewer.toolbar.tools[BlinkTool.tool_id]
    tool.activate()
    assert sum(layer.state.visible for layer in viewer.layers) == 1
    tool.close()
    assert not tool._timer.isActive()
    assert [layer.state.visible for layer in viewer.layers] == [True, True, False]
    viewer.close(warn=False)
