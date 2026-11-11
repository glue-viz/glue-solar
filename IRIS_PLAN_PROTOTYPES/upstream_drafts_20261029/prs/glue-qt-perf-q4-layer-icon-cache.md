# Cache layer icons by marker and color

- Upstream: glue-viz/glue-qt
- Fork branch: `nabobalis:perf-q4-layer-icon-cache` at `7b2198cc79` (on the fork, not rebuilt)
- Label: enhancement

## Body

~~~~~markdown
`layer_icon` looks up the marker's icon file, loads it as a bitmap, tints it and builds a new `QIcon` on every call. The data collection model calls it for each dataset and subset row whenever the view asks for the decoration role, and the edit subset toolbar calls it for every subset group each time it refreshes its combo box, so the same few icons are built again and again.

The icon is now cached on the marker and the RGBA value of the color (`functools.lru_cache`, 128 entries). Callers share one `QIcon` per marker and color; none of them changes it. Keying on the converted color, not on `style.color`, also covers colors restored from a session, which come back as lists and are not hashable.

A repeated `layer_icon` call goes from about 54 µs to about 1 µs.

`test_icon_role` in `glue_qt/core/tests/test_data_collection_model.py` fails without the change.
~~~~~

## Notes for the owner (not to paste)

- Not rebuilt: the fork's branch as it is, 2 files, +28 -3. The body is drawn from its commit message.
- Checked today: `test_data_collection_model.py` passes on the branch (16 passed); on main `test_icon_role` fails (`assert <QIcon ...> is <QIcon ...>`). The 54 µs and 1 µs are the commit's own, not re-measured.
