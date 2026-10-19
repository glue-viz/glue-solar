"""
Scale check of glue-solar's SST quicklooks, linking and point moves on large cubes, for a machine with the big data.

Run from any folder, with glue-solar's main installed (it needs the linking of SST cubes without IRIS data, D97):

    env HOME=$(mktemp -d) QT_QPA_PLATFORM=offscreen MPLBACKEND=agg \
        python sst_link_scale.py CUBE_A.fits [CUBE_B.fits ...]

and paste everything it prints. Two or more cubes of one observation also check 'Link points across cubes'. It reads
the cubes through glue-solar's lazy loader, so their files are memory-mapped, not read into RAM; the peak memory it
reports is the check that this holds on cubes larger than RAM.
"""

import resource
import sys
import time
from pathlib import Path


def rss_gb():
    """The process's resident memory now, in GB, from /proc on Linux (else the peak, from getrusage)."""
    try:
        return int(Path("/proc/self/statm").read_text().split()[1]) * resource.getpagesize() / 1e9
    except OSError:
        return peak_gb()


def peak_gb():
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak / 1e6 if sys.platform.startswith("linux") else peak / 1e9  # kB on Linux, bytes on macOS


def step(name, start):
    print(f"{name}: {time.perf_counter() - start:.1f} s, memory {rss_gb():.2f} GB, peak {peak_gb():.2f} GB", flush=True)


def settle(app, seconds=1.0):
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        app.processEvents()
        time.sleep(0.02)


def main(paths):
    start = time.perf_counter()
    from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
    from glue_qt.app import GlueApplication
    from qtpy.QtWidgets import QApplication

    import glue_solar
    from glue_solar.quicklook import coordinator, observation_key, quicklook
    from glue_solar.sources.loaders.iris import link_hpc
    from glue_solar.sources.sst import sst_data

    glue_solar.setup()
    app = GlueApplication()
    qt = QApplication.instance()
    step("import and start", start)
    cubes = []
    for path in paths:
        start = time.perf_counter()
        cubes.append(sst_data(path))
        size = Path(path).stat().st_size / 1e9
        step(f"load {cubes[-1].label} {cubes[-1].shape}, file {size:.1f} GB, key {observation_key(cubes[-1])}", start)
    for cube in cubes:
        start = time.perf_counter()
        quicklook(app, [cube])
        settle(qt)
        step(f"quicklook of {cube.label}", start)
    owners = coordinator(app.data_collection)._owners
    groups = {group.subset_state.reference_data: group for group in owners}
    first = cubes[0]
    if len(cubes) > 1:
        start = time.perf_counter()
        app.data_collection.add_link(link_hpc(app.data_collection, others=cubes))
        step(f"link ({len(app.data_collection.external_links)} links)", start)
    *_, rows, columns = first.shape
    for fy, fx in ((0.5, 0.5), (0.3, 0.6), (0.7, 0.4)):
        y, x = int(fy * rows), int(fx * columns)
        slices = [slice(0, 1)] * (first.ndim - 3) + [slice(None), slice(y, y + 1), slice(x, x + 1)]
        start = time.perf_counter()
        groups[first].subset_state = PixelSubsetState(first, slices)
        qt.processEvents()
        moved_in = time.perf_counter() - start
        settle(qt, 2.0)  # the profiles, computed on worker threads for large cubes
        moved = {
            cube.label: tuple(s.start for s in groups[cube].subset_state.slices[-2:]) for cube in cubes[1:] if cube in groups
        }
        step(f"point at {y},{x} of the first cube, moved in {moved_in:.2f} s; the others' points (y, x) {moved}", start)
    print(f"done; peak memory {peak_gb():.2f} GB")


if __name__ == "__main__":
    main(sys.argv[1:])
