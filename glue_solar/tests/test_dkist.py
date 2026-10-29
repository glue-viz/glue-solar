"""
DKIST Level 1 datasets opened from their ASDF files (D102): dkist's test datasets, an ASDF file alone or its small ViSP
raster with its FITS files, and its sample data, downloaded; sessions of them.
"""

import gc
import gzip
import re
import shutil
import threading
import time
import weakref
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import create_autospec

import dask.array as da
import numpy as np
import pytest
from glue.config import settings
from glue.core import DataCollection
from glue.core.autolinking import find_possible_links
from glue.core.command import ApplySubsetState
from glue.core.component import DaskComponent
from glue.core.data import Data
from glue.core.data_factories import load_data
from glue.core.exceptions import IncompatibleAttribute
from glue.core.state import GlueSerializeError, GlueSerializer, GlueUnSerializer
from glue.dialogs.link_editor.state import LinkEditorState
from glue.plugins.wcs_autolinking.wcs_autolinking import IncompatibleWCS, WCSLink
from glue.viewers.image.layer_artist import ImageLayerArtist
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
from glue_qt.viewers.common.data_slice_widget import SliceWidget
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer
from qtpy import QtWidgets
from qtpy.QtWidgets import QCheckBox, QDialog, QListWidget

import astropy.units as u
from astropy.coordinates import SkyCoord, SpectralCoord, StokesCoord
from astropy.io import fits
from astropy.stats import mad_std
from astropy.time import Time
from astropy.wcs.utils import pixel_to_pixel

from glue_solar import glue_patches
from glue_solar.conftest import find_irispy_test_file, int16_copy
from glue_solar.quicklook import _lon_lat, _times, coordinator, quicklook
from glue_solar.regrid import regrid_on_time
from glue_solar.sources.dkist import DKISTData, GlueWCS, _data, _glue_order, _SlitAt, _SlitPlace, dkist_data
from glue_solar.sources.iris import frame_quality_dkist, link_iris
from glue_solar.sources.loaders.iris import image_data
from glue_solar.sources.sst import sst_data
from glue_solar.tests.helpers import mouse, restore, shift
from glue_solar.tests.test_lazy import SJI
from glue_solar.tests.test_quicklook import bare_app_for, point_window, rows, slide
from glue_solar.tests.test_regrid import known_times, with_times
from glue_solar.tests.test_sst import write_sst_cube


def asdf_alone(tmp_path, name):
    """dkist's test dataset ``name``, its ASDF file without its FITS files, unzipped into ``tmp_path``."""
    from dkist.data.test import rootdir

    path = tmp_path / f"{name}.asdf"
    with gzip.open(Path(rootdir, f"{name}.asdf.gz")) as source, path.open("wb") as target:
        shutil.copyfileobj(source, target)
    return path


def small_visp():
    """dkist's test ViSP raster of (step, slit, wavelength) 3 by 10 by 25, with its FITS files."""
    from dkist.data.test import rootdir

    return Path(rootdir, "small_visp", "test_visp.asdf")


# dkist's small ViSP raster is dated 2044, which ERFA warns of
small_visp_dated_2044 = pytest.mark.filterwarnings("ignore:ERFA function.*dubious year")


def labels(data):
    return [cid.label for cid in data.world_component_ids]


def point(data, at, other):
    """The pixel of ``other`` that a Pixel point at pixel ``at`` of ``data`` reaches, as glue places it."""
    return PixelSubsetState(data, [slice(i, i + 1) for i in at])._to_linked_pixel_coords(other)


def drawn_over(app, reference, other, y=None, x=None):
    """Whether ``other`` draws over ``reference`` in an Image viewer of ``reference``, along its axes ``y``, ``x``."""
    viewer = app.new_data_viewer(ImageViewer, data=reference)
    if y is not None:
        viewer.state.y_att = reference.pixel_component_ids[y]
    if x is not None:
        viewer.state.x_att = reference.pixel_component_ids[x]
    viewer.add_data(other)
    viewer.figure.canvas.draw()
    return all(layer.enabled for layer in viewer.layers)


