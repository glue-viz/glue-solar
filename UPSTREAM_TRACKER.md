# Upstream tracker

Every patch glue-solar has for another project, as the pull request it is or should become, and where it stands.
One row per PR, in the order to open them. The review behind the "Before opening" column is
[REVIEW-20261112.md](IRIS_PLAN_PROTOTYPES/upstream_drafts_20261029/REVIEW-20261112.md); the reasons each patch
exists are in [UPSTREAM_REVIEW.md](UPSTREAM_REVIEW.md).

State on 2026-11-12: all branches on the forks (`nabobalis/glue`, `glue-qt`, `astropy`, `dkist`, `ndcube`) are
rebased onto their upstream's main of that day, and no commit message carries a session trailer. The same day the
branches the review asked for were fixed, squashed or split out and pushed (the rows marked built), the live drafts
were updated in place, and glue #2595 was closed. Nothing new has been opened. Rules for every PR (user,
2026-11-12): one purpose, the smallest diff that does it, one commit, a test that fails without the fix, and a title
and body a maintainer who has never seen glue-solar can follow. A PR text with `#NNNN` in it waits for the number of
the PR it builds on.

To refresh the PR and State columns: `gh pr list -R <upstream> --author nabobalis --state all --json number,title,state,isDraft,mergedAt,headRefName`.
State is one of: not built (the branch for this PR does not exist yet), built (on the fork, not opened), draft,
open, merged with its date, closed.

This file maps each branch to its PR. For the live state, checks and reviews of every PR opened on glue and glue-qt:
https://github.com/pulls?q=is%3Apr+author%3Anabobalis+org%3Aglue-viz+-repo%3Aglue-viz%2Fglue-solar+sort%3Aupdated-desc

## glue (`glue-viz/glue`)

`CHANGES.md` is generated from PR titles and labels: no changelog line, a `bug` or `enhancement` label instead. A
maintainer said on #2595 that he does not review drafts, so open PRs as ready.

