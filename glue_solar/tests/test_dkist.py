"""
DKIST Level 1 datasets opened from their ASDF files (D102): dkist's test datasets, an ASDF file alone or its small ViSP
raster with its FITS files, and its sample data, downloaded; sessions of them.
"""

import gzip
import re
import shutil
from pathlib import Path
from types import SimpleNamespace

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
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
from glue_qt.viewers.common.data_slice_widget import SliceWidget
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer

import astropy.units as u
from astropy.io import fits
from astropy.time import Time
from astropy.wcs.utils import pixel_to_pixel

from glue_solar import glue_patches
from glue_solar.conftest import find_irispy_test_file, int16_copy
from glue_solar.quicklook import _lon_lat, quicklook
from glue_solar.regrid import regrid_on_time
from glue_solar.sources.dkist import DKISTData, GlueWCS, _data, _glue_order, _SlitAt, _SlitPlace, dkist_data
from glue_solar.sources.iris import link_iris
from glue_solar.sources.loaders.iris import image_data
from glue_solar.sources.sst import sst_data
from glue_solar.tests.helpers import restore
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
    # below them, no longitude or latitude, as dkist gives off its pointing table, and their pixel 0's time
    lon, lat, _, time, stokes = cryo.coords.pixel_to_world_values(0, 0, -1, 0, 0)
    assert np.isnan([lon, lat]).all()
    assert (time, stokes) == (cryo.coords.pixel_to_world_values(0, 0, 0, 0, 0)[3], 1)


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
    qtbot.waitUntil(lambda: spectrum.profile is not None and np.array_equal(spectrum.profile[1], expected), timeout=60_000)
    qtbot.waitUntil(lambda: rows(point_window(app))[0][1] == pixel, timeout=60_000)
    # and no slider of the axes glue showed between x and y stays over the map's options
    options = viewers["map"].options_widget()
    shown = [slider for slider in options.findChildren(SliceWidget) if slider.isVisible()]
    assert shown == [slider for slider in options.slice_helper._sliders if slider]


def test_a_point_on_a_dkist_dataset_takes_its_viewer_s_stokes_and_measurement(qtbot, monkeypatch, tmp_path):
    app = bare_app_for(qtbot, monkeypatch)
    monkeypatch.setattr(settings, "SHOW_LARGE_DATA_WARNING", False)  # 'Add large data set?' to the Profile viewer
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


def test_a_dkist_dataset_s_nan_pixels_draw_transparent(app, tmp_path):
    with pytest.warns(UserWarning, match="VBI AJQWW: 0 of 27 files"):
        tile = load_data(str(asdf_alone(tmp_path, "large_vbi")))[4]
    app.data_collection.append(tile)
    viewer = app.new_data_viewer(ImageViewer, data=tile)
    # as IRIS data's: glue painted them black, so each tile of a mosaic in one viewer blackened those beneath (D103)
    assert viewer.layers[0].state.cmap_bad == (0, 0, 0, 0)
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
    # as it leaves glue, not when glue quits (user, 2026-10-23)
    collection.remove(data)
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
        assert data.meta == {"rest_wavelength": 6302.5}
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