def test_dkist_datasets_open_with_a_world_axis_per_array_axis(tmp_path):
    import dkist

    path = asdf_alone(tmp_path, "croppable_visp")
    with pytest.warns(UserWarning, match=re.escape(f"VISP BKEWK: 0 of 2752 files are in {tmp_path}; dkist reads")):
        visp = load_data(str(path))
    assert isinstance(visp, DKISTData)
    assert (visp.label, visp._load_log.path) == ("VISP BKEWK", str(path))
    # Stokes, raster step, wavelength and slit: the step's longitude, as the raster scans; its time no attribute
    assert labels(visp) == ["Stokes", "Helioprojective Longitude", "Wavelength", "Helioprojective Latitude"]
    center = tuple(n // 2 for n in visp.shape)
    lon = dkist.load_dataset(path).wcs.pixel_to_world_values(*center[::-1])[0]
    assert visp[visp.world_component_ids[1], center] == pytest.approx(lon - 1296000)  # -408", not 359.89°
    # a Cryo-NIRSP context imager's two axes of time, its measurements and scan steps: the measurement's index
    with pytest.warns(UserWarning, match="CRYO-NIRSP BMPNP: 0 of 36 files"):
        cryo = load_data(str(asdf_alone(tmp_path, "croppable_cryo")))
    assert labels(cryo)[:3] == ["Stokes", "Time", "Measurement Number"]
    # a VBI mosaic, a dataset per tile
    with pytest.warns(UserWarning, match="VBI AJQWW: 0 of 27 files"):
        tiles = load_data(str(asdf_alone(tmp_path, "large_vbi")))
    assert [tile.label for tile in tiles] == [f"VBI AJQWW {index}" for index in np.ndindex(3, 3)]
    assert labels(tiles[4]) == ["Time", "Helioprojective Latitude", "Helioprojective Longitude"]
    # a dataset without its headers table, where its frames' times raised KeyError: 'DATE-AVG'
    with pytest.warns(UserWarning, match="VISP ADDMM: 0 of 10444 files"):
        assert load_data(str(asdf_alone(tmp_path, "visp_no_headers"))).shape == (4, 2611, 996, 2545)


def test_a_dkist_level_2_inversion_does_not_open_as_level_1(tmp_path):
    path = asdf_alone(tmp_path, "test_L2_inversion")
    # its two floats of unsigned exponent, which asdf reads as strings and refuses, re-spelled at the same length
    path.write_bytes(re.sub(rb"(value: -?[\d.]+)\de(\d)", rb"\1e+\2", path.read_bytes()))
    # where it raised KeyError: 'instrumentName'
    with pytest.raises(
        ValueError, match="test_L2_inversion.asdf is a DKIST Level 2 inversion: glue-solar opens Level 1"
    ):
        load_data(str(path))


def slit_raster(step):
    """
    A raster of 3 steps along a slit of 10 pixels of 0.5" at 25 wavelengths, stepping ``step`` arcsec west and 10 s a
    step from 2023-11-14 (unix 1.7e9 s), as a `GlueWCS` dataset: sit-and-stare where it moves less than a pixel along
    the slit.
    """
    wcs = SimpleNamespace(
        pixel_n_dim=3,
        world_n_dim=4,
        pixel_shape=None,
        pixel_bounds=None,
        world_axis_physical_types=("em.wl", "custom:pos.helioprojective.lon", "custom:pos.helioprojective.lat", "time"),
        world_axis_units=("nm", "arcsec", "arcsec", "s"),
        world_axis_names=("wavelength", "helioprojective longitude", "helioprojective latitude", "time"),
        world_axis_object_components=[(kind, 0, "value") for kind in ("wavelength", "lon", "lat", "time")],
        world_axis_object_classes={
            "wavelength": (u.Quantity, (), {"unit": "nm"}),
            "lon": (u.Quantity, (), {"unit": "arcsec"}),
            "lat": (u.Quantity, (), {"unit": "arcsec"}),
            "time": (Time, (), {"format": "unix"}),
        },
        axis_correlation_matrix=np.array([[1, 0, 0], [0, 1, 1], [0, 1, 1], [0, 0, 1]], bool),
        pixel_to_world_values=lambda x, y, z: (
            500 + 0.01 * x,
            -100 + step * z + 0 * y,
            200 + 0.5 * y + 0 * z,
            1.7e9 + 10 * z,
        ),
    )
    data = Data(label="raster", coords=GlueWCS(wcs, _glue_order(wcs, (25, 10, 3)), []))
    data.add_component(np.zeros((3, 10, 25)), "data")
    return data


@pytest.mark.parametrize(("step", "along"), [(0.01, "Time"), (0.5, "Helioprojective Longitude")])
def test_a_slit_raster_steps_through_time_where_its_pointing_stays(step, along):
    assert labels(slit_raster(step)) == [along, "Helioprojective Latitude", "Wavelength"]


def test_an_image_view_along_the_steps_or_measurements_of_a_context_image_draws(app, tmp_path):
    with pytest.warns(UserWarning, match="CRYO-NIRSP BMPNP: 0 of 36 files"):
        cryo = load_data(str(asdf_alone(tmp_path, "croppable_cryo")))
    app.data_collection.append(cryo)
    # its scan steps or measurements along y, which dkist ravels into one index of its times: each draw raised
    # ValueError, WCSAxes' frame asking below pixel -0.5 of them (D103)
    for axis in (1, 2):
        viewer = app.new_data_viewer(ImageViewer, data=cryo)
        viewer.state.y_att = cryo.pixel_component_ids[axis]
        viewer.figure.canvas.draw()
        # and panned past their last, where dkist 1.18.1 gives a NaN time too
        viewer.state.y_min, viewer.state.y_max = 3, 10
        viewer.figure.canvas.draw()
    # off them, no longitude or latitude, as dkist gives off its pointing table, and their nearest end's time
    for off, end in ((-1, 0), (3, 2)):
        lon, lat, _, when, stokes = cryo.coords.pixel_to_world_values(0, 0, off, 0, 0)
        assert np.isnan([lon, lat]).all()
        assert (when, stokes) == (cryo.coords.pixel_to_world_values(0, 0, end, 0, 0)[3], 1)


@small_visp_dated_2044
def test_a_dkist_raster_opens_its_quicklook_and_labels_its_axes(qtbot, monkeypatch):
    import dkist

    app = bare_app_for(qtbot, monkeypatch)
    data, sit_and_stare = load_data(str(small_visp())), slit_raster(0.01)
    app.data_collection.extend([data, sit_and_stare])
    # an Image viewer of a raster's steps and slit labels the world axes glue gives them: the small raster's longitude,
    # as it steps 0.06", a pixel along its slit, and a sit-and-stare raster's time
    for raster, along in ((data, "Helioprojective Longitude"), (sit_and_stare, "Time")):
        viewer = app.new_data_viewer(ImageViewer, data=raster)
        state, pixel = viewer.state, raster.pixel_component_ids
        state.x_att = pixel[0]
        viewer.figure.canvas.draw()
        coords = viewer.axes.coords
        assert state.x_att_world.label == coords[3].get_axislabel() == along
        assert state.y_att_world.label == coords[2].get_axislabel() == "Helioprojective Latitude"
    # the small raster's quicklook: map, virtual slit and the spectrum at the map's center, step 1 and slit pixel 5
    viewers = quicklook(app, [data])
    assert [[viewer.state.title for viewer in row] for row in viewers["rows"]] == [
        ["VISP qVXjk map", "VISP qVXjk virtual slit"],
        ["VISP qVXjk spectrum"],
    ]
    spectrum = viewers["spectra"][0].state.layers[0]
    qtbot.waitUntil(lambda: spectrum.profile is not None, timeout=60_000)
    dataset = dkist.load_dataset(small_visp())
    waves = dataset.wcs.pixel_to_world_values(np.arange(25), 5, 1)[0]
    np.testing.assert_allclose(spectrum.profile, [waves, np.asarray(dataset.data[1, 5])])
    # its map as IRIS's, the steps across and the slit up, where the slit was along x (D103)
    state, pixel = viewers["map"].state, data.pixel_component_ids
    assert (state.x_att, state.y_att, state.aspect) == (pixel[0], pixel[1], "auto")
    # its wavelength slider the wavelength, where glue-qt gave the raster's time, a world axis of no axis of its own
    [slider] = [slider.state for slider in viewers["map"].options_widget().slice_helper._sliders if slider]
    assert (slider.label, slider.slider_unit) == ("Wavelength", "nm")
    assert float(slider.slider_label) == pytest.approx(waves[state.slices[2]], abs=1e-3)


@small_visp_dated_2044
def test_a_sit_and_stare_raster_s_quicklook_follows_its_point(qtbot, monkeypatch):
    app = bare_app_for(qtbot, monkeypatch)
    raster, other = slit_raster(0.01), load_data(str(small_visp()))  # its slit along latitude: its longitude no axis
    app.data_collection.extend([raster, other])
    quicklook(app, [raster])
    [group] = app.session.edit_subset_mode.edit_subset
    # a click on its map, where linking points raised IndexError (D97)
    point = PixelSubsetState(raster, [slice(2, 3), slice(4, 5), slice(None)])
    app.session.command_stack.do(ApplySubsetState(data_collection=app.data_collection, subset_state=point))
    assert group.subset_state.slices == point.slices
    quicklook(app, [other])  # and another quicklook opened while it is followed


@small_visp_dated_2044
def test_a_linked_dkist_raster_s_point_moves_to_the_step_at_the_place(qtbot, monkeypatch):
    app = bare_app_for(qtbot, monkeypatch)
    first, second = load_data(str(small_visp())), load_data(str(small_visp()))
    collection = app.data_collection
    collection.extend([first, second])
    collection.add_link(WCSLink(first, second))  # as glue offers as they load
    quicklook(app, [first])
    viewers = quicklook(app, [second])
    ours, theirs = (
        next(group for group in collection.subset_groups if group.subset_state.reference_data is data)
        for data in (first, second)
    )
    app.session.edit_subset_mode.edit_subset = [ours]
    point = PixelSubsetState(first, [slice(0, 1), slice(7, 8), slice(None)])  # step 0, where the other's is 1
    app.session.command_stack.do(ApplySubsetState(data_collection=collection, subset_state=point))
    # the step whose slit passes nearest, as an IRIS point reaches it, where only its slit pixel moved (D97, D102)
    assert theirs.subset_state.slices == point.slices
    assert viewers["slit"].state.slices[0] == 0


def repeated_raster(axes):
    """
    A raster of 3 steps of 0.5" along a slit of 6 pixels of 0.5", at 5 wavelengths, in Stokes I, Q, U and V, repeated
    twice 30 s apart, of numpy ``axes`` named 'stokes', 'repeat', 'step', 'slit' and 'wave', as a `GlueWCS` dataset of
    values numbering its pixels, its pointing and time along its steps and repeats, as dkist's gWCS ravels a ViSP
    raster's repeats or Cryo-NIRSP's measurements with its steps; and its values.
    """
    sizes = {"stokes": 4, "repeat": 2, "step": 3, "slit": 6, "wave": 5}
    along = {  # each world axis's pixel axes
        "lon": ("step", "repeat", "slit"),
        "wave": ("wave",),
        "lat": ("step", "repeat", "slit"),
        "time": ("step", "repeat"),
        "stokes": ("stokes",),
    }

    def world(*pixel):
        p = dict(zip(axes[::-1], pixel))  # APE 14 order
        lon = -100 + 0.5 * p["step"] + 0.01 * p["repeat"] + 0 * p["slit"]
        lat = 200 + 0.5 * p["slit"] + 0 * p["step"] + 0 * p["repeat"]
        return lon, 500 + 0.01 * p["wave"], lat, 1.7e9 + 10 * p["step"] + 30 * p["repeat"], 1.0 + p["stokes"]

    kinds = ("custom:pos.helioprojective.lon", "em.wl", "custom:pos.helioprojective.lat", "time")
    wcs = SimpleNamespace(
        pixel_n_dim=5,
        world_n_dim=5,
        pixel_shape=None,
        pixel_bounds=None,
        world_axis_physical_types=(*kinds, "phys.polarization.stokes"),
        world_axis_units=("arcsec", "nm", "arcsec", "s", ""),
        world_axis_names=tuple(along),
        world_axis_object_components=[(name, 0, "value") for name in along],
        world_axis_object_classes={
            "lon": (u.Quantity, (), {"unit": "arcsec"}),
            "wave": (u.Quantity, (), {"unit": "nm"}),
            "lat": (u.Quantity, (), {"unit": "arcsec"}),
            "time": (Time, (), {"format": "unix"}),
            "stokes": (u.Quantity, (), {"unit": ""}),
        },
        axis_correlation_matrix=np.array([[axis in along[name] for axis in axes[::-1]] for name in along]),
        pixel_to_world_values=world,
    )
    shape = [sizes[axis] for axis in axes]
    data = Data(label="raster", coords=GlueWCS(wcs, _glue_order(wcs, shape[::-1]), []))
    values = np.arange(np.prod(shape), dtype=float).reshape(shape)
    data.add_component(values, "data")
    return data, values


@pytest.mark.parametrize(
    ("axes", "pixel"),
    [
        (("stokes", "repeat", "step", "wave", "slit"), "Stokes 0, time 1, x 1, λ 2, y 3"),  # ViSP CZKPML's
        (("stokes", "step", "repeat", "slit", "wave"), "Stokes 0, x 1, time 1, y 3, λ 2"),  # Cryo-NIRSP AIOMGG's
    ],
    ids=["visp-repeats", "cryo-nirsp-measurements"],
)
def test_a_raster_s_repeats_or_measurements_are_a_slider_in_its_quicklook(qtbot, monkeypatch, axes, pixel):
    data, values = repeated_raster(axes)
    app = bare_app_for(qtbot, monkeypatch)
    app.show()  # the map's options in sight as it opens
    # where it was refused, the pointing moving along the repeats too, the steps across and the slit up (D103)
    viewers = quicklook(app, [data])
    stokes, repeat, step, slit = map(axes.index, ("stokes", "repeat", "step", "slit"))
    state, ids = viewers["map"].state, data.pixel_component_ids
    assert (state.x_att, state.y_att, state.aspect) == (ids[step], ids[slit], "auto")
    # the repeats a slider, as Stokes, not a time axis of λ–time and light curve panels: the spectra at the point follow
    # it, named as glue labels its axis
    assert set(viewers) == {"map", "slit", "spectra", "rows"}
    slide(viewers["map"], repeat, 1)
    index = [slice(None)] * 5
    index[stokes], index[repeat], index[step], index[slit] = 0, 1, 1, 3
    spectrum, expected = viewers["spectra"][0].state.layers[0], values[tuple(index)]
    qtbot.waitUntil(
        lambda: spectrum.profile is not None and np.array_equal(spectrum.profile[1], expected), timeout=60_000
    )
    qtbot.waitUntil(lambda: rows(point_window(app))[0][1] == pixel, timeout=60_000)
    # and no slider of the axes glue showed between x and y stays over the map's options
    options = viewers["map"].options_widget()
    shown = [slider for slider in options.findChildren(SliceWidget) if slider.isVisible()]
    assert shown == [slider for slider in options.slice_helper._sliders if slider]


def test_a_point_on_a_dkist_dataset_takes_its_viewer_s_stokes_and_measurement(qtbot, monkeypatch, tmp_path):
    app = bare_app_for(qtbot, monkeypatch)
    # 'Add large data set?' to the Profile viewer; through glue's store of settings, as pytest 9.2 undoes setattr by
    # deleting what is not in an object's __dict__ (pytest #10644)
    monkeypatch.setitem(settings._members, "SHOW_LARGE_DATA_WARNING", False)
    with pytest.warns(UserWarning, match="CRYO-NIRSP BMPNP: 0 of 36 files"):
        cryo = load_data(str(asdf_alone(tmp_path, "croppable_cryo")))
    # a Cryo-NIRSP context image's Stokes parameter × 100 + scan step × 10 + measurement, as its files are not here
    index = np.arange(4)[:, None, None] * 100 + np.arange(3)[:, None] * 10 + np.arange(3)
    cid = cryo.add_component(DaskComponent(da.broadcast_to(index[..., None, None], cryo.shape)), "index")
    app.data_collection.append(cryo)
    image = app.new_data_viewer(ImageViewer, data=cryo)
    image.state.slices = (2, 0, 1, 0, 0)  # Stokes U, measurement 1
    profile = app.new_data_viewer(ProfileViewer, data=cryo)
    profile.state.x_att = cryo.pixel_component_ids[1]  # its scan steps, along which its time runs
    point = PixelSubsetState(cryo, [slice(None)] * 3 + [slice(944, 945), slice(875, 876)])
    image._session.command_stack.do(ApplySubsetState(data_collection=app.data_collection, subset_state=point))
    [group] = app.data_collection.subset_groups
    [layer] = [layer for layer in profile.state.layers if layer.layer is not cryo]
    layer.attribute = cid
    # a point at the viewer's Stokes parameter and measurement, its time profile along the steps alone, where glue's
    # spanned them and, the Profile's maximum, gave Stokes V's last measurement's (D103)
    assert group.subset_state.slices[:3] == [slice(2, 3), slice(None), slice(1, 2)]
    qtbot.waitUntil(lambda: np.array_equal(layer.profile[1], [201, 211, 221]), timeout=60_000)
    # and at the Stokes parameter and measurement the sliders move to, as the quicklook's spectra follow them
    image.state.slices = (1, 2, 2, 0, 0)
    assert group.subset_state.slices[:3] == [slice(1, 2), slice(None), slice(2, 3)]
    qtbot.waitUntil(lambda: np.array_equal(layer.profile[1], [102, 112, 122]), timeout=60_000)


def test_a_point_on_a_dkist_raster_s_default_view_keeps_its_clicked_wavelength(qtbot, monkeypatch, tmp_path):
    app = bare_app_for(qtbot, monkeypatch)
    with pytest.warns(UserWarning, match="0 of 2752 files"):
        visp = load_data(str(asdf_alone(tmp_path, "croppable_visp")))
    app.data_collection.append(visp)
    image = app.new_data_viewer(ImageViewer, data=visp)  # glue's default view: the slit across, wavelength up
    image.state.slices = (2, 100, 0, 0)  # Stokes U, step 100
    point = PixelSubsetState(visp, [slice(None), slice(None), slice(400, 401), slice(851, 852)])
    image._session.command_stack.do(ApplySubsetState(data_collection=app.data_collection, subset_state=point))
    [group] = app.data_collection.subset_groups
    # at the viewer's Stokes parameter and the clicked wavelength, its profile along the steps alone, where it spanned
    # the wavelengths too (D103)
    assert group.subset_state.slices == [slice(2, 3), slice(None), slice(400, 401), slice(851, 852)]


@small_visp_dated_2044
def test_the_point_window_gives_a_dkist_raster_s_time_and_exposure(qtbot, monkeypatch):
    import dkist

    app = bare_app_for(qtbot, monkeypatch)
    data = load_data(str(small_visp()))
    app.data_collection.append(data)
    quicklook(app, [data])
    window = point_window(app)
    window.refresh()
    # at the point's step, 1, its file's DATE-AVG and XPOSURE (ms), as IRIS data's, where both were blank (D103)
    headers = dkist.load_dataset(small_visp()).headers
    when = np.datetime_as_string(np.datetime64(headers["DATE-AVG"][1]), unit="ms")
    assert rows(window)[0][3:5] == [f"{when} UTC", f"{headers['XPOSURE'][1] / 1000:.4g} s"]


@pytest.mark.parametrize("restored", [False, True])
def test_a_dkist_dataset_s_nan_pixels_draw_transparent(app, qtbot, monkeypatch, tmp_path, restored):
    with pytest.warns(UserWarning, match="VBI AJQWW: 0 of 27 files"):
        tile = load_data(str(asdf_alone(tmp_path, "large_vbi")))[4]
    app.data_collection.append(tile)
    viewer = app.new_data_viewer(ImageViewer, data=tile)
    if restored:  # and from a session, where glue's restored layer left its image's bad color unset: opaque
        installed = ImageLayerArtist.__init__ is glue_patches.image_layer_init
        assert installed == glue_patches.needs_cmap_bad_restore_workaround()  # probes glue's own method
        assert not glue_patches.needs_cmap_bad_restore_workaround(glue_patches.image_layer_init)
        app.save_session(str(tmp_path / "nan.glu"))
        with pytest.warns(UserWarning, match="VBI AJQWW: 0 of 27 files"):
            viewer = restore(qtbot, monkeypatch, tmp_path / "nan.glu").viewers[0][0]
    # as IRIS data's: glue painted them black, so each tile of a mosaic in one viewer blackened those beneath (D103)
    assert tuple(viewer.layers[0].state.cmap_bad) == (0, 0, 0, 0)  # a list once restored
    image = viewer.axes._composite(bounds=[(-0.5, 1.5, 2), (-0.5, 1.5, 2)])  # its files are not here: NaN
    np.testing.assert_array_equal(image[0, 0], [1, 1, 1, 1])  # the white background shows through


@small_visp_dated_2044
@pytest.mark.filterwarnings("ignore:Attempting to set identical low and high xlims")  # the latitude, constant along it
def test_the_iris_lines_leave_out_a_world_axis_of_another_unit(app):
    import dkist

    # dkist's own gWCS, of more world axes than pixel axes: glue gives the wavelength axis the latitude, in arcsec
    dataset = dkist.load_dataset(small_visp())
    data = Data(label="visp", coords=dataset.wcs)
    data.add_component(dataset.data, "data")
    app.data_collection.append(data)
    viewer = app.new_data_viewer(ProfileViewer, data=data)
    viewer.state.x_att = data.world_component_ids[2]  # raised UnitConversionError in glue's callback
    assert data.get_component(viewer.state.x_att).units == "arcsec"
    assert viewer.toolbar.tools["solar:lines"].positions() == []


@pytest.mark.remote_data
def test_a_vbi_mosaic_opens_a_dataset_per_tile_with_one_set_of_color_limits(dkist_sample):
    path = dkist_sample("YCDRFH_single_mosaic.tar")
    with pytest.warns(UserWarning, match="VBI YCDRFH: 9 of 27 files"):
        tiles = load_data(path)
    limits = {
        tuple(
            tile.compute_statistic("percentile", tile.main_components[0], percentile=p, random_subset=10_000)
            for p in (0.5, 99.5)
        )
        for tile in tiles
    }
    # one pair for all, from whole frames of every tile, those of their missing files, frames 1 and 2, left out
    [(low, high)] = limits
    values = np.concatenate(
        [np.asarray(tile.get_component(tile.main_components[0]).data[0, ::8, ::8]) for tile in tiles]
    )
    assert 0.98 < np.mean((low <= values) & (values <= high)) < 1


@small_visp_dated_2044
def test_a_one_file_dkist_dataset_samples_its_whole_frame():
    import dkist
    from dkist.io import DKISTFileManager
    from dkist.io.dask.loaders import AstropyFITSLoader

    # the small raster's step 0 as dkist reads a dataset of one file, such as a VBI single-shot mosaic's tile: its frame
    # the whole array, of no file axis, and its files an array of one
    dataset = dkist.load_dataset(small_visp())[0]
    dataset._file_manager = DKISTFileManager.from_parts(
        ["0.fits"], 0, float, (1, 10, 25), loader=AstropyFITSLoader, basepath=dataset.files.basepath
    )
    data = _data(dataset, "VISP qVXjk")
    data._mosaic, data._samples = [data], {}
    # the color limits' sample spans the frame, where it took its first row only
    cid = data.main_components[0]
    for statistic in ("minimum", "maximum"):
        assert data.compute_statistic(statistic, cid, random_subset=10_000) == data.compute_statistic(statistic, cid)


def opened_files(monkeypatch):
    """The names of the FITS files astropy opens from now on, as it opens them."""
    names, open_ = [], fits.open
    monkeypatch.setattr(
        fits, "open", lambda name, *args, **kwargs: names.append(Path(name).name) or open_(name, *args, **kwargs)
    )
    return names


@small_visp_dated_2044
def test_a_dkist_dataset_reads_its_views_from_its_files_kept_open(tmp_path, monkeypatch):
    shutil.copytree(small_visp().parent, tmp_path, dirs_exist_ok=True)
    (tmp_path / "1.fits").unlink()
    with pytest.warns(UserWarning, match="2 of 3 files"):
        data = load_data(str(tmp_path / "test_visp.asdf"))
    cid, view = data.main_components[0], (slice(None), slice(2, 8), slice(None, None, -3))
    expected = np.asarray(data.get_component(cid).data[view])  # dask's
    opened = opened_files(monkeypatch)
    # as dask reads it, the missing file's step NaN, each file opened once and kept open, where dask opened each at
    # every read and decompressed it whole (D103)
    for _ in range(2):
        np.testing.assert_array_equal(data.get_data(cid, view=view), expected)
    assert np.isnan(expected[1]).all()
    assert sorted(opened) == ["0.fits", "2.fits"]
    # up to `OPEN_FILES` of them (`_open_files`)
    monkeypatch.setattr("glue_solar.sources.dkist.OPEN_FILES", 1)
    opened.clear()
    for step in (0, 2, 0):
        data.get_data(cid, view=(step,))
    assert opened == ["2.fits", "0.fits"]


@small_visp_dated_2044
def test_a_removed_dkist_dataset_closes_its_files_kept_open(tmp_path):
    from glue_solar.sources.dkist import _OPEN

    shutil.copytree(small_visp().parent, tmp_path, dirs_exist_ok=True)
    data = load_data(str(tmp_path / "test_visp.asdf"))
    collection = DataCollection([data])
    data.get_data(data.main_components[0], view=(slice(None), 0))
    paths = {str(tmp_path / f"{i}.fits") for i in range(3)}
    assert paths <= set(_OPEN)
    # as it leaves glue, not when glue quits (user, 2026-10-23), and those a profile still computing reads after
    collection.remove(data)
    assert not paths & set(_OPEN)
    data.get_data(data.main_components[0], view=(slice(None), 0))
    assert not paths & set(_OPEN)


@small_visp_dated_2044
def test_a_dkist_dataset_closes_its_files_kept_open_as_reset_session_replaces_its_window(app, qtbot, tmp_path):
    from glue_solar.sources.dkist import _OPEN

    shutil.copytree(small_visp().parent, tmp_path, dirs_exist_ok=True)
    data = load_data(str(tmp_path / "test_visp.asdf"))
    app.data_collection.append(data)
    data.get_data(data.main_components[0], view=(slice(None), 0))
    paths = {str(tmp_path / f"{i}.fits") for i in range(3)}
    assert paths <= set(_OPEN)
    # Reset Session, as Open Session and 'Restore last session', closes the window, removing no data: they stayed open
    # until glue quit (user, 2026-10-23)
    qtbot.addWidget(app._reset_session())
    assert not paths & set(_OPEN)


def test_dkist_data_keep_up_to_4096_files_open_raising_the_open_file_soft_limit(monkeypatch):
    from glue_solar.sources.dkist import OPEN_FILES, _open_files

    resource = pytest.importorskip("resource")
    assert OPEN_FILES == _open_files()
    raised = []
    monkeypatch.setattr(resource, "setrlimit", lambda kind, limits: raised.append(limits))
    # macOS's soft limit of 256 raised: 128 files reopened a ViSP map's 510 at each move (D103)
    monkeypatch.setattr(resource, "getrlimit", lambda kind: (256, resource.RLIM_INFINITY))
    assert _open_files() == 4096
    assert raised == [(8192, resource.RLIM_INFINITY)]
    # up to a hard limit of 1024, not past it
    raised.clear()
    monkeypatch.setattr(resource, "getrlimit", lambda kind: (256, 1024))
    assert _open_files() == 512
    assert raised == [(1024, 1024)]


@small_visp_dated_2044
def test_an_image_buffer_of_a_dkist_dataset_reads_only_the_files_of_the_pixels_it_samples(tmp_path, monkeypatch):
    shutil.copytree(small_visp().parent, tmp_path, dirs_exist_ok=True)
    data = load_data(str(tmp_path / "test_visp.asdf"))
    expected = np.asarray(data["data"])[::2, :, 12]
    opened = opened_files(monkeypatch)
    # steps 0 and 2 at a wavelength, as an Image viewer zoomed out samples them: glue read their bounding box, step 1's
    # file too, of a ViSP map 500 files where its view samples 34 (D103)
    buffer = data.compute_fixed_resolution_buffer([(0, 2, 2), (0, 9, 10), 12], target_cid=data.main_components[0])
    np.testing.assert_array_equal(buffer, expected)
    assert sorted(opened) == ["0.fits", "2.fits"]


@small_visp_dated_2044
def test_a_dkist_image_viewer_redraws_without_evaluating_its_coordinates_again(app, monkeypatch):
    data = load_data(str(small_visp()))
    app.data_collection.append(data)
    viewer = app.new_data_viewer(ImageViewer, data=data)
    viewer.figure.canvas.draw()
    wcs, calls = data.coords._wcs, []
    evaluate = wcs.pixel_to_world_values
    monkeypatch.setattr(wcs, "pixel_to_world_values", lambda *pixel: calls.append(pixel) or evaluate(*pixel))
    # WCSAxes asks the same pixels at each draw, which dkist evaluated again, building a model per raster step: 3 s of
    # each ViSP map's draw (D103)
    viewer.figure.canvas.draw()
    assert calls == []


@small_visp_dated_2044
def test_a_dkist_dataset_s_coordinates_evaluate_on_one_thread_at_a_time(monkeypatch):
    data = load_data(str(small_visp()))
    coords, wcs = data.coords, data.coords._wcs
    world = coords.pixel_to_world_values(1, 5, 12)
    running, overlaps = [], []

    def alone(evaluate):
        def evaluated(*values):
            overlaps.append(bool(running))
            running.append(evaluate)
            time.sleep(0.5)
            running.remove(evaluate)
            return evaluate(*values)

        return evaluated

    for name in ("pixel_to_world_values", "world_to_pixel_values"):
        monkeypatch.setattr(wcs, name, alone(getattr(wcs, name)))
    # glue-qt's profile worker beside the GUI thread: dkist's VaryingCelestialTransform sets one model's parameters at
    # each raster step, then evaluates it, so one thread's map took another's step's pointing, and GlueWCS kept it
    threads = [
        threading.Thread(target=coords.pixel_to_world_values, args=(2, 5, 12)),
        threading.Thread(target=coords.world_to_pixel_values, args=world),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert overlaps == [False, False]


@pytest.mark.remote_data
def test_a_cryo_nirsp_raster_opens_its_quicklook(qtbot, monkeypatch, dkist_sample):
    import dkist

    path = dkist_sample("DBXVEL_full.tar")
    data = load_data(path)
    # 321 steps of 0.46" across 148": the steps' longitude
    assert labels(data) == ["Helioprojective Longitude", "Helioprojective Latitude", "Wavelength"]
    app = bare_app_for(qtbot, monkeypatch)
    viewers = quicklook(app, [data])
    assert [[viewer.state.title for viewer in row] for row in viewers["rows"]] == [
        ["CRYO-NIRSP DBXVEL map", "CRYO-NIRSP DBXVEL virtual slit"],
        ["CRYO-NIRSP DBXVEL spectrum"],
    ]
    spectrum = viewers["spectra"][0].state.layers[0]
    qtbot.waitUntil(lambda: spectrum.profile is not None, timeout=60_000)
    np.testing.assert_allclose(spectrum.profile[1], np.asarray(dkist.load_dataset(path).data[160, 959]))


def test_dkist_datasets_of_different_dimensions_link_pixel_to_pixel(tmp_path):
    import dkist

    path = asdf_alone(tmp_path, "croppable_visp")
    with pytest.warns(UserWarning, match="0 of 2752 files"):
        visp = load_data(str(path))
    # its Stokes I map at one wavelength: the raster's steps and slit, of their longitude, latitude and time
    stokes_i = _data(dkist.load_dataset(path)[0, :, 400], "VISP BKEWK map")
    dc = DataCollection([visp, stokes_i])
    # glue's autolinker raised AttributeError: 'GlueWCS' object has no attribute 'has_celestial'
    [[link]] = find_possible_links(dc).values()
    assert isinstance(link, WCSLink)
    dc.add_link(link)
    # pixel to pixel along the axes those vary along (D18, D102)
    assert point(visp, (0, 200, 400, 1000), stokes_i) == [200, 1000]
    assert point(stokes_i, (200, 1000), visp) == [None, 200, None, 1000]
    assert glue_patches.needs_wcs_link_workaround() == (WCSLink.__init__ is glue_patches.wcs_link_init)
    assert not glue_patches.needs_wcs_link_workaround(glue_patches.wcs_link_init)


@pytest.mark.remote_data
# sunpy's warning of those NaN, which glue shows: pytest raised it inside the link test, which refused them
@pytest.mark.filterwarnings("ignore:The conversion of these 2D helioprojective coordinates to 3D is all NaNs")
def test_off_limb_dkist_data_of_other_dates_do_not_link(tmp_path, dkist_sample):
    with pytest.warns(UserWarning, match="CRYO-NIRSP BMPNP: 0 of 36 files"):
        cryo = load_data(str(asdf_alone(tmp_path, "croppable_cryo")))
    # 2023-01-01 and 2025-03-22: sunpy gives no longitude or latitude off the limb between their observers, and the link
    # test passed on those NaN pixels (D103)
    with pytest.raises(IncompatibleWCS):
        WCSLink(cryo, load_data(dkist_sample("DBXVEL_full.tar")))


def test_an_sst_cube_ahead_of_dkist_datasets_leaves_their_links(tmp_path, sns):
    write_sst_cube(tmp_path / "cube.fits")
    with pytest.warns(UserWarning, match="0 of 2752 files"):
        visp = load_data(str(asdf_alone(tmp_path, "croppable_visp")))
    with pytest.warns(UserWarning, match="VBI AJQWW: 0 of 27 files"):
        tiles = load_data(str(asdf_alone(tmp_path, "large_vbi")))
    # glue's WCS link read whether the DKIST dataset has celestial axes only if the cube has, and raised ValueError
    # (ViSP) or IndexError (VBI) out of glue's autolinker, which suggested no link
    [links] = find_possible_links(DataCollection([sst_data(tmp_path / "cube.fits"), visp, *tiles])).values()
    assert {frozenset((link.data1, link.data2)) for link in links} == {
        frozenset((tiles[4], tile)) for tile in tiles[:4] + tiles[5:]
    }
    # and Link Data's WCS link of a slit-jaw image and the raster, in that order, which raised ValueError: none, as their
    # times differ
    with pytest.raises(IncompatibleWCS):
        WCSLink(sns[0], visp)


def test_a_mosaic_s_tiles_link_to_its_center_tile(app, tmp_path):
    with pytest.warns(UserWarning, match="VBI AJQWW: 0 of 27 files"):
        tiles = load_data(str(asdf_alone(tmp_path, "large_vbi")))
    dc = app.data_collection
    dc.extend(tiles)
    # each to the center tile, (1, 1): glue suggested every pair's 36 links (D102)
    [links] = find_possible_links(dc).values()
    pairs = [{tiles.index(link.data1), tiles.index(link.data2)} for link in links]
    assert sorted(pairs, key=sorted) == [{k, 4} for k in range(9) if k != 4]
    dc.add_link(links)
    # a corner tile's point and image reach the opposite corner's through it
    expected = pixel_to_pixel(tiles[0].coords, tiles[8].coords, 2048, 2048, 1)[::-1]
    assert point(tiles[0], (1, 2048, 2048), tiles[8]) == np.round(expected).astype(int).tolist()
    assert drawn_over(app, tiles[8], tiles[0])


def test_dkist_data_starting_later_link_and_reach_each_other_within_their_time(app, tmp_path):
    import dkist

    path = asdf_alone(tmp_path, "large_vbi")
    with pytest.warns(UserWarning, match="VBI AJQWW: 0 of 27 files"):
        tile = load_data(str(path))[4]
    # the tile's frames 0.8 of a frame later
    dataset = dkist.load_dataset(path)[1, 1]
    temporal = dataset.wcs.forward_transform.right
    temporal.intercept = 0.8 * temporal.slope * u.pix
    later = _data(dataset, "VBI AJQWW (1, 1) later")
    later._mosaic, later._samples = [later], {}
    # linked, where their pixel 0's time lies outside the other's, as a VBI mosaic's tiles and ViSP data observed with
    # them (D103)
    dc = app.data_collection
    dc.extend([tile, later])
    dc.add_link(WCSLink(tile, later))
    assert point(later, (0, 2048, 2048), tile) == [1, 2048, 2048]
    # and a point or image at a time outside the other's reaches none of it, where dkist's inverse raised
    # NotImplementedError
    with pytest.raises(IncompatibleAttribute):
        point(tile, (0, 2048, 2048), later)
    viewer = app.new_data_viewer(ImageViewer, data=tile)
    viewer.add_data(later)
    viewer.figure.canvas.draw()


def test_dkist_data_observed_together_over_part_of_their_times_link(tmp_path):
    import dkist

    path = asdf_alone(tmp_path, "large_vbi")
    with pytest.warns(UserWarning, match="VBI AJQWW: 0 of 27 files"):
        tile = load_data(str(path))[4]
    # a copy of the tile, its frames three times as far apart: the tile's frames lie within its first third, and its
    # middle past the tile's last, where the link test, at each one's middle pixel only, refused them; and one of frames
    # a tenth as far apart from 0.3 of the tile's span, all between the tile's, where it tried forwards at the tile's
    # pixels only (D103)
    for scale, start in ((3, 0), (0.1, 0.6)):
        dataset = dkist.load_dataset(path)[1, 1]
        temporal = dataset.wcs.forward_transform.right
        temporal.slope, temporal.intercept = scale * temporal.slope, start * temporal.slope * u.pix
        WCSLink(tile, _data(dataset, f"VBI AJQWW (1, 1) x{scale}"))


def test_raveled_dkist_data_starting_later_draw_over_each_other(app, tmp_path):
    import dkist

    path = asdf_alone(tmp_path, "visp_no_headers")
    with pytest.warns(UserWarning, match="VISP ADDMM: 0 of 10444 files"):
        visp = load_data(str(path))
    # its times, which dkist ravels from its repeats and steps, a fifth of their span later
    dataset = dkist.load_dataset(path)
    [temporal] = [model for model in dataset.wcs.forward_transform.traverse_postorder() if model.name == "Temporal"]
    temporal.lookup_table = temporal.lookup_table + np.ptp(temporal.lookup_table) / 5
    later = _data(dataset, "VISP ADDMM later")
    later._mosaic, later._samples = [later], {}
    app.data_collection.extend([visp, later])
    app.data_collection.add_link(WCSLink(visp, later))
    # blank at its first frame, before the other's: dkist's inverse raised ValueError there, an Unravel of a NaN time
    assert drawn_over(app, visp, later)


def test_a_mosaic_s_tiles_link_to_its_first_tile_left_once_its_center_tile_is_removed(
    app, qtbot, monkeypatch, tmp_path
):
    with pytest.warns(UserWarning, match="VBI AJQWW: 0 of 27 files"):
        tiles = load_data(str(asdf_alone(tmp_path, "large_vbi")))
    dc = app.data_collection
    dc.extend(tiles)
    [links] = find_possible_links(dc).values()
    dc.add_link(links)
    viewer = app.new_data_viewer(ImageViewer, data=tiles[0])
    for tile in tiles[1:]:
        viewer.add_data(tile)
    dc.remove(tiles[4])
    # its first tile is their center, linked to each other tile, where every link went with the center tile and the
    # tiles' layers but the reference's were disabled (D102, user 2026-10-22)
    rest = tiles[:4] + tiles[5:]
    assert {frozenset((link.data1, link.data2)) for link in dc.external_links} == {
        frozenset((rest[0], tile)) for tile in rest[1:]
    }
    assert all(tile._center is rest[0] for tile in rest)
    assert all(layer.enabled for layer in viewer.layers)
    # and in a session
    app.save_session(str(tmp_path / "vbi.glu"))
    with pytest.warns(UserWarning, match="VBI AJQWW: 0 of 27 files"):
        again = restore(qtbot, monkeypatch, tmp_path / "vbi.glu").data_collection
    assert all(tile._center is again[0] for tile in again)
    # a mosaic not linked stays so
    with pytest.warns(UserWarning, match="VBI AJQWW: 0 of 27 files"):
        others = load_data(str(asdf_alone(tmp_path, "large_vbi")))
    dc.extend(others)
    dc.remove(others[4])
    assert len(dc.external_links) == 7


def test_link_helioprojective_coordinates_links_dkist_data_by_time(app, tmp_path, sns):
    sji, _ = sns
    with pytest.warns(UserWarning, match="VBI AJQWW: 0 of 27 files"):
        tile = load_data(str(asdf_alone(tmp_path, "large_vbi")))[4]
    with pytest.warns(UserWarning, match="0 of 2752 files"):
        visp = load_data(str(asdf_alone(tmp_path, "croppable_visp")))
    dc = app.data_collection
    dc.extend([sji, tile, visp])
    link_iris(app.session, dc)
    # a VBI point reaches the slit-jaw frame nearest it in time, its last (2021 to 2023), at its place: a DKIST
    # dataset's longitude and latitude vary with its time
    last = sji.shape[0] - 1
    lon, lat = (tile[tile.id[f"Helioprojective {name}"], (1, 2048, 2048)] for name in ("Longitude", "Latitude"))
    x, y, _ = sji.coords.world_to_pixel_values(lon, lat, sji.coords.pixel_to_world_values(0, 0, last)[2])  # arcsec
    assert point(tile, (1, 2048, 2048), sji) == [last, round(float(y)), round(float(x))]
    # and a slit-jaw point the VBI frame nearest, its first
    assert point(sji, (31, 20, 18), tile)[0] == 0
    assert drawn_over(app, tile, sji)
    assert drawn_over(app, sji, tile)
    # a scanning raster's point reaches the slit-jaw frame nearest its step in time, its last, where it was
    # incompatible (`_SlitAt`), and the slit-jaw image draws over its map, its steps by its slit
    assert point(visp, (0, 344, 488, 1277), sji)[0] == last
    assert drawn_over(app, visp, sji, y=1)


def test_link_helioprojective_coordinates_links_a_context_image_of_repeated_measurements_by_time(
    app, tmp_path, irispy_test_files
):
    with pytest.warns(UserWarning, match="CRYO-NIRSP BMPNP: 0 of 36 files"):
        cryo = load_data(str(asdf_alone(tmp_path, "croppable_cryo")))
    # a slit-jaw image of frames 100 s apart, its frame 10 at the context image's first measurement: its 3 steps are
    # 180 s apart and their 3 measurements 10 s
    path = int16_copy(find_irispy_test_file(irispy_test_files, SJI), tmp_path / SJI, [0])
    [first] = [world for world in cryo.coords.pixel_to_world(0, 0, 0, 0, 0) if isinstance(world, Time)]
    start = (first.datetime64 - np.datetime64(fits.getval(path, "STARTOBS"))) / np.timedelta64(1, "s")
    sji = image_data(with_times(path, start + 100 * (np.arange(62) - 10)))
    # its frame 12 at (20, 18) shifted onto step 1's measurement 2, 200 s after the first, as 'IRIS: shift pointing…'
    at = (0, 1, 2, 944, 875)
    sji.coords.pointing_offset = tuple(float(a - b) for a, b in zip(_lon_lat(cryo, at), _lon_lat(sji, (12, 20, 18))))
    dc = app.data_collection
    dc.extend([sji, cryo])
    link_iris(app.session, dc)
    # the step and measurement nearest the frame's time, and the frame nearest theirs, where no time was linked, as the
    # context image's time varies along both axes, and the points were incompatible
    assert point(sji, (12, 20, 18), cryo) == [None, *at[1:]]
    LinkEditorState(dc).update_links_in_collection()  # Link Data's OK, which remade the link back with one input
    assert point(cryo, at, sji) == [12, 20, 18]
    assert drawn_over(app, cryo, sji)


def test_an_iris_frame_of_no_time_reaches_no_vbi_pixel(app, tmp_path, irispy_test_files):
    path = int16_copy(find_irispy_test_file(irispy_test_files, SJI), tmp_path / SJI, [0])
    regridded = regrid_on_time(image_data(with_times(path, known_times(62, 10.0, 30))))  # frames 30 to 39 of none
    with pytest.warns(UserWarning, match="VBI AJQWW: 0 of 27 files"):
        tile = load_data(str(asdf_alone(tmp_path, "large_vbi")))[4]
    app.data_collection.extend([regridded, tile])
    link_iris(app.session, app.data_collection)
    # dkist's inverse raised NotImplementedError at a NaN time, as the frame's link gives it
    assert point(regridded, (5, 20, 18), tile)[0] == 0
    with pytest.raises(IncompatibleAttribute):
        point(regridded, (35, 20, 18), tile)
    viewer = app.new_data_viewer(ImageViewer, data=regridded)
    viewer.add_data(tile)
    viewer.state.slices = (35, 0, 0)
    viewer.figure.canvas.draw()


def viewed(app):
    """Each viewer's reference dataset, x and y attributes and slices, by tab."""

    def view(state):
        x, y = (getattr(getattr(state, att, None), "label", None) for att in ("x_att", "y_att"))
        return state.reference_data.label, x, y, tuple(getattr(state, "slices", ()))  # a restored one's are a list

    return [[view(viewer.state) for viewer in tab] for tab in app.viewers]


@small_visp_dated_2044
def test_a_session_restores_dkist_datasets_and_their_image_and_profile_viewers(app, qtbot, monkeypatch, tmp_path):
    # D102: glue saved no `GlueWCS`, of a gWCS, and restored a `DKISTData` as a Data, of glue's color limits
    from dkist.io.dask.loaders import AstropyFITSLoader

    from gwcs import WCS as GWCS

    monkeypatch.setattr(app, "report_error", lambda message, detail: pytest.fail(detail))
    visp = load_data(str(small_visp()))
    with pytest.warns(UserWarning, match="CRYO-NIRSP BMPNP: 0 of 36 files"):
        cryo = load_data(str(asdf_alone(tmp_path, "croppable_cryo")))
    app.data_collection.extend([visp, cryo])
    visp.meta["rest_wavelength"] = 6302.5  # as "Set rest wavelength…" sets it
    image = app.new_data_viewer(ImageViewer, data=visp).state
    image.x_att, image.slices = visp.pixel_component_ids[0], (1, 0, 0)
    app.new_data_viewer(ProfileViewer, data=visp)
    app.new_data_viewer(ImageViewer, data=cryo)

    def limit(data):  # the high color limit an Image layer takes
        return data.compute_statistic("percentile", data.main_components[0], percentile=99.5, random_subset=10_000)

    path = tmp_path / "dkist.glu"
    (tmp_path / "glue").mkdir()
    monkeypatch.chdir(tmp_path / "glue")  # glue's own folder, not the session's, which dkist read the files from as NaN
    app.save_session(str(path), absolute_paths=False)  # as the dialog starts with
    for _ in range(2):  # and from a restored session
        assert "GlueWCS" not in path.read_text()  # the coordinates read from the ASDF file again, not saved
        for serializer in (GlueSerializer, GlueUnSerializer):  # as a fresh glue, of no gWCS saver
            monkeypatch.delitem(serializer.dispatch._data, GWCS, raising=False)
        with pytest.warns(UserWarning, match="CRYO-NIRSP BMPNP: 0 of 36 files"):  # its ASDF file read again
            restored = restore(qtbot, monkeypatch, path)
        for data, given in zip(restored.data_collection, (visp, cryo), strict=True):
            assert type(data) is DKISTData
            assert (data.label, labels(data)) == (given.label, labels(given))
            pixels = [np.array([0, n // 2, n - 1]) for n in given.shape[::-1]]  # first, middle and last
            for got, expected in zip(
                data.coords.pixel_to_world_values(*pixels), given.coords.pixel_to_world_values(*pixels), strict=True
            ):
                np.testing.assert_array_equal(got, expected)
        data = restored.data_collection[0]
        assert dict(data.meta) == dict(visp.meta)  # its rest wavelength, and its headers' band, line and air or vacuum
        np.testing.assert_array_equal(np.asarray(data["data"]), np.asarray(visp["data"]))
        expected = np.asarray(visp["data"])[1]
        with monkeypatch.context() as patch:  # its views read from its files, as before saving, not by dask (D103)
            patch.setattr(AstropyFITSLoader, "__getitem__", lambda *args: pytest.fail("read by dask"))
            np.testing.assert_array_equal(data[data.main_components[0], 1], expected)
        assert limit(data) == limit(visp)
        assert viewed(restored) == viewed(app)
        path = tmp_path / "again.glu"
        restored.save_session(str(path))


def test_a_session_restores_a_vbi_mosaic_in_one_image_viewer_and_its_links(
    app, qtbot, monkeypatch, tmp_path, irispy_test_files
):
    monkeypatch.setattr(app, "report_error", lambda message, detail: pytest.fail(detail))
    with pytest.warns(UserWarning, match="VBI AJQWW: 0 of 27 files"):
        tiles = load_data(str(asdf_alone(tmp_path, "large_vbi")))
    name = "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits"
    sji = load_data(str(find_irispy_test_file(irispy_test_files, name)))
    dc = app.data_collection
    dc.extend([*tiles, sji])
    [links] = find_possible_links(dc).values()  # each tile to the center tile
    dc.add_link(links)
    link_iris(app.session, dc)  # and to the slit-jaw image, by position and time
    viewer = app.new_data_viewer(ImageViewer, data=tiles[4])
    for tile in tiles[:4] + tiles[5:]:
        viewer.add_data(tile)
    app.save_session(str(tmp_path / "vbi.glu"))
    with pytest.warns(UserWarning, match="VBI AJQWW: 0 of 27 files"):
        restored = restore(qtbot, monkeypatch, tmp_path / "vbi.glu")
    *again, sji_again = collection = restored.data_collection
    assert [type(tile) for tile in again] == [DKISTData] * 9
    assert len({id(tile._samples) for tile in again}) == 1  # one sample for all
    assert all(tile._center is again[4] for tile in again)  # which glue's autolinker links other data to (#373)
    assert viewed(restored) == viewed(app)
    [[state]] = [[viewer.state for viewer in tab] for tab in restored.viewers]
    assert [layer.layer.label for layer in state.layers] == [layer.layer.label for layer in viewer.state.layers]
    # #373's links: a corner tile's point reaches the opposite corner, through the center tile, and the slit-jaw image
    assert len(collection.external_links) == len(dc.external_links)
    for other, given in [(again[8], tiles[8]), (sji_again, sji)]:
        assert point(again[0], (1, 2048, 2048), other) == point(tiles[0], (1, 2048, 2048), given)


@small_visp_dated_2044
def test_a_session_restores_a_dkist_raster_s_quicklook(qtbot, monkeypatch, tmp_path):
    app = bare_app_for(qtbot, monkeypatch)
    data = load_data(str(small_visp()))
    app.data_collection.append(data)
    viewers = quicklook(app, [data])
    app.save_session(str(tmp_path / "quicklook.glu"))
    restored = restore(qtbot, monkeypatch, tmp_path / "quicklook.glu")
    again = restored.tab(1)._solar_quicklook[-1]
    assert [[viewer.state.title for viewer in row] for row in again["rows"]] == [
        ["VISP qVXjk map", "VISP qVXjk virtual slit"],
        ["VISP qVXjk spectrum"],
    ]
    spectra = [viewers["spectra"][0].state.layers[0], again["spectra"][0].state.layers[0]]
    qtbot.waitUntil(lambda: all(spectrum.profile is not None for spectrum in spectra), timeout=60_000)
    np.testing.assert_array_equal(*(spectrum.profile for spectrum in spectra))


@small_visp_dated_2044
def test_a_dkist_dataset_made_in_glue_s_terminal_fails_to_save_as_glue_s_dask_arrays_do():
    collection = DataCollection([dkist_data(str(small_visp()))])
    # where it raised AttributeError: 'DKISTData' object has no attribute '_load_log'
    with pytest.raises(GlueSerializeError, match="Don't know how to serialize"):
        GlueSerializer(collection).dumps()


@pytest.mark.parametrize(
    ("name", "at", "reached"),
    [
        # ViSP's (Stokes, step, wavelength, slit), scanning: the step whose slit passes nearest, as on an IRIS raster
        ("croppable_visp", (0, 229, 400, 851), [None, 229, None, 851]),
        # sit-and-stare: the step nearest in time, the first (2021 to 2023), and the slit pixel level with the place
        ("sit-and-stare", (1, 3, 8), [0, 3, None]),
        # Cryo-NIRSP's spectrograph sample, scanning
        pytest.param("DBXVEL_full.tar", (107, 639, 305), [107, 639, None], marks=pytest.mark.remote_data),
    ],
)
def test_iris_points_reach_a_dkist_raster_at_its_step_and_slit_pixel_and_back(
    app, tmp_path, sns, dkist_sample, name, at, reached
):
    sji, iris_raster = sns
    if name == "croppable_visp":
        with pytest.warns(UserWarning, match="0 of 2752 files"):
            raster = load_data(str(asdf_alone(tmp_path, name)))
    else:
        raster = slit_raster(0.01) if name == "sit-and-stare" else load_data(str(dkist_sample(name)))
    # the slit-jaw image's frame 10 at (20, 18) and the IRIS raster's step 5 at slit pixel 20 shifted onto the raster's
    # pixel ``at``, as 'IRIS: shift pointing…' co-aligns them
    place = _lon_lat(raster, at)
    for data, pixel in ((sji, (10, 20, 18)), (iris_raster, (5, 20, 0))):
        data.coords.pointing_offset = tuple(float(a - b) for a, b in zip(place, _lon_lat(data, pixel)))
    dc = app.data_collection
    dc.extend([sji, iris_raster, raster])
    link_iris(app.session, dc)
    # it reaches the raster, where glue inverted the raster's coordinates from one world value per axis, not its time,
    # and the point was incompatible (D102, `_SlitAt`)
    assert point(sji, (10, 20, 18), raster) == reached
    quicklook_point = PixelSubsetState(iris_raster, [slice(5, 6), slice(20, 21), slice(None)])  # at every wavelength
    assert quicklook_point._to_linked_pixel_coords(raster) == reached
    # and back: the slit-jaw frame nearest the step's time, its last, at the place, and the IRIS raster's step there
    last = sji.shape[0] - 1
    x, y, _ = sji.coords.world_to_pixel_values(*place, sji.coords.pixel_to_world_values(0, 0, last)[2])
    assert point(raster, at, sji) == [last, round(float(y)), round(float(x))]
    assert point(raster, at, iris_raster) == [5, 20, None]
    # the slit-jaw image draws over the raster's steps by its slit, a sit-and-stare's too, whose longitude glue gives
    # no axis
    assert drawn_over(app, raster, sji, *[axis for axis, pixel in enumerate(reached) if pixel is not None])
    # and the links, named as glue's Link Data dialog shows them, save in sessions
    usings = [link.get_using() for link in dc.links if isinstance(link.get_using(), (_SlitAt, _SlitPlace))]
    assert usings
    assert all(u.__name__ == ("slit_pixel" if u.slit else "nearest_step") for u in usings if isinstance(u, _SlitAt))
    for using in usings:
        restored = GlueUnSerializer.loads(GlueSerializer(using).dumps()).object("__main__")
        assert (type(restored), restored.__gluestate__(None)) == (type(using), using.__gluestate__(None))


@pytest.mark.parametrize("off", [0.49, 0.51])
@pytest.mark.parametrize(("end", "inner"), [(0, 1), (687, 686)])  # the raster's first and last steps, and the next
def test_an_iris_point_past_half_a_step_beyond_a_dkist_raster_s_end_does_not_reach_it(
    app, tmp_path, sns, end, inner, off
):
    sji, _ = sns
    with pytest.warns(UserWarning, match="0 of 2752 files"):
        raster = load_data(str(asdf_alone(tmp_path, "croppable_visp")))
    # the slit-jaw image's frame 10 at (20, 18) shifted ``off`` a step beyond step ``end``, at its first slit pixel
    edge, next_ = (np.array(_lon_lat(raster, (0, step, 400, 0))) for step in (end, inner))
    place = edge + off * (edge - next_)
    sji.coords.pointing_offset = tuple(float(a - b) for a, b in zip(place, _lon_lat(sji, (10, 20, 18))))
    app.data_collection.extend([sji, raster])
    link_iris(app.session, app.data_collection)
    # within half a step it reaches that step, and past it none, as the quicklook's no match (D7), where it reached a
    # step off the raster up to one step beyond
    if off < 0.5:
        assert point(sji, (10, 20, 18), raster) == [None, end, None, 0]
    else:
        with pytest.raises(IncompatibleAttribute):
            point(sji, (10, 20, 18), raster)


def test_an_iris_point_reaches_a_dkist_raster_with_repeats_at_the_step_whose_slit_passes_nearest(app, sns):
    sji, _ = sns
    # 3 repeats, each a step west of the last, as dkist's pointing moves along ViSP's repeats and Cryo-NIRSP's
    # measurements; the slit-jaw image's frame 10 at the time of the last repeat's step 2, its (20, 18) shifted onto
    # that repeat's step 0
    seconds = (_times(sji, None)[10] - np.datetime64(0, "s")) / np.timedelta64(1, "s")
    raster = visp_like(repeats=3, drift=0.5, start=seconds - 80)
    place = _lon_lat(raster, (0, 2, 0, 4, 0))
    sji.coords.pointing_offset = tuple(float(a - b) for a, b in zip(place, _lon_lat(sji, (10, 20, 18))))
    dc = app.data_collection
    dc.extend([sji, raster])
    link_iris(app.session, dc)
    # the step whose slit passes nearest, in the repeat nearest in time, where glue placed it by its time alone (D102)
    assert point(sji, (10, 20, 18), raster) == [None, 2, 0, 4, None]
    # and none a step east of its first, 3 slit-jaw pixels, 0.5", past half a step (D7)
    with pytest.raises(IncompatibleAttribute):
        point(sji, (10, 20, 15), raster)
    for using in [link.get_using() for link in dc.links if isinstance(link.get_using(), _SlitAt)]:  # saved in sessions
        restored = GlueUnSerializer.loads(GlueSerializer(using).dumps()).object("__main__")
        assert restored.__gluestate__(None) == using.__gluestate__(None)


def test_a_linked_dkist_raster_with_repeats_s_point_moves_to_the_step_at_the_place_at_its_repeat(qtbot, monkeypatch):
    app = bare_app_for(qtbot, monkeypatch)
    # 3 repeats, each a step west of the last, as dkist's pointing moves along ViSP's repeats and Cryo-NIRSP's
    # measurements
    first, second = (visp_like(repeats=3, drift=0.5, inverse=True) for _ in range(2))
    collection = app.data_collection
    collection.extend([first, second])
    collection.add_link(WCSLink(first, second))  # as glue offers as they load
    quicklook(app, [first])
    quicklook(app, [second])
    ours, theirs = (
        next(group for group in collection.subset_groups if group.subset_state.reference_data is data)
        for data in (first, second)
    )
    # theirs at repeat 2, step 1, then ours at repeat 0, step 2, slit pixel 4
    for group, data, at in ((theirs, second, (0, 2, 1, 5)), (ours, first, (0, 0, 2, 4))):
        app.session.edit_subset_mode.edit_subset = [group]
        point = PixelSubsetState(data, [*(slice(i, i + 1) for i in at), slice(None)])
        app.session.command_stack.do(ApplySubsetState(data_collection=collection, subset_state=point))
    # at its repeat, the step whose slit passes nearest, 0, where it kept its step 1 (D97, D102)
    assert [s.start for s in theirs.subset_state.slices] == [0, 2, 0, 4, None]


KINDS = {
    "lon": ("custom:pos.helioprojective.lon", "arcsec"),
    "lat": ("custom:pos.helioprojective.lat", "arcsec"),
    "wave": ("em.wl", "nm"),
    "time": ("time", "s"),
    "stokes": ("phys.polarization.stokes", ""),
}


def observed(label, sizes, along, world, inverse, by):
    """
    A `DKISTData` as `dkist_data` loads one, of numpy axes of ``sizes`` by name, which name its pixel axes, of values
    numbering its pixels, each world axis along its named axes ``along``: 'lon' and 'lat' (arcsec), 'wave' (nm), 'time'
    (unix s) and 'stokes', at the pixels by name ``world`` gives, and ``inverse`` the other way; each frame (its last two
    axes) of its world time; observed by ``by``, its instrument and observing program execution (D105).
    """
    axes, kinds = list(sizes), list(along)
    wcs = SimpleNamespace(
        pixel_n_dim=len(axes),
        world_n_dim=len(kinds),
        pixel_shape=None,
        pixel_bounds=None,
        world_axis_physical_types=tuple(KINDS[kind][0] for kind in kinds),
        world_axis_units=tuple(KINDS[kind][1] for kind in kinds),
        world_axis_names=tuple(kinds),
        world_axis_object_components=[(kind, 0, "value") for kind in kinds],
        world_axis_object_classes={
            kind: (Time, (), {"format": "unix"}) if kind == "time" else (u.Quantity, (), {"unit": KINDS[kind][1]})
            for kind in kinds
        },
        axis_correlation_matrix=np.array([[axis in along[kind] for axis in axes[::-1]] for kind in kinds]),
        pixel_to_world_values=lambda *pixel: tuple(world(dict(zip(axes[::-1], pixel)))[kind] for kind in kinds),
        world_to_pixel_values=lambda *values: tuple(inverse(dict(zip(kinds, values)))[axis] for axis in axes[::-1]),
    )
    shape = [sizes[axis] for axis in axes]
    data = DKISTData(label=label, coords=GlueWCS(wcs, _glue_order(wcs, shape[::-1]), axes[::-1]))
    data.add_component(np.arange(np.prod(shape), dtype=float).reshape(shape), "data")
    frames = dict(zip(axes, np.indices(shape[:-2])))
    seconds = world({axis: frames.get(axis, 0) for axis in axes})["time"]
    times = np.broadcast_to(np.datetime64(0, "ns") + (seconds * 1e9).astype("timedelta64[ns]"), shape[:-2])
    data._frames, data._present = (times, np.full(shape[:-2], 0.01)), np.ones(shape[:-2], bool)
    data._observed, data._mosaic, data._samples, data._center = by, [data], {}, data
    return data


def visp_like(repeats=1, step=0.5, drift=0, start=1.7e9, inverse=False, stokes=2, wave_start=500, spacing=0.01, **meta):
    """
    A ViSP raster of ``stokes`` Stokes parameters, I and Q as TXIPCV's 4-D by default, of 3 steps ``step`` arcsec and
    10 s apart from unix ``start`` s along a slit of 10 pixels of 0.5", at 25 wavelengths ``spacing`` nm apart from
    ``wave_start`` nm; ``repeats`` of it 30 s apart, if more than one, on an axis after Stokes, as CZKPML's, each
    ``drift`` arcsec west of the last; with ``inverse`` its inverse, which takes the step and repeat from the time, as
    dkist's gWCS; with ``meta``, its headers' keys as `dkist_data` keeps them (D107).
    """
    repeat = {"repeat": repeats} if repeats > 1 else {}
    data = observed(
        "VISP RASTER",
        {"stokes": stokes, **repeat, "step": 3, "slit": 10, "wave": 25},
        {
            "wave": ("wave",),
            "lon": ("repeat", "step", "slit") if drift else ("step", "slit"),
            "lat": ("step", "slit"),
            "time": ("repeat", "step"),
            "stokes": ("stokes",),
        },
        lambda p: {
            "wave": wave_start + spacing * p["wave"],
            "lon": -100 + step * p["step"] + drift * p.get("repeat", 0) + 0 * p["slit"],
            "lat": 200 + 0.5 * p["slit"] + 0 * p["step"],
            "time": start + 30 * p.get("repeat", 0) + 10 * p["step"],
            "stokes": 1.0 + p["stokes"],
        },
        (
            lambda w: {
                "wave": (w["wave"] - wave_start) / spacing,
                "slit": (w["lat"] - 200) / 0.5,
                "step": (w["time"] - start) % 30 / 10,
                "repeat": (w["time"] - start) // 30,
                "stokes": w["stokes"] - 1,
            }
        )
        if inverse
        else None,
        ("VISP", "op"),
    )
    data.meta.update(meta)
    return data


def vbi_like(label, north=0, later=0, program="op", frames=4, drift=0):
    """
    A VBI tile of ``frames`` frames 9 s apart, 20 by 20 pixels of 0.25", ``north`` arcsec north, ``later`` seconds
    later, ``drift`` arcsec further north each frame.
    """
    return observed(
        label,
        {"frame": frames, "y": 20, "x": 20},
        {"lon": ("x",), "lat": ("frame", "y") if drift else ("y",), "time": ("frame",)},
        lambda p: {
            "lon": -102 + 0.25 * p["x"],
            "lat": 199 + north + drift * p["frame"] + 0.25 * p["y"],
            "time": 1.7e9 + later + 9 * p["frame"],
        },
        lambda w: {
            "x": (w["lon"] + 102) / 0.25,
            "y": (w["lat"] - 199 - north - drift * (w["time"] - 1.7e9 - later) / 9) / 0.25,
            "frame": (w["time"] - 1.7e9 - later) / 9,
        },
        ("VBI", program),
    )


def test_a_dkist_raster_s_quicklook_shows_its_context_imager_s_mosaic_slit_and_point_synced_both_ways(
    qtbot, monkeypatch
):
    from glue_solar.quicklook import coordinator
    from glue_solar.tests.helpers import select_point
    from glue_solar.tests.test_quicklook import LEAD, click, follow, hover, key, menu_action, readout

    app = bare_app_for(qtbot, monkeypatch)
    raster, elsewhere = visp_like(), vbi_like("VBI OTHER", program="another")
    shot = observed(  # a single shot of the raster's program, in its time, which has no frames to follow it
        "VBI SHOT",
        {"y": 20, "x": 20},
        {"lon": ("x",), "lat": ("y",), "time": ()},
        lambda p: {"lon": -102 + 0.25 * p["x"], "lat": 199 + 0.25 * p["y"], "time": np.asarray(1.7e9 + 0 * p["x"])},
        None,
        ("VBI", "op"),
    )
    # the north tile a frame later than the center tile
    center, north = vbi_like("VBI MOSAIC (1, 1)"), vbi_like("VBI MOSAIC (1, 2)", north=5, later=9)
    center._mosaic = north._mosaic = [center, north]
    north._center = center
    dc = app.data_collection
    dc.extend([elsewhere, shot, raster, north, center])
    dc.add_link(WCSLink(center, north))
    drawn_frames, buffer = [], DKISTData.compute_fixed_resolution_buffer

    def frames(data, bounds, *args, **kwargs):  # the frames the center tile is drawn at
        if data is center and kwargs.get("target_cid") is not None:
            drawn_frames.append(bounds[0])
        return buffer(data, bounds, *args, **kwargs)

    monkeypatch.setattr(DKISTData, "compute_fixed_resolution_buffer", frames)
    # the VBI mosaic observed with the raster, in one panel, as IRIS's slit-jaw images (D105)
    viewers = quicklook(app, [raster])
    panel = viewers["imager"]
    assert [viewer.state.title for viewer in viewers["rows"][0]] == [
        "VISP RASTER map",
        "VISP RASTER virtual slit",
        "VBI MOSAIC",
    ]
    assert [layer.state.layer for layer in panel.layers if layer.enabled and layer.state.layer in dc] == [center, north]
    # zoomed out to both, the north tile reaching 39.5 pixels north of the center tile's first row, at one percentile
    state = panel.state
    assert (state.y_min, state.y_max) == pytest.approx((-0.5, 39.5))
    assert {layer.percentile for layer in state.layers if layer.layer in dc} == {99.5}
    tool, coord = panel.toolbar.tools["solar:coordinate"], coordinator(dc)

    def drawn():  # the slit's ends and the point on the frame shown, in pixels
        return np.round(tool._slit.get_xydata(), 6).tolist(), np.round(tool._marker.get_xydata(), 6).tolist()

    # the slit at the point's step, 1: 99.5" east from 199.75" to 204.75" north, and the point at slit pixel 5, 202.5";
    # the frame nearest the step's time, 10 s, its frame 1, 9 s, as first drawn, where frame 0 was drawn first
    qtbot.waitUntil(lambda: bool(drawn_frames), timeout=60_000)
    assert set(drawn_frames) == {1} == {panel.state.slices[0]}
    assert drawn() == ([[10, 3], [10, 23]], [[10, 14]])
    # a step moves the frame, to step 2's 20 s, its frame 2
    point = coord.point
    coord.group.subset_state = PixelSubsetState(raster, [point.slices[0], slice(2, 3), *point.slices[2:]])
    qtbot.waitUntil(lambda: panel.state.slices[0] == 2, timeout=60_000)
    assert drawn() == ([[12, 3], [12, 23]], [[12, 14]])
    # a click on the frame moves the point to the raster's step and slit pixel there, one point for both, the frame
    # clicked staying, as on IRIS's slit-jaw images
    select_point(panel, 8, 8)
    clicked = [0, 0, 2, None]
    assert [s.start for s in coord.point.slices] == clicked
    qtbot.wait(100)
    assert panel.state.slices[0] == 2
    # the frame follows a map click, to step 1's frame 1, and an Undo back to the click's point goes back to the frame
    # clicked
    select_point(viewers["map"], 1, 5)
    qtbot.waitUntil(lambda: panel.state.slices[0] == 1, timeout=60_000)
    app._actions["undo"].trigger()
    qtbot.waitUntil(lambda: panel.state.slices[0] == 2, timeout=60_000)
    assert [s.start for s in coord.point.slices] == clicked
    # a click off the raster, 97.25" east, keeps the point
    select_point(panel, 19, 2)
    qtbot.wait(100)
    assert (coord.point.reference_data, [s.start for s in coord.point.slices]) == (raster, clicked)
    assert "outside raster FOV" in readout(panel)
    # a click on the north tile, 204" north, moves the point to the raster's step and slit pixel there, the frame
    # clicked staying, where only the center tile's clicks counted (D109)
    select_point(panel, 10, 20)
    assert [s.start for s in coord.point.slices] == [0, 1, 8, None]
    qtbot.wait(100)
    assert panel.state.slices[0] == 2
    # and an Undo back to it goes back to the panel's frame clicked, not the north tile's frame nearest it, 1
    select_point(viewers["map"], 1, 5)
    qtbot.waitUntil(lambda: panel.state.slices[0] == 1, timeout=60_000)
    app._actions["undo"].trigger()
    qtbot.waitUntil(lambda: panel.state.slices[0] == 2, timeout=60_000)
    assert [s.start for s in coord.point.slices] == [0, 1, 8, None]
    # Follow/lock's hover and lock click on the north tile move it there too (D109)
    follow(panel)
    hover(qtbot, panel, 8, 8)
    assert [s.start for s in coord.point.slices] == clicked
    hover(qtbot, panel, 10, 20)
    assert [s.start for s in coord.point.slices] == [0, 1, 8, None]
    hover(qtbot, panel, 8, 8)
    click(panel, 10, 20)
    hover(qtbot, panel, 8, 8)
    assert [s.start for s in coord.point.slices] == [0, 1, 8, None]
    key(panel, "escape")
    # the imager leading the time, a frame moves the raster to the step nearest it, none past half a step's cadence
    menu_action(panel, LEAD).trigger()
    slide(panel, 0, 0)
    qtbot.wait(100)
    slide(panel, 0, 2)
    qtbot.waitUntil(lambda: coord.point.slices[1].start == 2, timeout=60_000)
    slide(panel, 0, 3)  # 27 s, 7 s after step 2
    qtbot.wait(100)
    assert coord.point.slices[1].start == 2
    slide(panel, 0, 1)
    qtbot.waitUntil(lambda: coord.point.slices[1].start == 1, timeout=60_000)
    # a point past the frame shows on the north tile, at 204.5", in its frame nearest the frame shown, its frame 0, 9 s,
    # which the Point window names it by, and on no other
    coord.group.subset_state = PixelSubsetState(raster, [slice(0, 1), slice(1, 2), slice(9, 10), slice(None)])
    qtbot.waitUntil(lambda: drawn()[1] == [[10, 22]], timeout=60_000)
    assert "outside" not in readout(panel)
    window = point_window(app)
    window.refresh()
    assert [row[:2] for row in rows(window)] == [
        ["VISP RASTER", "Stokes 0, x 1, y 9, λ 12"],
        ["VBI MOSAIC (1, 2)", "time 0, y 2, x 10"],
    ]


def test_a_dkist_raster_s_steps_follow_its_context_imager_s_frames_in_time_at_its_repeat(qtbot, monkeypatch):
    from glue_solar.quicklook import coordinator
    from glue_solar.tests.test_quicklook import LEAD, leads, menu_action, readout

    app = bare_app_for(qtbot, monkeypatch)
    # 2 repeats 30 s apart of 3 steps 10 s apart, and 8 VBI frames 9 s apart
    raster, imager = visp_like(repeats=2), vbi_like("VBI", frames=8)
    app.data_collection.extend([raster, imager])
    viewers = quicklook(app, [raster])
    panel, coord = viewers["imager"], coordinator(app.data_collection)

    def point(repeat, step):  # at slit pixel 5
        pixel = [slice(0, 1), slice(repeat, repeat + 1), slice(step, step + 1), slice(5, 6), slice(None)]
        coord.group.subset_state = PixelSubsetState(raster, pixel)

    # step 1 of repeat 0, 10 s, its frame 1, 9 s; the imager leading the time, its frame 2, 18 s, step 2, 20 s
    qtbot.waitUntil(lambda: panel.state.slices[0] == 1, timeout=60_000)
    menu_action(panel, LEAD).trigger()
    slide(panel, 0, 2)
    qtbot.waitUntil(lambda: coord.point.slices[2].start == 2, timeout=60_000)
    # at repeat 1, the raster's step of it nearest the frame, none within half a step's cadence of 18 s, and 4, 36 s,
    # step 1, 40 s (D105)
    point(1, 2)
    qtbot.wait(100)
    assert readout(viewers["map"]).endswith("NO MATCH Δt = +12.0 s")
    slide(panel, 0, 4)
    qtbot.waitUntil(lambda: coord.point.slices[2].start == 1, timeout=60_000)
    assert coord.point.slices[1].start == 1
    assert readout(viewers["map"]).endswith("Δt +4.0 s")
    # the raster leading again, step 2 of repeat 1, 50 s, moves the frame to 6, 54 s
    menu_action(viewers["map"], LEAD).trigger()
    point(1, 2)
    qtbot.waitUntil(lambda: panel.state.slices[0] == 6, timeout=60_000)
    assert readout(panel).endswith("Δt +4.0 s")
    assert readout(viewers["map"]).endswith(leads())
    # and after Clear point its repeat slider, to repeat 0's step 2, 20 s, frame 2, where no time sync ran (D22)
    menu_action(viewers["map"], "Clear point").trigger()
    qtbot.wait(100)
    slide(viewers["map"], 1, 0)
    qtbot.waitUntil(lambda: panel.state.slices[0] == 2, timeout=60_000)
    assert readout(panel).endswith("Δt -2.0 s")


def test_a_click_on_a_sit_and_stare_raster_s_context_image_takes_the_step_nearest_its_frame_s_time(qtbot, monkeypatch):
    from glue_solar.quicklook import coordinator
    from glue_solar.tests.helpers import select_point
    from glue_solar.tests.test_quicklook import readout

    app = bare_app_for(qtbot, monkeypatch)
    # 3 steps 0.01" and 10 s apart, sit-and-stare (D102), and 8 VBI frames 9 s apart, of a mosaic's center tile and its
    # north tile, 5" north, 9 s later and 1" further north each frame
    raster, imager = visp_like(step=0.01), vbi_like("VBI MOSAIC (1, 1)", frames=8)
    north = vbi_like("VBI MOSAIC (1, 2)", north=5, later=9, frames=8, drift=1)
    imager._mosaic = north._mosaic = [imager, north]
    north._center = imager
    app.data_collection.extend([raster, imager, north])
    app.data_collection.add_link(WCSLink(imager, north))
    viewers = quicklook(app, [raster])
    panel, coord = viewers["imager"], coordinator(app.data_collection)
    # at frame 2, 18 s, step 2, 20 s, on the slit and beside it, at the slit pixel level with the click, as on IRIS's
    # slit-jaw images, where it took a step by the slits' offsets or found the click outside the raster (D7, D105)
    slide(panel, 0, 2)
    for x, y, slit in ((8, 8, 2), (7, 12, 4)):
        select_point(panel, x, y)
        assert [s.start for s in coord.point.slices] == [0, 2, slit, None]
    # and none at frame 7, 63 s, past half a step's cadence
    slide(panel, 0, 7)
    select_point(panel, 8, 8)
    assert [s.start for s in coord.point.slices] == [0, 2, 4, None]
    assert "outside raster FOV" in readout(panel)
    # on the north tile at frame 1, 9 s, through its own coordinates at its frame nearest that time, 0, 9 s: step 1,
    # 10 s, at the slit pixel level with the click, 204" (D109)
    slide(panel, 0, 1)
    select_point(panel, 8, 20)
    assert [s.start for s in coord.point.slices] == [0, 1, 8, None]
    # and none in the gap its drift opens at frame 2, 18 s, its frame 1, 204.5", on no tile, as #331 skips it
    slide(panel, 0, 2)
    select_point(panel, 8, 22)
    qtbot.wait(100)
    assert [s.start for s in coord.point.slices] == [0, 1, 8, None]
    assert "outside raster FOV" not in readout(panel)


def test_go_to_utc_and_blink_move_a_context_image_along_its_steps(qtbot, monkeypatch):
    from glue_solar.tests.test_quicklook import menu_action, type_in_dialog

    app = bare_app_for(qtbot, monkeypatch)
    # a Cryo-NIRSP spectrograph raster and context image of Stokes I and Q along their first axis, 3 steps 10 s apart
    raster = visp_like()
    raster._observed = ("CRYO-NIRSP", "op")
    imager = observed(
        "CRYO-NIRSP CI",
        {"stokes": 2, "step": 3, "y": 8, "x": 8},
        {"lon": ("x",), "lat": ("y",), "time": ("step",), "stokes": ("stokes",)},
        lambda p: {
            "lon": -102 + 0.5 * p["x"],
            "lat": 199 + 0.5 * p["y"],
            "time": 1.7e9 + 10 * p["step"],
            "stokes": 1.0 + p["stokes"],
        },
        None,
        ("CRYO-NIRSP", "op"),
    )
    app.data_collection.extend([raster, imager])
    viewer = app.new_data_viewer(ImageViewer, data=imager)
    viewer.state.slices = (0, 1, 0, 0)
    # with no time master shown, Go to UTC starts at the step shown and moves the step slider, where it read and moved
    # the Stokes slider (D38, D105)
    times = imager[imager.id["Time"], (0, slice(None), 0, 0)]
    opened = type_in_dialog(monkeypatch, str(times[2]))
    menu_action(viewer, "Go to UTC…").trigger()
    assert opened == [np.datetime_as_string(times[1], unit="ms")]
    assert viewer.state.slices[:2] == (0, 2)
    # a blink to it from its raster at step 0, the time master, shows it at its step nearest that time, at its own Stokes
    # parameter, where it took that step for its Stokes parameter (D41)
    viewer.state.slices = (1, 2, 0, 0)
    viewer.add_data(raster)
    menu_action(viewer, "Set blink partner here").trigger()
    viewer.state.reference_data = raster
    menu_action(viewer, "Blink").trigger()
    assert (viewer.state.reference_data, viewer.state.slices[:2]) == (imager, (1, 0))
    menu_action(viewer, "Blink").trigger()  # off


def test_a_cryo_nirsp_context_image_takes_its_spectrograph_s_step_stokes_parameter_and_measurement(qtbot, monkeypatch):
    from qtpy.QtCore import Qt

    from glue_solar.tests.helpers import press
    from glue_solar.tests.test_quicklook import LEAD, applied, menu_action, panels_list, readout, tick

    # Stokes I and Q, 3 steps 2" and 30 s apart of 2 measurements 5 s apart, its pointing moving 0.01" a measurement
    sizes = {"stokes": 2, "step": 3, "measurement": 2}
    along = {"lon": ("step", "measurement"), "lat": (), "time": ("step", "measurement"), "stokes": ("stokes",)}

    def frame(p):  # the world at the steps and measurements, the slit and frame aside
        return {"lon": 2 * p["step"] + 0.01 * p["measurement"], "time": 1.7e9 + 30 * p["step"] + 5 * p["measurement"]}

    def imager_pixel(w):
        seconds = np.asarray(w["time"]) - 1.7e9
        step = np.floor(seconds / 30 + 1e-9)
        measurement = (seconds - 30 * step) / 5
        lon = (w["lon"] - 798 - 2 * step - 0.01 * measurement) / 0.5
        return {
            "stokes": w["stokes"] - 1,
            "step": step,
            "measurement": measurement,
            "y": (w["lat"] + 701) / 0.5,
            "x": lon,
        }

    raster = observed(
        "CRYO-NIRSP SP",
        {**sizes, "slit": 6, "wave": 5},
        {**along, "lon": (*along["lon"], "slit"), "lat": (*along["lon"], "slit"), "wave": ("wave",)},
        lambda p: {
            **frame(p),
            "lon": 800 + frame(p)["lon"] + 0 * p["slit"],
            "lat": -700 + 0.5 * p["slit"] + 0 * p["step"] + 0 * p["measurement"],
            "wave": 1083 + 0.01 * p["wave"],
            "stokes": 1.0 + p["stokes"],
        },
        None,
        ("CRYO-NIRSP", "op"),
    )
    imager = observed(
        "CRYO-NIRSP CI",
        {**sizes, "y": 8, "x": 8},
        {**along, "lon": (*along["lon"], "x"), "lat": ("y",)},
        lambda p: {
            **frame(p),
            "lon": 798 + frame(p)["lon"] + 0.5 * p["x"],
            "lat": -701 + 0.5 * p["y"],
            "stokes": 1.0 + p["stokes"],
        },
        imager_pixel,
        ("CRYO-NIRSP", "op"),
    )
    app = bare_app_for(qtbot, monkeypatch)
    app.data_collection.extend([raster, imager])
    viewers = quicklook(app, [raster])
    panel, tool = viewers["imager"], viewers["imager"].toolbar.tools["solar:coordinate"]
    # its step, Stokes parameter and measurement as the raster's sliders give them, where it had no panel (D105)
    assert panel.state.slices[:3] == (0, 1, 0)
    slide(viewers["map"], 0, 1)
    slide(viewers["map"], 2, 1)
    qtbot.waitUntil(lambda: panel.state.slices[:3] == (1, 1, 1), timeout=60_000)
    coordinator = viewers["map"].toolbar.tools["solar:coordinate"].coordinator
    coordinator.group.subset_state = PixelSubsetState(raster, [*map(slice, (1, 2, 1, 3), (2, 3, 2, 4)), slice(None)])
    qtbot.waitUntil(lambda: panel.state.slices[:3] == (1, 2, 1), timeout=60_000)
    # the slit at step 2 and measurement 1, from -700.25" to -697.25" north, and the point at slit pixel 3, -698.5"
    assert np.round(tool._slit.get_xydata(), 6).tolist() == [[4, 1.5], [4, 7.5]]
    assert np.round(tool._marker.get_xydata(), 6).tolist() == [[4, 5]]
    # F steps the raster, which leads the time, round from its last step, and Space plays its steps, where they moved
    # and played its Stokes parameter, its first axis (D39)
    press(viewers["map"], Qt.Key_F)
    qtbot.waitUntil(lambda: panel.state.slices[:3] == (1, 0, 1), timeout=60_000)
    assert [s.start for s in coordinator.point.slices[:3]] == [1, 0, 1]
    press(viewers["map"], Qt.Key_Space)
    [playing] = [s for s in viewers["slit"].options_widget().slice_helper._sliders if s and s._play_timer.isActive()]
    assert playing is viewers["slit"].options_widget().slice_helper._sliders[1]
    press(viewers["map"], Qt.Key_Space)
    # after Clear point the raster still leads, from its virtual slit's step slider, its time axis's (D22); and the
    # context image leading the time, its step slider moves the raster's
    menu_action(viewers["map"], "Clear point").trigger()
    for leader, follower in ((viewers["slit"], panel), (panel, viewers["slit"])):
        if leader is panel:
            menu_action(panel, LEAD).trigger()
        for step in (0, 2):
            slide(leader, 1, step)
            qtbot.waitUntil(lambda step=step, follower=follower: follower.state.slices[1] == step, timeout=60_000)
    # the context image leading, at the measurement it takes from the raster's point, which times both alike
    coordinator.group.subset_state = PixelSubsetState(raster, [*map(slice, (0, 2, 0, 3), (1, 3, 1, 4)), slice(None)])
    qtbot.waitUntil(lambda: panel.state.slices[:3] == (0, 2, 0), timeout=60_000)
    assert readout(viewers["map"]).endswith("Δt +0.0 s")
    # turned off and on again in the Panels list, it comes back at the step nearest the point's, moved meanwhile, and
    # leads from there, where its old step took the point back (D66)
    panels = panels_list(app)
    applied(app, qtbot, viewers, panels, lambda: tick(panels, "CRYO-NIRSP CI", on=False))
    coordinator.group.subset_state = PixelSubsetState(raster, [*map(slice, (0, 0, 0, 3), (1, 1, 1, 4)), slice(None)])
    applied(app, qtbot, viewers, panels, lambda: tick(panels, "CRYO-NIRSP CI"))
    assert (panel.state.slices[1], coordinator.point.slices[1].start) == (0, 0)


@small_visp_dated_2044
def test_a_session_restores_a_dkist_raster_s_quicklook_with_its_context_imager(qtbot, monkeypatch, tmp_path):
    from glue_solar.quicklook import coordinator
    from glue_solar.sources import dkist

    # dkist's small ViSP raster and test VBI mosaic as if observed together: of one program execution, the raster's
    # frame times from the mosaic's first (D105)
    load = dkist._data

    def together(dataset, label):
        data = load(dataset, label)
        data._observed = (data._observed[0], "together")
        if data._observed[0] == "VISP":
            times, exposures = data._frames
            data._frames = (times - times.min() + np.datetime64("2023-10-16T18:45:07", "ns"), exposures)
        return data

    monkeypatch.setattr(dkist, "_data", together)
    app = bare_app_for(qtbot, monkeypatch)
    visp = load_data(str(small_visp()))
    with pytest.warns(UserWarning, match="VBI AJQWW: 0 of 27 files"):
        tiles = load_data(str(asdf_alone(tmp_path, "large_vbi")))
    dc = app.data_collection
    dc.extend([visp, *tiles])
    [links] = find_possible_links(dc).values()  # each tile to the center tile
    dc.add_link(links)
    viewers = quicklook(app, [visp])
    coordinator(dc).set_master(viewers["imager"].state.reference_data)
    slide(viewers["imager"], 0, 2)
    app.save_session(str(tmp_path / "pair.glu"))
    subsets, buffer = [], DKISTData.compute_fixed_resolution_buffer

    def counted(data, *args, **kwargs):  # the subsets the tiles draw
        if kwargs.get("subset_state") is not None and data._observed[0] == "VBI":
            subsets.append(data.label)
        return buffer(data, *args, **kwargs)

    monkeypatch.setattr(DKISTData, "compute_fixed_resolution_buffer", counted)
    with pytest.warns(UserWarning, match="VBI AJQWW: 0 of 27 files"):
        restored = restore(qtbot, monkeypatch, tmp_path / "pair.glu")
    # its context imager's panel, with every tile of its mosaic, where the restored tiles were their sources, and
    # leading the time, where they were observed apart
    panel, collection = restored.tab(1)._solar_quicklook[-1]["imager"], restored.data_collection
    shown = [layer.state.layer for layer in panel.layers if layer.enabled and layer.state.layer in collection]
    assert [tile.label for tile in shown] == [layer.layer.label for layer in viewers["imager"].state.layers]
    assert len(shown) == 9
    assert tuple(panel.state.slices) == viewers["imager"].state.slices == (2, 0, 0)
    assert coordinator(collection).masters[("DKIST", "together")] is panel.state.reference_data
    # none of the point and spectra it then removes drawn on the tiles, 0.2 s each through ViSP and VBI's WCS links
    restored.show()
    qtbot.wait(100)
    assert subsets == []


@small_visp_dated_2044
def test_dkist_data_label_dkist_s_lines_in_air_or_vacuum_as_their_headers_say(app):
    import dkist

    from glue_solar.lines import rest_wavelength

    # its first frame's band, line (nm) and air or vacuum, from its headers
    headers = dkist.load_dataset(small_visp()).headers
    assert load_data(str(small_visp())).meta == {key: headers[key][0] for key in ("WAVEBAND", "LINEWAV", "WAVEREF")}
    # about Ca II 854.2 nm: DKIST's line in air, as the headers say, where IRIS's lines labeled none, its Doppler
    # velocity from it, and in vacuum (D107)
    raster = visp_like(wave_start=854.0, spacing=0.02, WAVEREF="Air")
    app.data_collection.append(raster)
    viewer = app.new_data_viewer(ProfileViewer, data=raster)
    viewer.state.x_att = raster.world_component_ids[3]
    lines = viewer.toolbar.tools["solar:lines"]
    assert lines.positions() == [("Ca II", [pytest.approx(854.209)])]
    assert rest_wavelength(raster) == 8542.09
    assert "km / s" in type(viewer.state).x_display_unit.get_choices(viewer.state)
    raster.meta["WAVEREF"] = "Vacuum"
    assert lines.positions() == [("Ca II", [pytest.approx(854.444)])]
    # 'Lines in this range…' lists them, of no strengths, where irispy's catalog of IRIS's wavelengths listed none
    tool = viewer.toolbar.tools["solar:lines_in_range"]
    tool.activate()
    listing = tool.dialog.findChild(QListWidget)
    assert tool.dialog.windowTitle().startswith("DKIST lines in ")
    assert [listing.item(i).text() for i in range(listing.count())] == ["Ca II 8544.440 Å"]
    # of several, its band's line, He I 1083.0 nm's of Si I 1082.7 and He I's three, where it had none
    he = visp_like(wave_start=1082.6, spacing=0.02, WAVEREF="Air", LINEWAV=1083.0, WAVEBAND="He I (1083.0 nm)")
    assert rest_wavelength(he) == 10830.25011


def test_a_full_stokes_dkist_raster_s_quicklook_scales_q_u_and_v_by_their_noise_level(qtbot, monkeypatch):
    from glue_solar.quicklook import coordinator

    app = bare_app_for(qtbot, monkeypatch)
    raster = visp_like(stokes=4)
    rng = np.random.default_rng(0)
    values = rng.normal(0, 1, raster.shape) * np.array([10, 1, 1.5, 2])[:, None, None, None]
    values[0] += 1000
    values[1:, :, :5, 10:15] += 20  # polarized in the line
    raster.update_components({raster.main_components[0]: values})
    app.data_collection.extend([raster, vbi_like("VBI", frames=8)])
    viewers = quicklook(app, [raster])
    # as an SST cube's (#307): the noise level of Q, U and V at the quieter end, shaded on their spectra, and their
    # maps at 5 times it for Q and U and 10 for V, where glue's 99.5% of the whole raster showed them flat (D107)
    noise = [min(mad_std(values[k, :, :, end]) for end in (0, -1)) for k in (1, 2, 3)]
    bands = [[p for p in viewer.axes.patches if p.get_gid() == "solar:noise"] for viewer in viewers["spectra"]]
    assert [[(band.get_y(), band.get_y() + band.get_height()) for band in shown] for shown in bands] == [
        [],
        *[[(pytest.approx(-sigma), pytest.approx(sigma))] for sigma in noise],
    ]
    layers = [viewers[role].state.layers[0] for role in ("map", "slit")]
    whole = [(layer.v_min, layer.v_max) for layer in layers]
    for stokes in (1, 2, 3, 0):
        slide(viewers["map"], 0, stokes)
        qtbot.waitUntil(lambda: all(layer.viewer_state.slices[0] == stokes for layer in layers))
        limit = (0, 5, 5, 10)[stokes] * ([0, *noise])[stokes]
        expected = whole if stokes == 0 else [(pytest.approx(-limit), pytest.approx(limit))] * 2  # I: glue's 99.5%
        assert [(layer.v_min, layer.v_max) for layer in layers] == expected
    # its context imager keeps its own limits as the raster's step moves its frame
    imager = viewers["imager"].state
    before = imager.layers[0].v_min, imager.layers[0].v_max
    coordinator(app.data_collection).group.subset_state = PixelSubsetState(
        raster, [slice(0, 1), slice(2, 3), slice(5, 6), slice(None)]
    )
    qtbot.waitUntil(lambda: imager.slices[0] == 2, timeout=60_000)
    assert (imager.layers[0].v_min, imager.layers[0].v_max) == before
    # an artifact at its first wavelength, as AIOMGG's, or all NaN there, as DL-NIRSP's: at its last
    for first in (4 * values[:, :, :, 0], np.nan):
        values[:, :, :, 0] = first
        other = visp_like(stokes=4)
        other.update_components({other.main_components[0]: values})
        assert other._noise == {k: pytest.approx(mad_std(values[k, :, :, -1])) for k in (1, 2, 3)}
    # from up to 4 frames evenly spaced: of 4 repeats of 3 steps, repeats 1 and 3 at step 1, where 16 frames' files
    # took 0.28 s to open on TXIPCV (D109)
    repeated = visp_like(repeats=4, stokes=4)
    values = rng.normal(0, 1, repeated.shape)
    repeated.update_components({repeated.main_components[0]: values})
    noise = {k: pytest.approx(min(mad_std(values[k, 1::2, 1::2, :, end]) for end in (0, -1))) for k in (1, 2, 3)}
    assert repeated._noise == noise


def as_dkist(tile):
    """
    ``tile``, made by `observed`, its longitude and latitude a helioprojective SkyCoord, its wavelength a SpectralCoord
    and its Stokes parameter a StokesCoord, as dkist's gWCS gives them.
    """
    from sunpy.coordinates import Helioprojective

    wcs = tile.coords._wcs
    sky = {"frame": Helioprojective(obstime=Time(1.7e9, format="unix"), observer="earth"), "unit": u.arcsec}
    classes = {"sky": (SkyCoord, (), sky), "wave": (SpectralCoord, (), {"unit": u.nm}), "stokes": (StokesCoord, (), {})}
    wcs.world_axis_object_classes = {**wcs.world_axis_object_classes, **classes}
    wcs.world_axis_object_components = [
        ("sky", ("lon", "lat").index(kind), f"spherical.{kind}.arcsec")
        if kind in ("lon", "lat")
        else (kind, 0, "value")
        for kind in wcs.world_axis_names
    ]
    return tile


def vbi_tile(label, north=0, later=0):
    """
    A VBI tile as `vbi_like`'s, its place varying along its frames too, as dkist's pointing table gives it (`as_dkist`).
    """
    return as_dkist(
        observed(
            label,
            {"frame": 4, "y": 20, "x": 20},
            {"lon": ("frame", "x"), "lat": ("frame", "y"), "time": ("frame",)},
            lambda p: {
                "lon": -102 + 0.25 * p["x"] + 0 * p["frame"],
                "lat": 199 + north + 0.25 * p["y"] + 0 * p["frame"],
                "time": 1.7e9 + later + 9 * p["frame"],
            },
            lambda w: {
                "x": (w["lon"] + 102) / 0.25,
                "y": (w["lat"] - 199 - north) / 0.25,
                "frame": (w["time"] - 1.7e9 - later) / 9,
            },
            ("VBI", "op"),
        )
    )


def stitched(app, qtbot, tile):
    """The image 'Mosaic…' on ``tile`` adds, once its thread ends."""
    from glue_solar.sources import moments
    from glue_solar.sources.iris import mosaic_dkist

    count = len(app.data_collection)
    mosaic_dkist(tile, app.data_collection)
    qtbot.waitUntil(lambda: not moments._RUNNING and len(app.data_collection) > count, timeout=60_000)
    return app.data_collection[-1]


def test_mosaic_stitches_a_dkist_mosaic_s_tiles_at_the_frame_shown_into_an_image_linked_to_them(qtbot, monkeypatch):
    app = bare_app_for(qtbot, monkeypatch)
    # two tiles of 20 by 20 pixels of 0.25", the north one 4" north, overlapping the center one by 4 rows, its frames
    # 6 s later, 9 s apart, linked as glue suggests (D102)
    center, north = vbi_tile("VBI MOSAIC (1, 1)"), vbi_tile("VBI MOSAIC (1, 2)", north=4, later=6)
    center._mosaic = north._mosaic = [center, north]
    north._center = center
    dc = app.data_collection
    dc.extend([center, north])
    dc.add_link(WCSLink(center, north))
    viewer = app.new_data_viewer(ImageViewer, data=center)
    viewer.state.slices = (2, 0, 0)
    reads, get_data = [], DKISTData.get_data

    def read(data, cid, view=None):  # the tiles' values the mosaic reads, on its thread
        if cid is data.main_components[0] and threading.current_thread() is not threading.main_thread():
            reads.append((data.label, view))
        return get_data(data, cid, view=view)

    monkeypatch.setattr(DKISTData, "get_data", read)
    image = stitched(app, qtbot, center)
    # the frame the viewer shows of each tile, only, on one grid of their pixels, labeled by their mean time there, 21 s
    # from the first frame's, and opened in an Image viewer (D108)
    frame = (2, slice(None), slice(None))
    assert reads == [("VBI MOSAIC (1, 1)", frame), ("VBI MOSAIC (1, 2)", frame)]
    assert (image.label, image.meta["DATE-AVG"]) == ("VBI MOSAIC mosaic 2023-11-14T22:13:41", "2023-11-14T22:13:41.000")
    assert list(image.coords.world_axis_physical_types) == [
        "custom:pos.helioprojective.lon",
        "custom:pos.helioprojective.lat",
    ]
    assert image.shape == (36, 20)
    # at 99.5 % limits, where glue's Min/Max, of a few hot pixels, showed it flat (D109)
    shown = app.viewers[0][-1].state
    assert (shown.reference_data, shown.layers[0].percentile) == (image, 99.5)
    # each tile's pixel at that frame reaches the mosaic where its value is, the mean of both where they overlap
    values = image[image.main_components[0]]
    for tile, y in ((center, 5), (north, 12), (center, 17)):
        mosaic = point(tile, (2, y, 7), image)
        expected = 800 + 20 * y + 7 if y < 16 or tile is north else 800 + 20 * y + 7 - 160
        assert values[tuple(mosaic)] == pytest.approx(expected, abs=1e-3)
        # and a point on the mosaic there reaches the tile at that frame, not the north tile's frame nearest the center
        # tile's time, through glue's link of them, its frame 1
        assert point(image, mosaic, tile) == [2, y, 7]


def test_mosaic_of_dl_nirsp_tiles_is_at_their_stokes_parameter_repeat_and_wavelength_and_reaches_their_spectra(
    qtbot, monkeypatch
):
    app = bare_app_for(qtbot, monkeypatch)
    # two DL-NIRSP tiles of Stokes I and Q, 2 repeats 300 s apart and 3 wavelengths, of 10 by 10 pixels of 0.25", side
    # by side, their place varying with the repeat, as dkist's pointing table gives it
    tiles = [
        as_dkist(
            observed(
                f"DL-NIRSP TILES (0, {k})",
                {"stokes": 2, "repeat": 2, "wave": 3, "y": 10, "x": 10},
                {
                    "lon": ("repeat", "x"),
                    "lat": ("repeat", "y"),
                    "wave": ("wave",),
                    "time": ("repeat",),
                    "stokes": ("stokes",),
                },
                lambda p, k=k: {
                    "lon": -100 + 2.5 * k + 0.25 * p["x"] + 0 * p["repeat"],
                    "lat": 200 + 0.25 * p["y"] + 0 * p["repeat"],
                    "wave": 1083 + 0.01 * p["wave"],
                    "time": 1.7e9 + 300 * p["repeat"],
                    "stokes": 1.0 + p["stokes"],
                },
                lambda w, k=k: {
                    "x": (w["lon"] + 100 - 2.5 * k) / 0.25,
                    "y": (w["lat"] - 200) / 0.25,
                    "wave": (w["wave"] - 1083) / 0.01,
                    "repeat": (w["time"] - 1.7e9) / 300,
                    "stokes": w["stokes"] - 1,
                },
                ("DL-NIRSP", "op"),
            )
        )
        for k in range(2)
    ]
    for tile in tiles:
        tile._mosaic, tile._center = tiles, tiles[0]
    app.data_collection.extend(tiles)
    viewer = app.new_data_viewer(ImageViewer, data=tiles[1])
    viewer.state.slices = (1, 1, 2, 0, 0)  # Stokes Q, the second repeat, the third wavelength
    image = stitched(app, qtbot, tiles[1])
    # labeled by its wavelength, Stokes parameter and time, which its meta holds (D108)
    assert image.label == "DL-NIRSP TILES mosaic 1083.020 nm Q 2023-11-14T22:18:20"
    assert image.meta == {"DATE-AVG": "2023-11-14T22:18:20.000", "WAVELNTH": pytest.approx(1083.02), "STOKES": "Q"}
    assert image.shape == (10, 20)
    # a tile's value there, and a point on it reaches that tile's pixel at that repeat, at every Stokes parameter and
    # wavelength: its spectra
    mosaic = point(tiles[1], (1, 1, 2, 4, 6), image)
    assert mosaic == [4, 16]
    assert image[image.main_components[0]][4, 16] == pytest.approx(tiles[1]["data"][1, 1, 2, 4, 6], abs=1e-3)
    assert point(image, mosaic, tiles[1]) == [None, 1, None, 4, 6]


def test_a_session_restores_a_dkist_mosaic_s_image_and_its_links(qtbot, monkeypatch, tmp_path):
    from reproject import mosaicking

    app = bare_app_for(qtbot, monkeypatch)

    # dkist's test VBI mosaic, its tiles' frames of 4096 by 4096 pixels stitched on a grid of 2" pixels, not theirs
    find = mosaicking.find_optimal_celestial_wcs
    monkeypatch.setattr(mosaicking, "find_optimal_celestial_wcs", partial(find, resolution=2 * u.arcsec))
    with pytest.warns(UserWarning, match="VBI AJQWW: 0 of 27 files"):
        tiles = load_data(str(asdf_alone(tmp_path, "large_vbi")))
    app.data_collection.extend(tiles)
    app.new_data_viewer(ImageViewer, data=tiles[4]).state.slices = (1, 0, 0)
    image = stitched(app, qtbot, tiles[4])
    at = point(tiles[4], (1, 2048, 2048), image)
    reached = [point(image, at, tile) for tile in tiles[3:6]]
    assert [frame for frame, *_ in reached] == [1, 1, 1]
    app.save_session(str(tmp_path / "mosaic.glu"))
    with pytest.warns(UserWarning, match="VBI AJQWW: 0 of 27 files"):
        *again, mosaic = restore(qtbot, monkeypatch, tmp_path / "mosaic.glu").data_collection
    # its values, coordinates and meta, and its links to the tiles at the frame shown (`_At`)
    assert (mosaic.label, mosaic.meta) == (image.label, image.meta)
    assert np.isnan(image[image.main_components[0]]).any()  # empty pixels NaN, not reproject's 0
    np.testing.assert_array_equal(mosaic[mosaic.main_components[0]], image[image.main_components[0]])
    corners = ([0, image.shape[1] - 1], [0, image.shape[0] - 1])
    np.testing.assert_allclose(
        mosaic.coords.pixel_to_world_values(*corners), image.coords.pixel_to_world_values(*corners)
    )
    assert [point(mosaic, at, tile) for tile in again[3:6]] == reached


def footprints(viewer, monkeypatch, ticked=None):
    """
    Choose 'DKIST footprints…' on ``viewer``, ticking the datasets named ``ticked``, else leaving its ticks; the names
    it offers and whether each was ticked.
    """
    offered = {}

    def tick(dialog):
        for box in dialog.findChildren(QCheckBox):
            offered[box.text()] = box.isChecked()
            if ticked is not None:
                box.setChecked(box.text() in ticked)
        return QDialog.Accepted

    monkeypatch.setattr(QDialog, "exec", tick)
    viewer.toolbar.actions["solar:dkist_footprints"].trigger()
    return offered


def footprint_lines(viewer):
    """The DKIST footprints drawn on ``viewer``: their lines' x and y by color and width, and their labels."""
    lines = {
        (line.get_color(), line.get_linewidth()): line.get_xydata().T
        for line in viewer.axes.lines
        if line.get_gid() == "solar:dkist_footprint"
    }
    return lines, [text.get_text() for text in viewer.axes.texts if text.get_gid() == "solar:dkist_footprint"]


def test_dkist_footprints_draw_a_raster_s_slit_at_the_viewer_s_time_and_follow_its_frame(app, monkeypatch):
    # 8 frames 9 s apart; 2 repeats 30 s apart, the second 1" west; and a tile 0.25" (1 pixel) west each frame, as
    # LOQEPP's tiles move between frames
    tile, raster = vbi_like("VBI TILE", frames=8), visp_like(repeats=2, drift=1)
    drifting = observed(
        "VBI DRIFTING",
        {"frame": 8, "y": 20, "x": 20},
        {"lon": ("frame", "x"), "lat": ("y",), "time": ("frame",)},
        lambda p: {
            "lon": -102 + 0.25 * (p["x"] + p["frame"]),
            "lat": 199 + 0.25 * p["y"],
            "time": 1.7e9 + 9 * p["frame"],
        },
        None,
        ("VBI", "op"),
    )
    app.data_collection.extend([tile, raster, drifting])
    viewer = app.new_data_viewer(ImageViewer, data=tile)
    offered = {"VBI TILE": True, "VISP RASTER": True, "VBI DRIFTING": True}
    assert footprints(viewer, monkeypatch) == offered  # all at first
    (lines, labels), nan = footprint_lines(viewer), np.nan
    # the tile's own frame of 20 by 20 pixels
    x, y = lines["C0", 1]
    assert (np.nanmin(x), np.nanmax(x), np.nanmin(y), np.nanmax(y)) == pytest.approx((-0.5, 19.5, -0.5, 19.5))
    # the raster's 3 steps 0.5" (2 pixels) apart from -100" (x 8), its slit of 10 pixels of 0.5" from 200" (y 3 to 23),
    # faint, and their outline
    np.testing.assert_allclose(lines["C1", 0.5], [[8, 8, nan, 10, 10, nan, 12, 12, nan], [3, 23, nan] * 3])
    np.testing.assert_allclose(lines["C1", 1], [[8, 10, 12, 12, 10, 8, 8, nan], [3, 3, 3, 23, 23, 23, 3, nan]])
    assert labels == ["VBI TILE", "VISP RASTER", "VBI DRIFTING"]
    # the step at the frame's time: step 0 at frame 0, step 2, 20 s on, at frame 2, 18 s on, repeat 1's step 1, 40 s
    # on and 1" (4 pixels) west of repeat 0's, at frame 4, 36 s on, and none at frame 7, 63 s on, more than half a
    # step's 10 s past its last
    drawn = []
    for frame in (0, 2, 4, 7):
        viewer.state.slices = (frame, 0, 0)
        drawn.append(footprint_lines(viewer)[0])
    slits = [lines.get(("C1", 1.5)) for lines in drawn]
    np.testing.assert_allclose(slits[0], [[8, 8, nan], [3, 23, nan]])
    np.testing.assert_allclose(slits[1], [[12, 12, nan], [3, 23, nan]])
    np.testing.assert_allclose(slits[2], [[14, 14, nan], [3, 23, nan]])
    assert slits[3] is None
    # the drifting tile at its frame nearest the image's, 2 pixels west at frame 2
    for lines, west in zip(drawn[:2], (0, 2)):
        x, y = lines["C2", 1]
        assert (np.nanmin(x), np.nanmax(x)) == pytest.approx((west - 0.5, west + 19.5))


def test_dkist_footprints_draw_on_a_map_from_the_datasets_coordinates_alone_and_clear(app, monkeypatch):
    from astropy.wcs import WCS

    # a map of 40 by 40 pixels of 0.5" from -110", 190", in degrees as a FITS WCS gives them, at the raster's step 1
    wcs = WCS(naxis=2)
    wcs.wcs.ctype, wcs.wcs.cunit = ["HPLN-TAN", "HPLT-TAN"], ["arcsec", "arcsec"]
    wcs.wcs.cdelt, wcs.wcs.crpix, wcs.wcs.crval = [0.5, 0.5], [1, 1], [-110, 190]
    image = Data(label="AIA", coords=wcs, flux=np.zeros((40, 40)))
    image.meta["DATE-OBS"] = "2023-11-14T22:13:30"  # unix 1.7e9 s and 10
    raster, tiles = visp_like(), [vbi_like("VBI MOSAIC (1, 1)"), vbi_like("VBI MOSAIC (1, 2)", north=4)]
    for tile in tiles:
        tile._mosaic = tiles
    dc = app.data_collection
    dc.append(image)
    viewer = app.new_data_viewer(ImageViewer, data=image)
    tool = viewer.toolbar.tools["solar:dkist_footprints"]
    assert not tool.offered()  # no DKIST data
    dc.extend([raster, *tiles])
    assert tool.offered()
    # not on a raster's slit and wavelength
    assert not app.new_data_viewer(ImageViewer, data=raster).toolbar.tools["solar:dkist_footprints"].offered()

    # from the datasets' coordinates and times alone, a mosaic's tiles as one dataset
    monkeypatch.setattr(DKISTData, "get_data", lambda *args, **kwargs: pytest.fail("a DKIST dataset's values read"))
    assert footprints(viewer, monkeypatch, ticked=["VBI MOSAIC"]) == {"VISP RASTER": True, "VBI MOSAIC": True}
    lines, labels = footprint_lines(viewer)
    assert (list(lines), labels) == ([("C1", 1)], ["VBI MOSAIC"])
    # the tiles' 20 by 20 pixels of 0.25" from -102", 199", the second 4" north
    x, y = lines["C1", 1]
    extent = np.nanmin(x), np.nanmax(x), np.nanmin(y), np.nanmax(y)
    assert extent == pytest.approx((15.75, 25.75, 17.75, 35.75), abs=1e-3)
    # the raster's slit at the map's time, step 1 at -99.5", as the map is shown, or transposed
    assert footprints(viewer, monkeypatch, ticked=["VISP RASTER", "VBI MOSAIC"]) == {
        "VISP RASTER": False,
        "VBI MOSAIC": True,
    }
    nan = np.nan
    np.testing.assert_allclose(footprint_lines(viewer)[0]["C0", 1.5], [[21, 21, nan], [19.5, 29.5, nan]], atol=1e-3)
    viewer.state.x_att = image.pixel_component_ids[0]
    assert viewer.state.y_att is image.pixel_component_ids[1]
    np.testing.assert_allclose(footprint_lines(viewer)[0]["C0", 1.5], [[19.5, 29.5, nan], [21, 21, nan]], atol=1e-3)
    # gone with their dataset, drawn alone, which clears them
    footprints(viewer, monkeypatch, ticked=["VISP RASTER"])
    dc.remove(raster)
    assert footprint_lines(viewer) == ({}, [])
    assert not tool.checked
    # the other taking the first color; cleared, untick all
    assert footprints(viewer, monkeypatch) == {"VBI MOSAIC": True}
    lines, labels = footprint_lines(viewer)
    assert (list(lines), labels) == ([("C0", 1)], ["VBI MOSAIC"])
    assert footprints(viewer, monkeypatch, ticked=[]) == {"VBI MOSAIC": True}
    assert footprint_lines(viewer) == ({}, [])
    assert not tool.checked


def test_dkist_footprints_draw_on_an_iris_slit_jaw_frame_where_its_coordinates_place_them(
    app, monkeypatch, irispy_test_files
):
    from glue_solar.quicklook import _sji_pixels

    sji = image_data(find_irispy_test_file(irispy_test_files, SJI))
    # the raster's step 1 at the slit-jaw frame 1's time
    when = _times(sji, None)[1]
    raster = visp_like(start=(when - np.datetime64(0, "ns")) / np.timedelta64(1, "s") - 10)
    app.data_collection.extend([sji, raster])
    viewer = app.new_data_viewer(ImageViewer, data=sji)
    viewer.state.slices = (1, 0, 0)
    footprints(viewer, monkeypatch)
    lines, labels = footprint_lines(viewer)
    # each step's slit from -0.5 to 9.5 pixels along it, placed in that frame as the quicklook places points on it
    steps = np.repeat([[0], [1], [2]], 2, axis=1)
    lon, lat = _lon_lat(raster, (0, steps, np.tile([-0.5, 9.5], (3, 1)), 0))
    x, y = _sji_pixels(sji, 1, lon, lat)
    assert np.isfinite([x, y]).all()
    nan = np.full((3, 1), np.nan)
    np.testing.assert_allclose(lines["C0", 0.5], [np.hstack([x, nan]).ravel(), np.hstack([y, nan]).ravel()])
    np.testing.assert_allclose(lines["C0", 1.5], [[*x[1], np.nan], [*y[1], np.nan]])
    assert labels == ["VISP RASTER"]
    # and where a shift of its pointing moves them, at once
    shift(monkeypatch, sji, app.data_collection, (10, 0))
    x, y = _sji_pixels(sji, 1, lon, lat)
    np.testing.assert_allclose(footprint_lines(viewer)[0]["C0", 1.5], [[*x[1], np.nan], [*y[1], np.nan]])


def frame_line(profile):
    """The x of the frame quality's line at the frame shown, None while hidden."""
    [line] = [line for line in profile.axes.lines if line.get_gid() == "solar:frame"]
    return line.get_xdata()[0] if line.get_visible() else None


def freed(ref):
    """Whether the object of weak reference ``ref`` is gone, after a garbage collection."""
    gc.collect()
    return ref() is None


def click_curves(profile, x):
    """Click the frame quality's Profile viewer at ``x``."""
    mouse(profile, "button_press_event", x, np.mean(profile.axes.get_ylim()))


def test_frame_quality_plots_a_dkist_dataset_s_frames_from_its_headers_against_time(app, tmp_path):
    import dkist

    path = asdf_alone(tmp_path, "croppable_cryo")
    with pytest.warns(UserWarning, match="CRYO-NIRSP BMPNP: 0 of 36 files"):
        cryo = load_data(str(path))
    app.data_collection.append(cryo)
    frame_quality_dkist(cryo, app.data_collection)
    frames, profile = app.data_collection[-1], app.viewers[0][-1]
    # a row per FITS file, in time order, its headers' seeing, AO lock (1 while locked), exposure, light level and
    # elevation, and time, none of its files present (D110)
    headers = dkist.load_dataset(path).headers
    times = np.array(headers["DATE-AVG"], dtype="datetime64[ns]")
    order = np.argsort(times, kind="stable")
    assert frames.label == "CRYO-NIRSP BMPNP frame quality"
    assert [(cid.label, frames.get_component(cid).units) for cid in frames.main_components[:5]] == [
        ("ATMOS_R0", "m"),
        ("LIGHTLVL", "adu"),
        ("AO_LOCK", ""),
        ("XPOSURE", "ms"),
        ("ELEV_ANG", "deg"),
    ]
    for key in ("ATMOS_R0", "AO_LOCK", "LIGHTLVL"):
        np.testing.assert_array_equal(frames[key], np.array(headers[key], dtype=float)[order])
    np.testing.assert_array_equal(frames["Time"], times[order])
    # linked to the dataset by time
    np.testing.assert_array_equal(frames[cryo.find_component_id("Time")], times[order])
    # against its time in s since its first frame, the seeing shown, and the frames whose AO was not locked, all of
    # them, shaded
    state = profile.state
    assert state.reference_data is frames
    assert state.x_att.label == "Time Since 2023-01-01T13:00:03"
    seconds = (times[order] - times[order[0]]) / np.timedelta64(1, "s")
    np.testing.assert_allclose(frames[state.x_att], seconds)
    assert (state.layers[0].attribute.label, state.y_axislabel) == ("ATMOS_R0", "ATMOS_R0 [m]")
    [shaded] = [area for area in profile.axes.collections if area.get_gid() == "solar:ao_unlocked"]
    assert (shaded.get_paths()[0].vertices[:, 0].min(), shaded.get_paths()[0].vertices[:, 0].max()) == (0, 380)
    # another column picked: the y axis names it
    state.layers[0].attribute = frames.id["LIGHTLVL"]
    assert state.y_axislabel == "LIGHTLVL [adu]"
    # with no seeing, as Cryo-NIRSP's often, the light level shown: the AO lock is the shading
    app.data_collection.remove(frames)
    del cryo._quality["ATMOS_R0"]
    frame_quality_dkist(cryo, app.data_collection)
    assert app.viewers[0][-1].state.layers[0].attribute.label == "LIGHTLVL"
    with pytest.raises(ValueError, match="other is no DKIST dataset with its frames' seeing or exposure in its"):
        frame_quality_dkist(Data(label="other", values=np.ones(3)), app.data_collection)


def test_frame_quality_and_its_dataset_s_time_sliders_follow_each_other(app, qtbot, tmp_path):
    with pytest.warns(UserWarning, match="CRYO-NIRSP BMPNP: 0 of 36 files"):
        cryo = load_data(str(asdf_alone(tmp_path, "croppable_cryo")))
    app.data_collection.append(cryo)
    viewer = app.new_data_viewer(ImageViewer, data=cryo)
    viewer.state.slices = (2, 1, 2, 0, 0)  # Stokes U, its second scan step, its third measurement
    frame_quality_dkist(cryo, app.data_collection)
    profile = app.viewers[0][-1]
    # a line at the frame shown, in s since the first: steps 180 s apart, measurements 10 s; and it follows the
    # sliders (D110)
    assert frame_line(profile) == 200
    viewer.state.slices = (2, 2, 0, 0, 0)
    assert frame_line(profile) == 360
    # a click on the curves moves the step and measurement sliders to the frame nearest, at the Stokes parameter shown
    click_curves(profile, 188)
    assert viewer.state.slices[:3] == (2, 1, 1)
    assert frame_line(profile) == 190
    # not while a toolbar mode is on, such as glue's range selection
    profile.toolbar.active_tool = "select:xrange"
    click_curves(profile, 10)
    assert viewer.state.slices[:3] == (2, 1, 1)
    profile.toolbar.active_tool = None
    # an Image viewer opened later follows them too, at its own Stokes parameter
    later = app.new_data_viewer(ImageViewer, data=cryo)
    later.state.slices = (0, 0, 1, 0, 0)
    assert frame_line(profile) == 10
    click_curves(profile, 362)
    assert (viewer.state.slices[:3], later.state.slices[:3]) == ((2, 2, 0), (0, 2, 0))
    # but not while it shows the steps along y: it shows no one frame
    later.state.y_att = cryo.pixel_component_ids[1]
    later.state.slices = (*later.state.slices[:2], 2, *later.state.slices[3:])
    assert frame_line(profile) == 360
    # an Image viewer, then the Profile viewer, closed: neither kept for good by the other's callbacks, which echo keeps,
    # once Qt and PyQt let it go
    gone = weakref.ref(later)
    later.close(warn=False)
    del later
    viewer.state.slices = (2, 0, 0, 0, 0)  # the line on this one's frame
    qtbot.waitUntil(partial(freed, gone))
    coordinator(app.data_collection).unregister(viewer)  # as a quicklook panel turned off and on again
    coordinator(app.data_collection).register(viewer)
    gone = weakref.ref(profile)
    profile.close(warn=False)
    del profile
    qtbot.waitUntil(partial(freed, gone))


def test_frame_quality_of_a_mosaic_s_tile_follows_its_center_tile_s_viewer_by_time(app, tmp_path):
    with pytest.warns(UserWarning, match="VBI AJQWW: 0 of 27 files"):
        tiles = load_data(str(asdf_alone(tmp_path, "large_vbi")))
    app.data_collection.extend(tiles)
    viewer = app.new_data_viewer(ImageViewer, data=tiles[4])  # the center tile's, as the mosaic shows
    frame_quality_dkist(tiles[0], app.data_collection)
    frames, profile = app.data_collection[-1], app.viewers[0][-1]
    assert frames.label == "VBI AJQWW (0, 0) frame quality"
    x, times = frames[profile.state.x_att], frames["Time"]
    centers = tiles[4]._frames[0]
    # the line at the tile's frame nearest the center tile's shown, and a click moves the center tile's slider to its
    # frame nearest the tile's clicked (D110)
    for frame in (2, 1):
        viewer.state.slices = (frame, 0, 0)
        assert frame_line(profile) == x[np.argmin(abs(times - centers[frame]))]
    click_curves(profile, x[0])
    assert viewer.state.slices[0] == np.argmin(abs(centers - times[0]))


def test_a_dkist_dataset_s_frame_quality_is_nan_where_its_headers_mask_it(tmp_path):
    import dkist

    from astropy.table import MaskedColumn

    dataset = dkist.load_dataset(asdf_alone(tmp_path, "croppable_cryo"))
    seeing = dataset.headers["ATMOS_R0"]
    dataset.headers["ATMOS_R0"] = MaskedColumn(seeing, mask=np.arange(len(seeing)) == 4)  # as DKIST's at some frames
    # where it read the masked value as given
    quality = _data(dataset, "cryo")._quality["ATMOS_R0"].ravel()
    assert np.isnan(quality[4])
    assert np.isfinite(np.delete(quality, 4)).all()


def test_a_session_restores_a_dkist_dataset_s_frame_quality(app, qtbot, monkeypatch, tmp_path):
    with pytest.warns(UserWarning, match="CRYO-NIRSP BMPNP: 0 of 36 files"):
        cryo = load_data(str(asdf_alone(tmp_path, "croppable_cryo")))
    app.data_collection.append(cryo)
    frame_quality_dkist(cryo, app.data_collection)
    frames = app.data_collection[-1]
    app.save_session(str(tmp_path / "frames.glu"))
    with pytest.warns(UserWarning, match="CRYO-NIRSP BMPNP: 0 of 36 files"):
        again = restore(qtbot, monkeypatch, tmp_path / "frames.glu")
    # its values and its time in s since its first frame, which glue's coordinates of no state would lose
    restored = again.data_collection[-1]
    [world], [before] = restored.world_component_ids, frames.world_component_ids
    assert (restored.label, world.label) == (frames.label, before.label)
    np.testing.assert_array_equal(restored[world], frames[before])
    np.testing.assert_array_equal(restored["ATMOS_R0"], frames["ATMOS_R0"])
    # and the dataset restored has its frames' quality again: the action opens the curves restored, adding none
    count = len(again.data_collection)
    frame_quality_dkist(again.data_collection[0], again.data_collection)
    assert len(again.data_collection) == count
    assert again.viewers[0][-1].state.reference_data is restored


def download(app, qtbot, monkeypatch, data, typed, transfer=None):
    """
    'Download these frames…' on ``data``, its dialog's boxes typed as ``typed``, by name, and OK pressed, dkist's Globus
    transfer helper mocked, or ``transfer`` in its place; returns what the dialog opened with, by name, its summary
    too, and the helper.
    """
    import dkist.net.globus.transfer
    import dkist.net.helpers
    from dkist.io import DKISTFileManager

    from glue_solar.sources import moments
    from glue_solar.sources.iris import download_dkist

    # of dkist's helper's arguments, as dkist.net.helpers holds it, unmocked
    transfer = transfer or create_autospec(dkist.net.helpers._orchestrate_transfer_task)
    monkeypatch.setattr(dkist.net.globus.transfer, "_orchestrate_transfer_task", transfer)
    # the dataset's place at the data center as dkist finds it again, moved since its ASDF file was made (dkist #539)
    moved = {"bucket": "public", "primaryProposalId": "pid_9"}
    monkeypatch.setattr(DKISTFileManager, "_get_inventory", staticmethod(lambda id: {**moved, "datasetId": id}))
    opened = {}

    def exec_(dialog):
        boxes = {box.objectName(): box for box in dialog.findChildren(QtWidgets.QWidget)}
        for name, box in boxes.items():
            if isinstance(box, (QtWidgets.QLabel, QtWidgets.QCheckBox, QtWidgets.QSpinBox)) and name:
                kind = type(box).__name__
                opened[name] = getattr(box, {"QLabel": "text", "QCheckBox": "isChecked", "QSpinBox": "value"}[kind])()
        for name, value in typed.items():
            boxes[name].setChecked(value) if isinstance(value, bool) else boxes[name].setValue(value)
        return QtWidgets.QDialog.Accepted

    monkeypatch.setattr(QtWidgets.QDialog, "exec", exec_)
    download_dkist(data, app.data_collection)
    qtbot.waitUntil(lambda: not moments._RUNNING, timeout=60_000)
    return opened, transfer


@pytest.mark.parametrize(
    ("name", "slices", "defaults", "typed", "chosen"),
    [
        # at the viewer's Stokes parameter, U, all its steps at first: the dataset's mean file size, 5 GiB in 2752 files
        (
            "croppable_visp",
            (2, 0, 0, 0),
            {
                "first": 0,
                "last": 687,
                "polarization state": False,
                "summary": "688 files to download, about 1.3 Gbyte, 2022-10-24T18:57:45 to 2022-10-24T19:33:26",
            },
            {"first": 10, "last": 19},
            (2, slice(10, 20)),
        ),
        # a Cryo-NIRSP raster at the viewer's Stokes parameter, Q, and measurement, 2, its Stokes parameters all ticked;
        # of no size known
        (
            "croppable_cryo",
            (1, 0, 2, 0, 0),
            {
                "first": 0,
                "last": 2,
                "polarization state": False,
                "measurement number": False,
                "summary": "3 files to download, 2023-01-01T13:00:23 to 2023-01-01T13:06:23",
            },
            {"polarization state": True},
            (slice(None), slice(None), 2),
        ),
        # a VBI mosaic's 9 tiles, at the frames typed
        (
            "large_vbi",
            (0, 0, 0),
            {
                "first": 0,
                "last": 2,
                "summary": "27 files to download, about 428.5 Mbyte, 2023-10-16T18:45:07 to 2023-10-16T18:49:10",
            },
            {"last": 1},
            (slice(0, 2),),
        ),
    ],
)
def test_download_these_frames_sends_the_fits_files_chosen_alone_into_the_asdf_file_s_folder(
    app, qtbot, monkeypatch, tmp_path, name, slices, defaults, typed, chosen
):
    from glue_solar.sources.dkist import _ARRIVING

    with pytest.warns(UserWarning, match="0 of"):
        loaded = load_data(str(asdf_alone(tmp_path, name)))
    tiles = loaded if isinstance(loaded, list) else [loaded]
    app.data_collection.extend(tiles)
    app.new_data_viewer(ImageViewer, data=tiles[len(tiles) // 2]).state.slices = slices
    opened, transfer = download(app, qtbot, monkeypatch, tiles[0], typed)
    # the dialog's defaults, and the files' count, size and times (D110)
    assert opened == defaults
    # one transfer of those files alone, from the dataset's place, into the ASDF file's folder, in the background:
    # not dkist's ASDF file, browse movie and quality report too (`FileManager.download`)
    [call] = transfer.call_args_list
    source = Path("/public/pid_9", tiles[0]._dataset.meta["inventory"]["datasetId"])
    names = [name for tile in tiles for name in np.asarray(tile._dataset.files.fileuri_array)[chosen].ravel()]
    assert call.args == ([source / name for name in names],)
    assert call.kwargs == {"recursive": False, "destination_path": tmp_path, "wait": False}
    label = tiles[0].label.rsplit(" (", 1)[0]
    assert app.statusBar().currentMessage() == f"{label}: 0 of {len(names)} files downloaded"
    assert {str(tmp_path / name) for name in names} <= _ARRIVING  # read as missing until whole


def drawn(viewer, x, y):
    """The color, RGBA from 0 to 255, ``viewer``'s canvas draws at its data pixel ``x``, ``y``."""
    canvas = viewer.figure.canvas
    canvas.draw()
    rgba = np.asarray(canvas.buffer_rgba())
    column, row = viewer.axes.transData.transform((x, y))
    return tuple(int(v) for v in rgba[rgba.shape[0] - 1 - int(row), int(column)])


@small_visp_dated_2044
def test_downloaded_frames_fill_in_an_open_viewer_as_their_files_arrive_and_a_session_restores_them(
    app, qtbot, monkeypatch, tmp_path
):
    from glue_solar.sources import iris

    monkeypatch.setattr(iris, "DOWNLOAD_POLL", 400)
    shutil.copy(small_visp(), tmp_path)
    with pytest.warns(UserWarning, match="0 of 3 files"):
        data = load_data(str(tmp_path / "test_visp.asdf"))
    app.data_collection.append(data)
    viewer = app.new_data_viewer(ImageViewer, data=data)
    state = viewer.state
    state.x_att, state.y_att, state.slices = data.pixel_component_ids[0], data.pixel_component_ids[1], (0, 0, 12)
    white = (255, 255, 255, 255)
    assert drawn(viewer, 0, 5) == white  # its files are not here: NaN
    _, transfer = download(app, qtbot, monkeypatch, data, {"last": 1})
    [call] = transfer.call_args_list
    assert [path.name for path in call.args[0]] == ["0.fits", "1.fits"]
    # a file Globus is writing in place reads as missing, not opened part-written, whose HDU kept open it never found
    whole = (small_visp().parent / "0.fits").read_bytes()
    (tmp_path / "0.fits").write_bytes(whole[:2880])
    qtbot.wait(500)  # one look: whole only once unchanged at the next
    cid = data.main_components[0]
    assert not data._present[0]
    assert np.isnan(data.get_data(cid, view=(0,))).all()
    (tmp_path / "0.fits").write_bytes(whole)
    shutil.copy(small_visp().parent / "1.fits", tmp_path)
    with pytest.warns(UserWarning, match=re.escape(f"VISP qVXjk: 2 of 3 files are in {tmp_path}; dkist reads")):
        qtbot.waitUntil(lambda: app.statusBar().currentMessage() == "VISP qVXjk: 2 of 2 files downloaded")
    # their steps drawn, and the color limits taken from them, the viewer's sliders left as they were
    assert list(data._present) == [True, True, False]
    assert drawn(viewer, 0, 5) != white
    assert drawn(viewer, 1, 5) != white
    assert drawn(viewer, 2, 5) == white
    layer, values = viewer.layers[0].state, np.asarray(data[cid])[:2]
    assert (layer.v_min, layer.v_max) == (values.min(), values.max())
    assert tuple(state.slices) == (0, 0, 12)
    app.save_session(str(tmp_path / "downloaded.glu"))
    with pytest.warns(UserWarning, match="2 of 3 files"):
        restored = restore(qtbot, monkeypatch, tmp_path / "downloaded.glu")
    # its files present, and the one left to download
    [again] = restored.data_collection
    assert list(again._present) == [True, True, False]
    opened, transfer = download(restored, qtbot, monkeypatch, again, {})
    assert opened["summary"] == "1 file to download, 2044-03-15T08:23:14 (2 more already there)"
    assert [path.name for path in transfer.call_args.args[0]] == ["2.fits"]


@small_visp_dated_2044
def test_a_mosaic_s_tiles_keep_one_color_limits_as_a_download_s_files_arrive(app, qtbot, monkeypatch, tmp_path):
    from glue_solar.sources import iris

    monkeypatch.setattr(iris, "DOWNLOAD_POLL", 20)
    shutil.copy(small_visp(), tmp_path)
    shutil.copytree(small_visp().parent, tmp_path / "there")
    with pytest.warns(UserWarning, match="0 of 3 files"):
        tiles = [load_data(str(tmp_path / "test_visp.asdf")), load_data(str(tmp_path / "there" / "test_visp.asdf"))]
    app.data_collection.extend(tiles)
    app._layer_widget.ui.layerTree.set_selected_layers(tiles[1:])
    assert not app._layer_widget._actions["Download these frames…"].isVisible()  # of the second, its files all there
    samples = {}
    for tile in tiles:  # a mosaic's two tiles
        tile._mosaic, tile._samples = tiles, samples
    viewer = app.new_data_viewer(ImageViewer, data=tiles[0])
    viewer.add_data(tiles[1])
    for layer in viewer.layers:
        layer.state.percentile = 90  # limits that a sample of other frames moves
    download(app, qtbot, monkeypatch, tiles[0], {"last": 1})
    for name in ("0.fits", "1.fits"):
        shutil.copy(small_visp().parent / name, tmp_path)
    with pytest.warns(UserWarning, match="5 of 6 files"):
        qtbot.waitUntil(lambda: app.statusBar().currentMessage() == "VISP qVXjk: 2 of 2 files downloaded")
    # both tiles' limits taken again from their one sample, its frames' now too, as a mosaic's are synced (D102)
    first, second = (layer.state for layer in viewer.layers)
    assert (second.v_min, second.v_max) == (first.v_min, first.v_max)


@small_visp_dated_2044
def test_download_these_frames_falls_back_to_dkist_s_download_if_its_transfer_helper_moved(
    app, qtbot, monkeypatch, tmp_path
):
    from dkist.io import DKISTFileManager

    shutil.copy(small_visp(), tmp_path)
    with pytest.warns(UserWarning, match="0 of 3 files"):
        data = load_data(str(tmp_path / "test_visp.asdf"))
    app.data_collection.append(data)
    downloads = []
    monkeypatch.setattr(DKISTFileManager, "download", lambda files, **kwargs: downloads.append((files, kwargs)))
    # dkist's private helper of other arguments, as if it moved
    download(app, qtbot, monkeypatch, data, {"first": 1}, transfer=lambda files, *, wait: pytest.fail("called"))
    [(files, kwargs)] = downloads
    assert (files.filenames, kwargs) == (["1.fits", "2.fits"], {"path": tmp_path, "wait": False})


@small_visp_dated_2044
def test_a_download_s_files_read_as_they_are_once_glue_s_window_closes(qtbot, monkeypatch, tmp_path):
    from glue_qt.app.application import GlueApplication
    from qtpy.QtCore import QCoreApplication, QEvent

    import glue_solar
    from glue_solar.sources.dkist import _ARRIVING

    glue_solar.setup()
    window = GlueApplication()  # not the app fixture's, whose window pytest-qt would close again once deleted
    shutil.copy(small_visp(), tmp_path)
    with pytest.warns(UserWarning, match="0 of 3 files"):
        data = load_data(str(tmp_path / "test_visp.asdf"))
    window.data_collection.append(data)
    download(window, qtbot, monkeypatch, data, {})
    paths = {str(tmp_path / f"{step}.fits") for step in range(3)}
    assert paths <= _ARRIVING
    # Reset Session, Open Session and 'Restore last session' close it, and its watch of the files with it: a session
    # restored read them as missing for good
    window.close()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert not paths & _ARRIVING
