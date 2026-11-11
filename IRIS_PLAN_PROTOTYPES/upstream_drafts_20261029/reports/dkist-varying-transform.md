# dkist: VaryingCelestialTransform's shared model (thread race) and its per-index rebuild (dkist #246/#256)

- **Where:** a new issue on DKISTDC/dkist (bug template), citing #246 (closed 2024-11-04), #256 (open, plot
  performance) and #279 (open, refactor). No existing issue on the thread race (`gh search` for "thread",
  "VaryingCelestialTransform"). One issue for both, as they come from the same loop and one change fixes both; split
  off the thread race if you want it tracked on its own.
- **Review rows:** dkist rows 3 (R33, the per-index evaluation) and 5 (the thread race); UPSTREAM-PR there (a successor
  to the closed #762), so this issue is what that PR would close. Replaces the draft
  `scratchpad/fix13/wp13-dkist-read-path/dkist-varying-models.md`.
- **Reproducer:** `scripts/dkist_varying_transform.py`, run by `run.sh rel|main dkist_varying_transform.py`; outputs
  `out/dkist_varying_transform_{rel,main,pr762}.txt`. Release: dkist 1.18.1 (pip). Main: 2a4b15ba, from this folder's
  clone ahead on the path. `pr762`: the closed #762's head 2ad9b75c (`refs/pull/762/head`, fetched into the clone as
  local branch `pr-762`), the same way.

## Title

VaryingCelestialTransform is not thread-safe, and evaluates its model once per lookup index at every call

## Body (paste)

### Description

`BaseVaryingCelestialTransform` keeps one celestial compound model (`self._transform`, `dkist/wcs/models.py:234` on
main). For every distinct lookup index in a call, `_map_transform` (`:317-367`) calls `transform_at_index` (`:248-315`).
That sets the shared model's parameters for the index (`update_celestial_transform_parameters`, `:150-151`) and then
evaluates it on that index's points. This causes two problems.

