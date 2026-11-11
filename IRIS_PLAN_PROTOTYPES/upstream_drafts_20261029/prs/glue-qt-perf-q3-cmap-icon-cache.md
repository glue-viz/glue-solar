# Cache colormap icon images for QColormapCombo

- Upstream: glue-viz/glue-qt
- Fork branch: `nabobalis:perf-q3-cmap-icon-cache` at `2a3041138f` (pushed 2026-11-12)
- Label: enhancement

## Body

~~~~~markdown
`QColormapCombo` renders an icon for every registered colormap each time a combo is created and each time it is resized. Every image or scatter layer style editor and every subset facet dialog pays for the whole set again, and so does every step of a resize.

The cost is in building an image from the colormap, not in scaling it. `QColormapCombo` now builds one unscaled 200x1 image per colormap, shares it between combos, and scales it to the width of each.

| | main | this PR |
|---|---|---|
| Create a combo after the first, 15 colormaps | 4.6 ms | 0.1 ms |
| Resize a shown combo in 100 one-pixel steps, 15 colormaps | 453 ms | 7 ms |
| Create a combo after the first, 105 colormaps | 33 ms | 0.7 ms |
| Resize a shown combo in 100 one-pixel steps, 105 colormaps | 3.2 s | 44 ms |

PyQt6, Linux. 105 colormaps are glue's 15 and 90 of matplotlib's, registered as plugins do.

What it costs: the cached images (800 bytes of pixels each) and their colormaps outlive the combos, and a colormap changed in place keeps its old image. As the image is now scaled as a pixmap, some columns of an icon can show the neighbouring one of its 200 colour steps.

`test_colormap_combo_icon_cache` in `glue_qt/utils/tests/test_colors.py` fails without the change.
~~~~~

## Notes for the owner (not to paste)

- Existing fork branch, to force-push: reworked from `qt-small/patches/q3-alternative-unscaled-image-cache.diff`. The source is the patch's. The test is the patch's (a second combo at another width renders nothing), with its last assertion changed from "the icon is not null" to "the icon has the combo's icon size", which also checks the scaling.
- The review says the icons are pixel-identical. They are not at every width: over widths 20 to 1300 and glue's 15 colormaps, 997 widths have an icon that differs, by one colour step of 200 at most (largest channel difference 8 of 255). They are identical at 97, 300 and 640. The message and the body say so.
- The numbers are mine, from this machine (niced, offscreen). The old width-keyed branch on the same probe: 0.06 ms to create a combo, 461 ms for the 100-step resize.
- Tests on the branch: `test_colors.py`, 5 passed. Without the source change: `AssertionError: assert 30 == 0` (`render.call_count`), 1 failed, 4 passed.
- ruff: passes.
