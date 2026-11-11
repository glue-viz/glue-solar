# Save and restore a dataset's preferred colormap in sessions

- Upstream: glue-viz/glue
- Fork branch: `nabobalis:fix-session-style-meta`, commit f8d8d1a5 (pushed 2026-11-12)
- Open PR: #2597 (draft)
- Label: bug

## Body

~~~~~markdown
Saving a session fails with `TypeError: Object of type ListedColormap is not JSON serializable` for any dataset or subset whose `style.preferred_cmap` is set: the setter turns even a name into a `Colormap`, and `_save_style` writes that object into the record. `_load_style` drops the attribute.

`_save_style` now stores the colormap's name, and `_load_style` sets it again through the `preferred_cmap` setter. Older sessions load as before, and released glue ignores the new value when it loads a session saved with this change.

Why this does not use the existing `@saver(Colormap)`: its loader, `_load_cmap`, looks the name up with `colormaps[name]`, which raises `KeyError` for a colormap that is not registered under its name, so a session that saved would not load again. Here such a colormap loads as `None`, with a warning. The style record also holds plain values, not `context.do` records, and the setter already resolves a name through matplotlib's colormaps and then glue's.

Both new tests, `test_data_style_preferred_cmap` and `test_data_style_unknown_preferred_cmap`, fail on main with the `TypeError` above.

This PR no longer changes how `meta` is filtered. Saving a `Quantity` is now a PR of its own (#NNNN).
~~~~~

## Notes for the owner (not to paste)

- Replace #NNNN with the number of the `session-quantity-saver` PR once it is open, or delete that sentence.
- Dropped from the fork branch: `_save_meta`, its warning and the Quantity saver and loader (the last is now `session-quantity-saver`).
- Two small changes to what was kept. `_save_style` is one line, `getattr(style.preferred_cmap, 'name', None)`, without the `if 'preferred_cmap' in result` guard, which could not be false any more. The tests are renamed to sit beside `test_data_style`, and the restore is asserted with `d2.style.preferred_cmap.name == 'viridis'` instead of `d2.style == d.style`.
- I checked the answer about `@saver(Colormap)`: `_load_cmap({'cmap': 'not-registered'}, None)` raises `KeyError`.
- Tests: `glue/core/tests/test_state.py` 42 passed. On upstream/main both new tests fail: `TypeError: Object of type ListedColormap is not JSON serializable`.
- It merges cleanly with `session-quantity-saver` and with `perf-g9-session-do-all`, which touch the same two files.
- Lint: ruff 0.16.1 reports three findings in `glue/core/state.py`, all on upstream's own lines and present on upstream/main too.