1. **Threads get each other's pointing.** When two threads evaluate the same gWCS at different raster steps, one
   thread's parameters can be set while the other evaluates. The results are wrong with no error or warning: in the
   script below, about 90% of forward calls are wrong, by up to 0.0078° (28"), and about 73% of inverse calls. This
   hits any GUI that computes coordinates on a worker thread beside its drawing thread; we saw 143.6" errors on real
   ViSP data in glue.
2. **The cost follows the number of indices, at every call.** 1000 points at one raster step take 1 ms. The same
   number of points spread over the 688 steps of `croppable_visp` take 0.12-0.13 s and 688 model updates, and repeat
   the work at the next call with the same points. WCSAxes asks for the same frame and tick positions at every draw.
   On complete ViSP data this was 3 s of an 8 s draw for us. This is the cost #246 and #256 describe, and it is
   still there on main.

### Expected vs Actual behavior

Expected: a gWCS can be evaluated from several threads, and a call's cost follows its number of points.
Actual: see the output below.

### Steps to Reproduce

```python
import gzip
import shutil
import tempfile
import threading
import time
from pathlib import Path

import numpy as np

import dkist
from dkist.data.test import rootdir
from dkist.wcs import models

with tempfile.TemporaryDirectory() as folder:  # croppable_visp's gWCS; its FITS files are not needed
    path = Path(folder) / "croppable_visp.asdf"
    with gzip.open(Path(rootdir) / "croppable_visp.asdf.gz") as source, path.open("wb") as target:
        shutil.copyfileobj(source, target)
    ds = dkist.load_dataset(path)
wcs = ds.wcs.low_level_wcs
nstokes, nstep, nslit, nwave = ds.data.shape
print("dkist from", dkist.__file__, "| array", ds.data.shape, "(Stokes, raster step, slit, wavelength)")

# 1. The cost of a call follows the number of distinct raster steps in it, and is paid again at each call.
built = []
transform_at_index = models.BaseVaryingCelestialTransform.transform_at_index


def counted(self, *args, **kwargs):
    built.append(1)
    return transform_at_index(self, *args, **kwargs)


models.BaseVaryingCelestialTransform.transform_at_index = counted
for label, steps in (("1000 points at one raster step", np.full(1000, 100.0)),
                     ("1000 points across all raster steps", np.linspace(0, nstep - 1, 1000))):
    pixel = [np.full(1000, nwave // 2), np.full(1000, nslit // 2), steps, np.zeros(1000)]
    for attempt in (1, 2):
        built.clear()
        start = time.perf_counter()
        wcs.pixel_to_world_values(*pixel)
        print(f"{label}, call {attempt}: {time.perf_counter() - start:.3f} s, "
              f"transform_at_index called {len(built)} times")
models.BaseVaryingCelestialTransform.transform_at_index = transform_at_index

# 2. Threads evaluating the same gWCS at different raster steps get each other's pointing.
slit = np.arange(0, nslit, 4.0)


def call(step, inverse):
    pixel = [np.full(slit.size, nwave // 2), slit, np.full(slit.size, float(step)), np.zeros(slit.size)]
    world = wcs.pixel_to_world_values(*pixel)
    return wcs.world_to_pixel_values(*world) if inverse else world


steps = range(0, nstep, nstep // 8)[:8]
for inverse in (False, True):
    expected = {step: call(step, inverse) for step in steps}
    for locked in (False, True):
        lock, wrong, worst = threading.Lock(), [], [0.0]

        def work(step):
            for _ in range(40):
                if locked:
                    with lock:
                        got = call(step, inverse)
                else:
                    got = call(step, inverse)
                if not all(np.allclose(a, b, rtol=0, atol=1e-9) for a, b in zip(got, expected[step])):
                    wrong.append(step)
                    worst[0] = max(worst[0], max(np.abs(a - b).max() for a, b in zip(got[:2], expected[step][:2])))

        threads = [threading.Thread(target=work, args=(step,)) for step in steps]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        unit = "pixels" if inverse else "deg"
        print(f"{'world_to_pixel' if inverse else 'pixel_to_world'}, 8 threads at 8 raster steps, 40 calls each, "
              f"{'with a lock' if locked else 'no lock'}: {len(wrong)} of 320 calls wrong, worst error "
              f"{worst[0]:.2g} {unit}")
```

Output with dkist 1.18.1 (path shortened):

```
dkist from .../site-packages/dkist/__init__.py | array (4, 688, 976, 2555) (Stokes, raster step, slit, wavelength)
1000 points at one raster step, call 1: 0.001 s, transform_at_index called 1 times
1000 points at one raster step, call 2: 0.001 s, transform_at_index called 1 times
1000 points across all raster steps, call 1: 0.122 s, transform_at_index called 688 times
1000 points across all raster steps, call 2: 0.123 s, transform_at_index called 688 times
pixel_to_world, 8 threads at 8 raster steps, 40 calls each, no lock: 295 of 320 calls wrong, worst error 0.0078 deg
pixel_to_world, 8 threads at 8 raster steps, 40 calls each, with a lock: 0 of 320 calls wrong, worst error 0 deg
world_to_pixel, 8 threads at 8 raster steps, 40 calls each, no lock: 235 of 320 calls wrong, worst error 0.072 pixels
world_to_pixel, 8 threads at 8 raster steps, 40 calls each, with a lock: 0 of 320 calls wrong, worst error 0 pixels
```

and with main (2a4b15ba):

```
dkist from .../dkist-main/dkist/__init__.py | array (4, 688, 976, 2555) (Stokes, raster step, slit, wavelength)
1000 points at one raster step, call 1: 0.001 s, transform_at_index called 1 times
1000 points at one raster step, call 2: 0.001 s, transform_at_index called 1 times
1000 points across all raster steps, call 1: 0.128 s, transform_at_index called 688 times
1000 points across all raster steps, call 2: 0.129 s, transform_at_index called 688 times
pixel_to_world, 8 threads at 8 raster steps, 40 calls each, no lock: 289 of 320 calls wrong, worst error 0.0078 deg
pixel_to_world, 8 threads at 8 raster steps, 40 calls each, with a lock: 0 of 320 calls wrong, worst error 0 deg
world_to_pixel, 8 threads at 8 raster steps, 40 calls each, no lock: 233 of 320 calls wrong, worst error 0.072 pixels
world_to_pixel, 8 threads at 8 raster steps, 40 calls each, with a lock: 0 of 320 calls wrong, worst error 0 pixels
```

The same script on the head of the closed #762 (2ad9b75c), which evaluates all indices in one pass, gives 0 model
updates, 0.001 s for both calls, and 0 of 320 wrong calls both ways, without the lock.

### Possible fixes

- Evaluate all indices at once, with no shared state: gather each point's `crpix`, `crval` and `pc` from the
  tables by its index, and apply the affine, projection and rotation steps vectorized (as #762 did), or use a model
  set. Then a call costs what its points cost, and threads cannot interfere. This would also go well with the
  refactor in #279.
- Smaller, for the thread race alone: a lock around `_map_transform`'s loop, or a copy of the model for each index.
  The copy is safe but about 4x slower per call (0.12 s to 0.47 s on this dataset, with
  `update_celestial_transform_parameters` applied to a copy of the model).

### System Details

- DKIST Version: 1.18.1, and main 2a4b15ba
- SunPy Version: 8.0.1
- Astropy Version: 8.0.2 (gwcs 1.0.3, numpy 2.5.4)
- Python Version: 3.13.16
- OS information: Fedora Linux 44, x86-64

## Notes for the user (not to paste)

- #762's head conflicts with main in `models.py` and `test_models.py` (#764's and #765's edits), so a successor needs
  a rebase. #762 also wraps longitude to [-180°, 180°), an output change its successor should state.
- "143.6\" on real ViSP data in glue" is AIOMGG, from glue-solar's D103/#385 (register row `GlueWCS._lock`); "3 s of an
  8 s draw" is the draft's complete-ViSP figure (TXIPCV). Neither was re-run here.
- The copy cost (0.12 s to 0.47 s) is the review's `scratchpad/upstream-delta2/dkist/runs/vct_fresh_cost.py` on
  1.18.1 (`vct_fresh_cost_rel.log`: 0.122 s shared, 0.470 s with a copy per index, 0/320 wrong with 8 threads
  unlocked), not the pasted script, and not re-run here. Drop the number if you only want re-run figures.
- The racing share varies from run to run: 284-298 of 320 forward and 233-244 of 320 inverse across the review's runs
  and these.
