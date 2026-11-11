# Fix the exported profile script for subsets that are partial along the profile axis

- Upstream: glue-viz/glue
- Fork branch: `nabobalis:fix-profile-export-partial-subset`, commit 700faed6 (pushed 2026-11-12)
- Label: bug

## Body

~~~~~markdown
The script that `export_as_script` writes for a profile viewer fails when a subset layer's subset does not cover the whole profile axis, for example a range along that axis:

```
ValueError: operands could not be broadcast together with shapes (6,) (3,)
```

The script took the x values from the subset (`layer_data[...]`), which applies the subset's mask, so there were fewer of them than profile values. It now takes them from the subset's data, as the viewer does.

That alone does not give the viewer's plot, because the script also dropped the points where the profile is NaN. The viewer plots them, as gaps, and as the line is drawn in steps from mid-point to mid-point, a line without them ends half a step short. The script no longer drops them.

`test_subset_partial_along_profile_axis` fails on main with the error above, and with only the first change with an image difference (RMS 0.20).
~~~~~

## Notes for the owner (not to paste)

- The commit subject is "Fix exported profile script for subsets partial along the profile axis" (70 characters): the PR title you gave is 83, over the 72 allowed for a subject. Use either as the PR title; the heading above is yours.
- The change: `base_data = layer_data` for a dataset layer, `profile_x_values` from `base_data`, and the `keep` filter removed from the script. Four changed source lines and a three-line test.
- Removing the filter changes every exported profile script, not only subset ones: points where the profile or the x value is NaN are now plotted as gaps, as in the viewer. The 15 existing export tests still pass.
- Tests: `glue/viewers/profile/tests/test_python_export.py` 16 passed. On upstream/main: `ValueError: operands could not be broadcast together with shapes (6,) (3,)`, then `Output image ... glue_plot.png does not exist`. With the x values fixed but the filter kept: `Error: Image files did not match. RMS Value: 0.19577791769133607`.
- It conflicts with `origin/profile-slice` and `origin/profile-wcsaxes`, as expected: rows 31 and 34 are to be rebuilt on top of this.
- The test uses the default function ('maximum').
