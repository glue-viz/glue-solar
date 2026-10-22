"""
The quicklook of a cube of neither instrument, a plain FITS spectral cube as glue's own reader opens it: the map, the
virtual slit and the spectrum at the point, and wavelength against time and the light curve for a time axis, chosen from
its axes, on one point.
"""

import warnings

import numpy as np
import pytest
from glue.core.data_factories import load_data
from glue_qt.app import GlueApplication
from glue_qt.viewers.profile import ProfileViewer

from astropy.io import fits
from astropy.wcs import FITSFixedWarning

from glue_solar.quicklook import QuicklookImageViewer, quicklook
from glue_solar.sources.iris import quicklook_cube
from glue_solar.tests.helpers import select_point
from glue_solar.tests.test_quicklook import (
    bare_app_for,
    changes,
    drawn,
    entries,
    panels_list,
    point_window,
    rows,
    settle,
    slide,
)


@pytest.fixture
def cube_app(qtbot, monkeypatch):
    """An application whose modal dialogs fail the test, with glue's large-data prompt set to fire on any size."""
    monkeypatch.setattr(ProfileViewer, "large_data_size", 1)
    return bare_app_for(qtbot, monkeypatch)


WAVE, TIME = ("WAVE", "Angstrom", 0.1, 6562.5), ("TIME", "s", 10, 0)


def spectral_cube(path, shape, axes=(WAVE, ("STOKES", "", 1, 1), TIME), **cards):
    """
    A cube of ``shape``, such as (wavelength, y, x) or (time, Stokes, wavelength, y, x), written as a FITS file of right
    ascension, declination and as many of ``axes`` (each a CTYPE, CUNIT, CDELT and value at the first pixel) as it has
    others, and ``cards``, opened by glue's own reader, and its values.
    """
    axes = [("RA---TAN", "deg", -1e-4, 150), ("DEC--TAN", "deg", 1e-4, 2), *axes][: len(shape)]
    header = fits.Header({"DATEREF": "2021-09-05T00:00:00", "TIMESYS": "UTC", **cards})
    for n, (ctype, unit, step, value) in enumerate(axes, 1):
        header.update({f"CTYPE{n}": ctype, f"CUNIT{n}": unit, f"CDELT{n}": step, f"CRPIX{n}": 1, f"CRVAL{n}": value})
    values = np.arange(np.prod(shape), dtype=np.float32).reshape(shape)
    fits.writeto(path, values, header)
    with warnings.catch_warnings(action="ignore", category=FITSFixedWarning):  # wcslib's notes, such as MJDREF's
        return load_data(str(path)), values


def spectra(viewers):
    return [viewer.state.layers[0].profile[1] for viewer in viewers["spectra"]]


def point_line(viewer):
    """The y of the line the quicklook draws at the point across ``viewer``, the virtual slit (`_SpectralLines`)."""
    [line] = [line for line in viewer.axes.lines if line.get_gid() == "solar:point"]
    return line.get_ydata()[0]


