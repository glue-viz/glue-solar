# Hide replaced slice sliders

- Upstream: glue-viz/glue-qt
- Fork branch: `nabobalis:hide-replaced-slice-sliders` at `1d676dd942` (pushed 2026-11-12)
- Label: bug

## Body

~~~~~markdown
Changing the x and then the y attribute of an Image viewer of 4-D data in one go, from a script for example, leaves two stray sliders at the top left of the viewer's options widget.

`MultiSliceWidgetHelper._clear` closes the sliders it replaces. `close()` does not hide a slider that Qt has not shown yet, so the show that its layout queued still runs after the slider has been replaced. `_clear` now hides each slider before it closes it.

`test_replaced_sliders_stay_hidden` in `glue_qt/viewers/common/tests/test_multi_slice_helper.py` rebuilds the sliders twice before Qt processes events and checks that only the current ones are visible. It fails without the change.
~~~~~

## Notes for the owner (not to paste)

- New branch: the other commit of the fork's `slice-sliders-world-axis` (c14d5f0c). Source hunk and imports unchanged; the test is moved from the top of the class to its end, so that it does not conflict with the world-axis test.
- Tests on the branch: `test_multi_slice_helper.py`, 2 passed. Without the source change: the two replaced `SliceWidget`s are visible (`Extra items in the left set`), 1 failed, 1 passed.
- ruff: passes.
