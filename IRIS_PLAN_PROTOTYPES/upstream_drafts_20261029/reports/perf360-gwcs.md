# gwcs: WCS(model, ...) always deep-copies the model (perf360 c3)

- **Where:** a new issue on spacetelescope/gwcs (the repo has no issue template). No existing issue or PR found
  (`gh search` for "deepcopy", "copy model", "copy forward_transform", "copy=False", "copy", "slow", "speed",
  "performance"; #173 is about copying a whole WCS in user code; #422, slicing, is unrelated). The copy dates from
  297d484 (2015, "turn pipeline into a list") and moved in #545. An issue, not a PR: a new keyword is an API choice;
  the body offers the PR.
- **Review row:** perf360 REPORT (c) c3. irispy's side is a2 (build the gWCS from a step list), which sidesteps it.
- **Reproducer:** `scripts/perf360_gwcs.py` (an 11-leaf compound model, pure astropy); output
  `out/perf360_gwcs_rel.txt`; peak 147 MB. Release: gwcs 1.0.3 in iris-plan-latest-1028, `python -I -B`, 24G cap.
- **Main (7f7e664) not run:** the permission classifier refused to run the clone's code ("Code from External"). From
  the source: `Pipeline._initialize_pipeline` still builds `Step(input_frame, forward_transform.copy())`
  (`gwcs/wcs/_pipeline.py:406`), and `Step.copy` still shares the transform (`_step.py:108`). main also requires
  `input_frame` with a model (784f990), which the reproducer passes. 1.0.3 is on the 1.0.x branch, not an ancestor
  of main.

## Title

`WCS(model, input_frame=..., output_frame=...)` deep-copies the model; the list-of-steps form does not

## Body (paste)

`gwcs.WCS(forward_transform, input_frame=..., output_frame=...)` with a model always stores
`forward_transform.copy()`, a deep copy (`gwcs/wcs/_pipeline.py:406` on main, `:87` in 1.0.3). The list-of-steps
form, `WCS([(input_frame, model), (output_frame, None)])`, stores the caller's model itself: `Step.copy` copies the
step, not its transform. Neither the `WCS` docstring nor the docs say that the model form copies the model.

For a compound model of 11 leaf models, building the WCS takes 0.73 ms from a model and 1 us from a list of steps,
with the same world coordinates; the difference is the copy. A program that builds a model for one WCS, as irispy
does for each window of each IRIS raster file, pays for a copy nobody uses. Loading one IRIS observation in irispy
built 11,070 such WCSs, and copying their models was 17.7% of the load.

```python
"""gwcs.WCS(model, input_frame=..., output_frame=...) deep-copies the model; WCS([(frame, model), (frame, None)]) does not.

The model is a 4-D compound model of the kind a raster gWCS uses (11 leaf models). The script times both forms and
model.copy(), checks that both give the same world coordinates, and shows what the steps form shares.
"""

import resource
import sys
import timeit

import numpy as np

import astropy
import astropy.units as u
import gwcs
import gwcs.coordinate_frames as cf
from astropy.coordinates import ICRS
from astropy.modeling import models
from astropy.time import Time


def compound_model():
    spectral = models.Linear1D(slope=0.0025, intercept=133, name="wavelength")
    celestial = (
        (models.Shift(-274) & models.Shift(-546))
        | (models.Scale(0.35 / 3600) & models.Scale(0.1667 / 3600))
        | models.AffineTransformation2D(matrix=[[0.99, -0.01], [0.01, 0.99]])
        | models.Pix2Sky_TAN()
        | models.RotateNative2Celestial(0.05, -0.02, 180)
    )
    time = models.Tabular1D(points=np.arange(400), lookup_table=np.linspace(0, 3000, 400), name="time")
    sky_time = models.Mapping((0, 1, 1)) | (celestial & time)
    return spectral & sky_time & models.Identity(1)


pixel_frame = cf.CoordinateFrame(
    naxes=4, axes_type=["PIXEL"] * 4, axes_order=(0, 1, 2, 3), unit=(u.pix,) * 4, name="pixel"
)
output_frame = cf.CompositeFrame(
    [
        cf.SpectralFrame(axes_order=(0,), unit=u.nm, name="wavelength"),
        cf.CelestialFrame(axes_order=(1, 2), unit=(u.deg, u.deg), reference_frame=ICRS(), name="sky"),
        cf.TemporalFrame(Time("2015-03-11T15:19:47"), unit=(u.s,), axes_order=(3,), name="time"),
        cf.CoordinateFrame(naxes=1, axes_order=(4,), axes_type=["STEP"], unit=(u.pix,), name="scan"),
    ],
    name="world",
)


def model_form(model):
    return gwcs.WCS(model, input_frame=pixel_frame, output_frame=output_frame)


def steps_form(model):
    return gwcs.WCS([(pixel_frame, model), (output_frame, None)])


def per_call(fn, number=300):
    return min(timeit.repeat(fn, number=number, repeat=7)) / number


print(f"Python {sys.version.split()[0]}, numpy {np.__version__}, astropy {astropy.__version__}")
print(f"gwcs {gwcs.__version__} from {gwcs.__file__}")
model = compound_model()
print(f"model: {model.n_inputs} inputs, {model.n_outputs} outputs, {model.n_submodels} leaf models")
t_model = per_call(lambda: model_form(model))
t_steps = per_call(lambda: steps_form(model))
t_copy = per_call(model.copy)
print(f"WCS(model, input_frame=..., output_frame=...): {t_model * 1e3:.3f} ms")
print(f"WCS([(input_frame, model), (output_frame, None)]): {t_steps * 1e3:.3f} ms")
print(f"model.copy(): {t_copy * 1e3:.3f} ms")

a, b = model_form(model), steps_form(model)
rng = np.random.default_rng(0)
pixels = [rng.uniform(0, 300, 50) for _ in range(4)]
same = all(np.array_equal(x, y) for x, y in zip(a(*pixels), b(*pixels)))
print(f"same world coordinates at 50 pixels: {same}")
print(f"the WCS holds the caller's model: model form {a.pipeline[0].transform is model}, "
      f"steps form {b.pipeline[0].transform is model}")
b.bounding_box = ((0, 400), (0, 1000), (0, 400), (0, 1))
print(f"after setting the steps-form WCS's bounding_box, the caller's model has one: {model.has_user_bounding_box}")
print(f"peak RSS: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.0f} MB")
```

Output with gwcs 1.0.3 (main, 7f7e664, still makes this copy), paths shortened:

```
Python 3.13.16, numpy 2.5.4, astropy 8.0.2
gwcs 1.0.3 from .../site-packages/gwcs/__init__.py
model: 4 inputs, 5 outputs, 11 leaf models
WCS(model, input_frame=..., output_frame=...): 0.732 ms
WCS([(input_frame, model), (output_frame, None)]): 0.001 ms
model.copy(): 0.723 ms
same world coordinates at 50 pixels: True
the WCS holds the caller's model: model form False, steps form True
after setting the steps-form WCS's bounding_box, the caller's model has one: True
peak RSS: 147 MB
```

The `bounding_box` line shows why the copy can be wanted: with the steps form, setting the WCS's `bounding_box` sets it on the
caller's model too.

**Suggestion:** either or both:

- A `copy=True` keyword on `WCS` and `Pipeline`, passed down to `_initialize_pipeline`, so a caller that made the
  model for this WCS can pass `copy=False`:

  ```python
  Step(input_frame, forward_transform.copy() if copy else forward_transform),
  ```

- Say in the `WCS` docstring that a model is deep-copied, and that a list of steps is used as given (its transforms
  are shared with the caller, and changes such as a bounding box reach them).

I am happy to open a PR for either.

Python 3.13.16 on Fedora Linux 44, gwcs 1.0.3 from pip, astropy 8.0.2, numpy 2.5.4.

## Notes for the user (not to paste)

- The irispy figures (11,070 WCSs; 17.7% of stock #360's load in `gwcs.WCS()` deep-copying the forward transform)
  are the perf360 REPORT's, not re-run. a2 (the steps form) saved 17 s there, leave-one-out.
- main's `Pipeline` docstring already describes a no-copy, no-validation path for a `_BasePipeline` argument "to allow
  for the efficient creation of pipelines", so the maintainers do care about this cost; the body does not quote it,
  as `_BasePipeline` is private.
- A `copy` keyword also needs the `__init__` overloads of `WCS` and `Pipeline` (two each on main) updated; not
  sketched as a full diff.
