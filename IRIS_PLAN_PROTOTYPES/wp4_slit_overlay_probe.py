"""
Manual full-data checks for `wp4-slit-point-overlay`.

    env HOME="$(mktemp -d)" QT_QPA_PLATFORM=offscreen ~/mamba/envs/iris-plan/bin/python -B \
        IRIS_PLAN_PROTOTYPES/wp4_slit_overlay_probe.py ~/Git/glue-solar-<worktree> [case ...]

Each case runs in its own process on ~/DATA/IRIS. It opens a quicklook (so `link_hpc` and time sync
are on) and prints: the slit line against the displayed frame's `slit x position` − 1 at frames 0,
N//2 and N−1; for several raster steps, the SJI frame time sync picks, the marker against
`Coordinator.point_on` and its distance from that frame's slit line; the marker after the SJI is
moved by hand to its last frame; and the time per SJI frame step with the overlay drawn.
"""

import os
import pwd
import subprocess
import sys
import time
from glob import glob
from pathlib import Path

DATA = Path(pwd.getpwuid(os.getuid()).pw_dir) / "DATA" / "IRIS"  # HOME is a scratch directory
CASES = {
    # name: (raster glob, windows, stack, SJI glob, raster steps to put the point on)
    "4000255147": (
        "*4000255147_raster/*.fits",
        ["Si IV 1403"],
        False,
        "*4000255147_SJI_1400_t000.fits.gz",
        (0, 800, 1599),
    ),
    "4000005156-stack": (
        "*4000005156_raster/*.fits",
        ["Mg II k 2796"],
        True,
        "*4000005156_SJI_2796_t000_deconvolved.fits.gz",
        (0, 32, 63),
    ),
}


def run_case(name):
    import numpy as np
    from glue_qt.app import GlueApplication
    from glue_qt.utils import process_events

    import glue_solar
    from glue_solar.quicklook import coordinator, quicklook
    from glue_solar.sources.loaders.iris import image_data, raster_data

    raster_glob, windows, stack, sji_glob, steps = CASES[name]
    datasets = raster_data(sorted(glob(str(DATA / raster_glob))), windows, stack=stack)
    [path] = glob(str(DATA / sji_glob))
    sji = image_data(path)
    glue_solar.setup()
    app = GlueApplication()
    app.resize(1600, 1000)
    app.show()
    viewers = quicklook(app, [*datasets, sji])
    process_events()
    [sji_viewer] = viewers["sji"]
    tool = sji_viewer.toolbar.tools["solar:coordinate"]
    coord = coordinator(app.data_collection)
    n, ny, nx = sji.shape
    slit = np.asarray(sji.meta["slit x position"])

    def settle():
        for _ in range(20):
            process_events()
            time.sleep(0.01)

    def marker():
        crosshair = getattr(sji_viewer, "_crosshairs", None)
        return None if crosshair is None else tuple(crosshair.get_xydata()[0])

    print(f"{name}: SJI {sji.label} {sji.shape}, slit x {slit.min():.1f}-{slit.max():.1f}")
    for frame in (0, n // 2, n - 1):
        sji_viewer.state.slices = (frame, 0, 0)
        settle()
        line = tool._slit.get_xydata()[:, 0] if tool._slit.get_visible() else None
        print(f"  frame {frame}: slit line x {line}, expected {slit[frame] - 1:.2f}")

    spectrogram = viewers["spectrogram"]
    step_axis = 1 if stack else 0
    for step in steps:
        slices = list(spectrogram.state.slices)
        slices[step_axis] = step
        spectrogram.state.slices = tuple(slices)
        settle()
        frame = sji_viewer.state.slices[0]
        where = coord.point_on(sji_viewer)
        shown = marker()
        readout = sji_viewer.toolbar.tools["solar:frame_time"].label.text()
        gap = None if where is None else where[0] - (slit[frame] - 1)
        print(
            f"  step {step}: SJI frame {frame}, point_on {where}, marker {shown}, "
            f"x − slit {gap if gap is None else round(gap, 2)} px, readout '{readout.split(' · ', 1)[-1]}'"
        )

    sji_viewer.state.slices = (n - 1, 0, 0)  # by hand, away from the matched frame
    settle()
    print(f"  by hand to frame {n - 1}: point_on {coord.point_on(sji_viewer)}, marker {marker()}")

    start = time.perf_counter()
    frames = range(0, n, max(1, n // 20))
    for frame in frames:
        sji_viewer.state.slices = (frame, 0, 0)
        sji_viewer.figure.canvas.draw()
    print(f"  SJI step with overlay and draw: {(time.perf_counter() - start) / len(frames):.3f} s")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "--case":
        sys.path.insert(0, sys.argv[1])
        run_case(sys.argv[3])
    else:
        checkout, *names = sys.argv[1:]
        for name in names or CASES:
            subprocess.run([sys.executable, "-B", __file__, checkout, "--case", name], check=False)
