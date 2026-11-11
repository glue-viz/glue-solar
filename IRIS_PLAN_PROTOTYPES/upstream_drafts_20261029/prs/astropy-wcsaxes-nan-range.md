# WCSAxes: no ticks for a non-finite coordinate range instead of raising

- Upstream: astropy/astropy (branch is one commit on main 7732926be)
- Fork branch: `nabobalis:wcsaxes-nan-range` at `9308a07aa3fe0c3e8a72a0e88cbcfffd5d71b1c0` (existing name: force-push)
- Changelog fragment to rename: `docs/changes/visualization/PLACEHOLDER.bugfix.rst` to `<PR number>.bugfix.rst`

## Body

~~~~~markdown
### Description

This pull request is to address `ValueError: arange: cannot compute length`, raised at every draw of a `WCSAxes` whose scalar coordinate is NaN over the whole view, as a WCS gives outside its domain. dkist's gWCS does this for the time beyond an axis it ravels, so an image of such data cannot be panned past that axis.

`find_coordinate_range` gives a NaN range there. The locators' degenerate-range test, `value_min == value_max`, is False for NaN, so `_locate_values` calls `np.arange(nan, nan)`. This PR treats a range that is not finite like the degenerate one: no ticks, a finite sentinel spacing, and no minor ticks. The angle locator gets the same guard for direct calls; in a draw, `find_coordinate_range` already widens an all-NaN angle range to the full circle.

```python
import numpy as np
from astropy import units as u
from astropy.visualization.wcsaxes.formatter_locator import ScalarFormatterLocator

ScalarFormatterLocator(unit=u.s).locator(np.nan, np.nan)
# 8.0.2 and main: ValueError: arange: cannot compute length
# this PR: (<Quantity [] s>, <Quantity 1. s>)
```

<details><summary>Drawing it</summary>

```python
import matplotlib.pyplot as plt
import numpy as np
from astropy import units as u
from astropy.wcs.wcsapi import BaseLowLevelWCS


class NaNPast(BaseLowLevelWCS):
    """x, and a time that is NaN outside rows 0-9."""
    pixel_n_dim = world_n_dim = 2
    world_axis_physical_types = ["custom:x", "time"]
    world_axis_units = ["m", "s"]
    world_axis_names = ["x", "time"]
    axis_correlation_matrix = np.identity(2, dtype=bool)
    serialized_classes = False
    world_axis_object_components = [("x", 0, "value"), ("t", 0, "value")]
    world_axis_object_classes = {"x": (u.Quantity, (), {"unit": "m"}), "t": (u.Quantity, (), {"unit": "s"})}

    def pixel_to_world_values(self, x, y):
        x, y = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
        return 1.0 * x, np.where((np.rint(y) < 0) | (np.rint(y) > 9), np.nan, 10.0 * y)

    def world_to_pixel_values(self, x, t):
        return np.asarray(x, float), np.asarray(t, float) / 10


ax = plt.figure().add_subplot(projection=NaNPast())
ax.set_xlim(-0.5, 9.5)
ax.set_ylim(20, 30)  # past the time's rows
ax.figure.canvas.draw()  # 8.0.2 and main: ValueError: arange: cannot compute length
```

It raises the same way with minor ticks or the grid shown. A view that is only partly NaN draws before and after.

</details>

The new `test_non_finite_range` fails without the change. Only a range that is not finite takes the new branch, and such a range raised before.

### AI Disclosure
Written with Claude Code (Anthropic); model and version: **[OWNER TO FILL: model name and version, not recorded]**. Claude Code wrote the code change, the test, the changelog fragment, the commit message and this description, and ran the tests and the reproducers above. **[OWNER TO ADD: one line on your own review.]**

- [ ] I certify that I am human and that I take full responsibility for this pull request including all interactions with reviewers.

### Merge method
- [ ] By checking this box, the PR author has requested that maintainers do **NOT** use the "Squash and Merge" button. Maintainers should respect this when possible; however, the final decision is at the discretion of the maintainer that merges the PR.
~~~~~

## Notes for the owner (not to paste)

- Blanks to fill in the AI Disclosure: the model name and version (not recorded anywhere), and one line on your own review.
- The certification box is left unticked on purpose: you must tick it yourself. The Merge method box is optional.
- The template's `Fixes #` line is removed, as the template says to do when no issue is closed.
- astropy's AI policy also requires that you engage with reviewers yourself and can explain every change.
- Changed from the fork branch: only the fragment's grammar ("for example with a WCS that returns NaN outside its domain").
- Run: `astropy/visualization/wcsaxes/tests/test_formatter_locator.py`, 135 passed. With main's `formatter_locator.py`: 2 failed, 133 passed, both `test_non_finite_range` cases with `ValueError: arange: cannot compute length`.
- Run: the draw reproducer raises on 8.0.2 and on main's wcsaxes and draws on the branch (plain, minor ticks, grid). An all-NaN angle range reaches the angle locator as (0, 360) and (-90, 90) in a draw, so the angle guard matters for direct calls only, as the body says.
- "main" in these runs is the branch's (main's) `wcsaxes` folder on the compiled core of astropy 8.0.2; astropy main was not built, and the installed copy has no pytest config, so warnings-as-errors was not in force.
- Lint: ruff 0.16.1 check and format pass; upstream pins v0.17.3, which was not available.
- Not run: the whole suite, the docs build, towncrier, the other pre-commit hooks. CI's changelog check fails until the fragment is renamed.