def test_a_spectral_cube_opens_its_map_virtual_slit_and_spectrum(cube_app, qtbot, tmp_path):
    cube, values = spectral_cube(tmp_path / "cube.fits", (7, 12, 16))
    viewers = quicklook(cube_app, [cube])
    assert cube_app.tab_names[-1] == "cube"
    titles = [[viewer.state.title for viewer in row] for row in viewers["rows"]]
    assert titles == [["cube map", "cube virtual slit"], ["cube spectrum"]]
    assert set(viewers) == {"map", "slit", "spectra", "rows"}  # no time axis: no λ–time nor light curve
    # at the middle wavelength, the point at the map's center
    pixel = cube.pixel_component_ids
    for role, x, y in (("map", 2, 1), ("slit", 0, 1)):
        state = viewers[role].state
        assert isinstance(viewers[role], QuicklookImageViewer)
        assert (state.x_att, state.y_att, state.slices) == (pixel[x], pixel[y], (3, 6, 8))
    [group] = cube_app.session.edit_subset_mode.edit_subset
    assert (group.label, group.subset_state.slices) == ("Point", [slice(None), slice(6, 7), slice(8, 9)])
    assert viewers["map"].toolbar.active_tool.tool_id == "image:point_selection"
    np.testing.assert_array_equal(spectra(viewers), [values[:, 6, 8]])
    assert entries(panels_list(cube_app)) == [(title, True) for row in titles for title in row]

    def event(action):
        return changes(cube_app, qtbot, viewers, action)

    # a map click moves the point and the virtual slit to its x; one on the slit moves the map to its wavelength
    assert event(lambda: select_point(viewers["map"], 3, 7)) == {
        "point": ("cube", (None, 7, 3)),
        "slit": (None, None, 3),
    }
    assert event(lambda: select_point(viewers["slit"], 5, 2)) == {
        "point": ("cube", (None, 2, 3)),
        "map": (5, None, None),
    }
    np.testing.assert_array_equal(spectra(viewers), [values[:, 2, 3]])
    window = point_window(cube_app)
    settle(qtbot, window)
    assert rows(window) == [["cube", "λ 5, y 2, x 3", "6563.000 Å", "", "", f"{values[5, 2, 3]:.6g}", ""]]
    # a click that moves no slider: the slit's line and the Point window follow the point all the same
    assert event(lambda: select_point(viewers["map"], 3, 9)) == {"point": ("cube", (None, 9, 3))}
    settle(qtbot, window)
    assert point_line(viewers["slit"]) == 9
    assert rows(window)[0][1] == "λ 5, y 9, x 3"


def test_a_time_and_stokes_axes_add_their_panels(cube_app, qtbot, tmp_path):
    cube, values = spectral_cube(tmp_path / "cube.fits", (3, 2, 5, 12, 16))
    viewers = quicklook(cube_app, [cube])
    assert [[viewer.state.title for viewer in row] for row in viewers["rows"]] == [
        ["cube map", "cube virtual slit"],
        ["cube Stokes I", "cube Stokes Q"],
        ["cube λ–time", "cube light curve"],
    ]
    pixel = cube.pixel_component_ids
    for role, x, y in (("map", 4, 3), ("slit", 2, 3), ("wavelength", 2, 0)):
        state = viewers[role].state
        assert (state.x_att, state.y_att, state.slices) == (pixel[x], pixel[y], (0, 0, 2, 6, 8))
    assert viewers["curve"].state.x_att is cube.world_component_ids[0]  # time, not an index (D90)
    label = "cube"

    def event(action):
        return changes(cube_app, qtbot, viewers, action)

    # the time and Stokes sliders move the point and the other panels; a click on wavelength against time moves the
    # point to its time and the map to its wavelength
    assert event(lambda: select_point(viewers["map"], 3, 7)) == {
        "point": (label, (0, 0, None, 7, 3)),
        "slit": (0, 0, None, None, 3),
        "wavelength": (None, 0, None, 7, 3),
    }
    assert event(lambda: slide(viewers["map"], 1, 1)) == {
        "point": (label, (0, 1, None, 7, 3)),
        "map": (0, 1, 2, None, None),
        "slit": (0, 1, None, None, 3),
        "wavelength": (None, 1, None, 7, 3),
    }
    assert event(lambda: select_point(viewers["wavelength"], 4, 2)) == {
        "point": (label, (2, 1, None, 7, 3)),
        "map": (2, 1, 4, None, None),
        "slit": (2, 1, None, None, 3),
    }
    qtbot.waitUntil(lambda: viewers["curve"].state.layers[0].profile is not None)
    np.testing.assert_array_equal(spectra(viewers), [values[2, 0, :, 7, 3], values[2, 1, :, 7, 3]])
    np.testing.assert_array_equal(viewers["curve"].state.layers[0].profile[1], values[:, 1, 4, 7, 3])
    window = point_window(cube_app)
    settle(qtbot, window)
    assert rows(window)[0][1] == "time 2, Stokes 1, λ 4, y 7, x 3"


