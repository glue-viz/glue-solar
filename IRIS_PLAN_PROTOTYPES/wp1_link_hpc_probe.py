"""
Manual full-data checks for `wp1-m0-link-hpc`, run on ~/DATA/IRIS.

    env HOME="$(mktemp -d)" QT_QPA_PLATFORM=offscreen ~/mamba/envs/iris-plan/bin/python -B \
        IRIS_PLAN_PROTOTYPES/wp1_link_hpc_probe.py ~/Git/glue-solar-<worktree>

(2) 4000005156 Si IV 1403 scan 0 + deconvolved SJI 2796: at frames 0 and N-1 a raster-map ROI selects exactly
    the SJI pixels whose position in the loaded SJI's own coordinates falls in the ROI (0.05 px edge band
    exempt). Per-frame SJI pointing is irispy's to test (test_sji_gwcs_matches_the_fits_pointing).
Freeze: how long an SJI Image viewer at glue-qt's default size takes to draw a frame with that ROI's subset
    (glue computes the mask at screen resolution), for 4000005156 and for the 1600-step 4000255147
    sit-and-stare with its SJI 1400.
"""

import os
import pwd
import sys
import time
from glob import glob
from pathlib import Path

sys.path.insert(0, sys.argv[1])

import numpy as np  # noqa: E402
from glue.core.roi import RectangularROI  # noqa: E402
from glue.core.subset import RoiSubsetState  # noqa: E402
from glue_qt.app import GlueApplication  # noqa: E402
from glue_qt.viewers.image import ImageViewer  # noqa: E402

import glue_solar  # noqa: E402
from glue_solar.sources.loaders.iris import image_data, link_hpc, raster_data  # noqa: E402

DATA = Path(pwd.getpwuid(os.getuid()).pw_dir) / "DATA" / "IRIS"  # HOME is a scratch directory
print("glue_solar from", glue_solar.__file__)


def one(pattern):
    [path] = glob(str(DATA / pattern))
    return path


def load(sji_pattern, raster_pattern):
    app = GlueApplication()
    sji = image_data(one(sji_pattern))
    [raster] = raster_data([one(raster_pattern)], ["Si IV 1403"])
    dc = app.data_collection
    dc.extend([sji, raster])
    dc.add_link(link_hpc(dc))
    print(f"  SJI {sji.label} {sji.shape}; raster {raster.label} {raster.shape}")
    return app, sji, raster


def roi_state(raster, roi):
    return RoiSubsetState(xatt=raster.pixel_component_ids[0], yatt=raster.pixel_component_ids[1], roi=roi)


def draw_seconds(app, sji, raster, roi, frame):
    """Time the first draw of an SJI viewer frame that shows the raster ROI's subset."""
    viewer = app.new_data_viewer(ImageViewer, data=sji)
    viewer.state.slices = (frame, 0, 0)
    viewer.figure.canvas.draw()
    app.data_collection.new_subset_group(label="roi", subset_state=roi_state(raster, roi))
    start = time.perf_counter()
    viewer.figure.canvas.draw()
    seconds = time.perf_counter() - start
    size = viewer.figure.get_size_inches() * viewer.figure.dpi
    return seconds, f"{size[0]:.0f}x{size[1]:.0f} px figure"


def check_footprint():
    print("(2) 4000005156 Si IV 1403 scan 0 + SJI 2796 deconvolved")
    app, sji, raster = load("*4000005156_SJI_2796_t000_deconvolved.fits.gz", "*4000005156_raster/*_r00000.fits")
    n_steps, n_slit = raster.shape[:2]
    roi = RectangularROI(0.3 * n_steps + 0.3, 0.6 * n_steps + 0.3, 0.35 * n_slit + 0.3, 0.65 * n_slit + 0.3)
    (x, y), half_width, half_height = roi.center(), roi.width() / 2, roi.height() / 2
    ok = True
    for frame in (0, sji.shape[0] - 1):
        mask = sji.get_mask(roi_state(raster, roi), view=(frame, slice(None), slice(None)))
        rows, columns = np.indices(mask.shape)
        lon, lat, _ = sji.coords.pixel_to_world_values(columns, rows, frame)
        wavelength = np.full(lon.shape, raster.coords.pixel_to_world_values(0, 0, 0)[0])
        _, slit, step = raster.coords.world_to_pixel_values(wavelength, lat, lon)

        def inside(margin):
            return (abs(step - x) < half_width + margin) & (abs(slit - y) < half_height + margin)

        expected, edge = inside(0), inside(0.05) != inside(-0.05)
        wrong = int((mask[~edge] != expected[~edge]).sum())
        ok &= wrong == 0 and expected.sum() > 0
        print(f"  frame {frame}: selected {int(mask.sum())}, expected {int(expected.sum())}, edge band {int(edge.sum())}, "
              f"mismatches outside the band {wrong}")
    seconds, size = draw_seconds(app, sji, raster, roi, sji.shape[0] // 2)
    print(f"  SJI viewer draw with the subset: {seconds:.2f} s ({size})")
    app.close()
    return ok


def check_freeze_sit_and_stare():
    print("Freeze: 4000255147 Si IV 1403 sit-and-stare + SJI 1400")
    app, sji, raster = load("*4000255147_SJI_1400_t000.fits.gz", "*4000255147_raster/*_r00000.fits")
    n_steps, n_slit = raster.shape[:2]
    roi = RectangularROI(0.4 * n_steps, 0.6 * n_steps, 0.3 * n_slit, 0.7 * n_slit)
    seconds, size = draw_seconds(app, sji, raster, roi, sji.shape[0] // 2)
    print(f"  SJI viewer draw with the subset: {seconds:.2f} s ({size})")
    app.close()


ok = check_footprint()
check_freeze_sit_and_stare()
print("RESULT (2)", ok)
sys.exit(0 if ok else 1)
