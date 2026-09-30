"""
Manual full-data checks for `wp4-time-sync` (done-when 1 and 2), run on ~/DATA/IRIS.

    env HOME="$(mktemp -d)" QT_QPA_PLATFORM=offscreen ~/mamba/envs/iris-plan/bin/python -B \
        IRIS_PLAN_PROTOTYPES/wp4_time_sync_probe.py ~/Git/glue-solar-<worktree>

1. 4000005156 two-scan Mg II k stack + deconvolved SJI 2796, point at step 32. SJI master: the scan chosen
   per frame and the stack's signed offset at frames 0, 20 and 31; step and slit unchanged. Scan 0 alone:
   which frames are NO MATCH. Scan 0 as master: the SJI's match and offset at steps 0-3.
2. 4000255147 Si IV 1403 sit-and-stare + SJI 1400: every follower index is argmin |Δt| and, in coverage,
   |Δt| stays within half the follower's cadence, both ways; an SJI master keeps the slit.
Also times one synced step (spectrogram step to the SJI's new frame drawn).
"""

import os
import pwd
import sys
import time
from glob import glob
from pathlib import Path

sys.path.insert(0, sys.argv[1])

import numpy as np  # noqa: E402
from glue_qt.app import GlueApplication  # noqa: E402
from glue_qt.utils import process_events  # noqa: E402

import glue_solar  # noqa: E402
from glue_solar.quicklook import coordinator, observation_key, quicklook  # noqa: E402
from glue_solar.sources.loaders.iris import image_data, raster_data  # noqa: E402

DATA = Path(pwd.getpwuid(os.getuid()).pw_dir) / "DATA" / "IRIS"  # HOME is a scratch directory
glue_solar.setup()


def settle():
    for _ in range(5):
        process_events()


def times(data):
    return data[data.id["Time"]]


def open_quicklook(datasets):
    app = GlueApplication()
    viewers = quicklook(app, datasets)
    settle()
    return app, viewers, coordinator(app.data_collection)


def status(coord, data):
    viewer = next(v for v in coord._viewers if v.state.reference_data is data)
    kind, value = coord.time_status(viewer)
    return kind, None if kind == "master" else round(value / np.timedelta64(1, "s"), 3)


def brute_nearest(when, times):
    distance = np.abs(times - when)
    best = np.flatnonzero(distance == distance.min())
    return int(best[times[best] == times[best].min()][0])


def point_at(coord, viewers, data, **axes):
    group = coord.group
    slices = list(group.subset_state.slices)
    for axis, index in axes.items():
        slices[int(axis)] = slice(index, index + 1)
    viewers["spectrogram"].state.slices = tuple(
        s.start if s.start is not None else viewers["spectrogram"].state.slices[i] for i, s in enumerate(slices)
    )
    settle()


def case_4000005156():
    files = sorted(glob(str(DATA / "*4000005156_raster/*.fits")))
    [sji_path] = glob(str(DATA / "*4000005156_SJI_2796_t000_deconvolved.fits.gz"))
    [stack] = raster_data(files, ["Mg II k 2796"], stack=True)
    sji = image_data(sji_path)
    app, viewers, coord = open_quicklook([stack, sji])
    [sji_viewer] = viewers["sji"]
    spectrogram = viewers["spectrogram"].state
    spectrogram.slices = (0, 32, *spectrogram.slices[2:])  # the point at step 32
    settle()
    point = coord.point.slices
    coord.set_master(sji)
    scans, offsets = [], {}
    for frame in range(sji.shape[0]):
        sji_viewer.state.slices = (frame, 0, 0)
        settle()
        scans.append(coord.point.slices[0].start)
        if frame in (0, 20, 31):
            offsets[frame] = status(coord, stack)
    same = coord.point.slices[1:] == point[1:]
    print(f"1. SJI master: scan per frame {scans}; stack status at frames 0, 20, 31 {offsets}; step and slit kept {same}")
    app.close()

    [scan0] = raster_data(files[:1], ["Mg II k 2796"])
    sji = image_data(sji_path)
    app, viewers, coord = open_quicklook([scan0, sji])
    [sji_viewer] = viewers["sji"]
    coord.set_master(sji)
    unmatched = []
    for frame in range(sji.shape[0]):
        sji_viewer.state.slices = (frame, 0, 0)
        settle()
        if status(coord, scan0)[0] == "no match":
            unmatched.append(frame)
    print(f"   scan 0 alone, SJI master: NO MATCH frames {unmatched}")
    coord.masters.clear()
    results = []
    for step in range(4):
        spectrogram = viewers["spectrogram"].state
        spectrogram.slices = (step, *spectrogram.slices[1:])
        settle()
        results.append((step, *status(coord, sji)))
    print(f"   scan 0 master: SJI (step, status, Δt s) {results}; SJI half cadence 5.845 s")
    app.close()


