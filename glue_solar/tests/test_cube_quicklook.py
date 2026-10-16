"""
The quicklook of a cube of neither instrument, a plain FITS spectral cube as glue's own reader opens it: the map, the
virtual slit and the spectrum at the point, and wavelength against time and the light curve for a time axis, chosen from
its axes, on one point.
"""

import warnings

import numpy as np
import pytest
from glue.core.data_factories import load_data
from glue_qt.viewers.profile import ProfileViewer

from astropy.io import fits
from astropy.wcs import FITSFixedWarning

from glue_solar.quicklook import QuicklookImageViewer, quicklook
from glue_solar.tests.helpers import select_point
from glue_solar.tests.test_quicklook import (
    bare_app_for,
    changes,
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


def spectral_cube(path, shape, spectral=("WAVE", "Angstrom", 0.1, 6562.5)):
    """
    A cube of ``shape``, (wavelength, y, x) or (time, Stokes, wavelength, y, x), written as a FITS file of right
    ascension, declination, wavelength (``spectral``'s CTYPE, CUNIT, CDELT and value at the first pixel) and any Stokes
    and time axes, opened by glue's own reader, and its values.
    """
    axes = [("RA---TAN", "deg", -1e-4, 150), ("DEC--TAN", "deg", 1e-4, 2), spectral]
    axes += [("STOKES", "", 1, 1), ("TIME", "s", 10, 0)][: len(shape) - 3]
    header = fits.Header({"DATEREF": "2021-09-05T00:00:00", "TIMESYS": "UTC"})
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
    assert entries(panels_list(cube_app)) == [("Axes", False), *((title, True) for row in titles for title in row)]

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
    assert viewers["curve"].state.x_att is pixel[0]
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


def test_a_cube_without_a_wavelength_axis_has_no_quicklook(cube_app, tmp_path):
    cube, _ = spectral_cube(tmp_path / "cube.fits", (7, 12, 16), ("FREQ", "Hz", 1e9, 4.5e14))
    with pytest.raises(ValueError, match="no raster or slit-jaw image for a quicklook"):
        quicklook(cube_app, [cube])
