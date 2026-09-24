"""WP4 quicklook experiment. Requires the WP1 copied package; not production code."""
import numpy as np
from glue.core.component_link import ComponentLink
from glue.core.exceptions import IncompatibleAttribute
from glue.viewers.image.state import ImageViewerState
from glue_solar.sources.loaders.iris import _frame_times as cube_times, link_hpc


# ---------------------------------------------------------------- loader additions (go into loaders/iris.py)
def add_time(data, cube):
    times = cube_times(cube)
    if times is not None and data.find_component_id("Time") is None:
        data.add_component(np.broadcast_to(times.reshape((len(times),) + (1,) * (cube.data.ndim - 1)), cube.shape), "Time")


def slit_x(cube, *, pixel_stride=1):
    """Slit positions in image pixels; provide a known decimation stride explicitly."""
    if not np.isfinite(pixel_stride) or pixel_stride <= 0:
        raise ValueError("pixel_stride must be finite and positive")
    n = cube.data.shape[0]
    x = np.asarray(cube.extra_coords["slit x position"].wcs.pixel_to_world_values(np.arange(n)), dtype=float)
    return x / pixel_stride


def add_slit(data, cube, *, pixel_stride=1):
    if cube.extra_coords and "slit x position" in cube.extra_coords.keys():
        values = slit_x(cube, pixel_stride=pixel_stride)
        data.add_component(np.broadcast_to(values.reshape(-1, 1, 1), cube.shape), "Slit x")


def slit_subset_state(data):
    px = data.pixel_component_ids[2]
    return (px > data.id["Slit x"] - 0.5) & (px <= data.id["Slit x"] + 0.5)


# ---------------------------------------------------------------- time link (goes next to link_hpc)
def nearest(query, ref):
    """Nearest sorted reference time; ties choose earlier, outside coverage clamps. No gap tolerance yet."""
    ref = np.asarray(ref, dtype="datetime64[ns]")
    query = np.asarray(query, dtype="datetime64[ns]")
    if ref.ndim != 1 or query.ndim != 1 or not len(ref):
        raise ValueError("nearest needs one-dimensional times and a non-empty reference")
    if np.isnat(ref).any() or np.isnat(query).any() or np.any(ref[1:] < ref[:-1]):
        raise ValueError("times must be finite and reference times sorted")
    ref, q = ref.astype("int64"), query.astype("int64")
    if len(ref) == 1:
        return np.zeros(len(q), dtype=np.int32)
    i = np.clip(np.searchsorted(ref, q), 1, len(ref) - 1)
    return np.where(np.abs(q - ref[i - 1]) <= np.abs(ref[i] - q), i - 1, i).astype(np.int32)


def exposure_times(raster):
    """datetime64 per exposure: shape (nstep,) for one scan, (nscan, nstep) for a stack."""
    return raster["Time"][(slice(None),) * (raster.ndim - 2) + (0, 0)]


def link_time(data_collection, sji, raster):
    """Nearest-exposure links SJI <-> raster (or 4D stack): precomputed int32 index components + identity ComponentLinks (serializable).
    No JoinLink: a key join would make every subset that is IncompatibleAttribute on the partner select the partner whole."""
    t_sji = sji["Time"][:, 0, 0]
    t_ras = exposure_times(raster)
    near = np.unravel_index(nearest(t_sji, t_ras.ravel()), t_ras.shape)      # per SJI frame: (step,) or (scan, step)
    back = nearest(t_ras.ravel(), t_sji).reshape(t_ras.shape)               # per exposure: SJI frame
    names = ["exposure"] if t_ras.ndim == 1 else ["scan", "step"]
    links = []
    for axis, (name, index) in enumerate(zip(names, near)):
        label = f"Nearest {name}: {raster.label}"
        sji.add_component(np.broadcast_to(index.astype(np.int32).reshape((-1,) + (1,) * (sji.ndim - 1)), sji.shape), label)
        links.append(ComponentLink([sji.id[label]], raster.pixel_component_ids[axis]))
    label = f"Nearest frame: {sji.label}"
    raster.add_component(np.broadcast_to(back.reshape(back.shape + (1, 1)), raster.shape), label)
    links.append(ComponentLink([raster.id[label]], sji.pixel_component_ids[0]))
    data_collection.add_link(links)
    return links


