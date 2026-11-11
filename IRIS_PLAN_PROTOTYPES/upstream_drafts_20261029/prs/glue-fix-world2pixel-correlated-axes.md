# Keep correlated world inputs in world2pixel_single_axis

- Upstream: glue-viz/glue
- Fork branch: `nabobalis:fix-world2pixel-correlated-axes`, commit 1131be9d (pushed 2026-11-12)
- Open PR: #2598 (draft)
- Label: bug

## Body

~~~~~markdown
`world2pixel_single_axis` keeps the world inputs that are directly correlated with the requested pixel axis and collapses every other input to its first element. That is wrong when a kept input shares a pixel axis with a collapsed one. For a cube whose celestial axes depend on time, inverting pixel axis x needs the time of each element, but time was collapsed, so every element was inverted at the first time step.

The inputs kept are now the transitive closure, over shared pixel axes, of the world axes correlated with the requested pixel axis.

`test_world2pixel_single_axis_correlated_axes` uses a plain 2-D FITS WCS with a `PC` term (world 0 = x + 10 t, world 1 = t). For three points that all sit at pixel x = 5, main returns [5, 15, 25].
~~~~~

## Notes for the owner (not to paste)

- The two commits are squashed into one with the first commit's message. No code change: `git diff origin/fix-world2pixel-correlated-axes fix-world2pixel-correlated-axes` is empty.
- The title is unchanged. The body above replaces the live one, which quotes numbers from an IRIS cube that a maintainer cannot reproduce; this one quotes the test's own numbers, which I ran.
- Tests: `glue/core/tests/test_coordinates.py` 28 passed. On upstream/main the new test fails: `Mismatch at indices: [1]: 15.0 (ACTUAL), 5 (DESIRED); [2]: 25.0 (ACTUAL), 5 (DESIRED)`.
- Then mark it ready: a maintainer said he does not review drafts.
