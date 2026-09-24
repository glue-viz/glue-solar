"""
Context for a loaded IRIS observation, fetched on request: the GOES XRS light curve and an SDO/AIA image.
"""

import numpy as np
from glue.config import menubar_plugin
from glue.core import Data
from glue.core.component import Component
from glue.core.link_helpers import LinkSame
from glue.core.roi import PolygonalROI
from glue.core.subset import RoiSubsetState
from glue_qt.utils import set_cursor_cm
from qtpy import QtWidgets
from qtpy.QtCore import Qt

import astropy.units as u
from astropy.coordinates import SkyCoord

import sunpy.map
from sunpy.coordinates import Helioprojective, propagate_with_solar_surface
from sunpy.net import Fido
from sunpy.net import attrs as a
from sunpy.time import parse_time

from glue_solar.sources.loaders.iris import _GlueWCS, _observation_label, link_hpc
from glue_solar.sources.maps import _parse_sunpy_map

__all__ = ["aia_context", "fov_polygon", "goes_context", "goes_xrs", "sdo_context"]

_HPC = "custom:pos.helioprojective."


def goes_xrs(start, end):
    """
    GOES XRS 1-minute averages between two times (ISO strings) as a Glue dataset.

    Components ``xrsa`` (0.5-4 A) and ``xrsb`` (1-8 A) in W / m2, then ``time`` (datetime64).
    Needs the network: NOAA file listing, then a download into sunpy's download directory.
    """
    table = Fido.search(a.Time(start, end), a.Instrument.xrs, a.Resolution.avg1m)[0]
    if len(table) == 0:
        raise ValueError(f"No GOES XRS data found between {start} and {end}")
    # ponytail: the client lists every satellite flying; take the first, NOAA's primary designation is not modelled
    table = table[table["SatelliteNumber"] == table["SatelliteNumber"][0]]
    files = Fido.fetch(table, progress=False)
    if files.errors:
        raise OSError(f"{len(files.errors)} GOES file(s) failed to download: {files.errors[0]}")
    from sunpy.timeseries import TimeSeries  # optional GOES dependencies are needed only on this path

    series = TimeSeries(sorted(files), source="xrs", concatenate=True).truncate(start, end)
    frame = series.to_dataframe()
    data = Data(label=f"{series.observatory} XRS")
    for column in ("xrsa", "xrsb"):
        data.add_component(Component(frame[column].to_numpy(), units=str(series.units[column])), column)
    data.add_component(frame.index.values, "time")  # last: a datetime default attribute breaks the Profile viewer
    return data


def fov_polygon(data):
    """
    Helioprojective (longitude, latitude) of the four field-of-view corners of ``data``, in arcsec.

    Uses the first exposure/scan (every non-spatial pixel axis at index 0) and pixel centres.
    """
    wcs = data.coords
    types = list(getattr(wcs, "world_axis_physical_types", []))
    if _HPC + "lon" not in types or _HPC + "lat" not in types:
        raise ValueError(f"{data.label} has no helioprojective coordinates")
    lon, lat = types.index(_HPC + "lon"), types.index(_HPC + "lat")
    correlated = wcs.axis_correlation_matrix
    other = [w for w in range(wcs.world_n_dim) if w not in (lon, lat)]
    spatial = [
        p
        for p in range(wcs.pixel_n_dim)
        if (correlated[lon, p] or correlated[lat, p]) and not correlated[other, p].any()
    ]
    if len(spatial) != 2:
        raise ValueError(f"{data.label} has no two-dimensional helioprojective field of view")
    x, y = spatial
    shape = data.shape[::-1]  # pixel-axis order
    corners = np.zeros((4, wcs.pixel_n_dim))  # ponytail: pixel centres, the outline sits half a pixel inside the edge
    corners[:, x] = [0, shape[x] - 1, shape[x] - 1, 0]
    corners[:, y] = [0, 0, shape[y] - 1, shape[y] - 1]
    world = wcs.pixel_to_world_values(*corners.T)
    return np.asarray(world[lon]), np.asarray(world[lat])