| # | PR | From branch | Lines | Before opening | Needs | PR | State |
|---|---|---|---|---|---|---|---|
| 1 | Keep correlated world inputs in world2pixel_single_axis | `fix-world2pixel-correlated-axes` | 31 | mark ready | | #2598 | draft |
| 2 | Apply a restored layer's `cmap_bad` | `fix-restored-cmap-bad` | 28 | nothing | | | built |
| 3 | Return an empty array unchanged from unbroadcast | `fix-unbroadcast-empty` | 10 | nothing | | | built |
| 4 | Skip pairs with no physical type in common in wcs_autolink instead of raising ValueError | `fix-wcs-autolink-no-common-type` | 29 | nothing | | | built |
| 5 | Fix the exported profile script for subsets that are partial along the profile axis | `fix-profile-export-partial-subset` | 10 | nothing | | | built |
| 6 | Use matplotlib's date epoch in datetime64 <-> mpl conversions | `fix-datetime-epoch` | 122 | mark ready (it raises the matplotlib minimum from 3.2 to 3.3, as the body says) | | #2599 | draft |
| 7 | Save and restore a dataset's preferred colormap in sessions | `fix-session-style-meta` | 35 | mark ready; name 8's PR in the body once it is open | | #2597 | draft |
| 8 | Save a Quantity in sessions | `session-quantity-saver` | 29 | nothing | | | built |
| 9 | One link update when a dataset or component is removed | `perf-g3-batch-link-removal` | 40 | nothing | | | built |
| 10 | One pass over links per depth in discover_links | `perf-discover-links` | 81 | nothing | 9 first (same file) | | built |
| 11 | Keep the link manager's links in the order they were added | `stable-link-order` | 35 | nothing | merges cleanly with 9 and 10, in any order | | built |
| 12 | Import scipy.optimize only when approximating a WCS link as affine | `perf-g5-lazy-scipy-optimize` | 17 | nothing | before 13 | | built |
| 13 | Fix WCSLink between datasets with APE 14 WCSes other than astropy.wcs.WCS | `ape14-wcs-link` | 141 | decide on the 6-line guard against a transposed link (left out; the body states the limit) | | | built |
| 14 | Try a WCS link at the middle, first and last pixel of both datasets | `wcs-link-trial-pixels` | 75 | nothing | 13 | | built |
| 15 | Autolink datasets whose coords are low-level-only APE 14 WCSes | `wcs-autolink-low-level` | 32 | nothing | 13 | | built |
| 16 | Refuse NaN links between non-astropy WCSes in WCSLink's general case | `wcs-link-refuse-nan` | 91 | nothing: rebuilt so that every pair that links on main still links (user, 2026-11-12); a pair with one astropy.wcs.WCS is never refused | 14 | | built |
| 17 | Match world axes by physical type when WCSLink cannot tell them apart by class | `wcs-link-match-world-axes` | 87 | nothing; its source change and first test would also stand on main alone (60 lines), the second test needs 13 | 13, 16 | | built |
| 18 | Set image axis labels once per WCS reset | `perf-g1a-wcs-labels` | 43 | quote 103 to 71 ms, the commit's own number | | | built |
| 19 | Skip update and redraw of hidden image subset layers | `perf-g2-hidden-subset-layers` | 44 | nothing | | | built |
| 20 | No IPython import from viewers.common.viewer | `perf-g6-lazy-ipython` | 22 | say it needs glue-qt's half to gain in a Qt session | | | built |
| 21 | Serialize each object once per session save | `perf-g9-session-do-all` | 44 | nothing | | | built |
| 22 | view_shape for index arrays without building the view | `perf-g10-view-shape` | 37 | nothing | | | built |
| 23 | Return float32, not float64, for a float32 component and a scalar | `perf-g4-scalar-broadcast` | 33 | nothing | | | built |
| 24 | Slice-subset histogram without a full mask | `perf-g8-slice-histogram` | 43 | nothing | | | built |
| 25 | Recompute profiles for v_min and v_max only when normalizing | `perf-g7-profile-vminmax` | 75 | nothing | before 29 and 32 | | built |
| 26 | Read a DaskComponent at several index arrays | `dask-component-index-arrays` | 38 | put 3's PR number in the body | 3 | | built |
| 27 | Sample only the pixels a buffer needs from a DaskComponent | `frb-sample-dask-pixels` | 68 | put 26's PR number in the body | 26 | | built |
| 28 | Read coupled index arrays of a DaskComponent through vindex (optional) | from `fix-frb-dask-index-arrays` | ~26 | only to retire glue-solar's own `vindex` branch | 26 | | not built |
| 29 | Add a 'slice' collapse function to the profile viewer | `profile-slice`, rebuilt from its head | ~150 | gate both `slices` callbacks on the function; say released glue-qt would list 'Slice' with no slider | | #2596 | draft, parked |
| 30 | Show 'slice' profiles for layers of linked datasets | from `profile-slice` | ~70 | | 29 | | not built |
| 31 | Export 'slice' profiles to Python scripts | from `profile-slice` | ~65 | | 5, 29 | | not built |
| 32 | Add opt-in WCSAxes tick labels to the profile viewer | `profile-wcsaxes`, its own lines | ~300 | show only the world axis of `x_att` (wrong ticks for coupled axes today); can go straight onto main; settle the default with glue-qt #70 | | #2601 | draft, parked |
| 33 | Reset profile x limits saved in the other coordinate mode | from `profile-wcsaxes` | ~80 | | 32 | | not built |
| 34 | Export WCSAxes profile viewers to Python scripts | from `profile-wcsaxes` | ~85 | | 5, 32 | | not built |

