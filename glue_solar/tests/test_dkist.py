"""
DKIST Level 1 datasets opened from their ASDF files (D102): dkist's test datasets, an ASDF file alone or its small ViSP
raster with its FITS files, and its sample data, downloaded.
"""

import gzip
import re
import shutil
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from glue.core import DataCollection
from glue.core.autolinking import find_possible_links
from glue.core.data import Data
from glue.core.data_factories import load_data
from glue.core.exceptions import IncompatibleAttribute
from glue.plugins.wcs_autolinking.wcs_autolinking import WCSLink
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer

from astropy.wcs.utils import pixel_to_pixel

from glue_solar import glue_patches
from glue_solar.quicklook import quicklook
from glue_solar.sources.dkist import DKISTData, GlueWCS, _data, _glue_order
from glue_solar.sources.iris import link_iris
from glue_solar.tests.test_quicklook import bare_app_for


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


def drawn_over(app, reference, other, y=None):
    """Whether ``other`` draws over ``reference`` in an Image viewer of ``reference``, along its axis ``y`` if given."""
    viewer = app.new_data_viewer(ImageViewer, data=reference)
    if y is not None:
        viewer.state.y_att = reference.pixel_component_ids[y]
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


@pytest.mark.parametrize(("step", "along"), [(0.01, "Time"), (0.5, "Helioprojective Longitude")])
def test_a_slit_raster_steps_through_time_where_its_pointing_stays(step, along):
    # a raster of 3 steps along a slit of 10 pixels of 0.5" at 25 wavelengths, stepping ``step`` arcsec west a step:
    # sit-and-stare where it moves less than a pixel along the slit
    wcs = SimpleNamespace(
        pixel_n_dim=3,
        world_n_dim=4,
        pixel_shape=None,
        pixel_bounds=None,
        world_axis_physical_types=("em.wl", "custom:pos.helioprojective.lon", "custom:pos.helioprojective.lat", "time"),
        world_axis_units=("nm", "arcsec", "arcsec", "s"),
        world_axis_names=("wavelength", "helioprojective longitude", "helioprojective latitude", "time"),
        axis_correlation_matrix=np.array([[1, 0, 0], [0, 1, 1], [0, 1, 1], [0, 0, 1]], bool),
        pixel_to_world_values=lambda x, y, z: (500 + 0.01 * x, -100 + step * z + 0 * y, 200 + 0.5 * y + 0 * z, 10 * z),
    )
    data = Data(label="raster", coords=GlueWCS(wcs, _glue_order(wcs, (25, 10, 3)), []))
    data.add_component(np.zeros((3, 10, 25)), "data")
    assert labels(data) == [along, "Helioprojective Latitude", "Wavelength"]


@small_visp_dated_2044
def test_a_dkist_raster_opens_its_quicklook_and_labels_its_axes(qtbot, monkeypatch):
    import dkist

    app = bare_app_for(qtbot, monkeypatch)
    data = load_data(str(small_visp()))
    app.data_collection.append(data)
    # an Image viewer of the raster's steps and slit labels the world axes glue gives them
    viewer = app.new_data_viewer(ImageViewer, data=data)
    state, pixel = viewer.state, data.pixel_component_ids
    state.x_att = pixel[0]
    viewer.figure.canvas.draw()
    coords = viewer.axes.coords
    assert state.x_att_world.label == coords[3].get_axislabel() == "Time"
    assert state.y_att_world.label == coords[2].get_axislabel() == "Helioprojective Latitude"
    # its quicklook: map, virtual slit and the spectrum at the map's center, step 1 and slit pixel 5
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
    # a scanning raster's time has no axis of its own (D102), so glue cannot place a point on it from coordinates:
    # its point is incompatible with IRIS data, where it raised TypeError, but the slit-jaw image draws over its map
    with pytest.raises(IncompatibleAttribute):
        point(visp, (0, 344, 488, 1277), sji)
    assert drawn_over(app, visp, sji, y=1)  # its steps by its slit