def aia_context(data, wavelength=171 * u.AA, margin=100 * u.arcsec):
    """
    The SDO/AIA image nearest the start of ``data``'s observation, cut to the IRIS field of view plus ``margin``.

    Returns the cutout as a Glue dataset and a subset state outlining the IRIS field of view on it.
    Needs the network (VSO search and download).
    """
    start = parse_time(str(data.meta["STARTOBS"]))
    lon, lat = fov_polygon(data)
    # ponytail: IRIS flies in low Earth orbit; an Earth observer is within an arcsecond of its own frame
    corners = SkyCoord(lon * u.arcsec, lat * u.arcsec, frame=Helioprojective(obstime=start, observer="earth"))
    result = Fido.search(
        a.Time(start - 10 * u.min, start + 10 * u.min, near=start), a.Instrument.aia, a.Wavelength(wavelength)
    )
    files = Fido.fetch(result, progress=False)
    if files.errors or not files:
        raise OSError(f"No AIA {wavelength} image could be downloaded for {start.isot}")
    aia = sunpy.map.Map(files[0])
    with propagate_with_solar_surface():  # only changes anything when the image is not co-temporal
        corners = corners.transform_to(aia.coordinate_frame)
    bottom_left = SkyCoord(corners.Tx.min() - margin, corners.Ty.min() - margin, frame=aia.coordinate_frame)
    top_right = SkyCoord(corners.Tx.max() + margin, corners.Ty.max() + margin, frame=aia.coordinate_frame)
    cutout = aia.submap(bottom_left, top_right=top_right)
    context = _parse_sunpy_map(cutout, "SDO context")
    context.label = f"AIA_{int(cutout.wavelength.to_value(u.AA))}_context-{_observation_label(data.meta)}"
    context.coords = _GlueWCS(cutout.wcs)  # arcsec and physical-type names, so link_hpc pairs it with IRIS data
    x, y = cutout.wcs.world_to_pixel(corners)
    fov = RoiSubsetState(
        xatt=context.pixel_component_ids[1], yatt=context.pixel_component_ids[0], roi=PolygonalROI(vx=list(x), vy=list(y))
    )
    return context, fov


def _pick_iris_data(app, data_collection, title, prompt):
    """Ask which loaded IRIS dataset to use. The dialog's OK button is the explicit consent to go online."""
    candidates = [
        d
        for d in data_collection
        if "STARTOBS" in d.meta and d.coords is not None and _HPC + "lon" in d.coords.world_axis_physical_types
    ]
    if not candidates:
        QtWidgets.QMessageBox.warning(app, title, "Load an IRIS dataset first.")
        return None
    label, ok = QtWidgets.QInputDialog.getItem(app, title, prompt, [d.label for d in candidates], 0, False)
    return next(d for d in candidates if d.label == label) if ok else None


@menubar_plugin("IRIS: GOES context…")
def goes_context(session, data_collection):
    """Download the GOES XRS light curve spanning an IRIS observation and plot it."""
    app = session.application
    data = _pick_iris_data(app, data_collection, "GOES context", "Download the GOES XRS light curve (NOAA, via sunpy) for")
    if data is None:
        return
    try:
        with set_cursor_cm(Qt.WaitCursor):
            goes = goes_xrs(str(data.meta["STARTOBS"]), str(data.meta["ENDOBS"]))
    except Exception as error:  # noqa: BLE001 - network and reader failures stay a message box, never a crash
        QtWidgets.QMessageBox.critical(app, "GOES context", str(error))
        return
    app.add_datasets(goes)
    time = data.find_component_id("Time")
    if time is not None:  # rasters and stacks carry exact exposure times: a time range on the curve selects raster steps
        data_collection.add_link(LinkSame(goes.id["time"], time))
    from glue_qt.viewers.scatter import ScatterViewer

    viewer = app.new_data_viewer(ScatterViewer, data=goes)
    viewer.state.x_att, viewer.state.y_att, viewer.state.y_log = goes.id["time"], goes.id["xrsb"], True
    viewer.layers[0].state.line_visible = True


@menubar_plugin("IRIS: SDO context…")
def sdo_context(session, data_collection):
    """Download the AIA 171 image nearest the start of an IRIS observation, cut around its field of view, show it."""
    app = session.application
    data = _pick_iris_data(app, data_collection, "SDO context", "Download the AIA 171 Å image nearest the start (VSO, via sunpy) for")
    if data is None:
        return
    try:
        with set_cursor_cm(Qt.WaitCursor):
            context, fov = aia_context(data)
    except Exception as error:  # noqa: BLE001 - network and reader failures stay a message box, never a crash
        QtWidgets.QMessageBox.critical(app, "SDO context", str(error))
        return
    app.add_datasets(context)
    data_collection.add_link(link_hpc(data_collection))  # WP1; pairs the AIA lon/lat with every IRIS dataset by physical type
    data_collection.new_subset_group("IRIS FOV", fov)
    from glue_qt.viewers.image import ImageViewer

    app.new_data_viewer(ImageViewer, data=context)