#2595 was closed on 2026-11-12 without a comment, as 4, 13, 15 and 17 replace it; the comment to post once those
four are open is in `prs/close-2595.md`. Two things #2595 did have no replacement: its check that a dataset has as
many dimensions as its WCS, and skipping `SlicedLowLevelWCS` when nothing is sliced (which 1-D WCSes need on astropy
before 7.2; CI's py310 jobs install 6.1, not tested here). Its fork branch is deleted; the commits stay on glue-viz/glue
as `refs/pull/2595/head`.

## glue-qt (`glue-viz/glue-qt`)

glue-qt main's CI has been broken since 2026-02 and stops before any test runs. #69 fixes it: until it merges, every
other glue-qt PR shows 32 failing checks that say nothing about the PR. Open the rest in batches after it.

| # | PR | From branch | Lines | Before opening | Needs | PR | State |
|---|---|---|---|---|---|---|---|
| 1 | Fix CI: pytest-flake8, missing 'all' extra, leaked test viewers | `ci-fixes` | 20 | approved 2026-10-07; needs a maintainer to merge (the fork owner is pull-only); a comment on the overlap with their #65 would close the one open thread | | #69 | open |
| 2 | Fix the fit settings dialog for check box (BoolOption) options | `fit-settings-bool-option` | 18 | nothing | | | built |
| 3 | Profile fit: use the fitter configured in Settings | `fitter-settings` | 85 | decide how a value or bound set in Settings is cleared again (one line here, or in glue's `set_constraint`) | | | built |
| 4 | Profile fit: Clear removes every artist a fitter plots | `fit-artists` | 34 | nothing | | | built |
| 5 | Slice sliders: read the world axis glue's world components use | `slice-sliders-world-axis` | 39 | nothing | | | built |
| 6 | Hide replaced slice sliders | `hide-replaced-slice-sliders` | 31 | nothing | | | built |
| 6a | Slice sliders: warn only if the world axis shown depends on another axis | `slice-slider-dependent-axis-warning`, on 5 | 31 | put 5's PR number in the body | 5 | | built |
| 7 | Keep the edit subset when a dataset or another subset group is removed | `edit-subset-tree-rebuild` | 60 | nothing | | | built |
| 8 | Profile tools: use the display unit for Navigate and Collapse | `profile-tools-display-unit` | 34 | nothing | | | built |
| 9 | ComputeWorker: block on the work queue instead of polling | `perf-q1-worker-block` | 52 | nothing | | | built |
| 10 | Cache layer icons by marker and color | `perf-q4-layer-icon-cache` | 31 | nothing | | | built |
| 11 | Import the IPython terminal only when it is first opened | `perf-q5-lazy-terminal` | 44 | nothing | pairs with glue 20 | | built |
| 12 | Import QtQuick only when creating the Qt6 application | `lazy-qtquick-import` | 14 | nothing | before 21 | | built |
| 13 | Use the system fixed-width font for the profile fit log | `fit-log-fixed-font` | 14 | nothing | | | built |
| 14 | Profile viewer: small slice subsets of large data skip the worker | `perf-q2-slice-profile-sync` | 55 | put 9's PR number in the body | 9 merged | | built |
| 15 | Cache colormap icon images for QColormapCombo | `perf-q3-cmap-icon-cache` | 32 | nothing (the body says icons can differ from main's by one colour step) | | | built |
| 16 | Add an `applies` function to layer actions | `layer-action-applies` | 57 | nothing | | | built |
| 17 | Label slice sliders of WCS time axes with absolute times | `slice-widget-time-axis`, on 5 | 154 | the branch is fixed and squashed; the PR's description is still the owner's own, and the new text (which needs the numbers of 5 and 6a) is in `prs/`; a FITS WCS without MJDREF inside `SlicedLowLevelWCS` still shows 1858 dates | 5 | #75 | draft |
| 18 | Show the position under the mouse in the viewer status bar | `status-bar-cursor-readout` | 46 | owner: rewrite the description, which still describes the value readout (a draft is in `prs/`); look once on a real screen at the label beside a long status tip | | #74 | draft |
| 19 | Show the value under the mouse in an image viewer's status bar | from `status-bar-cursor-value` (#74 as it was, 6b579814) | ~70 | settle the read in the GUI thread on every move first | 18 | | not built |
| 20 | Let a fitter provide its own settings dialog (`settings_widget`) | `fitter-settings-widget`, on 3 | 43 | put 3's PR number in the body | 3 merged | | built |
| 21 | Show glue's name in the macOS menu | `macos-integration`, in part | ~30 | needs a Mac; drop the commit that repeats 1; an open review comment says the Dock label is unchanged | 12 | #68 | open |
| 22 | macOS fonts and icon sizes | from `macos-integration` | ~130 | it changes Linux and Windows too as written: gate on macOS or retitle | 21 | | not built |
| 23 | Profile viewer: slice sliders | from `profile-wcs-pr` | ~120 | no hasattr gate: a glue-core floor | glue 29 released | #70 | draft, parked |
| 24 | Profile viewer: WCSAxes wiring | from `profile-wcs-pr` | ~40 | decide the default first: as written it switches every Qt profile to pixel units | glue 32 to 34 released | | not built |

## astropy, dkist, ndcube

Reworked and pushed on 2026-11-12; their texts, like those of every built glue and glue-qt row, are in
`IRIS_PLAN_PROTOTYPES/upstream_drafts_20261029/prs/`. astropy
and ndcube require an AI disclosure in the PR body (astropy also a certification the owner ticks himself); each
branch carries a changelog fragment named `PLACEHOLDER` to rename to the PR number.

| # | PR | Upstream | From branch | Lines | Before opening | PR | State |
|---|---|---|---|---|---|---|---|
| 1 | WCSAxes: no ticks for a non-finite coordinate range instead of raising | astropy | `wcsaxes-nan-range` | 33 | owner: fill the model and version in the AI disclosure, add a line on your own review, tick the certification; rename the `PLACEHOLDER` fragment | | built |
| 2 | Card: test the value type and card image before reading two config items | astropy | `fits-card-config-reads` | 35 | as 1; its new test counts config reads (824 to 61 for a 412-card header) and may be seen as pinning an implementation detail | | built |
| 3 | wcsaxes: import pytest only when matplotlib is missing | astropy | `perf-a1-wcsaxes-pytest-import` | 33 | as 1; cites astropy#10302 | | built |
| 4 | Unravel and sanitize_index: treat a non-finite index as off the table | dkist | `nan-lookup-indices` (two commits, reviewed in order) | 71 | rename the `PLACEHOLDER` fragment | | built |
| 5 | Fix copy.copy of an NDMeta sharing its axes, comments and data shape | ndcube | `ndmeta-copy` | 26 | owner: write the description in your own words (sunpy's AI policy counts pasted AI text as inappropriate); rename the fragment | | built |
| 6 | Share values that are not axis-aware when slicing an NDMeta | ndcube | `ndmeta-slice-shallow-copy`, on 5 | 29 | as 5; cites sunpy/ndcube#815; ndcube's template asks for an issue first (the unposted "Slicing deep-copies the whole NDMeta") | | built |

## Issues, comments and the email

Texts are in `IRIS_PLAN_PROTOTYPES/upstream_drafts_20261029/reports/`; their reproducers are local only (OPERATIONS.md).

| Text | Where | State |
|---|---|---|
| A linked layer's buffer over the whole view | glue, new issue | not posted |
| World axes of data with more world than pixel axes | glue#2574, comment | not posted |
| `VaryingCelestialTransform`'s thread race and per-index rebuild | dkist, new issue | not posted |
| Whole-file reads | dkist#226, comment | not posted |
| Eight threads corrupt -TAB results | astropy#19174, comment | not posted |
| The fork-safety audit hook slows every deepcopy | filelock, new issue | not posted |
| Slicing deep-copies the whole NDMeta | ndcube, new issue (goes with ndcube 6 above) | not posted |
| `WCS(model, ...)` always deep-copies the model | gwcs, new issue | not posted |
| `enable_record_valued_keyword_cards = False` ignored for parsed card images | astropy, new issue | not posted |
| The red-blue profile cube cannot be printed | LM-SAL/irispy#360, comment | posted 2026-11-11 |
| `tabs2x()` on 2-D -TAB tables | email to WCSLIB's author | not sent |
