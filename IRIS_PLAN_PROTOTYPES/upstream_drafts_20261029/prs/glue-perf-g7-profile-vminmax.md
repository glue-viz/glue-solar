# Only recompute profiles for v_min/v_max changes when normalizing

- Upstream: glue-viz/glue
- Fork branch: `nabobalis:perf-g7-profile-vminmax`, commit 59afe161 (on the fork, not rebuilt)
- Label: enhancement

## Body

~~~~~markdown
`ProfileLayerArtist._update_profile` treats any change of the layer's `v_min` or `v_max` as a reason to compute the profile again. `_calculate_profile_postthread` calls `update_limits`, which sets both from the new profile, so every update that changes the limits (each move of a subset, for example) computes the profile a second time and draws it once more. `v_min` and `v_max` change the plotted values only when the viewer normalizes the profiles, so the profile is now recomputed for them only in that case.

That second pass was also the only thing that showed a profile layer again after a computation in a worker thread had re-enabled it, such as a subset layer that becomes valid again. So `_calculate_profile_postthread` now calls `_update_visual_attributes`, which ends with a redraw, where it called `redraw`. This also fixes a layer that stayed hidden when its limits did not change. The two changes go together: the first alone would hide such layers.

Measured in the Qt profile viewer on a 100x400x400 float32 cube, moving a one-pixel subset 20 times: compute runs per move go from 2 to 1 and canvas draws from 3 to 2, about 8 ms each.

Tests: `test_limits_recompute_only_if_normalized` and `test_threaded_profile_visible_after_enable`.
~~~~~

## Notes for the owner (not to paste)

- Not rebuilt and not run by me: the text is the commit message, shortened. The review marks the branch ready as it is and says it cannot be split.
- The tracker wants it before rows 29 and 32: #2596 and #2601 conflict with it on one line.