def test_the_lines_find_a_time_axis_after_the_wavelength_axis(cube_app, qtbot, tmp_path):
    # FITS (RA, DEC, TIME, WAVE): wavelength, time, y and x
    cube, _ = spectral_cube(tmp_path / "cube.fits", (5, 3, 12, 16), [TIME, WAVE])
    viewers = quicklook(cube_app, [cube])
    panel = viewers["wavelength"].state
    assert (panel.x_att, panel.y_att) == tuple(cube.pixel_component_ids[:2])
    assert drawn(viewers["wavelength"], "wavelength") == ("x", [2])  # the map's wavelength
    assert drawn(viewers["slit"], "wavelength") is None
    spectrum = viewers["spectra"][0].state
    spectrum.x_display_unit = "Angstrom"
    spectrum.x_min, spectrum.x_max = 6562.6, 6562.8
    assert (panel.x_min, panel.x_max) == (pytest.approx(1), pytest.approx(3))


def test_a_session_restores_the_quicklook(cube_app, qtbot, tmp_path):
    cube, values = spectral_cube(tmp_path / "cube.fits", (3, 2, 5, 12, 16))
    quicklook(cube_app, [cube])
    cube_app.save_session(str(tmp_path / "cube.glu"))
    with warnings.catch_warnings(action="ignore", category=FITSFixedWarning):  # it reads the file again
        restored = GlueApplication.restore_session(str(tmp_path / "cube.glu"), show=False)
    qtbot.addWidget(restored)
    qtbot.wait(20)
    panels = {viewer.state.title: viewer for viewer in restored.viewers[-1]}
    assert isinstance(panels["cube map"], QuicklookImageViewer)
    [group] = restored.session.edit_subset_mode.edit_subset
    # a click moves the point, and the spectra and the light curve with it
    select_point(panels["cube map"], 5, 9)
    qtbot.wait(20)
    assert group.subset_state.slices == [slice(0, 1), slice(0, 1), slice(None), slice(9, 10), slice(5, 6)]
    np.testing.assert_array_equal(
        [panels[f"cube Stokes {name}"].state.layers[0].profile[1] for name in "IQ"], values[0, :, :, 9, 5]
    )
    np.testing.assert_array_equal(panels["cube light curve"].state.layers[0].profile[1], values[:, 0, 2, 9, 5])


def test_the_data_action_opens_the_quicklook(cube_app, tmp_path):
    # 'Quicklook…' in the data collection's right-click menu, offered for such a cube only (test_plugin.py)
    cube, _ = spectral_cube(tmp_path / "cube.fits", (7, 12, 16))
    cube_app.data_collection.append(cube)
    quicklook_cube(cube, cube_app.data_collection)
    assert cube_app.tab_names[-1] == "cube"
    assert [viewer.state.title for viewer in cube_app.viewers[-1]] == ["cube map", "cube virtual slit", "cube spectrum"]


def test_a_pointing_that_moves_with_time_keeps_the_time_axis(cube_app, tmp_path):
    # right ascension moving a pixel a frame: the time axis stays time, though the position changes along it too
    cube, _ = spectral_cube(tmp_path / "cube.fits", (3, 5, 12, 16), [WAVE, TIME], PC1_4=1.0)
    viewers = quicklook(cube_app, [cube])
    assert viewers["wavelength"].state.y_att is cube.pixel_component_ids[0]  # λ–time


def test_a_cube_without_a_wavelength_axis_has_no_quicklook(cube_app, tmp_path):
    cube, _ = spectral_cube(tmp_path / "cube.fits", (7, 12, 16), [("FREQ", "Hz", 1e9, 4.5e14)])
    with pytest.raises(ValueError, match="no raster or slit-jaw image for a quicklook"):
        quicklook(cube_app, [cube])
    plane, _ = spectral_cube(tmp_path / "plane.fits", (1, 12, 16))  # one wavelength: no spectrum
    with pytest.raises(ValueError, match="no raster or slit-jaw image for a quicklook"):
        quicklook(cube_app, [plane])