def case_4000255147():
    [raster] = raster_data(glob(str(DATA / "*4000255147_raster/*.fits")), ["Si IV 1403"])
    [sji_path] = glob(str(DATA / "*4000255147_SJI_1400_t000.fits.gz"))
    sji = image_data(sji_path)
    app, viewers, coord = open_quicklook([raster, sji])
    [sji_viewer] = viewers["sji"]
    raster_times, sji_times = times(raster)[:, 0, 0], times(sji)[:, 0, 0]
    wrong, worst, step_times = 0, 0.0, []
    for step in (1, *range(0, raster.shape[0], 37), 800, raster.shape[0] - 1):
        spectrogram = viewers["spectrogram"].state
        start = time.perf_counter()
        spectrogram.slices = (step, *spectrogram.slices[1:])
        settle()
        sji_viewer.figure.canvas.draw()
        if step in (1, 800, raster.shape[0] - 1):
            step_times.append(round(time.perf_counter() - start, 3))
        expected = int(np.argmin(np.abs(sji_times - raster_times[step])))
        kind, delta = status(coord, sji)
        if kind == "match":
            wrong += sji_viewer.state.slices[0] != expected
            worst = max(worst, abs(delta))
    print(f"2. raster master: {wrong} frames not at argmin |Δt|; largest matched |Δt| {worst:.3f} s (SJI half cadence 5.94 s)")
    print(f"   one synced step (spectrogram step to SJI drawn) at exposures 1, 800, 1599: {step_times} s")
    slit = coord.point.slices[1]
    coord.set_master(sji)
    wrong, worst = 0, 0.0
    for frame in range(0, sji.shape[0], 7):
        sji_viewer.state.slices = (frame, 0, 0)
        settle()
        expected = int(np.argmin(np.abs(raster_times - sji_times[frame])))
        kind, delta = status(coord, raster)
        if kind == "match":
            wrong += coord.point.slices[0].start != expected
            worst = max(worst, abs(delta))
    print(
        f"   SJI master: {wrong} exposures not at argmin |Δt|; largest matched |Δt| {worst:.3f} s "
        f"(raster half cadence 1.445 s); slit kept {coord.point.slices[1] == slit}; key {observation_key(sji)[0]}"
    )
    app.close()


def case_3400109360():
    from glue.core import Data
    from glue.core.component import DateTimeComponent

    files = sorted(glob(str(DATA / "*3400109360_raster/*.fits")))[:2]
    [stack] = raster_data(files, ["Mg II k 2796"], stack=True)
    scan_times = times(stack)[:, stack.shape[1] // 2, 0, 0]
    all_times = np.sort(times(stack)[:, :, 0, 0].ravel())
    frames = all_times[0] + np.arange(40) * (all_times[-1] - all_times[0]) / 39
    sji = Data(label="SJI_1400", SJI_1400=np.arange(40 * 20, dtype=float).reshape(40, 4, 5))
    sji.meta = {"INSTRUME": "SJI", "TDESC1": "SJI_1400", "OBSID": stack.meta["OBSID"], "STARTOBS": stack.meta["STARTOBS"]}
    sji.add_component(DateTimeComponent(np.repeat(frames, 20).reshape(sji.shape)), "Time")
    app, viewers, coord = open_quicklook([stack, sji])
    [sji_viewer] = viewers["sji"]
    coord.set_master(sji)
    wrong = 0
    for frame in range(40):
        sji_viewer.state.slices = (frame, 0, 0)
        settle()
        wrong += coord.point.slices[0].start != brute_nearest(frames[frame], scan_times)
    step_times = times(stack)[0, :, 0, 0]
    print(f"3. 3400109360 two-scan stack (descending times per scan: {bool((np.diff(step_times) < np.timedelta64(0)).all())}), "
          f"synthetic SJI master: {wrong} of 40 frames not on the brute-force nearest scan")
    coord.masters.clear()
    wrong = 0
    for step in range(0, stack.shape[1], 3):
        spectrogram = viewers["spectrogram"].state
        spectrogram.slices = (0, step, *spectrogram.slices[2:])
        settle()
        expected = brute_nearest(times(stack)[0, step, 0, 0], frames)
        if status(coord, sji)[0] == "match":
            wrong += sji_viewer.state.slices[0] != expected
    print(f"   raster master: {wrong} matched SJI frames not on the brute-force nearest")
    app.close()


case_4000005156()
case_4000255147()
case_3400109360()
