# Save a Quantity in sessions

- Upstream: glue-viz/glue
- Fork branch: `nabobalis:session-quantity-saver`, commit fb93b7a1 (pushed 2026-11-12)
- Label: bug

## Body

~~~~~markdown
An astropy `Quantity` reaches the `np.ndarray` saver, whose `np.save` raises `TypeError: no implementation found for 'numpy.save' on types that implement __array_function__`. The loop that filters `Data.meta` skips only values that raise `GlueSerializeError`, so one `Quantity` in `Data.meta` aborts the whole session save.

This adds a saver and a loader for `Quantity`. The record is `{"value": <nested lists>, "unit": <string>}`.

Limits:

- The dtype is not kept: the value goes through `tolist()` and comes back as a float64 `Quantity`, so float32 and integer values become float64.
- A subclass is not kept: an `Angle`, for example, loads as a plain `Quantity`.
- The unit goes through the existing unit saver, so a unit glue cannot read back still raises `GlueSerializeError`, and such a value is left out of `meta` as before.

`test_astropy_quantity` fails on main with the `TypeError` above.
~~~~~

## Notes for the owner (not to paste)

- The saver and loader are the fork branch's, unchanged apart from the comment's wording.
- The test is new and shorter than `test_save_meta_quantity`: one `Data` with a scalar, an array and a custom-unit Quantity in `meta`. It sits after `test_astropy_compound_units`, far from the colormap tests, so the two PRs merge in either order (checked with `git merge-tree`).
- I checked the limits: a float32 Quantity and an `Angle` both load as a float64 `Quantity`.
- Not handled: a complex Quantity still fails at JSON encoding, as on main.
- Known and unchanged: a value left out for its unit is tried again on each `do_all` pass and then fails as "Circular reference detected". The outcome is the same (the value is left out).
- Tests: `glue/core/tests/test_state.py` 41 passed. On upstream/main: `TypeError: no implementation found for 'numpy.save' on types that implement __array_function__: [<class 'astropy.units.quantity.Quantity'>]`.
- Lint: no new findings (the same three on upstream's own lines of `state.py`).
