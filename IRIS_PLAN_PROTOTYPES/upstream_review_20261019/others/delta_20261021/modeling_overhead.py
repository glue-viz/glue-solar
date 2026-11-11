"""R37: astropy.modeling's per-call overhead on a one-point evaluation of a slit-jaw frame's celestial chain.

Shift & Shift | AffineTransformation2D | Scale & Scale | Pix2Sky_TAN | RotateNative2Celestial, as dkist's
`generate_celestial_transform` builds per frame; numpy's own arithmetic for the same point for scale.

Run: python -I modeling_overhead.py
"""

import cProfile
import pstats
import time

import numpy as np

import astropy
from astropy.modeling import models as m

chain = (
    (m.Shift(-208.0) & m.Shift(-194.0))
    | m.AffineTransformation2D(matrix=[[0.9998, -0.0175], [0.0175, 0.9998]])
    | (m.Scale(0.1663 / 3600) & m.Scale(0.1663 / 3600))
    | m.Pix2Sky_TAN()
    | m.RotateNative2Celestial(-0.055, 0.028, 180.0)
)


def best(f, n=2000):
    t = time.perf_counter()
    for _ in range(n):
        f()
    return (time.perf_counter() - t) / n * 1e6


print("astropy", astropy.__version__)
print(f"one point: {best(lambda: chain(100.0, 100.0)):.0f} us a call")
xs = np.random.default_rng(0).uniform(0, 400, 10_000)
print(f"10,000 points: {best(lambda: chain(xs, xs), 200):.0f} us a call")
profile = cProfile.Profile()
profile.runcall(chain, 100.0, 100.0)
stats = pstats.Stats(profile)
calls = {name: n for (_, _, name), (n, *_) in stats.stats.items()}
print("Python function calls in one evaluation:", sum(n for (*_,), (n, *_) in stats.stats.items()),
      "| isinstance:", calls.get("<built-in method builtins.isinstance>", 0),
      "| len:", calls.get("<built-in method builtins.len>", 0))
