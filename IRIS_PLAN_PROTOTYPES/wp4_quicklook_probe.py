"""
Manual full-data checks for `wp4-quicklook-preset`, `wp10-m0-large-data-modal` and `wp10-m0-roi-guard`.

    env HOME="$(mktemp -d)" QT_QPA_PLATFORM=offscreen ~/mamba/envs/iris-plan/bin/python -B \
        IRIS_PLAN_PROTOTYPES/wp4_quicklook_probe.py ~/Git/glue-solar-<worktree> [case ...]

Each case runs in its own process on ~/DATA/IRIS. It prints the raster panels' axes and slices, the
Profile's element count, whether glue's large-data `warn` was called (a spy fails the case if so),
how long `quicklook()` took, a Pixel click to drawn spectrum, and a slit-jaw frame step.
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
    # name: (raster glob, windows, stack, SJI glob)
    "4000255147-mg": ("*4000255147_raster/*.fits", ["Mg II k 2796"], False, "*4000255147_SJI_1400_t000.fits.gz"),
    "4000255147-siiv": ("*4000255147_raster/*.fits", ["Si IV 1403"], False, "*4000255147_SJI_1400_t000.fits.gz"),
    "4000255147-cii": ("*4000255147_raster/*.fits", ["C II 1336"], False, None),
    "3824262996": ("*3824262996_raster/*.fits", ["Mg II k 2796"], False, None),
    "4000005156-stack": (
        "*4000005156_raster/*.fits",
        ["Mg II k 2796"],
        True,
        "*4000005156_SJI_2796_t000_deconvolved.fits.gz",
    ),
    "3602506433-stack": ("*3602506433_raster/*.fits", ["Mg II k 2796"], True, None),
}


def run_case(name):
    import numpy as np
    from glue_qt.app import GlueApplication
    from glue_qt.viewers.profile import ProfileViewer

    import glue_solar
    from glue_solar.quicklook import quicklook
    from glue_solar.sources.loaders.iris import image_data, raster_data
    from glue_solar.tests.helpers import select_point

    raster_glob, windows, stack, sji_glob = CASES[name]
    files = sorted(glob(str(DATA / raster_glob)))
    start = time.perf_counter()
    datasets = raster_data(files, windows, stack=stack)
    if sji_glob:
        [sji] = glob(str(DATA / sji_glob))
        datasets.append(image_data(sji))
    load = time.perf_counter() - start

    def warn(*args, **kwargs):
        raise AssertionError("glue's large-data prompt was called")

    ProfileViewer.warn = warn
    glue_solar.setup()
    app = GlueApplication()
    start = time.perf_counter()
    viewers = quicklook(app, datasets)
    opened = time.perf_counter() - start
    raster = viewers["map"].state.reference_data
    print(f"{name}: {len(files)} file(s), {raster.label} {raster.shape} = {raster.size:.3g} elements, load {load:.1f} s")
    print(f"  quicklook() {opened:.2f} s; status: {app.statusBar().currentMessage()!r}")
    for role in ("map", "spectrogram", "wavelength"):
        state = viewers[role].state
        tools = [t for t in viewers[role].toolbar.tools if t.startswith("select:")]
        print(f"  {state.title}: x {state.x_att.label}, y {state.y_att.label}, slices {state.slices}, select tools {tools}")
    layers = [viewers[role].state.layers[0] for role in ("map", "spectrogram", "wavelength")]
    layers += [viewer.state.layers[0] for viewer in viewers["sji"]]
    print(
        f"  {len(app.viewers[-1])} viewers; percentiles {sorted({layer.percentile for layer in layers})}; "
        f"finite v_min < v_max: {all(np.isfinite(layer.v_min) and layer.v_min < layer.v_max for layer in layers)}"
    )
    spectrum = viewers["spectrum"]
    shown = [layer.layer.label for layer in spectrum.state.layers if layer.visible]
    print(f"  spectrum: layers shown {shown}, y {spectrum.state.y_min:.4g}..{spectrum.state.y_max:.4g}")

    # Pixel click on the map to a drawn spectrum; large profiles compute on a worker thread
    from glue_qt.utils import process_events

    for _ in range(3000):  # the seeded point's spectrum first
        process_events()
        if spectrum.state.y_max != 1:
            break
        time.sleep(0.01)
    print(f"  spectrum after the worker: y {spectrum.state.y_min:.4g}..{spectrum.state.y_max:.4g}")
    [line] = [a.plot_artist for a in spectrum.layers if a.state.visible]
    before = line.get_ydata().copy()
    step = raster.ndim - 3
    point = viewers["map"].state.slices
    start = time.perf_counter()
    select_point(viewers["map"], point[step] + 3, point[step + 1] + 5)
    for _ in range(3000):
        process_events()
        ydata = line.get_ydata()
        if len(ydata) != len(before) or not np.array_equal(ydata, before, equal_nan=True):
            break
        time.sleep(0.005)
    spectrum.figure.canvas.draw()
    print(f"  Pixel click to drawn spectrum: {time.perf_counter() - start:.2f} s")

    for viewer in viewers["sji"]:
        # glue gives the point an empty mask on any dataset not pixel-aligned with the raster
        viewer.figure.canvas.draw()
        steps = []
        for frame in (1, 2, 3):
            start = time.perf_counter()
            viewer.state.slices = (frame, *viewer.state.slices[1:])
            viewer.figure.canvas.draw()
            steps.append(time.perf_counter() - start)
        print(f"  SJI {viewer.state.reference_data.label} {viewer.state.reference_data.shape}: frame step {np.median(steps):.3f} s")
    app.close()


if __name__ == "__main__":
    checkout, *names = sys.argv[1:]
    sys.path.insert(0, checkout)
    if len(names) == 1:
        run_case(names[0])
    else:
        for name in names or CASES:
            result = subprocess.run([sys.executable, "-B", __file__, checkout, name])
            if result.returncode:
                print(f"{name}: FAILED ({result.returncode})")