# ---------------------------------------------------------------- viewers
def whisker(app, data, slit_index=None):
    """Image Viewer with wavelength along x, raster step (time for sit-and-stare) along y, slider on slit."""
    from glue_qt.viewers.image import ImageViewer

    pix = data.pixel_component_ids  # ponytail: irispy cubes are always (..., step, slit, wavelength)
    viewer = app.new_data_viewer(ImageViewer, data=data)
    viewer.state.x_att, viewer.state.y_att = pix[-1], pix[-3]
    if slit_index is not None:
        slices = list(viewer.state.slices)
        slices[data.ndim - 2] = slit_index
        viewer.state.slices = tuple(slices)
    return viewer


def sync_slices(app):
    """Keep the slice sliders of every Image Viewer (open now or later) on the nearest linked exposure/frame."""
    hook = getattr(app, "_iris_hook_viewer", None)
    if hook is None:
        hook = app._iris_hook_viewer = _install_slice_sync(app)
    for tab in app.viewers:
        for viewer in tab:
            hook(viewer)
    return hook


def _install_slice_sync(app):
    hooked, busy = {}, []

    def push(src):
        ref = src.reference_data
        if busy or ref is None:
            return
        lead = ref.ndim - 2
        if src.x_att is None or src.y_att is None or src.x_att.axis < lead or src.y_att.axis < lead:
            return  # ponytail: leading axes are exposure axes in IRIS cubes; a whisker viewer (step on y) does not drive
        point = tuple(np.array([int(s)]) for s in src.slices)
        busy.append(True)
        try:
            for dst in list(hooked):
                other = dst.reference_data
                if dst is src or other is None:
                    continue
                new = list(dst.slices)
                for axis in range(other.ndim - 2):
                    cid = other.pixel_component_ids[axis]
                    if cid in (dst.x_att, dst.y_att):
                        continue
                    try:
                        index = src.slices[axis] if other is ref else int(np.round(ref[cid, point][0]))
                    except (IncompatibleAttribute, ValueError):  # not linked along this axis / NaN
                        continue
                    new[axis] = int(np.clip(index, 0, other.shape[axis] - 1))
                dst.slices = tuple(new)
        finally:
            busy.pop()

    def hook(viewer):
        state = getattr(viewer, "state", None)
        if isinstance(state, ImageViewerState) and state not in hooked:
            callback = lambda *_: push(state)
            hooked[state] = callback
            state.add_callback("slices", callback)
            def unhook():
                state.remove_callback("slices", callback)
                hooked.pop(state, None)
            viewer.window_closed.connect(unhook)
        return hooked

    original = app.new_data_viewer

    def new_data_viewer(*args, **kwargs):
        viewer = original(*args, **kwargs)
        hook(viewer)
        return viewer

    app.new_data_viewer = new_data_viewer
    return hook


def observation_key(data):
    """Conservative pairing: require the observing program AND execution start."""
    obsid, start = data.meta.get("OBSID"), data.meta.get("STARTOBS")
    if obsid is None or start is None:
        return None
    try:
        start = np.datetime64(str(start), "ns")
    except ValueError:
        return None
    return None if np.isnat(start) else (str(obsid).split("_")[-1], str(start))


def quicklook(app, datasets):
    """SJI viewer + raster map viewer + mean-spectrum Profile viewer, linked in space and time, sliders synced."""
    from glue.viewers.profile.state import ProfileViewerState
    from glue_qt.viewers.image import ImageViewer
    from glue_qt.viewers.profile import ProfileViewer

    dc = app.data_collection
    dc.add_link(link_hpc(dc))
    types = {d: getattr(d.coords, "world_axis_physical_types", ()) for d in datasets}  # coords may be None
    sjis = [d for d in datasets if "time" in types[d]]
    rasters = [d for d in datasets if "em.wl" in types[d]]
    for sji in sjis:
        for raster in rasters:
            if observation_key(sji) is not None and observation_key(sji) == observation_key(raster):
                link_time(dc, sji, raster)
    viewers = []
    if sjis:
        viewers.append(app.new_data_viewer(ImageViewer, data=sjis[0]))
    if rasters:
        raster = rasters[0]
        pix = raster.pixel_component_ids
        image = app.new_data_viewer(ImageViewer, data=raster)
        image.state.x_att, image.state.y_att = pix[-3], pix[-2]  # step (or time) x slit: a map with world lon/lat axes
        slices = list(image.state.slices)
        slices[-1] = raster.shape[-1] // 2
        image.state.slices = tuple(slices)
        profile = app.new_data_viewer(ProfileViewer, data=raster)
        profile.state.x_att = raster.world_component_ids[-1]  # 'Wavelength'
        profile.state.function = "slice" if hasattr(ProfileViewerState, "slices") else "mean"
        viewers += [image, profile]
    sync_slices(app)
    return viewers
