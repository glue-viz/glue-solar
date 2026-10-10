# Glue speed

A to-do list of performance problems in glue-core 1.27.0, glue-qt 0.4.2 and the libraries under them (astropy, matplotlib, irispy), and in glue-solar itself, found by a profiling survey of real IRIS quicklook workflows on 2026-10-01. Nothing was patched: every item is a measured cost with a cause and a candidate fix, to be re-verified and then fixed (upstream on the user's direction, as M4 work in `IRIS_GLUE_GAP_PLAN.md`; glue-solar's own items were M0 work, merged as #90, #95 and #98).

**How it was measured.** Offscreen Qt with Agg on macOS (24 GB), app 1600x1000, device pixel ratio 1 and an emulated 2 (`QT_SCALE_FACTOR=2`), in the `iris-plan` env (glue-core 1.27.0, glue-qt 0.4.2, irispy 0.9.1, astropy 8.0.1, matplotlib 3.11.2, numpy 2.5.3), glue-solar at main 2fdb847 with key results re-run at 5eae565. Data from `~/DATA/IRIS`: 4000255147 (sit-and-stare Si IV 1403, 1600x417x262, and SJI 1400), 4000005156 (two-scan stack, deconvolved SJI 2796), 3602506433 (99 scans), 3824262996. Timings are medians of repeated steps after warm-up, taken with `perf_counter` wrappers at code boundaries (cProfile only for structure; it inflates times about 4.6x). Seven areas were profiled by one agent each, and a second agent re-measured each area's top findings. Offscreen Agg differs from a real screen; real-screen and Wayland numbers were not taken.

**Re-running.** The survey's scripts are in `IRIS_PLAN_PROTOTYPES/perf_survey_20261001.tar.gz` (132 scripts; extract it into a scratch directory). Evidence paths below are relative to that archive. Run with `env HOME="$(mktemp -d)" QT_QPA_PLATFORM=offscreen MPLBACKEND=agg ~/mamba/envs/iris-plan/bin/python <script>`, with a glue-solar checkout first on `sys.path` as the scripts do. Logs and profiles were not kept; the numbers below are the record.

**Second survey.** The large SST SOLARNET cubes and the biggest IRIS sets were measured on 2026-10-10, under 'SST and IRIS stress survey, 2026-10-10' below (SST1-SST13, verified the same day).

**How to use this file.** Tick an item's first box when its cost has been re-measured on current versions (note the date and numbers), and the second when it is fixed and released upstream (link the PR). Items are ranked by the time an IRIS user loses.

## Summary

Scope: offscreen Qt with Agg on macOS, at DPR1 and an emulated DPR2. Versions: glue-core 1.27.0, glue-qt 0.4.2, astropy 8.0.1. glue-solar was at 2fdb847, three merges behind origin/main 5eae565; a few items were re-run on 5eae565. Every glue and glue-qt file cited is unchanged on upstream main.

- **Draw.** At quicklook panel sizes, WCSAxes ticks and frame take 74-88% of every draw. The driver is the per-call cost of the WCS: about 0.36 ms per gWCS call, 37-59 calls per draw, of which only 17-20 are distinct. On slice steps the larger cost comes before the draw. glue's _set_wcs resets the axis labels, which triggers 4 eager astropy tick placements, about 66% of an SJI frame step. The image path dominates only on maximized or HiDPI panels (44-57%). Extra draws come from hidden subset layers, hidden tabs and glue-solar's coordinator timer.
- **IO.** Loading itself is fast: 0.39 s per Si IV window, with no copy. The cost is repeated gzip decompression (4-5 passes per SJI .fits.gz, 0.8 s per browser scan) and session save writing broadcast components in full (1.4 GiB for 2 scans).
- **Links.** discover_links grows about O(N^3): 6.8 s per link change at 102 datasets, 249 s for all-pairs at 99. Removal runs one full update per link (30 s at 53 datasets). A raster ROI shown on the SJI inverts the -TAB raster WCS for every screen pixel, once per attribute: 4.8 s per frame, about 30 s at DPR2. Any link change recomputes that mask.
- **Events.** echo and hub dispatch are under 1% of every action. The cost is in what the callbacks trigger: _set_wcs on slice changes, the 25 Hz polling profile worker running twice per point move (the spectrum is about 250 ms late in the quicklook), redundant redraws, and colormap icons rendered eagerly.

Top three upstream opportunities:
1. **glue-core `_set_wcs`:** put labels on the coords via set_axislabel; a lazy set_xlabel in astropy is the alternative. Measured: SJI frame step 105 -> 39 ms, click -130 ms, quicklook open -0.6 s.
2. **glue-core linked ROI mask:** one inversion per mask plus a cull to the ROI's footprint. Measured: 4.8 s -> 0.21 s per SJI frame.
3. **glue-qt / glue-core profile worker:** thread by work size rather than parent size, block on the queue, and stop re-running on v_min/v_max. Measured: quicklook spectrum about 368 -> 115 ms per point move.

Close behind are the hidden-subset redraws (-27 to -35 ms per move) and the discover_links rewrite (64-664x).

Not measured: real screens and Wayland, Mg II k windows, cold disk, Qt6.

## Ranked upstream findings

### R1. Every slice change re-runs glue's _set_wcs, and its axis-label round trip forces 4 eager WCSAxes tick placements

- [ ] Re-verified on current versions
- [ ] Fixed upstream

- Worked around in glue-solar by a probe-gated patch (#90): SJI step 104 → 35 ms on 4000255147 together with the other #90 fixes. Prototyped 2026-10-01: the glue-side fix takes the SJI set phase from 66 to 0.4 ms; astropy's lazy-label alternative is in 'WCSAxes tick rendering' (prototype 3, PR 4).

**Repository:** glue-core (astropy alternative, which also helps sunpy users). **Confidence:** high. **Verification:** Confirmed by the draw, events, hidpi-many and startup verifiers. Merged from draw#1, events#1, hidpi-many#1 and startup#2; links#7 is an untested duplicate.

**Slows.**

Frame steps on the SJI, plus raster slider steps where the displayed coordinates depend on the stepped axis: the sit-and-stare exposure step, the λ-time slit step and the stack raster step. Also: a Pixel click (the coordinator then moves 3 sliders), an x_att change, opening the quicklook and creating any image viewer.

**Cost.**

Remeasured at DPR1 (medians):
- SJI frame step: 104-109 ms, of which _set_wcs is 69 ms (66%). That splits into reset_wcs 0.6 ms, 2x set_xlabel 32 ms and 2x set_ylabel 32 ms.
- Pixel click: about 140 ms of 378-389 ms (36%, 3 calls).
- Exposure step: 31-32 ms of 205-233 ms.
- Stack raster step: 41 of 233 ms. λ-time slit step: 40 of 214 ms.
- x_att change: 65 of 106 ms (2 calls).
- Quicklook open: 84 tick placements inside label callbacks, 0.73-0.77 s (about 40% of quicklook()).
- New image viewer: 34-36 ms (30-39%).
In 1 of 4 exposure steps the SJI frame also moves, which adds 70-75 ms (mean 220 ms against a median of 204 ms).

**Cause.**

1. glue/viewers/image/viewer.py:96-98 `_on_slice_change` calls `_set_wcs` (100-150).
2. `_set_wcs` calls reset_wcs, sets x/y_axislabel to '' (120-121), then sets them back through _update_axes (74-82).
3. Each set goes through glue/viewers/matplotlib/viewer.py:152-162 to astropy WCSAxes.set_xlabel/set_ylabel (core.py:596-598, 613-615). Those call _update_tick_and_label_positions eagerly, and the next draw places the ticks again.
4. x_att and y_att both trigger _set_wcs (viewer.py:47-48), so changing an axis runs it twice.
Upstream: unchanged on glue main (GitHub 77dc9b88 checked by raw URL) and on astropy main 1f930be7c4 (core.py:685, 715).

**Candidate fix.**

glue-core: after reset_wcs, put the labels directly on the coordinate helpers with axes.coords[ndim-1-att.axis].set_axislabel(...), the axis mapping update_x_ticklabel already uses. Do not call WCSAxes.set_xlabel/set_ylabel. Do this in every _set_wcs, not only on slice changes, and merge the x_att and y_att changes into one _set_wcs. Dropping only the '' round trip saves about half.
astropy alternative: set_xlabel/set_ylabel store the label and pick its coordinate at draw time. Marking the ticks stale is not enough, because the coordinate is chosen from the tick update.

**Gain.**

End-to-end emulations, pixel-identical canvas, ticks and labels identical in 15/15 steps:
- SJI frame step: 105-109 -> 38-41 ms (-63%).
- Pixel click: 378-381 -> 246-247 ms (about -131 ms).
- Si IV tick at 800x500: 60.5 -> 30.3 ms.
- Exposure step: -13 to -35 ms end to end (the profile-worker tail sets the end).
- Stack raster step: 238 -> 206 ms. λ-time slit step: 220 -> 184 ms.
- Quicklook open: 1.91 -> 1.29 s (-0.6 s). This needs the label change in every _set_wcs or the astropy fix; slice-only gives -0.14 s.
- New image viewer: about -35 ms.
- Drag: with coalescing, about 29 SJI draws/s against 5 today.

### R2. A raster ROI shown on a linked slit-jaw viewer inverts the raster WCS for every screen pixel, once per ROI attribute

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-core. **Confidence:** High for (1), medium for (2).. **Verification:** Confirmed (links#1, links#2). The links#2 gain was corrected: 10-22x is the total gain, not a gain on top of the 2x.

**Slows.**

Changing the SJI frame (slider, play, coordinator time sync), or any redraw after the cache is dropped, while an ROI drawn on a raster map is shown on the SJI.

**Cost.**

In the app (quicklook SJI 484x252 px, DPR1, n=5):
- 4000255147: 4.79 s per frame with the ROI, against 0.10 s without (98%).
- 4000005156: 0.57 s against 0.10 s (83%).
- Doubled buffer, standing in for DPR2: 29.7 s per frame.
Each of the two attribute evaluations is 48-49% of the mask and runs the identical inversion. 67% of each inversion goes to screen pixels outside the raster footprint, which can only produce False.

**Cause.**

- glue/core/subset.py:563-564 RoiSubsetStateNd.to_mask evaluates data[xatt] and data[yatt] separately.
- Each goes through component_link.py:166/375 to coordinate_helpers.py:122-124 world2pixel_single_axis, which runs the full world_to_pixel_values and keeps one axis. glue-solar's gated copy (glue_patches.py:52-54) does the same.
- fixed_resolution_buffer.py:312 calls get_mask for every screen pixel. The pixel shortcut at subset.py:569 applies only to the data's own pixel cids.
Upstream: unchanged on glue main.

**Candidate fix.**

1. Compute every needed pixel axis of the linked dataset from one world_to_pixel_values call per to_mask/get_mask. Use a cache keyed on coords, input cids and view, shared by sibling CoordinateComponentLinks.
2. For ROIs on another dataset's pixel or world cids, map the ROI outline forward and evaluate the inverse chain only inside its bounding box plus a margin. Fall back to the current path when the forward chain is missing or not finite.

**Gain.**

Measured outside glue; masks 100% identical to glue's.
- (1) alone: 4.64 -> 2.26 s (2.06x), 0.463 -> 0.205 s, 29.7 -> 14.3 s.
- (1)+(2): 4.64 -> 0.21 s (21.8x), 29.7 -> 2.92 s (10.2x), 0.463 -> 0.048 s (9.8x).
Only rectangular raster-pixel ROIs were tested. The outline bound holds because each exposure maps the slit affinely.

### R3. The spectrum waits on glue-qt's 25 Hz polling worker twice per point move, because a one-pixel profile is sized by its parent cube

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-qt (polling, size threshold); glue-core (v_min/v_max trigger). **Confidence:** high. **Verification:** Confirmed (profile-stats#1, events#2). The profile-stats verifier corrected the quicklook numbers (a measurement-pump artifact); the events verifier corrected the tail share.

**Slows.**

Every Point move (Pixel click or drag, raster time step) until the spectrum panel shows the new spectrum. Also ROI drags in a Profile viewer.

**Cost.**

Lone Profile viewer:
- 80.9 ms to the first correct spectrum, against 10.8 ms synchronous (stack: 66.5 against 8.7 ms).
- Per move: 2 worker runs and 3 spectrum draws (26.8 ms).
Quicklook (sit-and-stare):
- The spectrum is drawn at 360-382 ms threaded, against 87-90 ms synchronous, and painted at 368 against 117 ms.
- So the worker costs about 250-290 ms (75%) of the spectrum's latency. Its result lands behind the main-thread _set_wcs block of rank 1.
- The worker tail after the image panels is 34-38 ms (15%) of a time step.
Idle round trip: 23 ms to start, 0.5 ms of compute, 43 ms from compute end to postthread.

**Cause.**

- glue_qt/viewers/matplotlib/compute_worker.py:33 polls with time.sleep(1/25) and emits compute_end only on the next empty poll (40-46).
- glue_qt/viewers/profile/layer_artist.py:50 threads any layer with state.layer.size > 1e7. Subset.size is the parent's size (glue/core/subset.py:406): 174,806,400 here.
- glue/viewers/profile/layer_artist.py:82 calls update_limits in postthread, and v_min/v_max are recompute triggers (123-136), so a second round trip and extra draws follow.
Upstream: unchanged on glue and glue-qt main.

**Candidate fix.**

(c) glue-qt: decide threading from the work size (the sliced shape for a SliceSubsetState), never for the whole-cube layer (which would then compute twice on the main thread). Rank this first for the quicklook.
(a) glue-qt: block on work_queue.get and emit compute_end as soon as the queue is empty.
(b) glue-core: drop v_min/v_max as recompute triggers, or update the limits under ignore_callback, and reapply normalisation to the cached profile.

**Gain.**

- (c): the quicklook spectrum is painted at about 115 ms instead of 368 ms, about -250 ms per point move.
- (a)+(b): lone viewer 80.9 -> 20.5 ms, one fewer draw. In the quicklook the paint still waits behind the _set_wcs block until rank 1 is fixed.
- Zero-latency emulation: time step -42 to -63 ms wall, spectrum draws 3 -> 1; click -19 ms today, about -70 ms after rank 1.

### R4. Subset changes fully update and redraw viewers whose subset layer is hidden

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-core. **Confidence:** high. **Verification:** Confirmed (draw#3, events#3, hidpi-many#5). The events verifier corrected the time-step gain to -14..-27 ms.

**Slows.**

Every Point move or raster step in the quicklook (the SJI panel and other quicklooks hide the Point layer). Any subset edit while some viewers hide that subset layer.

**Cost.**

Per Point move: the hidden SJI layer's update takes 3.6 ms, plus one extra SJI draw of 27-28 ms at DPR1 (about 33 ms at DPR2).
Wall time saved without it:
- Exposure step: 203.7 -> 174.1 ms (14.5%).
- Click: -35 ms (9%).
- Time step: -14 to -27 ms (6-11%; the worker tail bounds it).
- Stack raster step: 231 -> 195 ms. λ-scan slit step: 161 -> 134 ms.
- With a second quicklook open: point move 416 -> 277 ms (-33%), spectrogram tick 490 -> 324 ms (-34%).
- Five tiled SJI viewers with 4 hidden: 157.6 -> 44.3 ms.

**Cause.**

glue/viewers/common/viewer.py:309-314 `_update_subset` calls update() on every layer artist of the subset. ImageSubsetLayerArtist.update (glue/viewers/image/layer_artist.py:390-396) and `_update_visual_attributes` (337-357) force _update_image and redraw() whatever state.visible is. Unchanged on glue main.

**Candidate fix.**

While a subset layer is not visible, and was not visible at the last draw, drop its caches and mark it stale without redrawing. Redraw once on a visible-to-hidden transition. Redo _update_data (the crosshair) when the layer is shown again.

**Gain.**

Measured by emulation:
- -27 to -35 ms per point move for each viewer with a hidden layer.
- -33% per point move with two quicklooks open.
- -72% to -83% in tiled multi-viewer layouts.
The gain overlaps with rank 9 and with glue-solar's coordinator fix on the SJI draw; they do not add up.

### R5. WCSAxes re-places every tick on every draw and evaluates the same frame points once per world coordinate

- [ ] Re-verified on current versions
- [ ] Fixed upstream

- Prototyped 2026-10-01: memo -25 %, batching -50 % and a placement cache -60 % per SJI draw, with skeptic verdicts and a PR order, in 'WCSAxes tick rendering'.

**Repository:** astropy. **Confidence:** High for the cost, medium for the shape of the fix.. **Verification:** Confirmed (draw#2, hidpi-many#3). The hidpi verifier added the batching estimate and noted that the 50-60% placement share holds for SJI only (Si IV is about 30%).

**Slows.**

Every draw of an image viewer with a WCS: slider steps, pan drags, contrast/bias drags, and point moves across N viewers.

**Cost.**

WCSAxes share of each quicklook-size draw (DPR1): map 75% (12.7 of 17.0 ms), spectrogram 82%, λ-time 88%, SJI 86% (24.5 of 28.4 ms).
WCS calls:
- 37-59 pixel_to_world_values calls per draw, of which only 17-20 have distinct inputs.
- The SJI gWCS costs 0.36-0.41 ms per call, almost independent of the point count. WCS evaluation is 54% of an SJI draw (15.4 ms) and 16-24% of a raster draw.
- An exposure step makes 435 calls (65.5 ms, 32%).
One tick placement: SJI 16.2-16.5 ms (33 calls), Si IV 7.3-7.5 ms (49 calls).
Point move across N tiled SJI viewers: placement is 23% of the draw at N=1, 50% at N=5 and 56% at N=10 (167 of 325 ms).

**Cause.**

In astropy/visualization/wcsaxes:
- core.py:517-529 draw_wcsaxes places the ticks on every draw, with no cache.
- coordinate_helpers.py:966-1050 _update_ticks calls frame.sample (995) and shifted_pixel_to_world (1023-1030) once per coordinate. Each transform evaluates every world axis and keeps one.
- frame.py:57-64, 192 and 373 transform the spines again.
Unchanged on astropy main 1f930be7c4 (coordinate_helpers.py:1013, 1041).

**Candidate fix.**

astropy:
- Sample the frame and the shifted samples once per tick update, batch them into one transform call, and share the results across CoordinateHelpers (about 2 calls instead of 33 for the SJI).
- Cache the tick placement while the limits, axes bbox, transform and slice are unchanged, so subset-only and contrast redraws skip it.
A per-draw memo in glue-solar's _GlueWCS is a stopgap (see the glue-solar list).

**Gain.**

Measured (memo what-if):
- SJI draw: 28.1 -> 21.4 ms. SJI contrast event: 31.0 -> 24.9 ms.
- SJI frame step: 104.9 -> 71.9 ms, with rank 1 unfixed.
- Exposure step: 205 -> 178.5 ms.
Estimated, not prototyped:
- Batching saves 12-13 ms per SJI placement (about 80%).
- Placement caching saves about 16 ms per redrawn SJI viewer, about half of a 10-viewer point move.

### R6. LinkManager.discover_links restarts its scan after every accepted link and runs once per dataset, about O(N^3) for link_hpc's star

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-core. **Confidence:** high. **Verification:** Confirmed (links#4, io-model#1).

**Slows.**

Loading or linking many datasets: the IRIS browser on multi-scan observations, keep_hpc_linked, the quicklook's add_link, arithmetic components, and pressing OK in Link Data.

**Cost.**

One update_externally_derivable_components:
- N=9 star: 0.006 s.
- N=36: 0.325 s (star), 3.98 s (all-pairs).
- N=99: 6.58 s (star), 249 s (all-pairs).
Other actions:
- keep_hpc_linked on 102 datasets: 6.84 s.
- Appending 1 dataset to 101 linked datasets: 6.71 s.
- In the app: the browser path for 99 scans takes 8.65 s, append plus relink 14.7 s.
discover_links is 77% (N=9 star) to 99% (all-pairs, N=99) of an update.

**Cause.**

glue/core/link_manager.py:77-90 breaks and restarts 'while True' after each accepted link. Each restart calls accessible_links (38-51), which rebuilds set(get_from_ids()) for every link: 40k calls and 53M get_from_ids at 101 datasets. update_externally_derivable_components (249-255) repeats this for every dataset. Unchanged on glue main.

**Candidate fix.**

Index the links by input cid once per update and expand level by level, with missing-input counters and depth = max input depth + 1. Compute self._links | self._inverse_links once per update.

**Gain.**

Two independent prototypes gave identical derivable cids and depths:
- 64-201x at N=36-99 star.
- 664x at N=99 all-pairs (249 -> 0.37 s).
- 188x at 102 datasets (6.87 -> 0.037 s).
Expected: the 99-scan browser load drops from 8.65 s to about 1.6 s, and a single append on 102 datasets from 6.7 s to about 0.23 s.

### R7. The one-pixel Pixel point is drawn as a 50%-alpha full-view RGBA image, and its mask is cube-sized

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-core. **Confidence:** high. **Verification:** Confirmed (draw#4, hidpi-many#6). Corrections: the mask is cached on colour-only draws, its RSS effect is far below 175 MB, and the realistic gain is 14-31 ms rather than 40%.

**Slows.**

Every redraw of a raster or SJI panel that shows the Point (all quicklook raster panels). Worst on maximized or HiDPI viewers.

**Cost.**

Maximized spectrogram (1258x810), with and without the Point image:
- DPR1: 66.9 -> 44.6 ms. DPR2: 125.2 -> 78.5 ms. The Point is 33-37% of the draw: RGBA build 3.9-7.3 ms, matplotlib resample 12.7 ms (DPR1) or 33.5 ms (DPR2).
Other sizes:
- Maximized SJI point move: the subset make_image is 22.4-23.4 ms of 71-73 ms (32%).
- Quicklook size at DPR2: map 23.2 -> 17.3 ms, spectrogram 28.3 -> 24.4 ms.
The mask (SliceSubsetState.to_mask, 0.3-1.5 ms) is rebuilt only when the subset, slice or limits change; colour-only draws hit ARRAY_CACHE. Its 175 MB calloc is mostly never touched.

**Cause.**

- glue/viewers/image/layer_artist.py:253-278: ImageSubsetArray builds a full-view RGBA.
- Lines 307-309 give every subset layer an imshow, PixelSubsetState included, on top of the crosshair (311-315).
- matplotlib/image.py:517-557 premultiplies, resamples and demultiplies it at device resolution.
- glue/core/subset.py:1380-1384 allocates np.zeros(data.shape, bool) for index-array views.
Unchanged on glue main.

**Candidate fix.**

- For a PixelSubsetState, draw only the crosshair, or an image whose extent is the bounding box of the selected pixels (the box keeps the tint visible when zoomed in).
- Build SliceSubsetState masks from the index arrays (start <= index < stop).
Computing the mask in a box but still returning a full-view array saves only about 6 ms.

**Gain.**

- About 14-31 ms per large redrawn viewer (20-43% of the draw).
- 22 ms (DPR1) to 47 ms (DPR2) on a maximized spectrogram.
- 4-6 ms per quicklook-size panel at DPR2.
- Index-array mask: 0.04 ms against 0.3-1.5 ms, identical output.

### R8. irispy's -TAB raster WCS makes world-to-pixel slow everywhere and ill-posed for sit-and-stare rasters

- [x] Re-verified on current versions (irispy main 3352413, 2026-10-09: 7-13 ms/pt on 4000255147, 13.2 s per SJI 1400 screen inversion; the ambiguity is a plateau of about 6 exposures between 0.05" pointing jumps, not a full overlap; a numpy inverse was prototyped and closed as irispy #234: the user will not re-implement WCSLIB and accepts the cost, D54; design in `IRIS_PLAN_PROTOTYPES/irispy_designs_20261009.tar.gz`)
- [x] Declined (user, 2026-10-09): no re-implementation of WCSLIB's inverse
- [ ] Future work: a direct bilinear-cell solve in WCSLIB's own `tabvox` for 2-D tables (`wp0-wcslib-tab-inverse`)
- [ ] Fixed upstream

**Repository:** irispy (WCS construction); wcslib via astropy (tabs2x). **Confidence:** High for the cost and cause, medium for the gain.. **Verification:** Confirmed (links#3); the verifier provided the evidence for the cause. irispy main was not checked.

**Slows.**

Any lookup from SJI pixels to raster pixels: rank 2's linked ROI mask, and any per-pixel reverse link to a raster.

**Cost.**

On the real SJI screen grid (4000255147): 176 us per pixel inside the raster footprint, 25.5 us outside.
Random raster points: 6154 us/pt (sit-and-stare 4000255147), 7.6 us (4000005156), 29.7 us (3824262996). The forward direction costs 0.02-0.04 us.
Wcsprm.s2p is 99.5% of rank 2's mask at DPR1 and 99.7% at DPR2.
Sit-and-stare round trips are off by up to 6 exposures, and 55% of points are off by more than 0.01 px.

**Cause.**

irispy builds the raster WCS as WAVE, HPLT-TAB, HPLN-TAB with a 1600-entry table. wcslib's tabs2x (cextern/wcslib/C/tab.c, unchanged through wcslib 8.9 on astropy main) loops over every voxel, runs a recursive dissection on each candidate, and stops at the first match. In a sit-and-stare all 1600 voxels overlap (the table spans 13 arcsec, median step 0.000 arcsec). That explains both the cost and the ambiguity. A synthetic table with 0.35 arcsec steps inverts 300x faster.

**Candidate fix.**

irispy: give sit-and-stare rasters, and ideally all rasters, a non-TAB or separable WCS in which the exposure axis does not drive lon/lat. This changes what an ROI on the step axis means.
wcslib/astropy: a faster -TAB inverse, for example starting from the previous point's cell or using a spatial index.
glue can only call it less often (rank 2).

**Gain.**

Not prototyped.
- Residual after rank 2: 0.21 s per SJI frame at DPR1 and 2.9 s at DPR2, nearly all s2p.
- A well-posed 1600-entry -TAB still costs 13-21 us/pt, about 1 s per 63k-pixel inversion (estimated).
- A non-TAB WCS would approach the 0.1 s frame cost, and it also fixes the wrong masks on sit-and-stare rasters.

### R9. Canvases in hidden tabs do full Agg redraws that are never painted

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-qt (or matplotlib). **Confidence:** high. **Verification:** Confirmed (hidpi-many#4); the verifier quantified the overlap with rank 4.

**Slows.**

Point moves or slider ticks in one quicklook while other quicklook tabs are open. Any subset change while viewers sit in a non-current tab.

**Cost.**

Two quicklooks (4000255147 hidden, 4000005156 shown):
- Point move: 416-431 ms, of which the hidden tab's 6 draws take 117-120 ms (28%), with 0 paints.
- Spectrogram tick: 490-493 ms, of which the hidden tab takes 118-120 ms (24%).
N SJI viewers in a hidden tab cost 81, 188 and 328 ms per point move for N=1, 5 and 10.

**Cause.**

matplotlib/backends/backend_qt.py:494-526 _draw_idle checks only width and height, not visibility. glue_qt/viewers/matplotlib/widget.py MplCanvas does not override it, so every draw_idle from glue renders hidden canvases. Unchanged on glue-qt main 9780eaf9; matplotlib main was not checked.

**Candidate fix.**

glue-qt MplCanvas, or matplotlib FigureCanvasQT: while the canvas is not visible, drop the pending draw and mark it dirty; draw once in showEvent.

**Gain.**

Emulated:
- Point move: 416-431 -> 312-323 ms (-25%). Tick: 490 -> 351 ms (-28%).
- 10 hidden SJI viewers: 328 -> 17 ms.
- Showing the tab again costs one draw per dirty canvas.
In the quicklook, 4 of the 6 hidden draws are also rank 4's hidden-layer draws, so the two gains do not add up. This fix still covers hidden tabs whose layers are visible.

### R10. After Collapse, every redraw re-aggregates the cube buffer and aggregates subset masks with the data's function

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-core (numpy for nanmedian). **Confidence:** High for the cost, medium for the native-resolution gain.. **Verification:** Confirmed (profile-stats#3); the pan estimate and the one-time collapse cost were corrected.

**Slows.**

Any redraw of a map that has an AggregateSlice: pan, zoom, point move or slider, including the quicklook's Point layer.

**Cost.**

Sit-and-stare cube, 588x347 canvas, redraw time:
- Plain slice: 16.9 ms.
- nanmean over 20 px: 33 ms. nanmedian over 20 px: 60 ms.
- nanmean over 100 px: 61 ms. nanmedian over 100 px: 218 ms.
- With the Point layer: 25 / 52 / 91 / 120 / 317 ms.
Point move while collapsed (nanmedian over 100 px): 275 ms of map drawing; in the quicklook 171-179 ms per move.
Components: np.nanmedian 175 ms on the 333x196x100 float64 buffer; mask gather 52 ms, of which view_shape is 24.5 ms; nanmedian on the bool mask 54 ms (np.any takes 0.4 ms).

**Cause.**

- glue/viewers/image/state.py:474-479 applies agg_func after compute_fixed_resolution_buffer on every call. The FRB cache (fixed_resolution_buffer.py:341) holds the buffer before aggregation.
- Subset layers (state.py:463) aggregate booleans with the data's function.
- glue/utils/array.py:121 view_shape materialises broadcast_to for index-array views.
- subset.py:1382 allocates a full-cube mask.
- numpy 2.5.3's nanmedian takes the np.ma path for short axes, 2.5x slower than sort-and-count.
Unchanged on glue main.

**Candidate fix.**

- Cache the aggregated 2D result keyed on bounds and function, or collapse once at native resolution and run the FRB on the 2D result.
- Aggregate masks with np.any.
- Compute view_shape with np.broadcast_shapes.
- Use a sort-based nanmedian, or raise it with numpy.

**Gain.**

- Point move while collapsed: 275 ms -> about 50 ms of map drawing.
- Pan with nanmedian over 100 px: 317 ms -> about 150 ms (sort nanmedian, np.any and view_shape together), or about 20 ms with a cached native-resolution collapse.
- That one-time collapse costs 80 ms (nanmean), 246 ms (sort nanmedian) or 1.72 s (np.nanmedian) on the sit-and-stare cube.

### R11. Any link change drops every linked subset mask, even when the subset's own link chain is unchanged

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-core. **Confidence:** medium. **Verification:** Confirmed (links#6); the verifier measured the Link Data OK cost directly in the app.

**Slows.**

Loading and linking another dataset, or pressing OK in Link Data without edits, while a linked ROI is shown (for example a raster ROI on the SJI).

**Cost.**

Appending an unrelated 3602506433 scan and running keep_hpc_linked takes 0.016 s. The next SJI draw then takes 4.71-4.74 s (4000255147) or 0.50-0.51 s (4000005156), against 0.030 s with the cache.
Link Data OK with no edits: the next draw takes 4.72 s or 0.50 s.

**Cause.**

- glue/core/data.py:640-660 broadcasts on any new key or any change of link identity (line 649).
- glue/dialogs/link_editor/state.py:318-331 builds new link objects on every OK.
- image/layer_artist.py:42-44 and common/viewer.py:288-293 call ImageSubsetLayerArtist.update (392-396), which drops ARRAY_CACHE.
Unchanged on glue main.

**Candidate fix.**

- In ImageSubsetLayerArtist.update, keep the cached mask unless the chains that the subset_state.attributes resolve through actually changed.
- Have the link editor reuse unchanged link objects.
- Comparing links by from/to ids and function fixes only the OK case, because append plus link legitimately adds cids.

**Gain.**

About 4.7 s -> 0.03 s per affected viewer per link change (4000255147); after rank 2, about 0.2 s -> 0.03 s. Not prototyped.

### R12. Removing a linked dataset runs one full link update per removed link, and clear() is not batched

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-core. **Confidence:** high. **Verification:** Confirmed (links#5, io-model#2).

**Slows.**

Deleting datasets from the layer tree, removing link_hpc's anchor dataset, and DataCollection.clear().

**Cost.**

Leaf removal:
- N=36 star: 0.59 s. N=99 star: 13.0 s.
- N=36 all-pairs: 70 updates, 319 s.
Anchor removal, including glue-solar's relink:
- 28 datasets: 2.40 s. 53: 30.0 s. 98: 194 updates, 362 s.
In the app, deleting 25 of 28 scans takes 2.57 s. clear() makes N(N-1) updates for all-pairs.

**Cause.**

glue/core/link_manager.py:158-166 _data_removed calls remove_link once per link, each with update_external=True (214-215), although the list path updates only once (198). DataCollection.clear (data_collection.py:128-131) sets the sync-suppression flag, but remove_link ignores it. Unchanged on glue main.

**Candidate fix.**

Call remove_link once with the list in _data_removed, and honour DataCollection's sync flag so clear() and batched removals update once at the end.

**Gain.**

Simulated batch:
- Anchor removal at 53 datasets: 30.0 -> 0.93 s (32x). At 28: 2.40 -> 0.135 s.
- The single deferred update costs 0.15 s at N=99. With rank 6 the relink also drops to about 0.03 s.

### R13. Opening a gzipped SJI decompresses the whole file 4-5 times

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** astropy (root cause), irispy, glue-core. **Confidence:** high. **Verification:** Confirmed (io-model#4, startup#3); the gain was corrected from 5x to 2.9x.

**Slows.**

Opening a slit-jaw, deconvolved SJI or AIA cutout .fits.gz through File > Open, the IRIS browser, irispy or glue's FITS reader.

**Cost.**

SJI 1400 of 4000255147 (129.6 MB uncompressed); one decompression takes 0.357 s.
- glue load_data(auto): 2.18 s (5 decompressions).
- glue-solar image_data: 1.78 s. irispy read_files: 1.64 s (4 each).
- glue fits_reader: 1.56 s (4).
zlib is 74% of load_data's profile.

**Cause.**

astropy/io/fits/hdu/base.py:364 seeks past each HDU's data after reading its header. On a gzip stream that decompresses the data, and reading the data later seeks back and decompresses again. HDUList always reads the first HDU (hdulist.py:1263).
Callers also reopen the same file:
- irispy: io/utils.py:34 getheader, then io/sji.py:200 fits.open plus verify, plus aux reads.
- glue: core/data_factories/fits.py (fits.open in is_fits, then per-HDU reads). For IRIS files is_iris_fits matches first, so is_fits adds a pass only for non-IRIS .gz files.
Unchanged on irispy LM-SAL main 813f4cc, astropy main and glue main.

**Candidate fix.**

- irispy and glue's fits_reader: when the file is gzip, decompress once into BytesIO and open that.
- astropy: defer the seek past the data until the next HDU is needed, or keep the decompressed stream for read-only gzip opens.
- glue is_fits: parse the header blocks without fits.open.
The header-only reads in glue-solar are in the glue-solar list.

**Gain.**

Decompressing once saves about 1.43 s per gzipped SJI: load_data 2.18 -> about 0.75 s (2.9x).

### R14. ProfileViewerState._reset_y_limits computes whole-cube profiles on the main thread

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-core (the glue-qt artist signals the reset). **Confidence:** high. **Verification:** Confirmed (profile-stats#2).

**Slows.**

Opening the quicklook (the spectrum panel's add_data). In plain glue: adding a cube to a Profile viewer, or changing Function, Normalize or the y unit while the cube layer is visible.

**Cost.**

Quicklook open: one main-thread whole-cube 'mean' takes 368-400 ms of a 4.0 s quicklook() on sit-and-stare, and 119 ms of 3.76 s on the stack. The result is thrown away, because glue-solar hides that layer.
Plain glue add_data: the main thread blocks for 199 ms, then the worker recomputes the same profile (183 ms).
Function-change freezes on sit-and-stare: mean 661 ms, median 2.80 s, maximum 430 ms (stack: 147, 574 and 86 ms).
Mg II k is 2.1x larger; its cost is extrapolated, not measured.

**Cause.**

glue/viewers/profile/state.py:212-228 reads layer.profile for every layer synchronously (update_profile, then compute_statistic, 427 -> 473). It is called from the normalize and function callbacks (66-67) and from reset_limits (161), which runs on reference_data changes (331). None of this goes through glue-qt's threaded artist, and add_data also queues a forced worker job. Unchanged on glue main.

**Candidate fix.**

Use only already-cached profiles in _reset_y_limits. Let the glue-qt artist reset the y limits when its computation ends. Do not force reset=True when the cache was just filled.

**Gain.**

- Quicklook open: -0.37 to -0.40 s on sit-and-stare, -0.12 s on the stack (about -0.86 s for Mg II, extrapolated).
- Removes the 0.4-2.8 s freezes on Function changes.
- Halves the CPU of add_data.

### R15. glue-qt's data tree rebuilds itself and reloads tinted icons from disk for every dataset or subset added

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-qt. **Confidence:** high. **Verification:** Confirmed (io-model#5); the verifier raised the cost to 1.18 s and the confidence to high.

**Slows.**

Adding many datasets at once (File > Open of many files, the IRIS browser loading 99 scans), especially with a Point subset group open.

**Cost.**

app.add_datasets of 99 Si IV scans with a quicklook open takes 1.365 s. With the model unsubscribed it takes 0.185 s, so the model's reactions cost 1.18 s (87%): 198 rebuilds, 11,401 layer_icon calls and 125k lstat calls. The cost is quadratic in the number of datasets added.

**Cause.**

glue_qt/core/data_collection_model.py:413-426 invalidates the model, emits layoutChanged and new_item for each DataCollectionAddMessage and SubsetCreateMessage. new_item calls select_indices (468), which re-queries every row. Each DecorationRole query calls glue_qt/icons/helpers.py:26 layer_icon, which loads and tints the PNG with no cache. Unchanged on glue-qt main.

**Candidate fix.**

Cache icons per (marker, colour). Insert rows with beginInsertRows/endInsertRows. Select only the newest item, once. Or coalesce the add messages with hub.delay_callbacks in DataCollection.extend.

**Gain.**

Up to about 1.18 s per 99 datasets added. This is an upper bound from unsubscribing; a real row-insert fix keeps some per-row cost.

### R16. glue-qt's slice slider applies every dragged position synchronously, so uncoalesced input queues up behind slow ticks

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-qt. **Confidence:** High for the mechanism; medium for the absolute rates (posted Qt events, offscreen).. **Verification:** Confirmed (hidpi-many#2).

**Slows.**

Dragging a slice slider in an Image viewer with plain glue-qt. glue-solar currently masks this with its 100 ms throttle.

**Cost.**

Simulated 2 s drag, 120 positions at 60 Hz, 800x500 viewer.
Every position delivered (Wayland/macOS-like):
- SJI: 0.5 draws/s. The 2 s drag finishes after 8.2-8.3 s, with a median display lag of 1.34-1.41 s (max 6.3 s).
- Si IV: 1.2 draws/s, lag 0.4-0.7 s.
With X11-like motion compression: SJI 9.3-9.5 draws/s at 133 ms lag; Si IV 17 draws/s at 66 ms.

**Cause.**

glue_qt/viewers/common/data_slice_widget.py:43 autoconnects QSlider.valueChanged to slice_center. slice_widget.py:54-61 and 123 then set viewer_state.slices synchronously for every value, so rank 1's full tick setter runs per position. Draws are deferred to QTimer.singleShot(0) (backend_qt.py:494-504) and starve while input queues. Unchanged on glue-qt main.

**Candidate fix.**

In SliceWidget, while sliderDown, coalesce to the latest sliderPosition with a 0 ms single-shot timer, and apply the final value on release.

**Gain.**

- Coalescing: SJI 9.7 draws/s at 110 ms lag with no backlog under uncompressed input, against about 6 s of backlog today.
- With rank 1 fixed: about 26-33 draws/s (by arithmetic, not re-run).
- Under compressed (X11-like) input, glue-qt's tracking already matches coalescing.
- It could explain part of the user's Wayland vs X11 tick difference; this was not measured on a real screen.

### R17. Each image layer's colormap combo renders an icon for every registered colormap at creation and on every resize

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-qt (glue-solar controls how many colormaps are registered). **Confidence:** high. **Verification:** Confirmed (startup#5). events#4 was rejected because its numbers were inflated 1.85x: its harness ran glue_solar.setup() twice and registered 189 colormaps.

**Slows.**

Creating an image viewer or adding a data layer to one; opening the quicklook; resizing.

**Cost.**

With glue-solar's 102 colormaps:
- Building a QColormapCombo takes 28-30 ms, and each width change takes the same (4.2-4.4 ms with glue's 15 colormaps).
- Per new image viewer: 57 ms in _update_icons (2 calls), against 8.5 ms without glue-solar.
- Adding a data layer to the SJI viewer: 29.6 of 84.7 ms (35%).
- Quicklook open: 8 calls, 0.24 s (10-12.6%).

**Cause.**

glue_qt/utils/colors.py:190-219 re-renders every cmap2pixmap in __init__ and in resizeEvent, with no cache. glue_qt/core/layer_artist_model.py:357-373 builds every layer's style editor, combo included, eagerly. Unchanged on glue-qt main.

**Candidate fix.**

Keep a module-level pixmap cache keyed on (colormap, width, steps). Render the icons lazily, in showPopup or through a delegate. Rebuild on resize only when the width changed. Optionally build the style editors on selection.

**Gain.**

Cache what-if: -60 ms per new image viewer (about 40%); quicklook call 1.908 -> 1.737 s (-0.17 s).

### R18. Image-only changes (contrast/bias, wavelength step) redraw the whole WCSAxes figure

- [ ] Re-verified on current versions
- [ ] Fixed upstream

- Prototyped 2026-10-01: reusing the tick placement takes an SJI contrast redraw from 27.4 to 11.0 ms ('WCSAxes tick rendering', prototype 3).

**Repository:** glue-qt / glue-core (astropy for tick reuse). **Confidence:** medium. **Verification:** Confirmed (draw#5) as an upper bound; the verifier added the blit design caveat.

**Slows.**

Contrast/bias drags, the slit-vs-time wavelength step, and any redraw where the limits, slice and size are unchanged.

**Cost.**

At DPR1:
- Map contrast event: 18.5 ms (WCSAxes 62%).
- SJI contrast event: 31.0 ms (WCSAxes 77%); 38.8 ms at DPR2.
- Map wavelength step: 34.7 ms (WCSAxes 33%).
Tick computation inside those draws: 6.1 ms (map), 16.4 ms (SJI).

**Cause.**

Every change goes through canvas.draw_idle (glue/viewers/matplotlib/layer_artist.py:73-74, viewer.py:223-224) into a full FigureCanvasQTAgg draw. Neither glue nor glue-qt (glue_qt/viewers/matplotlib/widget.py) has animated or blitted artists. Unchanged on main.

**Candidate fix.**

glue/glue-qt: cache a background below the image, and redraw the image plus the WCSAxes decorations on top of it; invalidate on limit, slice or size changes. A single copy_from_bbox is not enough, because ticks and frame overlay the image.
Cheaper partial fix: astropy tick-placement reuse (rank 5).

**Gain.**

Upper bound, with no WCSAxes at all: map contrast 18.5 -> about 7 ms, SJI contrast 31 -> about 8 ms, wavelength step 35 -> about 23 ms.
Tick reuse alone: -6 ms (map) and -16 ms (SJI) per event.

### R19. On maximized or HiDPI viewers, glue's float64 RGBA composite and matplotlib's device-resolution resample dominate

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-core (matplotlib for the resample). **Confidence:** medium. **Verification:** Confirmed (draw#6); the verifier halved the DPR1 float32 gain. The FRB-cap part (hidpi-many#7) is untested.

**Slows.**

Every image redraw of a large panel or at devicePixelRatio 2.

**Cost.**

Maximized SJI (1258x810):
- DPR1: draw 50.6 ms; the image path is about 44% (composite 8.6-10.6 ms, resample 12.2 ms).
- DPR2: draw 86.9 ms; the image path is about 57% (resample 42.3 ms).
Full tab (1568x797): static draw 58 ms at DPR1, 104 ms at DPR2; make_image 30.7 -> 71.7 ms.
The cost is small at quicklook panel sizes (6-14 ms).

**Cause.**

- glue/viewers/image/composite_array.py:93-228 builds a float64 RGBA even for a single opaque layer (np.ones at 166, zeroing, +=, clip).
- frb_artist.py:16-31 and mpl_scatter_density base_image_artist.py:52 compute the buffer at 72 dpi, whatever the number of data pixels in view.
- matplotlib/image.py:533-557 resamples, demultiplies and converts the float array at device resolution.
glue is unchanged on main; matplotlib main was not checked.

**Candidate fix.**

glue-core: build a float32 composite (uint8 for a single opaque layer), and cap the FRB bins at the reference-data pixels in view, aligned to pixel centres.
matplotlib: skip the demultiply when alpha is 1, or add a faster nearest-neighbour upsample for opaque RGBA.

**Gain.**

- float32 cast on the maximized SJI: -3.2 ms at DPR1, -11.4 ms at DPR2. Pixels differ by at most 1/255 in 14-21% of pixels.
- float32 plus the FRB cap (hidpi, not re-verified), full tab at DPR2: static draw 104 -> 80 ms, slider tick 182 -> 157 ms. The cap prototype shifts edges in 3-3.5% of pixels and still needs alignment.

### R20. Session save serializes every object on each do_all pass and writes broadcast components at full size

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-core. **Confidence:** high. **Verification:** Confirmed (io-model#3). The 2-scan save was not re-run because of the memory budget.

**Slows.**

File > Save Session with IRIS data. This is currently also blocked for glue-solar data; see the glue-solar list.

**Cost.**

With stub savers:
- 1 Si IV scan of 4000005156: 1.93 s, 741 MB of JSON.
- 2 scans: 3.6-4.6 s, 1412 MiB, RSS 4.2-4.3 GB.
- 10 scans of 3602506433: 0.68 s, 287 MB.
The zero-stride Time and Exposure time components are 76% of the bytes. Each component is base64-encoded 2x (DataCollection) or 3x (app).

**Cause.**

glue/core/state.py:326-334 GlueSerializer.do_all re-runs do() on every registered object on each pass. state.py:1266-1271 _save_numpy calls np.save on broadcast_to views, which writes them in full. Unchanged on glue main.

**Candidate fix.**

Serialize only newly registered objects on each pass. Save unbroadcast(arr) plus the original shape and broadcast back on load (a small loader change).

**Gain.**

- One-pass do_all: 1.4-1.7x (1.93 -> 1.33 s), with byte-identical JSON.
- Unbroadcasting cuts the size to about 24%, and the base64 and json time with it. Not timed; the 2-scan session is estimated at under 1 s and about 350 MB.

### R21. compute_statistic copies each chunk to float64 and masks it before calling the nan-function

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-core. **Confidence:** high. **Verification:** Confirmed (profile-stats#5).

**Slows.**

Whole-cube profiles: rank 14's quicklook-open pass, visible data layers in a Profile viewer, and Function changes.

**Cost.**

Sit-and-stare cube, profile along wavelength:
- mean: 673 ms, 713 MiB peak (numpy float32 nanmean takes 194 ms).
- maximum: 433 ms, 375 MiB.
- Stack mean: 151 ms, 724 MiB.
cProfile of one mean: float64 copy 245 ms, keep/assign 206 ms, nanmean 283 ms.

**Cause.**

glue/utils/array.py:465-486 builds a keep mask, copies the chunk to float64 and sets non-finite values to NaN, then calls the nan-function, which copies again. glue/core/data.py:1675-1730 does the chunking. Unchanged on glue main.

**Candidate fix.**

Reduce in the native dtype with where=np.isfinite(chunk):
- mean: sum with dtype=float64 divided by count_nonzero.
- max/min: initial=+-inf, plus an all-NaN rule.
Fold the subset mask into the same where=, and keep the copy only for median and percentile.

**Gain.**

- mean: 673 -> 441 ms (-34%), 713 -> 75 MiB.
- Stack mean: 151 -> 79 ms, 724 -> 50 MiB.
- maximum: 433 -> 423 ms.
Results match (rtol 1e-5; maximum is exact with the all-NaN rule).

### R22. glue imports IPython, ipykernel and qtconsole at startup, though the terminal only opens on click

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-core, glue-qt. **Confidence:** high. **Verification:** Confirmed (startup#4); the verifier found the third import site.

**Slows.**

Every launch of glue.

**Cost.**

0.154-0.155 s of time to window (2.446 s with glue-solar, 1.679 s without). It also loads 568-597 extra modules and 28 MB of RSS.

**Cause.**

- glue/viewers/common/viewer.py:4 imports IPython, which is used only in cleanup (429).
- glue_qt/app/application.py:39 imports the terminal module (terminal.py:18-28: IPython, ipykernel, qtconsole).
- GlueApplication.start() calls _fix_ipython_pylab (application.py:1222), which imports IPython (48-51).
Unchanged on main.

**Candidate fix.**

- Use sys.modules.get('IPython') in Viewer.cleanup.
- Import the terminal inside _create_terminal.
- Return early from _fix_ipython_pylab when IPython has not been imported.
The first two alone save only 0.072 s.

**Gain.**

About 0.155 s per launch; about 0.15 s moves to the first click of the IPython button.

### R23. The Histogram viewer builds a full-cube mask for the Point subset on every move, and copies the cube for the data histogram

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-core. **Confidence:** high. **Verification:** Confirmed (profile-stats#4).

**Slows.**

Point moves while a Histogram viewer of the raster is open; adding a cube to a Histogram viewer.

**Cost.**

- Point-subset histogram: 35.4 ms (sit-and-stare) or 10 ms (stack) per move on the worker thread, with a 167 or 50 MiB transient. Little UI latency (about +20 ms of drawing).
- Whole cube: 679 ms with a 728 MiB peak. add_data is idle after 1.24 s, and RSS grows by 480 MB.

**Cause.**

- glue/core/data.py:1938-1953 compute_histogram turns a subset into a full-shape get_mask. Unlike compute_statistic (1733-1735), it has no SliceSubsetState.to_array path.
- glue/utils/array.py:546-568 builds a keep mask and copies x[keep], although histogram1d already drops NaN and out-of-range values.
Unchanged on glue main.

**Candidate fix.**

- Use subset_state.to_array for SliceSubsetState.
- Pass raw 1-D, unweighted numpy input to histogram1d, keeping the 10*spacing xmax nudge at array.py:605.
- Optionally default random_subset for large data; that is a UX choice, because the histogram becomes approximate.

**Gain.**

- Subset histogram: 35.4 ms -> under 0.1 ms, with no transient.
- Whole cube: 679 -> 490 ms, 728 -> 0.1 MiB.
Counts are identical.

### R24. Every append runs a full link update, including an all-pairs equivalent_pixel_cids pass

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-core. **Confidence:** high. **Verification:** Confirmed (io-model#6).

**Slows.**

Appending datasets one at a time: scripts, and glue-solar's quicklook (see the glue-solar list). Also every link update.

**Cost.**

102 unlinked datasets:
- One all-pairs pass: 0.14 s.
- Appending one at a time: 5.38 s, against 0.158 s for one extend (34x).
- equivalent_pixel_cids is 15.7 of 18.1 s profiled (353,702 calls), mostly _find_identical_reference_cid rebuilding the component lists.

**Cause.**

glue/core/data_collection.py:59-90: append calls _sync_link_manager, which runs a full update. link_manager.py:257-264 calls equivalent_pixel_cids for every ordered pair of datasets, and each call rebuilds the main, coordinate and derived component lists. Unchanged on glue main.

**Candidate fix.**

Skip the pairwise pass when no identity link touches a pixel cid, recompute only the datasets whose links changed, and cache the component lists per update.

**Gain.**

About 0.14 s per update at 100 datasets; up to the full 5.4 s for append loops.

### R25. The WCS autolinking plugin imports scipy.optimize at plugin load

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-core. **Confidence:** high. **Verification:** Confirmed (startup#6); the verifier corrected the glue-solar condition (ndcube must be deferred too).

**Slows.**

Every launch.

**Cost.**

0.169 s of time to window without glue-solar (load_plugins 0.177 -> 0.022 s).
With glue-solar: no saving today, and none after glue-solar defers only irispy. It saves 0.171 s once glue-solar also defers ndcube, which pulls in gwcs and through it scipy.optimize.

**Cause.**

glue/plugins/wcs_autolinking/wcs_autolinking.py:6 imports leastsq at module level, but only two functions use it (287, 302). Unchanged on glue main.

**Candidate fix.**

Import leastsq inside the two functions.

**Gain.**

About 0.17 s per launch. For IRIS users this needs glue-solar's import deferrals first.

### R26. glue imports dask.array at import time only for isinstance checks

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-core. **Confidence:** medium. **Verification:** Untested (startup#7).

**Slows.**

Every launch.

**Cost.**

0.136 s without glue-solar. With glue-solar: none today (reproject needs dask), 0.105 s after glue-solar defers irispy and sunpy.map.

**Cause.**

glue/utils/array.py:10-14, glue/core/data.py:42 and glue/core/component.py:11 import dask.array at module level inside try/except.

**Candidate fix.**

Check that 'dask.array' is in sys.modules before the isinstance check, and import dask inside the functions that build dask arrays.

**Gain.**

0.10-0.14 s per launch. For IRIS users only after glue-solar's deferrals (probably including ndcube; not re-checked).

### R27. Derived arithmetic components with a numeric constant upcast float32 data to float64

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-core. **Confidence:** high. **Verification:** Untested (links#8).

**Slows.**

Reading a derived component such as 'x * 2' on IRIS float32 cubes: histogram, image or statistics.

**Cost.**

On a 1600x417x262 float32 cube: 0.093-0.104 s and a 1334 MB peak per read, recomputed on every read. numpy takes 0.041 s and 667 MB.

**Cause.**

glue/core/component_link.py:483 BinaryComponentLink.compute broadcasts scalars into int64 arrays, which defeats NumPy 2's weak-scalar rule.

**Candidate fix.**

Broadcast only ndarray operands, and pass scalars straight to the operator.

**Gain.**

2.3x faster and half the peak memory per read.

### R28. glue's WCS autolinker suggests and accepts a link for every pair of datasets

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-core (glue-qt dialog). **Confidence:** medium. **Verification:** Untested (io-model#7).

**Slows.**

File > Open of many FITS cubes through glue's FITS reader. IRIS data loaded by glue-solar is not affected today (_GlueWCS is low-level only), but would be after glue-viz/glue#2595.

**Cost.**

25 Si IV headers: find_possible_links takes 0.275 s and returns 300 links; accepting them takes 2.87 s (91%).

**Cause.**

glue/plugins/wcs_autolinking/wcs_autolinking.py:316-345 builds a WCSLink for every pair, as its own PERF comment at 333-335 notes. glue-qt's autolinker then adds them all.

**Candidate fix.**

Suggest one star per compatible group, linking each dataset to a reference dataset (as link_hpc does).

**Gain.**

25 scans: 2.87 -> 0.215 s (13x). The gap grows with N, and rank 6 lowers both.

### R29. The splash screen appears only after glue and the whole Qt app are imported

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-qt (matplotlib owns the font-cache rebuild). **Confidence:** medium. **Verification:** Untested (startup#9 and startup#11, merged).

**Slows.**

Launch: what the user sees first (perceived latency).

**Cost.**

The splash appears at about 1.36 s of the 2.44 s to the window, so nothing is on screen for about 56% of startup. On a first launch with an empty matplotlib font cache, import glue takes 9.3 s (font_manager 8.3 s) with nothing on screen.

**Cause.**

- glue_qt/main.py:6-8 imports glue before any UI exists.
- main.py:207-211 get_splash imports glue_qt.app, whose __init__ imports the application, the viewers and the terminal.
- glue imports matplotlib.axes, and so the font cache, eagerly.

**Candidate fix.**

Create the QApplication and the splash before importing glue. Move QtSplashScreen out of glue_qt.app, or make glue_qt/app/__init__ lazy.

**Gain.**

The splash appears about 0.27 s earlier on a normal launch, and the 9 s first-launch wait becomes visible. Time to window does not change.

### R30. Small glue-qt one-off costs: QtQuick imported on Qt5, QFont('Courier') on macOS

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-qt. **Confidence:** medium. **Verification:** Untested (startup#10).

**Slows.**

Launch (QtQuick); opening the first Profile viewer (Courier).

**Cost.**

QtQuick: 35 ms per launch on Qt5. QFont('Courier'): 54.6 ms on the first profile viewer, against 2.6 ms for the system fixed font (macOS).

**Cause.**

glue_qt/utils/app.py:3 imports QtQuick unconditionally, but uses it only on Qt6 (line 54). glue_qt/viewers/profile/profile_tools.py:112 calls QFont('Courier'), a family macOS lacks, which makes Qt build its alias table.

**Candidate fix.**

Import QtQuick under QT6 only, and use QFontDatabase.systemFont(FixedFont).

**Gain.**

About 35 ms per launch on Qt5, and about 50 ms on the first profile viewer on macOS. Linux not measured.

### R31. import glue imports glue_qt through a glue.config re-export

- [ ] Re-verified on current versions
- [ ] Fixed upstream

**Repository:** glue-core. **Confidence:** high. **Verification:** Untested (startup#8).

**Slows.**

Non-Qt use of glue-core with glue-qt installed (scripts, glue-jupyter).

**Cost.**

import glue takes 1.11 s, against 0.83 s with glue_qt blocked. No cost to the Qt app, which imports glue_qt anyway.

**Cause.**

glue/config.py:949-958 re-exports names from glue_qt.config.

**Candidate fix.**

Provide the re-exports through a PEP 562 module __getattr__ that imports glue_qt.config on first access, with a DeprecationWarning.

**Gain.**

About 0.28 s for non-Qt users; nothing for IRIS Qt users.

## glue-solar's own costs

These are glue-solar code; the M0 work fixed most of them (#90, #95, #98).

### S1. Exposure labels from #87 slow slider steps on origin/main 5eae565 (confirmed by the draw and events verifiers on a git-archive copy).

- [ ] Re-verified
- [x] Fixed in glue-solar (#90, 2026-10-01)

- Cause: FrameTimeTool._label_exposures (tools.py) sets the exposure-axis label again after every glue _set_wcs, and each set_ylabel is a full WCSAxes tick placement.
- Cost: the λ-time slit step's set phase grows from 47 to 73-76 ms (_set_wcs 65.5 ms with 4 set_ylabel calls). A Pixel click grows from 368 to 401 ms; _set_wcs per click from 135 to 166 ms (8 y-label callbacks instead of 6).
- Fix: put the label on the coordinate helper with axes.coords[i].set_axislabel instead of calling set_ylabel, and stop reacting to glue's ''-then-label round trip. This is still needed after the glue-core rank-1 fix.
- Untested: the map's new pixel-index tick overlay raised the map draw from 17.6 to 21 ms.

### S2. The coordinator's 0 ms QTimer moves the sliders after glue has already drawn the Point change (confirmed, events#5, gain corrected from -39 ms; draw#8 untested).

- [ ] Re-verified
- [x] Fixed in glue-solar (#90, 2026-10-01)

- Code: quicklook.py:216-219 (timer), _subset_changed 318-331, _update 386-402.
- Cost: the spectrogram, λ and SJI panels draw twice per Pixel click (10 draws instead of 7). About 20 ms of extra λ-scan draw per stack raster step (draw, untested).
- Fix: for clicks, apply the point synchronously inside the same defer_draw; keep the timer only while dragging.
- Gain: -25 ms wall per click today (6-7%), and the image panels are final 84 ms sooner. The wall gain grows once the profile-worker fix (rank 3) lands.

### S3. Workaround for glue-core rank 4: the quicklook hides the Point layer instead of removing it (confirmed, events#3).

- [ ] Re-verified
- [x] Fixed in glue-solar (#90, 2026-10-01)

- Code: quicklook.py:399-402 and 857-870 hide the layer on the SJI panel and on other quicklooks' panels. glue still updates and redraws hidden subset layers.
- Fix: remove the layer with viewer.remove_subset where it must not show (re-add it when needed), or apply item 2.
- Gain: about -35 ms per click and -14 to -27 ms per time step. The glue-core fix itself gives -33% per point move with a second quicklook open.

### S4. Plugin load imports irispy and sunpy.map, which pull in reproject, dask, scipy.signal/stats, dkist and aiohttp (confirmed, startup#1 plus the verifier's ndcube correction).

- [ ] Re-verified
- [x] Fixed in glue-solar (#98, 2026-10-02)

- A second chain: stack_spectrograms.py:7-8 imports ndcube, which imports gwcs and through it scipy.optimize.
- Cost: 0.51-0.56 s of a 2.45 s launch. The fix applied in memory gave 2.446 -> 1.934 s, 596 fewer modules and 49 MB less RSS. Deferring ndcube saves another 0.075 s.
- Fix: import read_files inside image_data, iris_data and raster_data (loaders/iris.py:16). Register the GenericMap qglue parser without importing sunpy.map (sources/maps.py:10-11). Import ndcube inside stack_spectrogram_sequence.
- This also unlocks glue-core's startup gains for scipy.optimize (0.17 s) and dask (about 0.1 s).

### S5. Header reads decompress whole .fits.gz files (confirmed, startup#3 and io-model#4).

- [ ] Re-verified
- [x] Fixed in glue-solar (#98, 2026-10-02)

- Code: scan_directory (sources/loaders/scan.py:154, fits.getheader) and is_iris_fits (sources/iris.py:19-21).
- Cost: opening the IRIS browser on /Users/nabil/DATA/IRIS takes 0.98 s, of which the 7 gz files take 0.89 s, on every open and rescan. File > Open identification takes 0.39 s (SJI 1400 of 4000255147) and 0.16 s (SJI 2796 deconvolved).
- Fix: read only the primary header with fits.Header.fromfile(gzip.open(p, 'rb')).
- Gain: browser open 0.98 -> 0.18 s (-0.80 s); -0.39 s per gzipped SJI opened.

### S6. Slider drag throttle (confirmed, hidpi-many#2).

- [ ] Re-verified
- [x] Fixed in glue-solar (#98, 2026-10-02)

- Code: tools.py:21-44 at 2fdb847 (29-52 on main). It waits a fixed 100 ms after the first sliderMoved, so the period is 100 ms plus the tick cost.
- Cost: SJI 5 draws/s at 108-113 ms lag; Si IV 6 draws/s at 64-73 ms lag.
- Fix: replace the 100 ms interval with a 0 ms single-shot timer that applies slider.sliderPosition() (coalesce to the latest position).
- Gain: SJI 9.7 draws/s at 110 ms lag. Si IV 16-17 draws/s, but lag rises from 65 to 120-127 ms, a smoothness-for-latency trade. About 26-33 draws/s once glue-core rank 1 lands.

### S7. _GlueWCS.pixel_to_world_values recomputes per-axis metadata on every call (untested: draw#7 and hidpi-many#8 measured it independently; the memo variant was confirmed by the draw#2 verifier).

- [ ] Re-verified
- [x] Fixed in glue-solar (#90, 2026-10-01)

- Code: sources/loaders/iris.py:86-97. Each call rebuilds u.Unit per axis and world_axis_physical_types, and round-trips through Quantity.
- Cost: 0.056-0.059 ms per call, against 0.017 ms for the wrapped FITS WCS. That is 12.5 ms per Si IV tick (21%) and 7.8 ms per SJI tick.
- Fix: precompute the arcsec factors and the longitude wrap once per wrapper.
- Gain from the cached-factor what-if: exposure step 203 -> 184 ms, λ-time slit 212 -> 188 ms, SJI frame 105 -> 96 ms, map contrast 18.2 -> 16.0 ms. About 2.5 ms per tick remains after glue-core rank 1.
- Optional stopgap for astropy rank 5: memoize identical calls within one draw or tick update. The draw verifier's memo in this wrapper gave SJI draw 28.1 -> 21.4 ms and SJI frame step 104.9 -> 71.9 ms.

### S8. A wavelength-slider step runs the full time sync, and the SJI point is projected twice per sync (confirmed, events#6).

- [ ] Re-verified
- [x] Fixed in glue-solar (#90, 2026-10-01)

- Code: quicklook.py:253-254 starts the timer on any slider change of the time master's viewer, wavelength included. _sync (464-495) then calls every listener, and point_on calls _sji_pixels twice per sync (1.84 ms each; tools.py:108-150 and 310-338).
- Cost: Coordinator._update takes 11 ms of a 35 ms map wavelength step (31%).
- Fix: start the timer only when the time-axis slider changed, or return early when master, time, step and point are unchanged. Memoize point_on per (point, SJI frame).
- Gain: 35.1 -> 23.9 ms per wavelength step (-32%, measured); about -2 ms per sync from the memo.

### S9. quicklook() appends datasets one at a time (confirmed, io-model#6).

- [ ] Re-verified
- [x] Fixed in glue-solar (#90, 2026-10-01)

- Code: quicklook.py:791-794 appends each dataset not yet in the collection, and each append runs a full link update.
- Cost: 5.38 s for 99 new scans, against 0.158 s with one extend. It only applies when quicklook() is given new datasets; the IRIS browser extends first.
- Fix: collection.extend([d for d in datasets if d not in collection]).

### S10. setup() registers all 87 sunpy colormaps (confirmed, startup#5; events#4's numbers were inflated by a double setup() in its harness).

- [ ] Re-verified
- [x] Fixed in glue-solar (#98, 2026-10-02)

- Code: __init__.py:14-17, 102 colormaps in total.
- Cost: each QColormapCombo build or resize takes 28-30 ms, against 4.3 ms with glue's 15. That is 57 ms against 8.5 ms per new image viewer, and 0.24 s at quicklook open.
- Fix: register only the colormaps IRIS and AIA use (irissji*, sdoaia*, about 34 in total). Saves about 20 ms per combo call; glue-qt's pixmap cache (rank 17) removes most of the rest.

### S11. Session save fails for glue-solar data (confirmed, io-model#3).

- [ ] Re-verified
- [ ] Fixed in glue-solar

- _GlueWCS has no saver (GlueSerializeError), and Quantity meta raises TypeError in np.save.
- Browser-loaded datasets have no LoadLog, so even include_data=False writes every array: 1412 MiB for 2 scans of 4000005156.
- This matches the plan's D13 and wp3-file-references items.

### S12. glue_patches.py:52-54 carries a gated copy of glue's world2pixel_single_axis with the same full-inversion-per-axis behaviour (confirmed as part of links#1). When glue-core fixes rank 2's single inversion, this copy must follow or be dropped; otherwise the linked ROI mask keeps the 2x cost.

- [ ] Re-verified
- [ ] Fixed in glue-solar



### S13. The quicklook adds the raster to the spectrum panel and then hides it (confirmed, profile-stats#2).

- [ ] Re-verified
- [x] Fixed in glue-solar (#95, 2026-10-01)

- glue's _reset_y_limits computes the hidden layer's whole-cube profile on the main thread first: 368-400 ms of quicklook open on the sit-and-stare cube, 119 ms on the stack.
- No glue-solar workaround was tested; the fix is glue-core rank 14.

### S14. Turning an Image viewer's axes off skips WCSAxes in every draw (measured 2026-10-01, not a survey finding).

- [ ] Re-verified
- [x] Fixed in glue-solar (#90, 2026-10-01)

- Code: WCSAxes.draw_wcsaxes returns at once when `axison` is False (astropy main core.py:585-587). Hiding a coordinate's ticks and labels saves nothing: `_update_tick_and_label_positions` (core.py:555-582) still updates every coordinate, and astropy #20499 only keeps hidden coordinates off the spines. glue-core has a `show_axes` state on Matplotlib viewers (glue/viewers/matplotlib/state.py:135) that glue-qt never connects.
- Cost measured: the quicklook on 4000255147 (Si IV 1403 and SJI 1400), offscreen 640x480 canvases, axes on and off alternated in one process while two other jobs ran (ratios hold, absolute times are inflated). One panel's redraw: map 25.5 -> 10.6 ms, spectrogram 29.3 -> 10.8, λ-t 35.0 -> 11.2, SJI 30.6 -> 7.7 (−58 to −75 %). A step with every panel's axes off and every panel redrawn: map wavelength 168 -> 73 ms (−56 %), spectrogram raster step 392 -> 233 (−41 %), λ-t slit 353 -> 189 (−46 %), SJI frame 229 -> 124 (−46 %).
- What remains with the axes off: 12-28 CoordinateHelper._update_ticks calls per step, from glue's _set_wcs label round trip (WCSAxes.set_xlabel and set_ylabel place ticks eagerly and do not check `axison`, core.py:596-615 in 8.0.1). Ranked item R1 (glue) or a lazy set_xlabel (astropy) removes them.
- Fix: an opt-in 'Hide axes' in glue-solar, connecting `show_axes` to `set_axis_off`/`set_axis_on` (#90); upstream, an axes-options checkbox in glue-qt (`wp0-perf-qt`).
- Scripts: wcsaxes_study_20261001.tar.gz, `axesoff/ab.py` (one panel at a time) and `axesoff/ab_all.py` (all panels).

## SST and IRIS stress survey, 2026-10-10

`wp10-l-sst-stress` (D62, D63). **Verified the same day** by an independent session-model run with its own scripts: 10 findings confirmed, causes or numbers corrected where noted, none refuted. The numbers below are the verified ones. The archive `IRIS_PLAN_PROTOTYPES/sst_stress_20261010.tar.gz` holds:
- the survey: `report.md`, `numbers.json`, `scripts/` and `out/`;
- the verification: `verify.md` and `verify/`, with its own scripts and output.

**How it was measured.**
- **Software:** the `iris-plan-qt6` env (glue-core 1.27.0, glue-qt 0.4.2, astropy 8.0.1, irispy main 8c220d4, matplotlib 3.11.2, numpy 2.5.3, PyQt6 on Qt 6.11), with glue-solar main 4c57625; the verification ran on 75b7a73.
- **Machine and app:** macOS, 24 GB, 12 CPUs; offscreen Agg; app 1600x1000 at DPR 1; a fresh process per big cube.
- **SST path:** glue's File > Open, `load_data(path, factory=auto_data)`, then `add_datasets` with the autolinker.
- **IRIS path:** the browser (`scan_directory`, the browser's `_load`, `keep_hpc_linked`), then `quicklook`.
- **Memory and I/O:** macOS `proc_pid_rusage` (RSS, footprint, `diskio_bytesread`).
- **Cache state:** the page cache could not be dropped, but each SST cube was 0% cached at its first run, so its open, viewer and Profile numbers are cold.

**SST cubes** (numpy order t, Stokes, λ, y, x; all float32 with a -TAB WCS; memory-mapped, 0 bytes read on open). The columns are:
- Open, in s, including glue's autolinker;
- a new Image viewer, cold, in s, with the GB read;
- a slider step, first visit / warm, in ms;
- the Profile button, cold, in s, with the main-thread freeze;
- the disk read by the Profile;
- a Pixel drag with a Profile open, in ms per move;
- session restore.

| Cube | Shape | GB | Open | Viewer (read) | Step | Profile (freeze) | Read | Drag | Restore |
|---|---|---|---|---|---|---|---|---|---|
| obs492 Ca II 8542 | 6×4×21×2274×2281 | 9.86 | 0.25 | 1.8 (0.74) | 34-39 / 20 | 27.4 (21.2) | 9.2 GB | 183-194 | fails |
| obs492 Fe I 6173 | 6×4×14×2274×2280 | 6.61 | 0.25 | 1.8 (0.72) | 37-39 / 19 | 18.7 (14.9) | 6.1 GB | 195 | fails |
| obs492 Fe I 6302 | 6×4×11×2275×2280 | 5.22 | 0.24 | 1.8 (0.71) | 37-39 / 19 | 13.7 (10.5) | 4.3 GB | 201 | fails |
| obs495 Ca II K 3950 | 6×1×55×1848×1402 | 3.30 | 0.24 | 1.75 (0.68) | 27 / 17 | 8.2 (6.1) | 2.2 GB | 182 | fails |
| obs498 H-beta 4846 | 6×1×17×1846×1403 | 1.04 | 0.35* | 1.6 (0.50)* | 25 / 17 | 3.3 (1.9)* | 0.7 GB | 170-198 | fails |
| obs167 Fe I 6173 (2020) | 6×4×12×1324×1328 | 1.93 | 0.38* | refused (SST2) | 28-30 / 21 | 6.2 (3.7)* | 1.5 GB | 186 | fails |
| obs171 H-alpha (2020) | 5×1×11×1323×1326 | 0.39 | 0.33* | refused (SST2) | 25 / 21 | 1.2 (0.5)* | 0.06 GB | 189 | fails |

- **Survey-only numbers:** values marked * were not re-measured. The survey's open times included its 30 ms quiet windows, so they run about 0.1-0.35 s high. The 2020 cubes' numbers past the viewer were taken with SPECSYS set in memory.
- **What works:**
  - Playback keeps glue-qt's 100 ms timer on every cube, and plays 40 frames/s at 25 ms.
  - A rectangle subset settles in 0.25-0.28 s.
  - Session saves take 8-19 ms, 61-159 KB.
  - Peak RSS was 14.0 GB, with a 4.4 GB footprint.
  - glue-solar's generic tools work on SST cubes: Measure, Path diagram (a 4-D diagram), Follow/lock, Hide axes, Per-frame limits, Wavelength band, Physical aspect, Zoom 1:1, Colour bar, Cursor readout, Loop…, Clear point and Blink. The IRIS-only entries are hidden.

**IRIS sets**, through the browser and quicklook path; steps and moves in ms. The survey timed its restores under cProfile, which inflates them 2.5-3×, so only the verified restores are given.

| Observation, windows | Open s (load / quicklook) | Exposure or scan step | Click / move | Restore s |
|---|---|---|---|---|
| 4000255147, Si IV 1403 + SJI 1400 | 3.4-4.35 | 194-207 (7 draws) | 248-264 / 235-240 | |
| 4000255147, 9 windows + SJI 1400 | 13.4-13.6 | 865-875 (47 draws) | 760-887 / 985-991 | 6.7 |
| 3660259102 sit-and-stare, 9 windows | 12.4 | 845 | 711 / 958 | |
| 3824262996 400 steps, 8 windows | 5.6 | 361-374 | 378-385 / 417-424 | |
| 3602506433 99-scan stack, 7 windows | 16.7 (11.2 / 4.8) | 599-606 | 608 / 742 | 19.8 (SST6) |
| 3630104144 120-scan stack, 8 windows | 18.8 (12.4 / 5.5) | 693-695 | 702 / 886 | |
| 4000005156 2-scan stack, 9 windows + SJI 2796 | 10.1 | 772 | 685 / 856 | |

**Not measured:**
- An IRIS region shown on an SST Image viewer. That inverts irispy's -TAB raster WCS once per SST screen pixel; R8 gives about 6 ms per point inside a sit-and-stare's footprint.
- An SST light curve. It would be a Profile with x = time, which recomputes the whole-cube data layer (R14).
- sunpy maps beside a quicklook. They carry a plain astropy WCS that `link_hpc` links, the same class as SST1.
- Co-pointed SST and IRIS data: see SST3.

### SST1. An IRIS quicklook beside an SST cube crashes glue: wcslib is called on the SST cube's WCS from several threads, outside `WCS_LOCK`

- [x] Re-verified (2026-10-10: 4 of 4 runs crashed again)
- [x] Fixed in glue-solar (#226, 2026-10-10)

- **Cost:** 8 of 8 unprotected runs crashed, with SIGSEGV or SIGABRT, and the session was lost.
  - Most crashed while the quicklook opened; one crashed on the first SST step or drag after it.
  - No SST Profile viewer is needed: the quicklook's own spectrum panels compute the SST point's and rectangle's profiles over the IRIS windows on worker threads.
  - With every WCS entry point locked, 3 of 3 runs completed. A lock on the transforms only still aborted.
- **Cause:** `keep_hpc_linked`/`link_hpc` link the SST cube's plain astropy WCS, and its `WCSDVARR` dataset, to IRIS (20 → 122 links). glue-qt's `ComputeWorker` threads and the main thread then call wcslib on that WCS, unlocked, through:
  - `subset.to_mask` → `component_link` → `glue_patches.world2pixel_single_axis` → `all_world2pix`;
  - `pixel_selection_subset_state.to_array` → `glue_patches._to_linked_pixel_coords` → `link_manager.pixel_cid_to_pixel_cid_matrix` → the same.

  The heap corruption surfaces in whichever thread allocates next, sometimes inside IRIS's locked `_GlueWCS`. In every dump, the only unlocked wcslib calls are on the SST WCS.
- **Fix:** put the WCS of every non-`_GlueWCS` dataset that `link_hpc` links behind `WCS_LOCK`, properties too, sunpy maps included. Take the lock in `world2pixel_single_axis` and `_to_linked_pixel_coords`. Ship it with SST3's fix: once locked, the main thread waits behind multi-second worker inversions. Root cause: astropy#19174 (`wp0-astropy-19174`).
- **Evidence:** the survey's `scripts/sst.py CUBE NAME --iris sit [--wcs-lock]`; the verification's `verify/beside.py`, which also crashed with `--no-profile` and with `--no-roi` (`verify/out/b1.log` to `b4.log`).

### SST2. The 2020 SSTRED exports open but no viewer shows them: 'SPECSYS= not yet supported'

- [x] Re-verified (2026-10-10)
- [ ] Fixed (`wp13-solarnet-tab-wcs`)

- **Cost:** obs167 and obs171 cannot be displayed at all.
- **Cause:** these headers have OBSGEO but no SPECSYS.
  - astropy's `fitswcs._get_components_and_classes` raises for an empty SPECSYS when an observer location is present.
  - WCSAxes builds every axis's classes to get the celestial frame.
  - The 2023 exports carry `SPECSYS='TOPOCENT'` and work.
- **Fix:** the SOLARNET loader sets `SPECSYS='TOPOCENT'` on ground-based files without one, before glue builds the WCS. Done in memory, this makes both cubes work in every phase. The alternative is an astropy change that treats an empty SPECSYS as "no spectral observer".

### SST3. An SST region shown on an IRIS quicklook costs minutes per action, once SST1 is locked

- [x] Re-verified (2026-10-10; cause corrected)
- [x] Fixed (#226, 2026-10-10: data outside the IRIS observations are linked only on request, D64)

- **Cost:** on 4846 beside 4000255147 (9 windows), against the quicklook alone:

  | Action | With the SST region | Quicklook alone |
  |---|---|---|
  | Quicklook open | 328 s with the harness's lock; 798 s with profiles on the main thread | 13.6 s |
  | Exposure step | 3.6-4.4 s | 0.87 s |
  | SJI frame step | 2.8-3.5 s | 0.042 s |
  | Click | 3.5-4.3 s | 0.76 s |

  SST Pixel moves take 500-735 ms with IRIS open, against 194 ms alone, as the hidden IRIS tab redraws (R4, R9). RSS reaches 7.9-12.3 GB.
- **Cause:** the subset group puts the SST rectangle on all 10 IRIS datasets. `RoiSubsetState.to_mask` maps each IRIS pixel to world and through the SST WCS's `all_world2pix`; on the open, that is 774 of 788 s, 98%.
  - The verification corrected the mechanism. glue's FITS reader does not load CWDIS3 (`has_distortion` is False), so the cost is wcslib's -TAB inverse, not a distortion iteration.
  - Inverse cost: 975 µs per point inside the cube's footprint and 7.9 µs outside, where the result is NaN. The forward transform costs 0.09 µs per point.
  - The surveyed pair (a 2013 IRIS field and a 2023 SST field) never overlaps, so it measured the cheap case. Co-pointed data (obs171 with IRIS 3660258923, the real use) costs about 100× more per covered pixel, about a minute for a half-covered SJI frame.
- **#226's measurements correct the co-pointed case.** Through glue, a co-pointed SST WCS costs about what a non-overlapping one does: an SJI step took 2.05 s against 1.84 s.
  - glue inverts the SST WCS at its wavelength and time CRVAL, which lies outside the -TAB table, so every IRIS pixel takes the 7.9 µs path and gets NaN.
  - So an SST region selects no IRIS pixels even when linked: 0 of 161,796 SJI pixels got a position. D67 gives the fix to `wp13-solarnet-tab-wcs`.
- **Fix:** R2's footprint cull helps only where the region does not overlap. A faster inversion is ruled out (R8, D54). That leaves glue-solar's link scope: link non-IRIS data only on request ('IRIS: link helioprojective coordinates'), or keep foreign subsets off the quicklook's panels. The user chooses.

### SST4. The Profile button on a large cube reads the whole file, freezes the main thread for about 3/4 of the wait, and adds the file to RSS

- [x] Re-verified (2026-10-10; numbers corrected)
- [ ] Worked around in glue-solar (`wp10-l-sst-profile-hidden-data`); upstream R14, R21

- **Cost:** about 2.6-2.8 s per GB, cold. On 8542:
  - 27.4 s, of which 21.2 s is frozen;
  - 9.2 GB read;
  - RSS 10.3 GB steady, 14.0 GB peak, with a 4.4 GB footprint peak.

  The table above has every cube. Two dialogs come first: 'Creating a profile viewer', then 'Add large data set?'.
- **Cause:**
  - `ProfileViewerState._reset_y_limits` computes the whole-cube maximum on the main thread.
  - The worker then computes it again on a warm cache: 5.9 s on 8542.
  - `compute_statistic` chunks only along the profile axis, so each chunk is one λ plane, 1.24e8 values on 8542. Its float64 copy is about 1 GB, which is what pushes the footprint to 4.4 GB (R21).
- **Fix:** upstream, R14 and R21, or glue-qt adding the data layer hidden at `large_data_size`. glue-solar can hide the data layer of non-IRIS cubes of 1e8 values or more now, as S13 does for the quicklook. That also removes SST9.

### SST5. SST sessions save but never restore ('HDUList is required'), including the autosaved last session

- [x] Re-verified (2026-10-10)
- [ ] Fixed (`wp13-solarnet-tab-wcs`)

- **Cost:** restore fails within 5-12 ms on 8542, 6173, 6302, 3950 and obs171.
- **Autosave:** closing the app with an SST cube open writes a 65 KB `glue-solar-last-session.glu`. Its 1 MB guard lets it through, because glue's FITS components carry load logs. 'IRIS: restore last session' then fails the same way.
- **Cause:** glue saves the WCS as a header string and rebuilds it with `WCS(Header)` without the HDUList (`glue/core/state.py` `_save_wcs`/`_load_wcs`).
- **Fix:** a saver or session patch that rebuilds the WCS from the logged file.

### SST6. Restoring a multi-window stack reads every raster file once per window

- [x] Re-verified (2026-10-10; cost corrected)
- [ ] Fixed in glue-solar (`wp3-l-restore-one-read`)

- **Cost:** 3602506433 with 7 windows and 99 files restores in 19.8 s. Of that, 13.8 s is data, in 693 `read_files` calls (99 × 7). The browser loads it in 10.9 s with 99 calls. The survey's 49.3 s, and its 70.7 s for 3630104144, ran under cProfile.
- **Cause:** each window has its own load log, and restoring it (`raster_files_data` → `_raster_windows_data(files, [window])`) opens every file for that one window.
- **Fix:** read each file once for all logged windows of one restore, with a session patch that groups the raster logs or a per-restore cache. Tested directly: one call for all 7 windows takes 5.6-6.3 s against 13.5 s for one per window, so the restore should drop to about 12 s.

### SST7. Each ticked window multiplies the quicklook's redraws: about 4× per step with 9 windows

- [x] Re-verified (2026-10-10)
- [ ] Fixed in glue-solar (`wp4-l-window-rows-redraw`); per-draw cost R1, R5, R18

- **Cost:** on 4000255147, going from 1 window to 9:

  | Action | 1 window | 9 windows |
  |---|---|---|
  | Exposure step | 194-207 ms, 7 draws | 865-875 ms, 47 draws |
  | Click | 248-264 ms | 760-887 ms |
  | Move | 235-240 ms | 985-991 ms |
  | Open | 3.4-4.35 s | 13.4-13.6 s |

  The map λ step (95 ms) and the SJI frame step (48 ms) do not change. With the point curves, row and column open, a move takes 1668 ms.
- **Cause:** every other window's spectrum panel and λ panel redraws on each step and move.
- **Fix:** blit the moving time and point markers, refresh images only when their slice changes, or redraw only the visible rows.

### SST8. An SST Pixel drag with a Profile open costs about 190 ms per move

- [x] Re-verified (2026-10-10; split corrected)

- **Cost:** 170-201 ms per move with a Profile viewer open, against 31-34 ms without one.
  - About 95-110 ms is waiting: R3's 25 Hz polling, twice.
  - About 44-57 ms is the Profile viewer's extra draws on the main thread.
  - The worker computes for only 0.4-0.5 ms, and the cube-sized mask stays virtual.
- **Covered by** R3 (a) for the wait, and R3 (b), v_min/v_max no longer triggering a recompute, for the draws; and R7.

### SST9. A Path diagram, or any link change, recomputes the Profile's whole-cube data layer

- [x] Re-verified (2026-10-10; cause corrected)

- **Cost:** after Enter (0.17-0.18 s) comes a settle of 3.5-7.0 s, varying with how many recomputes the link change triggers; 5.3 s on 8542.
- **Cause:** the Path adds 3 links. Then `Data._update_externally_derivable_components` broadcasts (`glue/core/data.py:640-660`), `Viewer._update_data` follows (`glue/viewers/common/viewer.py:288-307`), and `ProfileLayerArtist.update` resets its cache. The data layer's whole-cube maximum recomputes (5.35 s on 8542); the rectangle's profile takes only 0.36-0.42 s.
- **Covered by** R11, as its Profile data-layer case; `wp10-l-sst-profile-hidden-data` removes it for large non-IRIS cubes.

### SST10. A new Image viewer on a cold memory-mapped cube reads about 0.7 GB at random for its Min/Max limits

- [x] Re-verified (2026-10-10)
- [ ] Fixed upstream (`wp0-perf-core-stats-io`, as R32)

- **Cost:** 1.75-1.82 s cold against 0.53-0.55 s warm, reading 0.68-0.74 GB in about 10,000 page-ins. `compute_statistic` takes 1.17-1.25 s.
- **Cause:** `StateAttributeLimitsHelper` (`glue/core/state_objects.py:405-422`) calls `random_subset`, which draws 10,000 uniform random indices with one `np.random.randint` per axis (`glue/core/data.py:1849-1851`, `glue/utils/array.py:756`). Each index lands on a different page of the mapped file.
- **Fix:** sample whole planes or rows, as glue-solar's `RawComponent._sample` does, or sort the indices by page.

### SST11. 'Light curves of every window and SJI…' is offered on a single-scan raster with no SJI, then refuses

- [x] Re-verified (2026-10-10, on 75b7a73)
- [ ] Fixed in glue-solar (`wp11-l-point-curves-offered`)

- **Cost:** an error box on 3824262996 ('… has no exposures or scans, and its observation no slit-jaw image loaded').
- **Cause:** `_PointCurvesEntry.offered` checks only for an IRIS role.
- **Fix:** make `offered` run `_point_curves`' own check (D61: entries hide where they cannot act).

### SST12. File > Open makes 33 datasets per SST cube

- [x] Re-verified (2026-10-10; description corrected)
- [ ] Fixed (`wp13-solarnet-tab-wcs`)

- **What it makes:** glue's `fits_reader` (priority 100) reads every HDU; glue-solar's IRIS factory declines in 1.3 ms. The 33 datasets are:
  - the cube, 5-D and memory-mapped;
  - `WCSDVARR`, 5-D with its own WCS, which looks like data;
  - 31 empty 0-D datasets with no components: `WCS-TAB` and the 30 `VAR-EXT` tables, whose multi-dimensional columns glue drops with about 30 warnings.
- **Cost:** the open takes 0.24-0.25 s and reads 0 bytes.

### SST13. A cold sit-and-stare in the browser reads the whole raster file

- [x] Re-verified (2026-10-10; cause corrected)

- **Cost:** 1.43 of 1.43 GB is read on 3660259102, during the browser's `_load`, on its worker thread behind the progress bar. The load takes 3.5-4.6 s cold against 2.8 s warm. The quicklook's own phase reads 5 MB.
- **Cause:** `_load` samples each shown dataset's colour limits with `RawComponent._sample`, up to `SAMPLE_BYTES` (512 MiB) of whole planes each. With 9 windows, the samples cover the file.
- **Decision** (D63, PROVISIONAL): no action. It costs 1-2 s cold on an SSD, off the main thread.

## Decoupling WCSAxes from matplotlib

This is a read-only feasibility study of astropy main 1f930be7c4 (2026-09-28), answering whether WCSAxes could work outside matplotlib, for example in Qt. File:line references are to `astropy/visualization/wcsaxes/` on main. The call counts come from `decouple/count_calls.py` in wcsaxes_study_20261001.tar.gz, an Agg script with no timing: a FITS helioprojective TAN WCS with an IRIS-like roll, a 500x500 image, and a 6x6 inch figure.

- One draw makes 37 `pixel_to_world_values` calls on 26,625 points. 33 of those calls are one tick placement.
- `get_xlabel()` on its own makes the same 33 calls.
- Label layout makes 2 text-extent calls per tick label (12 for 6 labels) and 1 per axis label.

- [ ] Re-verified on current versions
- [ ] Proposed upstream

**Short answer.** Yes, and it is less work than it looks.

- WCSAxes already bypasses matplotlib's Axis, Tick and Locator machinery. It hides them (core.py:195-202) and draws its own decorations through a dummy z-order artist (core.py:32-48). The exception is the 1D frame, which keeps matplotlib's own y axis (core.py:201, 723-724).
- Its only ticker import is `Formatter.fix_minus` (formatter_locator.py:16, 65).
- About 1,800 of the 6,633 source lines are already free of matplotlib, or nearly so.
- The coupled geometry needs only the view limits, the data-to-display transform (an affine for linear axes) and the DPI. Only label anchoring, overlap removal and axis-label placement need a text renderer.

Decoupling does not make glue faster by itself. The measured cost is WCS calls, and those are the same whichever toolkit draws. Do the speed fixes (R1, R5) first, and shape them so they produce the first matplotlib-free function.

### Coupling map

| Module (lines) | Takes from matplotlib | Pure geometry or formatting |
|---|---|---|
| core.py (1061) | `Axes` subclass (51), `subplot_class_factory` (1058), z-order Artist hack (32-48), `transData` override (143-146), canvas key event (154), `Affine2D`/`Transform` in `get_transform` (817-911), `get_tightbbox` re-runs the whole `draw_wcsaxes` (913-926), `rcParams['axes.grid']` (553), wrappers for imshow, contour and `*_coord` | orchestration (556-583, 585-626), `format_coord` (160-187), SkyCoord to arrays (303-355) |
| coordinates_map.py (203) | only `axes.get_xlim/ylim` in `get_coord_range` (161-176) | container, aliases, repr |
| coordinate_helpers.py (1652) | rcParams (125, 140-147), one `PathPatch` per grid line clipped to the frame patch (919-942), `Path` codes (1279, 1426-1427), `axes.contour` for contour grids (1520), `transData` for tick angles (1023-1067), renderer groups (920-982), arbitrary Text/PathPatch kwargs in `set_ticklabel`, `set_axislabel` and `grid` (659-696, 739-769, 335-380) | locator calls, spine crossings by interpolation, longitude wrapping (1100-1241), grid sampling and world-to-pixel (1281-1339), label strings (1136) |
| frame.py (462) | `Line2D`/`PathPatch` drawing (200-230, 360-375, 441-462), rcParams (178-179), `Spine._get_pixel` through `transData` (67-68) for normals (104-109) and the label midpoint (111-129), spines read `parent_axes.get_xlim` (386-395) | spine outlines in data pixels, resampling (232-249), position validation |
| ticks.py (249) | `Line2D` subclass used for style (11), rcParams (51-62), one `renderer.draw_markers` per tick (230-247), `points_to_pixels` (188) | per-spine storage of world, pixel, angle and displacement (142-167) |
| ticklabels.py (376) | `Text` subclass (43), `get_window_extent` twice per label (257, 332), `transData` (251), `points_to_pixels` (252), `Bbox.count_overlaps` (373), rcParams minus sign (28-32) | sorting, label simplification (153-197), anchor geometry from width and height (262-305) |
| axislabels.py (151) | `Text` subclass (12), rcParams (15-20), `Bbox.union` of tick-label boxes (114), draws and then measures (148-151) | rotation and padding rules (98-145) |
| grid_paths.py (120) | `Path` with MOVETO/LINETO codes (5, 55-88) | discontinuity and round-trip masking |
| formatter_locator.py (721) | `rcParams['text.usetex']` (490), `fix_minus` (65), mathtext separators `$\mathregular{^h}$` (527-531) | locators (385-439, 650-697), `Angle.to_string`, format parsing |
| transforms.py (238) | `CurvedTransform` subclasses `Transform` (31), `Path` (54) | frame-to-frame conversion through SkyCoord (118-154) |
| wcsapi.py (491) | the WCS transforms inherit `CurvedTransform` (340, 419) | coord_meta from APE 14 (135-293), slicing (296-329), `pixel_to_world_values` (478) |
| utils.py (174) | `transform_contour_set_inplace` takes a ContourSet (117-174) | `select_step_*` (15-87), `get_coord_meta` |
| coordinate_range.py (147), _auto.py (139) | none: the transform is duck-typed | range finding modelled on PGSBOX, automatic spine assignment |
| helpers.py (198) | all of it: `AuxTransformBox`, `Ellipse`, `AnchoredOffsetbox` (113-123), `AnchoredSizeBar` (186) | pixel-scale arithmetic |
| patches.py (202) | `Polygon` subclasses (68, 133) | vertex generation (37-66) |

Aside, checked: `coords.frame.update()` (core.py:571) is `OrderedDict.update()` called with no arguments, so it does nothing. `BaseFrame` subclasses OrderedDict (frame.py:155) and defines no `update`.

### What the tick algorithm actually needs

- **Data pixels plus the WCS only.**
  - Coordinate range: one 51x51 call (coordinate_range.py:44-58).
  - Tick values and spacing: the locators.
  - Frame sampling: 4x1000 points per coordinate (frame.py:232-249).
  - Spine crossings (coordinate_helpers.py:1100-1241).
  - Grid paths (1281-1339 and grid_paths.py).
  - Automatic spine assignment (_auto.py).
- **Display geometry, but only through the transform.**
  - Tick angles shift the samples 2 device pixels and map them back through `transData.inverted()` (coordinate_helpers.py:1023-1067).
  - Spine normals go through `transData` (frame.py:104-109).
  - For linear axes this is a 2x2 matrix (aspect ratio and flips), and no renderer is involved.
  - Tick lengths and pads also need the DPI.
- **Needs a text renderer.**
  - Label anchors need each label's width and height (ticklabels.py:257-305).
  - Overlap removal needs the final boxes (373).
  - Axis-label placement needs the union of the tick-label boxes and the size of the rotated label (axislabels.py:108-151).
  - These steps run in order: tick labels for every coordinate, then axis labels against all the boxes (core.py:606-624).
- **Label strings** are pure, but they are written for matplotlib. They contain mathtext such as the hour-angle separators and `{unit:latex}` axis labels (coordinate_helpers.py:819), and they read rcParams. A non-matplotlib backend needs a `'unicode'` output mode; `Angle.to_string` already has one.

Of the 33 calls in one placement:

- 16 are the 2-pixel shifts for the tick angles (60% of the points).
- 8 resample the same frame again for the second coordinate, with identical input.
- 1 is the range grid; the rest are 2-point spine updates.

None of these depend on how the result is drawn.

### A split

```python
# _layout.py: imports numpy and astropy only
place_ticks(pixel_to_world, coord_specs, spines, to_display, from_display, dpi, settings)
    -> {coord: {spine: TickSet(world, pixel_xy, angle_deg, normal_deg, disp, text)}}
place_labels(ticks, measure, pad_px, tick_out_px, exclude_overlapping)
    -> anchors, kept flags, boxes   # optional phase
place_axis_labels(spines, label_boxes, measure, ...)
grid_lines(world_to_pixel, pixel_to_world, coord_range, ...) -> list of (K, 2) polylines with breaks
```

- **Inputs:**
  - An APE 14 low-level WCS plus slices, through the existing `apply_slices` and `WCSPixel2WorldTransform.transform`. These only need wrapping, not a new base class.
  - View limits and the spine outlines in data pixels.
  - `measure(text) -> (w, h)`.
  - A text mode: mathtext, unicode or ascii.
  - Locator and format settings.
- **Outputs:** the TickSet fields above plus grid polylines in data pixels.
- **The matplotlib backend** is today's classes, slimmed down. `Ticks`, `TickLabels` and `AxisLabels` keep their style APIs but receive positions. `draw_wcsaxes` passes `transData.transform` and its inverse, plus a `measure` backed by the renderer.

**Public API that must stay:**

- The `WCSAxes` constructor and `projection=wcs`, `reset_wcs`, `get_coords_overlay`, and `get_transform`, which returns a matplotlib Transform.
- `plot_coord`, `scatter_coord`, `text_coord`, the imshow and contour overrides, `grid`, `tick_params`, and `set_xlabel`/`get_xlabel` and their y versions.
- `CoordinatesMap` indexing.
- Every `CoordinateHelper` setter and getter: `set_ticks`, `set_ticklabel(**Text kwargs)`, `set_axislabel(**Text kwargs)`, `set_major_formatter`, `set_format_unit`, `set_separator`, the position and visibility setters, the minor-tick setters, `add_tickable_gridline`, `format_coord`, and the `locator`/`formatter` properties.
- `SphericalCircle`, `Quadrangle`, `add_beam` and `add_scalebar` stay matplotlib-only.

**Extension points that constrain where the boundary goes:**

- Users subclass `BaseFrame` and read `self.parent_axes.get_xlim()` (docs custom_frames.rst:81-86). So the core should consume the spines' arrays, not replace frames.
- The transforms are public matplotlib Transforms (transforms.py:23-28, generic_transforms.rst). The core should duck-type `.transform`, `.inverted` and `.has_inverse`.
- Downstream code touches internals: glue uses `frame.set_color` and `reset_wcs`, mpl-animators calls `reset_wcs` per frame (sunpy/mpl-animators#3), and sunpy uses others.

**Size.** About 1,100-1,200 lines move behind the boundary:

- `_update_ticks`, `_compute_ticks` and the grids: about 560.
- Frame geometry: about 250.
- Label layout: about 200.
- Axis labels: about 90.
- Orchestration: about 80.

That is plus 400-600 new lines (result types, entry points, adapter): roughly 2-3k changed lines over 3-4 PRs.

**Test guard.**

- There are 56 `@figure_test` tests: test_images.py 47, test_frame.py 4, test_transform_coord_meta.py 3, test_wcsapi.py 2.
- They compare hashes exactly (tolerance 0, astropy/tests/figures/helpers.py:22) against two hash libraries (tox.ini:4-6, 26), with baselines in astropy/astropy-figure-tests.
- A pure move that keeps the arithmetic order keeps every hash. That is a strong regression guard with no churn, provided the matplotlib backend passes `transData`'s own callables rather than a recomputed 2x2 matrix.
- Numeric changes go in separate PRs that regenerate the hashes.
- Add matplotlib-free unit tests: import the core in a subprocess with `sys.modules['matplotlib'] = None`, and compare stored tick tables for TAN, an all-sky CAR with wrap, AIT with an elliptical frame, a sliced 3D cube, helioprojective with roll, and the 1D frame.
- Existing tests that touch private attributes: test_misc.py and test_coordinate_helpers.py (`_axislabels`, `_coord_range`, spines) and test_wcsapi.py (`_ticks`).

### Prior art and other consumers

- [astropy#9993](https://github.com/astropy/astropy/issues/9993) (Robitaille, 2020, open, needs-discussion), "Think about ways to make WCSAxes be usable by other plotting libraries", raised for STScI's Jupyter tools. mhvk advised waiting for a concrete request.
- [astropy#16464](https://github.com/astropy/astropy/issues/16464) (2024, open) proposes public `CoordinateHelper.get_ticks()`/`get_ticklabels()` and mentions splitting the core out. pllim asked whether that needs an APE and whether it overlaps with astrowidgets.
- [glue-jupyter#154](https://github.com/glue-viz/glue-jupyter/issues/154) (2020, open) asks for world coordinates in the bqplot image viewer and is blocked on #9993. Maarten Breddels said bqplot takes `tick_values`, but labels only through a formatter.
  - Today the viewer only sets the axis label to the world attribute name (glue_jupyter/bqplot/image/viewer.py:68-74), and its ticks are pixel indices.
  - jdaviz Imviz inherits this: its compass, coords_info and orientation plugins show world information, but there are no WCS ticks.
  - Both glue-qt (through matplotlib, unchanged) and glue-jupyter's bqplot viewer (new) would use a core.
  - A browser backend cannot measure text synchronously from the kernel, so the label phase must be optional or approximate.
- **Ginga** has its own [WCSAxes canvas object](https://github.com/ejeschke/ginga/blob/main/ginga/canvas/types/astro.py) (lines 1079-1260). It draws grid lines with labels inside the image, celestial only, and recomputes only when the limits or rotation change. It has no spine ticks.
- **ds9** uses Starlink AST `astPlot` plus `astGrid` through a Tk backend ([tksao/frame/grid2d.C:171-172](https://github.com/SAOImageDS9/SAOImageDS9/blob/master/tksao/frame/grid2d.C)). AST's GRF callbacks (Line, Mark, Text, TxExt for text extent, Qch, Scales, Attr, Cap) are a long-standing precedent for this exact split. starlink-pyast ships a [matplotlib GRF](https://github.com/Starlink/starlink-pyast/blob/master/src/starlink/Grf.py) (lines 198-399). WCSAxes' range finder is itself "inspired by PGSBOX" (coordinate_range.py:11).
- **Firefly** (drawingLayers/WebGrid.js, ComputeWebGridData.js) and **Aladin Lite / ipyaladin** (Rust/WebGL, src/core/src/renderable/grid/) have their own grids, which cannot be reused from Python.
- **matplotlib's axisartist** `grid_finder.py` already separates grid computation from the artists, and WCSAxes' `select_step_*` came from it (utils.py:16).
- **Nothing found** for pyqtgraph, vispy, napari, Bokeh or plotly (issue, repo and code searches). pyqtgraph's `AxisItem.setTicks` takes (value, string) pairs, which only covers unrotated rectangular axes. An IRIS SJI with roll needs ticks of one coordinate on two spines, at an angle, so any second backend has to draw its own tick items, as WCSAxes does in matplotlib.

### Would a Qt-native renderer be faster?

R5 and R18 measured an SJI draw at 28.4 ms:

- WCSAxes takes 24.5 ms of it.
- Tick placement takes 16.2-16.5 ms of that.
- Placement is mostly 33 gWCS calls at 0.36-0.41 ms each, nearly independent of the number of points.

Placement costs the same under QPainter, pyqtgraph or bqplot, because it is the same `pixel_to_world` calls. A renderer swap can only reach the remaining WCSAxes drawing, about 8 ms per SJI draw. That figure is derived from the notes, not measured: label layout and drawing, one `draw_markers` call per tick (ticks.py:230-247) and the frame lines. Part of it can also be removed inside matplotlib, by batching the tick markers per spine and caching label anchors with the placement. On maximized or HiDPI panels the cost is the image path (R19), which a Qt WCS axis does not touch. For glue-solar, hiding the axes (S14) already removes all of it.

- **The speed fixes need no decoupling.**
  - R5: batch the frame and shifted samples into about 2 calls (estimated -12 to -13 ms per SJI placement), and cache the placement while limits, size, transform and slice are unchanged (-16 ms per redrawn SJI viewer).
  - R1: glue's label fix, or a lazy `set_xlabel` in astropy (SJI step 105 -> 39 ms).
- **What decoupling buys:**
  - Reuse in glue-jupyter, jdaviz and other toolkits.
  - Tests that do not need matplotlib.
  - A pure function whose inputs are an obvious cache key.
- **What it costs in glue-qt:** a Qt overlay would make the screen differ from matplotlib export and from glue's script export (glue/viewers/image/viewer.py:247), unless the whole viewer left matplotlib.

### Recommendation

It is worth proposing upstream, but as the third step, and argued on reuse rather than speed.

1. R1 in glue-core (with a lazy `set_xlabel` in astropy) and R5 in astropy. Write R5's batched sampling as a matplotlib-free function that takes `pixel_to_world`, the spines in data pixels and the display-transform callables. That is the core's first piece, and the measured speed gain justifies it on its own.
2. #16464's getters. They are small and unblock glue-jupyter#154 with a hidden Agg WCSAxes as a stopgap.
3. The split itself, discussed on #9993/#16464 first (which answers pllim's APE question). Order it as a pure-move PR with unchanged hashes, then the public core API, then a bqplot backend in glue-jupyter (not in astropy) as the proof.

**Risks:**

- Few people maintain it. Robitaille wrote 191 of the 430 non-test commits ever made to wcsaxes, and 70 of the 152 since 2023.
- The figure tests compare hashes exactly, so any reordering of floating-point operations changes the images. Keep numeric changes out of the move PRs.
- Custom frames, matplotlib Transforms and the free-form Text/PathPatch kwargs fix where the boundary can go.
- Downstream code uses private attributes.
- #9993 has sat in needs-discussion for six years, so a working second backend will carry the proposal better than another issue.

### Matplotlib-free core prototype

Built 2026-10-01 as a starting point for in-person discussion. It does step 3 of the Recommendation above, ahead of steps 1 and 2. WCSAxes' tick, grid and label geometry moves into a new module, `astropy/visualization/wcsaxes/_layout.py`, which imports only numpy and astropy. The matplotlib classes call it, and every figure renders as before. Two demos outside astropy draw the same ticks with Qt and with bqplot.

- [x] Pushed to the fork as a private copy (branches only: no PR, no upstream notice)
- [x] Reviewed by Fable 5.1 (2026-10-01; fixes pushed on top as new commits)
- [ ] Proposed upstream

**Where things are.**
- 2026-10-07: the fork's heads have moved past the tips below (`wcsaxes-layout-core` b8cef6ea98, `-core-demos` 58d0fb37ec), beside the user's `wcsaxes-layout-core-minimal` and `wcsaxes-layout-model`; the local clone, the demos repository and the env's editable astropy below are gone, so re-clone the fork before any WCSAxes work.
- Branches on the user's fork nabobalis/astropy: `wcsaxes-layout-core` (4 move commits plus 5 review commits, tip 7f4e1cb774, on upstream main c55a2b2067 of 2026-09-30) and `wcsaxes-layout-core-demos` (the same plus the demos under `demos/wcsaxes_core/`, tip c685829d4a). Pushed 2026-10-01; no PR and no upstream notice. Local clone: `/Users/nabil/Git/astropy-wcsaxes-core`, with a `fork` remote and origin's push URL disabled. `/Users/nabil/Git/astropy` was only read.
- Demos: `demos/wcsaxes_core/` on the demos branch (`qt/`, `bqplot/`, `check_move.py`, `README.md`), copied from the local repository `/Users/nabil/Git/wcsaxes-core-demos` where they were written (no remote).
- Env: micromamba `astropy-wcsaxes-core` (Python 3.13.15, numpy 2.5.3, matplotlib 3.11.2, PyQt5 5.15.11, bqplot 0.13.1, pytest-mpl 0.19.0). astropy 8.1.0.dev676 is an editable install of the clone. The linters match astropy's pre-commit pins: ruff 0.15.20, codespell 2.4.3 and numpydoc 1.10.0.
- Scripts: `IRIS_PLAN_PROTOTYPES/wcsaxes_core_20261001.tar.gz` holds the design (`wcsaxes-core/design.md`; sections 12 and 13 cover the two review rounds), the check scripts (`tick_tables.py`, `compare_figures.sh`, `no_mpl.py`, `review_fix/run_checks.sh`) and the Fable probes. The baselines are not archived; the scripts regenerate them from c55a2b2067.

**Commits** (12 files, +2071/−621; `_layout.py` is 1174 lines, `tests/test_layout.py` 659):

| SHA | Commit | What moves |
|---|---|---|
| ab1da84b88 | Move WCSAxes tick placement into a matplotlib-free module | Spine resampling and normals, tick placement. Also a tolerant package `__init__`, the changelog fragment `XXXXX.api.rst` and the no-matplotlib tests |
| 46a6b95e79 | Compute WCSAxes grid lines in the matplotlib-free layout module | Grid line vertices and path codes. `grid_paths` keeps thin wrappers |
| 4d9b546e32 | Lay out WCSAxes tick labels in the matplotlib-free layout module | Sorting, simplification, anchoring and overlap removal of tick labels. `measure` is a callable |
| 8371f45c41 | Place WCSAxes axis labels in the matplotlib-free layout module | Spine midpoint and axis-label position |

Demos: 6f55618 (Qt), 07def1f (bqplot), d18fde0 (`check_move.py`). No commit message in either repository contains `#`, `@` or `github.com`, so pushing creates no notices. Each message ends with the Claude-Session line.

**What was verified, and how.** Every check ran on each of the 4 commits, against baselines taken from c55a2b2067:
- **Figures.** All 59 figure tests have byte-identical PNG hashes at tolerance 0 (`test_latex_labels` is excluded: no TeX on this machine). A run with one dot added to a figure fails, so the check can see a change.
- **Tick tables.** `tick_tables.py` records 16 cases, each drawn 4 times (initial, pan, zoom, resize): ticks, labels as drawn, grid paths, axis labels and frame data. The output is byte-identical to the baseline (`cmp`). A label-state dump (positions, alignments, boxes) is also identical.
- **Call counts.** `pixel_to_world_values` plus `world_to_pixel_values` calls per draw are unchanged in all 16 cases, for example tan 37, overlay 94, car_allsky 61/49/55/55 and tickable_gridline 126/114/126/126. No timing was done.
- **Tests.** astropy's own pytest config, run through `-c`: 270 passed, 63 skipped, 1 xfailed; with `--remote-data=any`, 330 passed, 3 skipped, 1 xfailed. The baseline was 261 and 321; the 9 new tests account for the difference. One new test imports `_layout` in a subprocess with `sys.modules['matplotlib'] = None` and lays out TAN and off-sky AIT images against stored values. Each commit's mutation runs failed at least one test, apart from the two gaps listed under the open findings.
- **No-matplotlib import.** With matplotlib blocked, `astropy.visualization.wcsaxes`, `_layout` and `coordinate_range` import. Asking for `WCSAxes` and the other public names raises `ModuleNotFoundError` naming matplotlib. Test collection without matplotlib gives 12 skipped and no errors.
- **Independent review.** A second agent re-ran all of this and wrote a 26-scenario differential harness that runs on both the base and HEAD. The scenarios cover custom frames, overlays, 3-D slices, `reset_wcs`, tight bbox saves to PNG, PDF and SVG, and `format_coord`, and the harness records every WCS call in order. The base and HEAD outputs are byte-identical.
- **Lint.** ruff check and format, codespell and numpydoc pass on every touched file.
- **Move check.** `check_move.py` applies the renames (`self.` to `spec.` and so on) to the 17 moved pieces at the base and compares them with `_layout` through `ast.unparse`. 251 lines are the same, 69 stayed behind or were replaced, and 25 are new.

**Review findings left open.**
- **The diff does not read as a move.** `--color-moved` marks only part of it, because the moved code is renamed on the way. `check_move.py` shows the move instead. For a PR, the better form is two commits per step, a rename in place and then a byte-for-byte move (8 commits). Offering commit 1 on its own is also an option.
- **With matplotlib installed, `_layout` still loads it.** Importing `_layout` runs the package `__init__`, which imports the public API (86 matplotlib modules, including `matplotlib.axes`). `formatter_locator` reads `rcParams` and `Formatter.fix_minus`. The commit messages now say that only `_layout` itself does not need matplotlib. A lazy `__init__` was not done, because it would change when matplotlib is imported for every user.
- **Import behaviour change.** Without matplotlib, the package now imports and only its classes fail. This is stated in the changelog fragment. `XXXXX` has to be renamed once there is a number.
- **The label boundary is TickLabels' storage.** The labels go through a namespace of six `defaultdict(list)`. `_layout.tick_labels(placed)` now builds it. Kept boxes passed between coordinates, and the union for axis labels, are still left to the caller. `TickTable`'s field names (`angle`, `normal`, `disp`) were not renamed; their docstring maps them to the label names.
- **Tests.** The no-matplotlib test is a 195-line script in a string, checked against a hand-maintained snapshot. The two tests that compare with WCSAxes check that plain inputs are enough (plumbing), not the algorithm; the figure hashes and the snapshot guard the algorithm. The new tests do not catch the dx NaN fallback or the segment index on curved spines; the figure tests and tick tables do.
- **One residual draw case.** A `TickLabels` drawn with `exclude_overlapping` on and no non-empty labels, before `_existing_bboxes` is set, would still raise. No code path does this (design.md 6.8(h)).

**Fable 5.1 review (2026-10-01).** Two reviewers on a different model from the implementers.
- **Behaviour.** A line-by-line read against c55a2b2067 found no change in operation order, NaN handling, longitude wrapping, the second-crossing logic, minor ticks, the 1-D branch or label geometry. The one ported routine, the overlap count, matched matplotlib's `Bbox.count_overlaps` in 20,000 adversarial cases. sunpy, aplpy, ndcube, mpl-animators, glue, yt, gammapy, pvextractor and jdaviz reach into none of the moved names. Three low findings at the edges: the grid's inverse transform was built before the no-ticks return (fixed: built lazily again); state left behind when a draw raises part way differs (documented in design.md 6.8(c)); `coordinate_helpers.wrap_angle_at` no longer feeds tick placement (commented). Verdict: "safe to show maintainers as a pure move; the pushback will be about size and the rename-heavy diff, not behaviour."
- **Maintainer read.** The tick, grid and axis-label halves are the right cut. The tick-label half is TickLabels' internals with `self.` removed and should be presented as the step that needs a redesign (a label table), not a move. The import change for running without matplotlib is the only API change and nothing can use it yet, because `formatter_locator` and `wcsapi` still need matplotlib. The new tests guarded mostly plumbing (fixed: in-process tests against hand-worked results, rerun with matplotlib blocked). For upstream: open with ticks only, as a rename-in-place commit followed by a cut-and-paste commit, without the import machinery.
- **Applied on top:** lazy grid inverse; the wcsaxes tests skipped through a conftest instead of `tests/__init__.py` (which had broken `pkgutil.walk_packages` and `generate_config` over astropy without matplotlib); TickLabels filled from `_layout.label_store`; a narrower `_layout` surface; hand-checked tests. Every commit: 59 of 59 figures hash-identical, tick tables and WCS call counts identical, 273 passed (333 with remote data).
- **Left for the user and maintainers:** keeping or dropping the import change in a first PR (the fix agent kept it, because without it `_layout` cannot run without matplotlib at all); the label-table redesign; splitting the series for upstream, which needs a history rewrite of the fork branches.

**What the demos showed.** Both demos call only `_layout`, `find_coordinate_range` and `AngleFormatterLocator`. They create no Figure, Axes, transform or renderer, and they check at exit that pyplot, figure and the backend modules were never imported. Each has a `compare.py` that draws WCSAxes on the same frame and exits 1 on a mismatch. Both exit 0 on the final branch. The cases are a rolled helioprojective WCS, an all-sky CAR with the 0/360 seam, and a TAN RA/Dec image, each as first drawn and after a pan, zoom and resize.
- **Exact:** tick world values, label texts after simplification, which labels are drawn, and grid vertices and codes.
- **Positions:** ticks agree to 1e-12 px and 1e-11°. Label anchors agree within 0.5 px in Qt, which measures text with its own metrics, and to 0.00 px in bqplot, which measures with Pillow and DejaVu Sans. The exception is TAN RA, off by up to 3.45 px: matplotlib draws the hour superscripts as mathtext and the demos use Unicode.
- **Qt** (QPainter, 374 lines): pan, zoom and resize just repaint, and the layout is recomputed on every paint. **bqplot:** the layout is recomputed when the scales change, which is what PanZoom triggers. There is also a notebook, plus static HTML pages and screenshots.

**What the demos could not show.**
- They cannot run without matplotlib installed (see the open findings above).
- Hour labels are mathtext, which the demos map to Unicode by string replacement. Default axis labels that carry a unit have the same problem.
- Coordinate metadata (type, wrap, format unit) is written by hand, because `transform_coord_meta_from_wcs` needs a matplotlib frame and Transform. Label spines are fixed: the automatic placement is not in the core.
- Part of each demo's `layout()` (90 lines in Qt, 69 in bqplot) still redoes what `CoordinateHelper` and `AxisLabels` do around the core: passing kept boxes between coordinates, the union for axis labels, and the label visibility rule.
- `measure` must follow matplotlib's convention: the advance width, and a height of one em unless the ink is taller. Qt's natural line height put labels 2.4 px off. bqplot's kernel cannot measure text in the browser, so its boxes are approximate.
- Not exercised: overlap exclusion (no labels overlap in any view), minor ticks, the interactive Qt window (offscreen only), and mouse pan and zoom in a live Jupyter session (no kernel here; the HTML pages are static).

## WCSAxes tick rendering

This section records a read-only study of astropy's WCSAxes. It covers how WCSAxes places and draws ticks, where the time goes on IRIS data, and three ways to make it cheaper. Each way was built as a runtime monkeypatch and then re-measured by a second agent (the "skeptic") with its own harness. Nothing in astropy, glue, glue-qt, glue-solar or irispy was edited, and nothing was posted upstream. It expands R5 and the astropy halves of R1 and R18. The architecture question (can WCSAxes leave matplotlib) is in "Decoupling WCSAxes from matplotlib" above.

- [ ] Re-verified on current versions
- [ ] Proposed upstream (M4, on the user's direction)

**References and versions.**
- File:line references are to `astropy/visualization/wcsaxes/` on astropy main 1f930be7c4, the #20499 merge. The wcsaxes tree is unchanged at c55a2b2067. "8.0.1:" marks a line in the installed release, which every prototype ran against.
- Scripts are in `IRIS_PLAN_PROTOTYPES/wcsaxes_study_20261001.tar.gz`. Paths below are relative to that archive.
- Run them with `env HOME="$(mktemp -d)" QT_QPA_PLATFORM=offscreen MPLBACKEND=agg ~/mamba/envs/iris-plan/bin/python <script>` from the archive root, with a glue-solar checkout first on `sys.path`.
- Versions: astropy 8.0.1, matplotlib 3.11.2, gwcs 1.0.3, numpy 2.5.3, glue-core 1.27.0. glue-solar was main 2fdb847, at /Users/nabil/Git/glue-solar-main.

**Short answer.**
- **The WCS is called too often.** WCSAxes is slow on IRIS because of this, not because of matplotlib.
  - An SJI draw makes 37 `pixel_to_world_values` calls, and only 17 of them have distinct inputs.
  - Each gWCS call costs about 0.36 ms, whatever the number of points.
  - One tick placement is 33 of those calls. Every draw places the ticks again, and glue's `_set_wcs` adds 4 more placements per slice step through `set_xlabel`/`set_ylabel`.
- **Three prototypes.** All three draw identical output on the IRIS cases and pass astropy's WCSAxes tests. Every runnable figure PNG stayed byte-identical (59 or 60 of 60; the 60th needs LaTeX).
  - A per-placement memo: SJI draw -25%. Confirmed, and also run on astropy main.
  - Batching the frame calls: SJI draw -50%. Not confirmed, because it changes behaviour for WCSes that raise or return NaN. Two of the three changes have a verified fix.
  - A placement cache across draws: SJI redraw with nothing changed -60%. Confirmed, with known limits on how it detects a changed WCS. It does nothing for pans, zooms or new slices.
- **Recommendation.** Propose the memo PR first, then batching. Decide on the cache only after both are in. glue's R1 fix is independent of all three and should go first in glue-core: it removes the 4 eager placements per slice step whatever astropy does.
- **"Tricky" applies mainly to the cache.** The memo touches only core.py and leaves the tick algorithm alone. Batching changes only how `_update_ticks` calls the WCS, not its arithmetic. Both kept every figure byte-identical. The cache is the hard one, because it has to know when a WCS has changed, which is the design astrofrog argued against on #16362.

### How tick placement works

This is what someone changing placement needs to know. The full walkthrough, with more detail and measurements, is `walkthrough.md` in the archive.

**Objects.**
- **WCSAxes** (core.py:51) is an ordinary Axes.
  - It hides matplotlib's own spines and x/y axes (195-202).
  - `transData` stays the affine data-to-display transform, and data coordinates are image pixels. World coordinates never enter `transData`.
  - It draws its decorations from `_WCSAxesArtist` (32-48), a dummy artist that calls `draw_wcsaxes` inside matplotlib's z-order pass.
- **CoordinatesMap.** `ax.coords` is one (coordinates_map.py:11), and `ax._all_coords` holds it plus any overlays (core.py:528, 794).
  - Each map owns a frame (coordinates_map.py:57) and a transform.
  - It holds one `CoordinateHelper` per world axis of the **unsliced** WCS (65-102).
  - A world axis the slice drops gets `coord_index=None` (84-87). It never gets ticks, a grid or a mouse-over value.
- **CoordinateHelper** (coordinate_helpers.py:49) owns:
  - a formatter_locator (411-426);
  - one `Ticks` Line2D (117);
  - one `TickLabels` Text (120-124);
  - one `AxisLabels` Text (129-133).

  The Text artists are moved and drawn once per label.
- **Frames** are OrderedDicts of `Spine`s.
  - Shapes: rectangular `brtl`, with auto order `bltr` (frame.py:378-395); 1-D `bt` with `SpineXAligned` (326-375); elliptical `chv` (398-462).
  - Setting `Spine.data` (pixel coordinates) transforms it to world at once and stores the inward normal in display space (57-65, 104-109).
  - `add_tickable_gridline` (coordinate_helpers.py:1341-1455) adds spines whose `data_func` `update_spines` re-runs (frame.py:279-282).

**Transforms and slices.**
- `reset_wcs` (core.py:455-554) builds the coordinate metadata (type, wrap, unit, format unit, names) from the WCS physical types through `transform_coord_meta_from_wcs` (wcsapi.py:135-293).
  - Helioprojective longitude wraps at 180° and formats in arcsec.
  - It makes no WCS calls: 0.40 ms on SJI.
  - It rebuilds the CoordinatesMap, which loses every `set_ticks`, `set_major_formatter`, `set_ticklabel` and `grid` customization and drops overlays. It keeps the frame's Path object, so clipped artists stay valid (496-526).
- `apply_slices` (wcsapi.py:296-329) returns a `SlicedLowLevelWCS`. The slice index is frozen into the transform, so every slice step needs a new `reset_wcs`.
- **`WCSPixel2WorldTransform`** (wcsapi.py:419-491) is a non-affine matplotlib Transform.
  - `.transform(N×2)` (460-485) is one `pixel_to_world_values` call that returns every kept world axis. Callers keep one column, `[:, coord_index]`.
  - The inverse (340-416) accepts exactly two world inputs (387-388).
- Overlays compose that transform with a `CoordinateTransform`, which runs `SkyCoord.transform_to` on every call (transforms.py:118-154).
- Nothing on this path is memoized.

**One draw.**
1. `WCSAxes.draw` (core.py:628-667) runs `apply_aspect`.
2. It then runs `frame._update_patch_path()` (663), which calls `update_spines`. That is 4 two-point WCS calls whose world values nothing reads.
3. `Axes.draw` reaches `draw_wcsaxes` (585-626). It returns at once when the axes is off (586; that is S14). Otherwise it does three things.
   1. **Places the ticks:** `_update_tick_and_label_positions(keep_coord_range=True)` (556-583). For each map:
      - `coords.frame.update()` (571), which is `OrderedDict.update()` with no arguments, a no-op since 2016;
      - `_coord_range` from `find_coordinate_range` (coordinate_range.py:23-147), one call on a 51×51 grid over the view;
      - `_update_ticks()` for every coordinate;
      - then `auto_assign_coord_positions` once.
   2. **Draws the grid:** `_draw_grid` for every coordinate (only after `grid()`), then `del coords._coord_range` "to protect from accidental use of a stale range".
   3. **Draws the decorations:** `_draw_ticks` per coordinate, which collects tick-label bboxes, then `_draw_axislabels`, then the frame.
4. `_drawn = True` turns on `format_coord`.

**`_update_ticks`** (coordinate_helpers.py:984-1139; 8.0.1: 966). A `# TODO: this method should be optimized for speed` comment sits at 988.
1. **Skip.** It returns when `coord_index is None`.
2. **Values.** It calls `self.locator(*range)`, which returns tick values and a spacing. The spacing is stored in `_fl_spacing`, and `format_coord` takes its precision from it.
3. **Frame sampling.** It calls `frame.sample(1000)` (1013). That runs `update_spines()` (4 two-point calls), then builds new spines resampled to 1000 points, one WCS call per spine.
4. **Tick angles, per spine.**
   - Spines that are empty or all-NaN for this coordinate are skipped (1026-1037).
   - The spine is moved to display space with `transData`, shifted +2 px in x, mapped back with `transData.inverted()` (1024) and evaluated again. The same is done with ±2 px in y, the sign taken from `frame.origin` (`shifted_pixel_to_world`, 1041-1067). Where a shift lands on NaN, the other direction is tried.
   - That is 2 calls per spine per coordinate, or 4 with the NaN fallback. The result depends on axes size and DPI.
   - The display-space gradient rotated by 90° gives the gridline direction (1070-1082). It is flipped when it points away from the inward normal (1084-1091).
5. **Crossings.** `_compute_ticks` (1141-1241) finds every segment where the coordinate crosses a tick value. Longitudes also test t+360. Position and angle are interpolated linearly. One value can give several ticks on one spine, and ticks are found on **every** spine, visible or not.
6. **Labels.** All of a coordinate's labels are formatted in one call (1136-1139).

The second coordinate repeats the first's sample and shift inputs exactly. With n visible coordinates, one draw therefore makes **5 + 16n** calls: 1 range call, then for each coordinate 4 corner, 4 sampled and 8 shifted calls, then 4 patch-path calls. That is 37 calls for SJI and TAN (n=2) and 53 for the Si IV spectrogram (n=3), each with 17 distinct inputs.

**Automatic spine assignment** (_auto.py:8-139).
- Every visible coordinate starts with '#' (automatic) positions. With exactly two visible coordinates, both also get ticks on all four spines (core.py:537-551, wcsapi.py:254-267).
- The remaining '#' coordinates try every permutation of the free spines in `bltr` order. Each option is scored by the number of ticks it would show, which is why ticks are needed on every spine first.
- The winner is written back as `[spine, '#']`.
- On main, a coordinate with both ticks and tick labels hidden is left out (57-65, #20499). It still runs `_update_ticks`.

**Drawing.**
- **Ticks:** one `draw_markers` per tick on each visible spine (ticks.py:174-249).
- **Tick labels:**
  - `_set_xy_alignments` (ticklabels.py:222-309) runs on every draw. It simplifies sexagesimal labels, measures each label and anchors it.
  - The draw (349-376) measures each label again (257 and 332). With `exclude_overlapping`, which defaults to False (51), it skips labels that overlap earlier ones.
- **Axis labels** (axislabels.py:61-151) sit outside the union of **all** coordinates' tick-label bboxes. They are shown only on spines where that coordinate drew tick labels.
- **`get_tightbbox`** (core.py:913-926) runs a whole `draw_wcsaxes`.
- **Grid:**
  - 'lines' (coordinate_helpers.py:1281-1339) makes one inverse call and one round-trip call, and clips each path to `frame.patch`. That patch runs `update_spines` again (931-936).
  - 'contours' (1467-1525) makes a 200×200 forward call and runs `ax.contour` on every draw.

**Eager `set_xlabel`/`set_ylabel`** (core.py:670-732; eager calls at 685 and 715; 8.0.1: 598, 615).
- **What.** Each call runs a full `_update_tick_and_label_positions()`, then gives the text to the first coordinate whose axis-label positions contain 'b' (or 'l').
- **Also eager:** `get_xlabel`, `get_ylabel` (735, 744) and `tick_params(axis='x'|'y')` (1046).
- **Why.** With '#' positions, the coordinate on b is known only after auto-assignment, and that needs every spine's tick count. Before the first draw no coordinate has 'b', so without the placement the label would be lost.
- **Origin.** The eager call came with automatic placement (#17243, astropy 7.0), in commit 46a541d624, "Fixed non-image tests".
- **Cost.** The ticks it computes are thrown away and the next draw recomputes them.

**What survives between draws:** nothing on the placement path.
- `_coord_range` is deleted on purpose.
- `sample` builds new spines every time.
- The `TickLabels._stale` flag only saves work within one draw.
- The transforms have no memo.

**Invariants a change must keep.**
1. Ticks are computed on every spine, because auto-assignment scores spines by tick count. The default 2-D view has ticks on all four spines and labels on b and l.
2. Rotated, curved and wrapping grids keep working: several crossings per spine, the t+360 test, `coord_wrap`, and `_coord_scale_to_deg` for arcsec longitudes (IRIS).
3. NaN handling stays: all-NaN spines are skipped, a NaN shift goes the other way, and a NaN segment gives no tick (off-limb and off-footprint views).
4. Hidden coordinates stay hidden. A coordinate with `coord_index None` gets no ticks, grid, range entry or mouse-over value. A hidden-but-present coordinate still sets `_fl_spacing`.
5. Overlays keep their own frame and transform, at fixed 't' and 'r' (core.py:802-806).
6. 1-D frames, elliptical frames and `data_func` spines keep working.
7. Label simplification and overlap exclusion depend on the order along the spine and on the coordinate draw order. Axis labels need every coordinate's tick-label bboxes.
8. Grid lines and ticks share the locator values, and `format_coord` needs `_fl_spacing`.
9. The frame's Path object keeps its identity across `reset_wcs`.
10. `set_xlabel` attaches to the coordinate that ends up on b or l, even before the first draw.

### Where the time goes on IRIS WCSes

**Setup** (`measure/measure.py`).
- **Axes.** Plain matplotlib on an Agg canvas, with the axes from glue's own `init_mpl(wcs=True)`: glue's margins, 8 pt tick labels and 10 pt axis labels.
- **WCS.** `ax.reset_wcs(slices=<glue's wcsaxes_slice>, wcs=data.coords)`, the call glue's `_set_wcs` makes.
- **Image.** `imshow(nearest)` stands in for glue's FRB artist. Use the WCSAxes milliseconds, not the image or total draw times.
- **Sampling.** DPR1, medians of 30 redraws after 3 warm-ups.
- **Agreement with the app.** The call counts match the in-app survey exactly (37/53/59). SJI WCSAxes takes 22.3 ms here against 24.5 ms in the app.

**Cases.**

| Case | WCS | Slice | Shown coordinates |
|---|---|---|---|
| SJI 1400 (4000255147) | gWCS, 400x417x388 | t = 200 | lon, lat |
| SJI 2796 deconvolved (4000005156) | gWCS, 32x771x1506 | | lon, lat |
| Si IV spectrogram (4000255147) | -TAB FITS, 1600x417x262 | exposure 800 | λ, lat, lon |
| Si IV λ-time | -TAB FITS | slit 208 | λ, lat, lon |
| Plain 2-D map | HPLN/HPLT-TAN, 1024², 0.6"/px | | lon, lat |

**Static redraw at 400x330 (ms, medians).** "p2w ms" is the time spent in `pixel_to_world_values`, with the share spent on repeated inputs in brackets.

| Case | Draw | WCSAxes (share) | Placement | p2w calls (distinct) | p2w ms (repeats) | TickLabels.draw | AxisLabels.draw | Patch path |
|---|---|---|---|---|---|---|---|---|
| SJI 1400 | 26.6 | 22.3 (84%) | 15.9 | 37 (17) | 15.4 (8.0) | 2.0 | 2.2 | 1.63 |
| SJI 2796 | 50.6 | 27.6 (55%) | 18.3 | 37 (17) | 17.2 (8.7) | 4.1 | 2.4 | 1.84 |
| Si IV spectrogram | 21.7 | 18.4 (85%) | 7.9 | 53 (17) | 5.3 (3.4) | 6.7 | 2.8 | 0.41 |
| Si IV λ-time | 37.2 | 29.1 (78%) | 10.0 | 59 (20) | 6.3 (3.9) | **14.8** | 3.0 | 0.43 |
| TAN map | 20.6 | 7.0 (34%) | 3.2 | 37 (17) | 1.3 (0.6) | 2.3 | 0.9 | 0.08 |

- **Panel size.** WCSAxes does not depend on panel size: at 1258x810 SJI takes 23.8 ms and the Si IV spectrogram 20.8 ms. Only the image grows. The 1000 frame samples and the 51×51 range grid are fixed by `conf` (`__init__.py`:29-35).
- **Pans** (limits change, WCS unchanged) cost the same as static redraws.
- **World-to-pixel:** 0 calls per draw in every case.
- **Automatic assignment:** under 0.1 ms.
- **Non-WCS work in `_update_ticks`:** about 0.7-1.1 ms per coordinate.
- **Static redraws are cacheable.** Over 30 redraws the WCS inputs were byte-identical draw to draw, and so was the tick output.

**Where the 37 SJI calls come from.**

| Call site | Calls | ms |
|---|---|---|
| `shifted_pixel_to_world` | 16 | 6.8 |
| `frame.sample`, resampled spines | 8 | 3.5 |
| `frame.sample`, `update_spines` | 8 | 2.9 |
| `_update_patch_path`, `update_spines` | 4 | 1.6 |
| Coordinate range | 1 | 0.7 |

On the Si IV views the split is 24-30 shifted, 12 + 12 sample, 4 patch and 1 range. λ-time has 2 extra shifted calls per coordinate from the NaN fallback.

**Cost per call (ms, medians; `measure/` Table 3).**

| WCS | 1 pt | 1000 pts | 5000 pts | Fixed per call | Per 1000 pts |
|---|---|---|---|---|---|
| SJI 1400 gWCS, WCSAxes transform | 0.361 | 0.427 | 0.684 | 0.360 | 0.065 |
| SJI 1400, inner gwcs | 0.289 | 0.360 | 0.691 | 0.288 | 0.076 |
| Si IV -TAB, WCSAxes transform | 0.067-0.071 | 0.091-0.093 | 0.23-0.26 | 0.061-0.067 | 0.031-0.036 |
| Si IV, inner astropy WCS | 0.019-0.023 | 0.036-0.044 | 0.11-0.12 | 0.019-0.020 | 0.019 |
| TAN map | 0.005 | 0.047 | 0.25-0.28 | 0.003-0.004 | 0.049-0.057 |

- **gWCS is bound by the number of calls:** a 1000-point call costs 1.2 times a 1-point call. The plain TAN map is bound by points.
- **glue-solar's wrapper.** `_GlueWCS` adds about 0.05 ms per call (S7).
- **World-to-pixel.** gWCS world-to-pixel costs 2.1-2.2 ms per call, but it is not on the draw path.

**WCS time for one static draw's inputs (`measure/batch.py`; results identical in every row).** This table shows why batching beats de-duplicating.

| Case | As WCSAxes calls it | Distinct inputs only | One call on all distinct inputs |
|---|---|---|---|
| SJI 1400 | 37 calls, 26,625 pts, 14.2 ms | 17 calls, 14,609 pts, 6.6 ms | 1.22 ms |
| SJI 2796 | 14.3 ms | 6.7 ms | 1.25 ms |
| Si IV spectrogram | 53 calls, 4.07 ms | 1.34 ms | 0.36 ms |
| Si IV λ-time | 59 calls, 5.49 ms | 1.76 ms | 0.54 ms |
| TAN map | 1.05 ms | 0.57 ms | 0.50 ms |

**Eager labels on a glue slice step (ms).** The set phase is `reset_wcs` followed by glue's 4 label sets (x and y to '' and back).

| Case | Set phase | reset_wcs | WCS calls (distinct) | Same step with `coord.set_axislabel` | One `set_xlabel` (calls) |
|---|---|---|---|---|---|
| SJI 1400 | 66.6 | 0.58 | 132 (17) | 0.40 | 16.1 (33) |
| SJI 2796 | 65.8 | 0.55 | 132 (17) | 0.40 | 16.1 (33) |
| Si IV spectrogram | 32.1 | 0.73 | 196 (17) | 0.61 | 7.9 (49) |
| Si IV λ-time | 38.6 | 0.71 | 220 (20) | 0.56 | 10.2 (55) |
| TAN map | | | | | 3.0 (33) |

**Hot spots, largest first.**
1. **Eager placement in `set_xlabel`/`set_ylabel`** (R1): 66 ms of SJI work per slice step, with only 17 distinct inputs among 132 calls. These placements also run with the axes off (S14).
2. **One WCS call per coordinate per frame sample and per shift** (R5): on SJI, WCS evaluation is 15.4 of 26.6 ms, and 8.0 ms of that repeats inputs already seen in the same draw.
3. **No reuse across draws** (R5, R18): a redraw with nothing changed pays the full placement, 15.9 ms on SJI.
4. **Tick labels on the λ-time view.**
   - TickLabels.draw takes 14.8 ms, 40% of the draw.
   - Latitude wobbles with time in sit-and-stare data, so it gets 48 labels. All 24 on the left spine are drawn on top of each other (see `measure/lt_400x330.png`).
   - The wavelength labels are 12-character strings in metres and cost 4.3 ms.
   - This is a display problem, not an algorithm one; see the open questions.
5. **The frame is updated 1 + n times per draw**: in `_update_patch_path` and once per coordinate in `sample()`. Those are 4 + 4n calls on the same four 2-point inputs, 1.6 + 2.9 ms on SJI.

### Prototypes

All three are runtime monkeypatches against installed astropy 8.0.1. Each skeptic used its own harness. Their baselines differ by up to 1 ms, so compare the gains within a row more than across rows.

| | Per-placement memo | Batched calls | Placement cache |
|---|---|---|---|
| Scope | One placement | One placement | Across draws |
| Files touched upstream | core.py | core.py, frame.py, coordinate_helpers.py | core.py |
| WCS calls per SJI draw | 37 -> 21 | 37 -> 3 | 37 -> 5 on a hit, 37 + 1 on a miss |
| SJI static draw (skeptic, ms) | 25.7 -> 19.3 (-25%) | 26.3 -> 13.2 (-50%) | 26.6 -> 10.7 (-60%) |
| Pans, zooms, new slices | same gain as static | gain on every draw (not timed separately) | no gain, +0.4-0.5 ms per miss |
| SJI glue slice step (skeptic, ms) | 90.2 -> 58.6 (-35%) | 91.0 -> 28.9 (-68%) | 92.4 -> 30.7 (-67%) |
| Si IV spectrogram static draw | 21.7 -> 19.0 | 22.1 -> 16.6 | 21.5 -> 12.9 |
| TAN map static draw | 22.8 -> 22.6 (noise) | gain about 0.7 ms, interleaved only | 22.0 -> 20.0 |
| Output | identical | identical on IRIS; 3 differences on failing WCSes | identical, except the known probe and formatter limits |
| Skeptic verdict | confirmed; also run on main | not confirmed | confirmed |

#### Prototype 1: per-placement memo of `pixel_to_world_values`

**Files.** `minimal/memo_patch.py` (59 lines; importing it installs it). The upstream form is `minimal/upstream_core.diff`, against main core.py, +55/-16.

**What it changes.** While a placement runs, `coords._transform.transform` returns a copy of an earlier result when it sees byte-identical input.
- **Lifetime.** It is the same lifetime `_coord_range` already has: from `_update_tick_and_label_positions` to the `del` after the grid in `draw_wcsaxes` (main core.py:556-604).
- **Mechanism.**
  - A context manager puts an instance attribute `transform` on the transform object, which shadows the method. It deletes the attribute in a `finally`.
  - The key is `(shape, dtype.str, tobytes())`, and every caller gets its own copy (`copy(order="K")`).
  - Re-entry is a no-op, so the draw and the eager label paths nest safely.
- **What it covers.** Every caller goes through `self.transform.transform`: the `Spine.data` setter, `shifted_pixel_to_world`, `find_coordinate_range` and the grid. So it covers the overlay composite too.
- **What it leaves.** The 4 `_update_patch_path` calls in `WCSAxes.draw` sit outside the scope. That is why a draw goes to 21 calls, not 17.

**Measured gain.** Prototype numbers, separate processes:
- **Static draw:** SJI 1400 27.4 -> 21.2 ms (-23%), SJI 2796 48.7 -> 41.9, Si IV spectrogram 22.3 -> 19.2, λ-time 39.5 -> 35.5, TAN 23.4 -> 22.9.
- **Glue slice step:** SJI 94.1 -> 60.5 ms (-36%), with 132 -> 68 calls in the set phase. Si IV spectrogram 55.3 -> 39.5, λ-time 77.5 -> 59.0.
- **One `set_xlabel`:** SJI 16.7 -> 9.7 ms (33 -> 17 calls), Si IV 7.9 -> 4.8 ms (49 -> 17).
- **astropy's own benchmark headers** (in-process A/B, `minimal/msx_ab.py`):
  - basic plot 7.62 -> 7.49 ms and with grid 9.85 -> 9.85, both neutral;
  - **grid with fk5 overlay 37.4 -> 27.5 ms (-26%)**, the only existing asv benchmark that moves.
- **Bookkeeping cost:** 0.4-11 µs per call, about 0.13 ms per placement. That is why cheap 2-D FITS WCSes come out neutral.

**Skeptic** (`skeptic_minimal/`). Confirmed.
- **Timing.** In-process ABBA toggling: SJI 25.65 -> 19.34 ms (-25%), SJI 2796 -13%, Si IV spectrogram -13%, λ-time -8%, TAN -1%. The slice step went SJI 90.2 -> 58.6 ms.
- **Through glue's Qt ImageViewer** (offscreen, `skeptic_minimal/glue_viewer.py`): SJI static draw 24.71 -> 18.29 ms, slice step 88.41 -> 56.70 ms.

**Identity.**
- **Prototype check.** It compared 7 cases bit for bit after every step: the IRIS cases, TAN, a rotated RA/Dec near the pole with a galactic overlay and grid, and an all-sky Aitoff ellipse.
  - Fields compared: the RGBA hash; every tick, tick-label and axis-label field; `_fl_spacing`; `format_coord`; a tight savefig.
  - Steps: pan, zoom in and out, off-footprint, slice change, resize.
  - Every step was identical.
- **Skeptic check** (`skeptic_minimal/edge.py`). 27 scenarios × 12 steps, with 0 of 324 steps different. It covered:
  - custom spacing and values, minor ticks, hidden coordinates, all-auto positions;
  - three kinds of overlay, colorbars, tiny and zero-size axes;
  - NaN-outside and raising WCSes, custom transforms;
  - 1-D, swapped and sliced 3-D cubes;
  - `plot_coord`, and the IRIS data.

**astropy tests.**
- Plain run: 237 passed, 63 skipped, 1 xfailed, the same as stock.
- With the figure tests forced to run through the prototype's plugin (pytest-mpl is not installed): 296 passed, and 1 failed in both modes (`test_latex_labels`, no LaTeX installed).
- 59 of 59 PNGs were byte-identical. These are macOS hashes, not astropy's Linux baselines.

**On astropy main.** The skeptic loaded main's wcsaxes tree from `git archive` over the installed astropy (`skeptic_minimal/shadow_plugin.py`). Nothing in ~/Git/astropy was touched.
- `upstream_core.diff` applies cleanly.
- Calls on a TAN draw: 37 -> 21. Calls in `set_xlabel`: 33 -> 17.
- main's tests: 319 passed and 1 failed (LaTeX), the same with and without the diff.
- Figures: 59 of 59 identical.
- Edge harness: 0 of 324 steps differ. The same harness finds 34 steps where 8.0.1 and main differ, so it does catch real changes.

**Risks and notes.**
- **Review style.** Shadowing a method with an instance attribute is unusual. The alternatives:
  - an explicit `_cache` checked inside `WCSPixel2WorldTransform.transform` and `CoordinateTransform.transform`. This loses most of the overlay gain, because the composite calls `transform_non_affine`;
  - a proxy transform swapped into `coords._transform`, `frame.transform` and each helper. That is more invasive.
- **Purity.** It assumes the transform is a pure function of its input during one placement. Code that counts WCS calls sees fewer.
- **Warnings.** A warning the WCS raises is reported fewer times under the `'always'` filter: 37 -> 21 per draw. Under the default filter it is 2 in both.
- **Sketch mismatch.** The diff's wrapper calls `uncached(np.asarray(values))`, which would strip a mask or a Quantity. The monkeypatch passes `values` unchanged (memo_patch.py:35). No WCSAxes caller passes either today, but change the diff to match before proposing it.
- **Remaining SJI WCS time.** It keeps the 17 distinct calls separate: SJI WCS time 15.4 -> 9.4 ms, against about 1.2 ms batched.

#### Prototype 2: batch the WCS calls of one placement and share them between coordinates

**Files.** `batch/wcsaxes_batch.py` (265 lines, `install()`/`uninstall()`). Pytest plugin `batch/wcsaxes_batch_plugin.py`. Skeptic's fixes in `skeptic_batch/batch_fix.py` (40 lines, layered on the module).

**What it changes.**
1. **Lazy `Spine.world`** (wcsaxes_batch.py:40-52, replacing the setter at main frame.py:57-65). World values are computed on first read. Nothing in wcsaxes reads the world values of the frame's own spines, so `update_spines` no longer calls the WCS. That removes the 4 patch-path calls, the 4 per coordinate in `sample`, and the 4 per coordinate in the grid's `frame.patch`.
2. **One call for all resampled spines.** `BaseFrame.sample` (wcsaxes_batch.py:55-78; main frame.py:232) transforms them together. Spine classes that set world eagerly (`SpineXAligned`, 1-D) keep their own behaviour.
3. **One cache per placement.** `_update_tick_and_label_positions` is wrapped (81-88) to give each CoordinatesMap a `_tick_cache` for one call only, which is astrofrog's per-draw pattern from #16362.
   - The copied `_update_ticks` (120-233) takes the sampled frame from the cache.
   - Its `shifted_pixel_to_world` reads `_shifted_world` (91-117). That computes both ±2 px shifts for every spine in one call, and the NaN-fallback direction in one more call, only when a coordinate needs it.
   - The cache key includes `id(transform)`.
- **Result.** A draw makes 3 calls: range, sample and shifts. It makes 4 when the NaN fallback is needed. Folding the 51×51 range grid into the same call would make it 2 and save about 0.7 ms more on gWCS; this was not done.
- **Guard.** The three copied functions are checked by source hash at import. They are byte-identical on 8.0.1 and main, so the change carries over directly.

**Measured gain** (prototype, interleaved in one process; skeptic's separate-process numbers in brackets):

| Case | Static draw 400x330 | Static draw 1258x810 | Slice step, set phase | Slice step + draw | WCS calls per draw |
|---|---|---|---|---|---|
| SJI 1400 | 28.1 -> 13.9 [26.3 -> 13.2] | 35.2 -> 20.8 [34.9 -> 21.5] | 65.5 -> 17.1 [65.4 -> 16.8] | 93.4 -> 31.0 [91.0 -> 28.9] | 37 -> 3 |
| SJI 2796 | 48.9 -> 34.4 [44.0 -> 29.5] | 58.6 -> 44.1 | 71.3 -> 20.9 | 119.7 -> 55.3 [111.5 -> 48.2] | 37 -> 3 |
| Si IV spectrogram | 23.0 -> 17.3 [22.1 -> 16.6] | 35.4 -> 30.5 | 31.6 -> 13.0 | 54.4 -> 30.9 [53.0 -> 29.2] | 53 -> 3 |
| Si IV λ-time | 39.4 -> 33.2 [37.2 -> 31.5] | 51.9 -> 46.2 | 40.5 -> 19.8 | 76.9 -> 50.4 [73.5 -> 47.6] | 59 -> 4 |
| TAN map | 21.8 -> 20.8 [lost in noise] | 29.8 -> 28.7 | | | 37 -> 3 |

- **One `set_xlabel`:** SJI 16.5 -> 3.8 ms (33 -> 3 calls), Si IV spectrogram 7.7 -> 2.9, λ-time 9.7 -> 4.5, TAN 2.9 -> 2.1.
- **Stage split** (`batch/measure_patched/`, SJI):
  - placement 15.9 -> 4.3 ms;
  - WCS time 15.4 ms in 37 calls -> 2.6 ms in 3 calls (range 0.82, sample 0.72, shifts 1.02);
  - `frame.sample` 6.7 -> 0.9 ms, and `_update_patch_path` 1.63 -> 0.04 ms.
- **Largest piece left.** On the Si IV spectrogram, TickLabels.draw (7.1 ms) is now the largest piece.
- **R5's estimate holds.** R5 estimated 12-13 ms saved per SJI placement; measured, it is 11.6 ms.

**Identity** (`batch/compare.py`).
- **What it compares.** It builds stock and patched figures in one process and compares exact sha1 fingerprints after every draw:
  - every tick and tick-label field, major and minor;
  - the resolved positions, axis labels and `_fl_spacing`;
  - `format_coord`;
  - the Agg RGBA buffer.
- **Steps (13-15 per case).** Pan, zoom, zoom past the footprint, flip y (the negative shift branch), 16 glue slice steps, resize, minor ticks, grid (lines, or contours on Si IV) and `set_xlabel`.
- **Cases (9).** The 5 IRIS and TAN cases, plus:
  - a rotated RA/Dec wrapping through 0 with a galactic overlay;
  - an all-sky AIT ellipse with an fk5 overlay;
  - AIT in a rectangular frame running off the sky (NaN spines and the NaN fallback);
  - a 1-D frame.
- **Result.** Identical at every step.
- **Negative control** (`batch/negctl.py`). Scaling the batched shifts by (1 + 1e-12) broke 11 of 12 steps.

**astropy tests.**
- Plain run: 237 passed, 63 skipped, 1 xfailed, the same as stock.
- With figure tests run through the plugin: 297 passed in both modes. All 60 figure tests ran, and 60 of 60 PNGs were byte-identical.
- The skeptic re-ran the plain suite under astropy's CI warning rules (`filterwarnings=error`, `xfail_strict`; `skeptic_batch/pytest_cfg/pytest.ini`) with the same result. Its figures were also identical, 60 of 60.

**Skeptic** (`skeptic_batch/`). Not confirmed: the gain holds, but output changes were found.
- **Where nothing changed.** 191 edge steps were identical (`skeptic_batch/identity.py`). They covered:
  - spacing and number;
  - `exclude_overlapping`;
  - hidden coordinates;
  - top and right spines;
  - inversions;
  - zoom and sub-pixel zoom;
  - dpi 37 and 250;
  - colorbars, tight bbox, tiny and zero-size axes;
  - axis off;
  - a heliographic overlay.
- **Output changes**, all on failing-WCS or zero-size cases (`skeptic_batch/fp_synthetic_*.json`):
  1. **A WCS whose `pixel_to_world_values` always raises.** Stock raises when the axes is created, through `self.patch = self.coords.frame.patch` (main core.py:155) -> `update_spines` -> the `Spine.data` setter. The patched axes is created without error, and every draw raises from `find_coordinate_range` instead. The cause is the lazy `Spine.world`. **Not fixed.**
  2. **Zero-size axes with an all-NaN WCS.** Stock raises `LinAlgError: Singular matrix` from `transData.inverted()` (main coordinate_helpers.py:1024), which runs on every call. The copy dropped that line, so the patched version draws. **Fixed in `batch_fix.py`** by keeping the inversion at the top of `_update_ticks`.
  3. **A WCS that raises outside its domain** (NaN above the top edge, raises for x < -1). Stock draws 14 ticks. The patched version raises, because the batched calls evaluate points stock never touches: fallback shifts for every spine, and shifts around all-NaN spines. **Fixed in `batch_fix.py`** by falling back to one call per request when a batched call raises. In the normal case the call count stays at 3.
- **Notes.**
  - The TAN gain shows only interleaved (about 0.7 ms).
  - The prototype's own TAN table (21.8 -> 20.8) disagrees with its `batch/out_tan.json` (23.3 -> 22.4).

**Risks.**
- **Pointwise transforms.** Batching assumes output row i depends only on input row i. That holds for wcslib including -TAB, gWCS, `SlicedLowLevelWCS` and SkyCoord overlays. Stock already calls with 2, 1000 and 2601 points, so a non-pointwise user transform is already inconsistent there.
- **One platform.** Bitwise identity was checked on macOS arm64 only. On x86 Linux, SIMD loops could differ by one ulp between batch lengths, and the figure tests (tolerance 0) would show it.
- **Lazy `Spine.world` is a public behaviour change.** `Spine` is a public class, and an exception now appears at first read rather than when the data is set (change 1). There are three options:
  - (i) document it;
  - (ii) keep the eager setter and accept 8 more calls per draw: 4 in `sample`, which runs once per placement because the sample is shared, and the 4 patch-path calls. That is about 2.9 ms on SJI (estimated: 8 × 0.36 ms). The memo PR does not help here, because the two sets of 4 fall in different scopes;
  - (iii) keep it lazy but read `.world` once in `WCSAxes.__init__`, so creation still raises. This is untested.
- **The NaN fallback is computed for every spine** once any coordinate needs it: about 8,000 extra points, about 0.25 ms on -TAB.
- **Stale shifts.** If a formatter or locator callback changed limits, size or DPI in the middle of a placement, the shared shifts would be stale. This is unlikely.
- **1-D frames gain nothing:** 7 calls stay 7.

#### Prototype 3: placement cache across draws, with optional lazy labels

**Files.** `cache/wcsaxes_cache.py` (214 lines; `install(lazy=False|True)`, `uninstall()`, and a `STATS` hit/miss counter). Pytest plugin `cache/wcsaxes_patch_plugin.py` with `cache/pytest.ini`.

**What it changes.**
- **(b) The cache.** It replaces `_update_tick_and_label_positions` (main core.py:556-583).
  - Each CoordinatesMap keeps its last placement while the key matches: the coordinate range plus everything `_update_ticks` writes (`_fl_spacing`, the Ticks and TickLabels dicts, `_lblinfo`, `_lbl_world`).
  - On a hit it restores fresh copies and marks the TickLabels stale. `auto_assign_coord_positions` still runs every time (0.05 ms), so position, visibility and overlay changes behave exactly as before.
  - `reset_wcs` builds a new CoordinatesMap, so a new WCS or slice always starts empty.
- **The key** (`_key`, 60-91). Plain values are compared by pickle bytes, objects by identity.
  - The map and frame: the transform's identity, the frame class and the spine names.
  - The view: xlim and ylim, the scale names, and the full `transData` matrix (size, DPI, limits).
  - `conf.frame_boundary_samples`, `conf.coordinate_range_samples`, and rcParams `text.usetex` and `axes.unicode_minus`.
  - Per coordinate:
    - `coord_index`, type, unit, wrap and `_coord_scale_to_deg`;
    - the formatter_locator's identity and the pickle of its `vars()`;
    - the custom formatter's identity;
    - the minor-tick settings.
  - **A probe of the WCS:** the transform's output on a 3×3 grid over the view, one extra call per placement. This catches in-place WCS edits, such as a crval change, but only if one of the 9 points moves. The `ponytail: probe, not a WCS hash` comment at line 65 marks this limit.
  - If the key cannot be built, the placement runs uncached.
- **(a) Lazy labels** (`install(lazy=True)`).
  - `set_xlabel`/`set_ylabel` append to a queue. The next placement replays it in order after auto-assignment.
  - The queue is also replayed before 12 CoordinateHelper methods that could change or read the label's coordinate, and before `get_coords_overlay`.
  - `reset_wcs` drops the queue.

**Measured gain** (base / cache / lazy, ms, 400x330; `cache/out/tables.md`):

| Case | Static draw | Slice step total | WCS calls per draw |
|---|---|---|---|
| SJI 1400 | 28.1 / 11.9 / 11.5 | 95.6 / 31.7 / 29.2 | 37 -> 5 |
| SJI 2796 | 48.2 / 30.8 / 30.9 | 115.4 / 52.0 / 50.7 | 37 -> 5 |
| Si IV spectrogram | 22.5 / 15.1 / 14.6 | 56.2 / 25.7 / 23.9 | 53 -> 5 |
| Si IV λ-time | 38.3 / 28.8 / 28.8 | 75.2 / 38.1 / 37.6 | 59 -> 5 |
| TAN map | 22.0 / 20.0 / 19.5 | | 37 -> 5 |

- **Calls on a hit.** The 5 calls are the probe plus the 4 patch-path calls.
- **Contrast change:** SJI 28.7 -> 12.7 ms, which matches R18's tick-reuse estimate of about -16 ms.
- **Pans** miss every time: no faster, and 0.41 ms of bookkeeping on SJI (0.35 ms of it the probe).
- **One `set_xlabel`:** SJI 16.4 -> 0.5 -> 0.0 ms.
- **Lazy adds little.** On glue's slice step, lazy saves only 0.5-5 ms beyond the cache, because the cache already turns glue's 4 label sets into 1 placement plus 3 hits. Lazy only saves a whole placement when the limits change between the label set and the draw, or when no draw follows.

**Identity** (`cache/ident.py`, `cache/compare.py`).
- **Cases.** The IRIS cases, TAN, TAN rolled 30°, an all-sky AIT with off-sky NaN and an FK5 overlay, and a 1-D frame.
- **Steps.** Static draw, contrast, pan, zoom, glue slice steps and resize. Then `set_ticks(number=8)`, a format unit, a formatter, minor ticks, toggling `unicode_minus`, grids, an in-place crval edit, tick labels moved to 't', and label-ordering cases.
- **Result.** 16 of 16 case/mode pairs were identical to base at every step.
  - The hit/miss log shows hits on static, contrast, grid, position moves and relabel.
  - It shows misses on pan, zoom, resize, set_ticks, unit, formatter, minor ticks, unicode_minus and the crval edit.
- **Negative control.** A key that never changes broke 16-20 of about 20 steps per case.

**astropy tests** (`pytest -c cache/pytest.ini`, astropy 8.0.1's own pytest settings including `filterwarnings=error`).
- Base and cache: 297 passed, 1 failed (LaTeX), 3 skipped, 1 xfailed. Lazy: 296 passed, 2 failed.
- **The lazy-only failure** is `test_misc.py::test_set_label_properties` (8.0.1 test_misc.py:152-171). It reads private `_axislabels` right after `set_xlabel`, with no draw.
- **Figures.** All 59 runnable PNGs were identical to base, on a first save and on a second save that hits the cache.
- **Coverage warning.** With a key that never changes, the suite still passes, and only 2 of 59 figures change (`TestFrame::test_update_clip_path_*`). astropy's tests barely exercise redraws after a change.

**Skeptic** (`skeptic/`). Confirmed.
- **Plain matplotlib:**
  - SJI static draw 26.6 -> 10.7 ms;
  - slice step 92.4 -> 30.7 ms;
  - one `set_xlabel` 16.3 -> 0.49 ms;
  - Si IV spectrogram static draw 21.5 -> 12.9 ms;
  - λ-time static draw 36.0 -> 27.8 ms.
- **glue's Qt ImageViewer** (`skeptic/glue_app.py`, offscreen, no plugins): static draw 26.6 -> 10.4 ms, slice step 96.3 -> 31.0 ms.
- **Pans.** Interleaved A/B (`skeptic/pan_ab.py`, n=200) gives +0.5 ms per miss.
- **Tests.** Same as the prototype, with 171 cache hits during the suite.
- **Edge sequences.** 19 synthetic and 2 IRIS sequences were identical to base (`skeptic/edge.py`). They covered:
  - spacings, values, formats and units;
  - `set_coord_type`;
  - hidden coordinates;
  - top and right spines;
  - overlays added after the first draw;
  - colorbars, tiny and zero-size axes, NaN regions;
  - a transform that starts raising;
  - `savefig` at other DPIs and with a tight bbox;
  - constrained layout;
  - an elliptical frame;
  - inversions and a log scale.
- **Problems found.**
  - Both reported limits reproduce as stale ticks: a formatter whose output depends on a global, and a transform mutated only between the probe points.
  - **Warnings.** The probe's `catch_warnings` resets Python's once-per-location registry. A warning shown once per draw in base appears [2,0,1,3,2,0] times over six draws.
  - **Lazy mode after `ax.cla()`.** A label queued just before `cla()` is never flushed into private state. The pixels are the same.
  - **Pickling.** The prototype's pickling caveat does not matter, because a WCSAxes figure cannot be unpickled in 8.0.1 anyway.

**Risks.**
- **The cache checks the WCS by probing, which is not proof.** This is the objection astrofrog raised on #16362 ("hash(wcs) does not change even if some of the transformation parameters change"). Upstream will probably want an explicit invalidation instead of the probe.
- **Some state is outside the key:** formatter output, custom frames whose `update_spines` reads other state, mutable custom transforms, other rcParams, and non-linear scales (keyed by name only).
- **Warnings are not repeated on a hit.**
- **astropy's suite would not catch a bad key.** New invalidation tests are needed, and `cache/ident.py`'s sequence is a template.
- **Lazy labels change behaviour.**
  - The label's coordinate is chosen at the next placement, not at call time.
  - Exactness relies on a hand-kept list of 12 flushing methods.
  - A test that reads private state needs rewriting.
- **Misses are not faster**, so slider drags still need batching.

### Recommended astropy PRs, smallest first

These are for M4 and only on the user's direction. Each PR should state numbers on solar data, because astrofrog asked for exactly that on #16366.

**Step 0, in glue-core and independent of astropy: the R1 fix.** In `_set_wcs`, set the labels with `axes.coords[...].set_axislabel(...)` instead of `set_xlabel`/`set_ylabel`.
- **Gain.** The SJI set phase drops from 66 ms to 0.4 ms, with ticks and labels identical. The astropy changes can at best match it. Each step still needs one placement for its new transform: with the cache, the first label set makes it and the draw hits; with lazy labels, the draw makes it.
- **What still needs astropy.** Other WCSAxes users (sunpy, mpl-animators, scripts) still pay the eager placement. That is the astropy half below.

**PR 1: reuse `pixel_to_world_values` results within one placement (the memo).**
- **The change.** core.py only, about 30 lines of logic (`minimal/upstream_core.diff`, +55/-16), with the same scope and argument as `_coord_range` from #16366. Pass `values` through unchanged in the wrapper before opening it.
- **What reviewers will want:**
  - A non-image test that counts `pixel_to_world_values` calls on a 2-D WCS (37 -> 21 per draw, 33 -> 17 per `set_xlabel`).
  - A test that no `transform` attribute is left behind and that callers never share a result array.
  - Every figure hash unchanged on CI (the `py312-test-image-mpl380-cov` tox env; 56 `@figure_test` functions, 60 collected tests).
  - A `performance` changelog entry.
  - The `benchmark` label. `time_basic_plot_with_grid_and_overlay` moves about -23 to -26%, near asv's 1.3x threshold. The other four do not move.
  - A new asv benchmark in astropy-benchmarks with a sliced 3-D WCS or an APE-14 WCS with a fixed per-call delay, standing in for gWCS. All 5 existing wcsaxes benchmarks use 2-D FITS headers.
- **Expected objection.** The instance-attribute shadowing may be challenged ("follow local idioms"). Have the explicit-cache alternative ready, and say what it loses: the overlay gain.
- **Why first.** It is the smallest and most reviewable, it matches the maintainer's stated design, it was already run on main, and an existing benchmark moves.

**PR 2: batch the frame sample and the tick-angle shifts (prototype 2 plus `batch_fix.py`).**
- **The change.** frame.py (the `Spine.data` setter and `world` getter, `sample`), coordinate_helpers.py (`_update_ticks`, about 10 lines plus a helper) and core.py (`_update_tick_and_label_positions`). These are private methods, which #10936 allows to change.
- **Before opening:**
  - Fold in both skeptic fixes.
  - Pick an option for the lazy `Spine.world` behaviour change (see prototype 2's risks).
  - Consider evaluating shifts only for spines stock would evaluate, so the batched call never touches new points. Untested.
  - Measure it stacked on PR 1, which was not done. After PR 1 its extra gain on SJI should be roughly 19 -> 13 ms per draw. That is an estimate from separate harnesses.
- **What reviewers will want:**
  - The same call-count test (37 -> 3).
  - Tests for WCSes that raise outside their domain, all-NaN spines and zero-size axes, showing unchanged behaviour.
  - Figure hashes unchanged on Linux CI. This is the real test of the x86 ulp risk.
  - The benchmark from PR 1.
  - The bit-exact fingerprint harness (`batch/compare.py`) described in the PR as evidence.
- **Why second.** It is the biggest gain on every draw, pans and slider drags included, but it changes the code few people know (`_update_ticks`) and needs the failing-WCS fixes.

**PR 3, only after PRs 1 and 2 are in and re-measured: the placement cache across draws.**
- **How much it would still save.** Once batched, an SJI placement costs about 4.3 ms. That is what the cache would still save per unchanged redraw, against 16 ms today (estimated).
- **What it would still be for:** contrast and bias drags, and redraws of unchanged viewers.
- **What it cannot help:** glue slice steps, because every step makes a new transform.
- **The alternative.** R18's redraw caching in glue/glue-qt, which avoids the invalidation question inside astropy. It can skip WCSAxes only if the decorations are cached as their own layer above the image; R18's upper bound assumes no WCSAxes work at all.
- **If proposed:**
  - Open an issue first, asking astrofrog which invalidation he would accept, for example an explicit `invalidate` hook plus the cheap key fields, instead of the probe.
  - Bring new tests that redraw after every kind of change (`cache/ident.py`'s sequence), because the current suite passes with a cache that never invalidates.

**PR 4, optional: lazy `set_xlabel`/`set_ylabel`.**
- **Gain after PRs 1 and 2.** An eager placement costs SJI 3.8 ms batched, or 9.7 ms with the memo alone, so the gain per label call is small.
- **Cost.** It changes when a label picks its coordinate, needs a hand-kept list of 12 flushing methods, and breaks `test_set_label_properties`.
- **Ask first.** Ask astrofrog whether the eager call in 46a541d624 ("Fixed non-image tests") was only there for the tests.
- **Skip it if R1 lands in glue.**

**A drive-by for PR 1 or 2.** `coords.frame.update()` (core.py:571) is a no-op. Removing it is safe unless a custom frame defines `update()`, which would currently be called on every placement. Check sunpy's custom frames first.

**How this changes the ranked items.**
- **R5.** Both candidate fixes are now prototyped and measured: batching -11.6 ms per SJI placement (estimate was 12-13), caching -15.9 ms per unchanged SJI redraw (estimate 16).
- **R1.** The astropy alternative (lazy labels) is prototyped, and adds 0.5-5 ms beyond the cache for glue. The glue-side fix stays the first choice.
- **R18.** Tick reuse measured SJI contrast 27.4 -> 11.0 ms (skeptic).
- **S7.** After batching, `_GlueWCS`'s 0.05 ms per call matters for only 3 calls per draw instead of 37.

### Upstream context

**Earlier WCSAxes speed work (all merged).**
- [#7568](https://github.com/astropy/astropy/pull/7568) (astrofrog, 2018): all contour paths go through one transform call, which made contours 10-1000x faster (14.5 s -> 198 ms). It is the only earlier batching change.
- [#14164](https://github.com/astropy/astropy/pull/14164) (ayshih, 2022): `_update_ticks` reuses spine world values already computed and bails out on all-NaN spines. It was approved by Cadair and larrybradley and backported to 5.2 as a bugfix, after [sunpy#6652](https://github.com/sunpy/sunpy/issues/6652).
- [#16362](https://github.com/astropy/astropy/issues/16362) and [#16366](https://github.com/astropy/astropy/pull/16366) (ayshih, merged 2024-09 by astrofrog): `find_coordinate_range` now runs once per draw instead of 4 times. The gain was only about 8% (66 -> 61 ms; 483 -> 448 ms with an overlay). It introduced `_coord_range` and used the `performance` changelog type.
- [#17404](https://github.com/astropy/astropy/pull/17404) (thuiop, 2024): imshow was slow because of a `minversion(PIL)` call.
- [#17243](https://github.com/astropy/astropy/pull/17243) (astrofrog, astropy 7.0): automatic placement. Its commit 46a541d624 added the eager placement to `set_xlabel`, `set_ylabel`, `get_xlabel`, `get_ylabel` and `tick_params`. The tests that cover this are test_misc.py:155-172, 549-574 and 664-674, and test_images.py:602 and 1150.
- [#12630](https://github.com/astropy/astropy/pull/12630) (dstansby): moved tick-label pixel coordinates to draw time, because computing them earlier "is not a safe thing to do".

**Open items that match ours.**
- [glue#1587](https://github.com/glue-viz/glue/issues/1587) (astrofrog, 2018): slicing is slow because the labels and ticks are redrawn every time. This is R1/R18.
- [glue#1823](https://github.com/glue-viz/glue/issues/1823): the image viewer is slow with overplotted points.
- [sunpy#6652](https://github.com/sunpy/sunpy/issues/6652) (2022): `draw_grid` takes 0.38 s, or 1.56 s with the grid, nearly all of it in `_update_ticks`.
- [astropy#12446](https://github.com/astropy/astropy/issues/12446): contour gridlines are created during draw. QuLogic warns against changing artists inside draw, which matters for any cache of drawn artists.
- [sunpy#4971](https://github.com/sunpy/sunpy/pull/4971) (merged 2021): the WCS animator updates only when the integer index changes. This is a precedent for skipping redundant slice updates.

**What has not been tried before.** Searches found no prior work on caching ticks across draws, memoizing `pixel_to_world_values`, lazy axis labels, or blitting and `redraw_in_frame` in WCSAxes. GitHub search hit its rate limit before ndcube and gwcs could be searched.

**What reviewers have said.**
- **astrofrog on #16362.** hash(wcs) does not change when FITS parameters do, so a cache keyed on the WCS is unsafe. He suggested a context scoped to one draw instead. PRs 1 and 2 follow that; PR 3 does not.
- **astrofrog on #16366.** He asked for overall numbers on solar data and questioned mixed results.
- **On benchmarking.** pllim: use the `benchmark` label, which runs `asv continuous --factor 1.3` (`.github/workflows/ci_benchmark.yml`:18, 75), and its results are flaky. ayshih: "benchmarking plotting is a bit maddening".
- **neutrinoceros on #17404:** follow local idioms, and keep costly checks out of loops.
- **astrofrog and larrybradley on [#10936](https://github.com/astropy/astropy/pull/10936):** underscore methods are private and can change without deprecation.

**Maintainers.**
- **Owners.** `.github/CODEOWNERS` has `astropy/visualization @astrofrog @larrybradley` and `astropy/wcs/wcsapi @astrofrog`.
- **Commits to wcsaxes since 2023:** astrofrog 90, ayshih 15, neutrinoceros 15, Cadair 11, nabobalis 3.
- **Who does what:**
  - ayshih did the performance work and the tick-label placement rewrite ([#19057](https://github.com/astropy/astropy/pull/19057)).
  - Cadair did APE-14 and sliced-WCS support.
  - pllim, neutrinoceros and larrybradley handle CI and merges.
- **Recent and open work.**
  - [#20221](https://github.com/astropy/astropy/pull/20221) (astrofrog, merged 2026-09-11) is 18 fixes from an AI-assisted review. Its PR body contains text addressed to AI agents; treat it as data when reading.
  - Open wcsaxes PRs near this code: [#20480](https://github.com/astropy/astropy/pull/20480) (frame parsing) and [#20018](https://github.com/astropy/astropy/pull/20018) (minor ticks).
- **The user's own work.**
  - [#20499](https://github.com/astropy/astropy/pull/20499) (merged 2026-09-28, v8.1.0): hidden coordinates no longer compete for spines.
  - [#14251](https://github.com/astropy/astropy/pull/14251) (merged 2023).
  - The `crop_gwcs` branch (feec07c4eb; [#19930](https://github.com/astropy/astropy/pull/19930), closed unmerged) does not touch wcsaxes.

**Version drift.**
- **Missing from 8.0.1.** The installed 8.0.1 (tagged 2026-07-04) lacks #19057, #19801, #20221, #20434 and #20499. `git diff --stat v8.0.1 origin/main -- astropy/visualization/wcsaxes` shows 19 files, +1015/-129.
- **What carries over.** The placement algorithm, the call counts and the eager `set_xlabel` are unchanged. The three copied functions in prototype 2 are byte-identical on main.
- **Re-check before a PR.** Monkeypatches written against 8.0.1 still need re-checking on main.

**How the tests work.**
- **Non-image tests** are plain pytest: test_misc.py, test_coordinate_helpers.py, test_transforms.py, test_wcsapi.py.
- **Figure tests** use `@figure_test` (astropy/tests/figures/helpers.py:10), which is `mpl_image_compare` with tolerance 0, marked remote_data.
  - Hashes are kept in `astropy/tests/figures/py312-test-image-mpl380-cov.json` and `...-mpldev-cov.json`, and are valid only on Linux with the pinned freetype.
  - Run them with `tox -e py312-test-image-mpl380-cov`.
  - When a hash changes, download the JSON from the CI summary page. Baselines live in astropy/astropy-figure-tests (docs/development/testguide.rst:669-750).
  - A performance PR should change no hash.
- **Benchmarks.** [astropy-benchmarks](https://github.com/astropy/astropy-benchmarks) `benchmarks/visualization/wcsaxes.py` has 5 benchmarks, all on 2-D FITS celestial headers:
  - `time_basic_plot`;
  - `..._with_grid`;
  - `..._with_grid_and_overlay`;
  - two contour benchmarks.

### Stock astropy problems found on the way

These behave the same with and without every prototype. All were found on 8.0.1; those marked "main?" have not been re-checked on main, and #20221 may have fixed some.
- [ ] **`format_coord` on a 1-D WCSAxes** raises `ValueError('Expected 1 world coordinates, got 2')` (8.0.1 core.py:167). main's `_display_world_coords` (core.py:160-187) has the same code. No issue found.
- [ ] **Three-coordinate views (both Si IV views).**
  - `grid(draw_grid=True)` with 'lines' raises `IndexError` in `SlicedLowLevelWCS.world_to_pixel_values`.
  - `WCSWorld2PixelTransform` raises `ValueError('Expected 2 world coordinates, got 3')` (main wcsapi.py:387-388), so `plot_coord`, `scatter_coord` and line grids cannot be used there. Contour grids work.
  - Related: R8, where the sliced Si IV world-to-pixel takes 5-15 ms per point.
- [ ] **A sliced-out coordinate (SJI time, `coord_index` None).** main?
  - `set_ticklabel_position('#')` on all three coordinates makes every draw raise `TypeError: 'NoneType' object is not iterable` (8.0.1 _auto.py:116).
  - With `set_ticks_position('all')` as well, after `invert_xaxis()` every draw raises `IndexError` (8.0.1 ticklabels.py:155), even after un-inverting.
  - Reproducer: `skeptic_batch/side_auto.py`.
- [ ] **Swapped 3-D cube.** With slices `('y','x',7)`, the third coordinate's labels on top and `tick_params(labelsize=6)`, `simplify_labels` raises `IndexError`. main?
- [ ] **`add_tickable_gridline` fully outside the view** raises `IndexError` in `transform`. main?
- [ ] **Zero-width or zero-height axes** raise `LinAlgError: Singular matrix` on draw. main?
- [ ] **Pickling.** A WCSAxes figure cannot be unpickled (`TypeError: BaseFrame.__init__() missing parent_axes and transform`). main?
- [ ] **First draw against second draw.** They differ in the last bits of one axis-label y position and one label bbox. A cache across draws must reproduce the second draw.
- [ ] **Wrong second crossing (8.0.1 only, fixed on main by #20221).** `t *= _coord_scale_to_deg` mutates the loop variable (8.0.1 coordinate_helpers.py:1178). A second crossing of an arcsec longitude on one spine therefore gets a wrong value. IRIS longitudes are arcsec, so rolled IRIS views on 8.0.1 can show it.

### Open questions

1. **Stacking.** Do PRs 1 and 2 stack as expected? They were never measured together. After batching, the memo may only help overlays and grids.
2. **Linux hashes.** Does batching keep the figure hashes on Linux x86? Only CI can tell.
3. **Lazy `Spine.world`.** Which option should PR 2 take: (i), (ii) or (iii)?
4. **Range call.** Should PR 2 also fold the range call into the batch (3 -> 2 calls, about 0.7 ms on gWCS)?
5. **Patch-path calls.** Should the 4 `_update_patch_path` calls (1.6 ms on SJI) be covered? The memo would need a wider scope, around all of `Axes.draw`. Batching's lazy `Spine.world` already removes them.
6. **The cache upstream.** Is the cross-draw cache worth proposing once PRs 1 and 2 and R18's redraw caching in glue exist? If so, what invalidation would astrofrog accept?
7. **Eager labels.** Was the eager placement in `set_xlabel` (46a541d624) only for the tests? Do sunpy or mpl-animators call `set_xlabel` per frame? If not, PR 4 has little value beyond glue.
8. **λ-time tick labels** (glue-solar, unmeasured). The fix could be:
   - `set_ticklabel(exclude_overlapping=True)` on latitude;
   - hiding latitude labels when the coordinate barely changes;
   - formatting wavelength in Angstrom, as the plan already decided (arcsec + Angstrom units).

   `exclude_overlapping` still measures every label, so its gain needs measuring.
9. **Not covered.** No prototype was run at DPR2 or on a real screen. Batching was not run in glue's Qt viewer. The cache's pan cost was measured only offscreen.
10. **Reporting.** Should the stock problems above be re-checked on main and reported upstream? That is an outward action for the user to decide.

### Files

All files are in `IRIS_PLAN_PROTOTYPES/wcsaxes_study_20261001.tar.gz`. Paths are relative to the archive root, which was scratchpad `wcsaxes/`.

| Path | What |
|---|---|
| `walkthrough.md`, `measure.md`, `upstream.md` | Full understand-phase notes this section condenses |
| `explain/` | `calls.py`, `phases.py`, `grid_probe.py`, `reset_probe.py`; outputs `out_*.txt`, `phases_*.txt` |
| `measure/` | `measure.py` (harness), `out_*.json`, `log_*.txt`, `tables.py`/`tables.md`, `batch.py`/`batch.log` (batching table), `probe2.py` and logs (label counts, Si IV world-to-pixel cost), `lt_*.png`/`spec_*.png` (Si IV renders) |
| `upstream/` | Search outputs and main copies read with `git show` |
| `minimal/memo_patch.py` | **Prototype 1** monkeypatch |
| `minimal/upstream_core.diff` | Prototype 1 as a diff against main core.py |
| `minimal/` (other) | `memo_plugin.py` (pytest), `identity.py`/`compare.py`, `measure.py`/`run_all.sh`/`tables.md`, `msx_ab.py`, `bench_asv.py`, `overhead.py` |
| `skeptic_minimal/` | `ab.py`, `edge.py`/`cmp_edge.py`, `glue_viewer.py`, `warn_check.py`, `count_calls.py`, `run_pytest.sh`, `shadow_plugin.py` (main's wcsaxes over 8.0.1) |
| `batch/wcsaxes_batch.py` | **Prototype 2** monkeypatch |
| `batch/` (other) | `wcsaxes_batch_plugin.py`, `compare.py`, `negctl.py`, `measure_patched/`, `figs_0`/`figs_1` |
| `skeptic_batch/batch_fix.py` | The two failing-WCS fixes for prototype 2 |
| `skeptic_batch/` (other) | `timing.py`, `identity.py`, `fp_*.json`, `side_auto.py` (stock bugs), `pytest_cfg/pytest.ini` |
| `cache/wcsaxes_cache.py` | **Prototype 3** monkeypatch |
| `cache/` (other) | `wcsaxes_patch_plugin.py`, `pytest.ini`, `cases.py`, `ident.py`/`compare.py`, `bench.py`/`tables.py`/`overhead.py`, `py` (wrapper), `out/` |
| `skeptic/` | `bench.py`, `glue_app.py`, `pan_ab.py`, `edge.py`/`edge_compare.py`, `warn_probe.py`, `cla_probe.py`, `stats_plugin.py`, `out/` |
| `axesoff/` | S14's scripts |

The archive leaves out the rendered figure PNGs (except `measure/lt_*.png` and `spec_*.png`), JSON outputs over 1 MB, and `skeptic_minimal/shadow_*`, the copy of astropy main's wcsaxes tree (regenerate it with `git -C <astropy clone> archive 1f930be7c4 astropy/visualization/wcsaxes`).

## Raw findings by area, with the second measurement

Every finding each area reported, including those the ranking merged or left out, with the re-measuring agent's verdict where it tested one (it tested up to six per area).

### Area: events

**Setup and baselines.** Event and callback overhead (echo notifications, glue hub dispatch, draw requests) in the 4000255147 Si IV 1403 + SJI 1400 quicklook. Setup: glue-core 1.27.0, glue-qt 0.4.2, echo 0.15.0, astropy 8.0.1, matplotlib 3.11.2 in the iris-plan env. glue-solar comes from ~/Git/glue-solar-main at 2fdb847 (#84), which is 3 merges behind origin/main 5eae565 (#86, #87, #88). The quicklook ran in a 1600x1000 offscreen window at dpr 1 (raster panels 402x327 px, SJI 609x327 px). Every number below is a median of n=7 unless stated. "Wall to idle" runs from the action until no draw, coordinator timer or profile worker is pending. Counts come from wrappers installed at runtime around echo CallbackProperty.notify and _notify_global, Hub.broadcast and _find_handlers, FigureCanvasQT.draw_idle, DeferredMethod, MplCanvas.draw and paintEvent, Data.compute_fixed_resolution_buffer and compute_statistic. Nothing on disk was patched. Baseline per action (wall to idle):
- map wavelength step: 33.6 ms
- spectrogram exposure (time) step: 237 ms
- SJI frame step: 106 ms
- Pixel click on the map: 383 ms
- axis swap on the map: 101 ms
- colormap change: 26-29 ms
- adding a layer to the SJI viewer: 114 ms

Colormap changes are clean: 1 draw and under 1 ms of event work. The echo and hub plumbing is cheap on every action. The cost comes from what the callbacks trigger: WCSAxes tick computations, redundant draws across event-loop turns, and profile-worker latency.

#### events#1. Every slice change of an IRIS cube, and every axis swap, rebuilds the WCSAxes labels through 4 full tick computations (confirmed)

- **Slows:** SJI frame slider step; raster exposure (time) slider step; Pixel click (the coordinator then moves 3 viewers' sliders); axis swap; opening the quicklook
- **Repository:** glue-core (primary); astropy (WCSAxes.set_xlabel/set_ylabel eager tick update, alternative fix that also helps sunpy users); **confidence:** high; **share:** - SJI step: 66% of 105.6 ms
- Pixel click: 37% of 383 ms
- axis swap: 63% of 101 ms
- exposure step: 14% of 237 ms
- quicklook(): 28% of 2.67 s

**Cost.**

MatplotlibImageMixin._set_wcs took 64.6 ms on the SJI, 31.8 ms on the spectrogram and 25.5 ms on the map (n=9 direct calls). Inside actions (n=7 recorded):
- SJI step: 69.6 ms
- exposure step: 32.1 ms
- click: 141 ms (3 calls)
- axis swap: 63.3 ms (2 calls)
- quicklook open: 25 calls, 761 ms
Each _set_wcs makes 4 WCSAxes._update_tick_and_label_positions calls. Each one costs 15.6 ms on the SJI gwcs and 6-8 ms on the raster panels. One axes.set_xlabel costs 16.4 ms on the SJI; coords[i].set_axislabel twice costs 0.02 ms; reset_wcs costs 0.5-0.8 ms.

**Cause.**

glue/viewers/image/viewer.py:96-98: _on_slice_change calls _set_wcs(relim=False) whenever _changing_slice_requires_wcs_update is set (lines 133-148), which is true for the IRIS WCS because lon/lat depend on time.
_set_wcs (lines 100-150) sets state.x_axislabel and y_axislabel to '' (lines 120-121), then _update_axes (lines 74-82) sets them back to the world labels. That makes 4 echo notifications to update_x/y_axislabel at glue/viewers/matplotlib/viewer.py:152-162. These call WCSAxes.set_xlabel/set_ylabel, which call self._update_tick_and_label_positions() eagerly (astropy/visualization/wcsaxes/core.py:596-598 and 613-615 in 8.0.1). That is a full frame sample and tick computation through the WCS, and the next draw repeats it anyway (draw_wcsaxes).
On an axis swap, x_att and y_att are both connected to _set_wcs (viewer.py:47-48). ImageViewerState swaps y_att inside the x_att callback, so _set_wcs runs twice, each time with reset_limits.

**Upstream main.**

Still present:
- glue main dae530c3: viewer.py and matplotlib/viewer.py are identical to 1.27.0.
- astropy main 1f930be7c4: set_xlabel still calls _update_tick_and_label_positions (core.py:685 and 715).
- glue-solar origin/main 5eae565 is worse. #87's FrameTimeTool._label_exposures sets the exposure-axis label again after each glue reset, so y_axislabel fires 8 times instead of 6 per click. Measured from a git-archive copy: click 412 vs 383 ms, _set_wcs 168 vs 141 ms.

**Candidate fix.**

glue-core: for a slice-only change, call axes.reset_wcs(slices=...) and then re-apply the labels and tick-label sizes directly on the coordinates glue already maps to each axis (axes.coords[ndim-1-att.axis].set_axislabel, as update_x_ticklabel does). This replaces the ''-then-label state round trip through axes.set_xlabel. Also skip _update_appearance_from_settings on slice changes, and run one _set_wcs per swap: coalesce x_att and y_att, or defer to a single call.
astropy (alternative or additional): stop set_xlabel/set_ylabel from computing ticks eagerly. Store the label and resolve the target coordinate in draw_wcsaxes, which computes positions anyway.

**Gain.**

The lean path (reset_wcs + 2 direct set_axislabel + tick sizes) measured 0.8 ms, against 25-65 ms for the full _set_wcs. Expected results (estimates from component timings, not an end-to-end run with the fix):
- SJI step: about 106 -> 42 ms (-60%)
- click: about 383 -> 245 ms (-36%)
- axis swap: about 101 -> 39 ms (-60%)
- exposure step: -31 ms (-13%)
- quicklook open: about -0.7 s
The gain is larger at devicePixelRatio 2, because text layout is part of the tick computation.

**Evidence.**

Files under perf_survey_20261001/events/:
- run_all.out: per-action counters and the 'timed' rows for _set_wcs and _update_tick_and_label_positions.
- trace_pixel_click_map_spectrogram_exposure_step_sji_frame_step_add_layer_sji.log: timelines showing 4 tick updates inside each _set_wcs, then 1 more in the draw.
- bench_fixes.log section A: the split of _set_wcs into its parts, n=9.
- bench_fixes.log section E: 25 _set_wcs calls during quicklook open.
- run_origin_main.out: the glue-solar 5eae565 comparison.
- prof_sji_frame_step.txt: the cProfile.

**Second measurement.** Setup: glue-solar-main 2fdb847 (3 merges behind origin/main 5eae565; quicklook.py is identical); 4000255147 Si IV 1403 + SJI 1400; offscreen Agg, dpr 1; other agents were running at the same time.

Direct _set_wcs calls (median of 9, two runs):
- SJI: 66.0 / 67.1 ms
- spectrogram: 32.2 / 32.5 ms
- map: 25.9-32.2 ms
- one _update_tick_and_label_positions: 16.2-16.7 ms (SJI), 6.3-8.2 ms (raster panels)
- lean path (reset_wcs + 2 set_axislabel + appearance + tick sizes): 0.8-1.0 ms

Inside actions (wall to idle, n=9):
- SJI step: _set_wcs 69.6 of 105.0 ms (66%)
- click: 3 calls, about 140 ms of 378-389 ms (36%)
- x-axis change on the map: 2 calls, 65.4 of 106.1 ms (62%)
- exposure step: 31.3 of 233 ms (13%)
- quicklook(): 25 calls, 763 ms of 2.41 s (32%). 84 tick computations (727 ms) ran inside the x/y label callbacks.

The lean path renders pixel-identical figures (0 differing pixels on the SJI, spectrogram and map), and the next draw costs the same (27.6 vs 28.8 ms on the SJI). The eager tick work is pure waste.

Fix emulated end to end (my own slices callback runs the lean path; glue's flag is off; nothing on disk changed; alternating):
- SJI step: 105.2 -> 39.1 ms (-66 ms, n=9)
- click: 380.6 -> 246.4 ms (n=9) and 377.9 -> 247.1 ms (n=15), so about -131 to -134 ms
- exposure step: -13.0 ms (n=9) and -23.6 ms (n=15)

glue-solar origin/main 5eae565 (git archive copy), n=9: click 401 vs 368 ms; y-label callbacks 8 vs 6 per click; _set_wcs 166 vs 135 ms.

**Correction.** 1. The cause, the file:line citations and the upstream-main status all hold.

2. The 'axis swap' is not a swap. Setting x_att to the current y_att makes ImageViewerState pick y itself, the last or second-to-last world axis (state.py _on_xatt_world_change). The map therefore goes from (exposure, slit) to (slit, wavelength), and repeated changes alternate between (1,2) and (2,1). There are still 2 _set_wcs calls per change. Because of this, a harness that repeats the action leaves the map on a different view; the original run_actions ran it after the click, so the click numbers are unaffected.

3. The exposure-step gain is smaller end to end: -13 to -24 ms, not -31 ms. The main thread saves 31 ms, but the profile worker tail (finding 2) sets when the action ends.

4. At quicklook open, only 3 of the 25 _set_wcs calls (140 ms) come from a slice change. The other 22 come from x_att, y_att, reference_data or add_data and need a full reset. The slice-only lean path therefore removes only about 0.14 s. The quoted -0.7 s needs either the astropy change (no eager ticks in set_xlabel/set_ylabel) or setting the labels directly in every _set_wcs.

5. _update_appearance_from_settings costs about 0.1 ms, and my lean timing includes it. Skipping it gains nothing.

6. To instrument this, note that glue-qt's ImageViewer is built with decorate_all_methods(defer_draw), so it holds its own copies of the mixin methods. Wrapping MatplotlibImageMixin after glue_qt.viewers.image is imported records nothing.

7. The dpr 2 effect was not measured (offscreen only).

#### events#2. The spectrum panel waits on glue-qt's 25 Hz polling worker, twice per point move (confirmed)

- **Slows:** Every move of the Point: raster time step, Pixel click (and drags)
- **Repository:** glue-qt (worker polling); glue-core (second profile run on limits change); **confidence:** high; **share:** Time step: the spectrum finishes 56.7 ms after the image panels (median, n=9, range 26-76 ms). That tail is about 24% of the 237 ms action. Click: the tail is 22.6 ms (6%), because the image work currently dominates; it becomes the critical path once finding 1 is fixed.

**Cost.**

Idle quicklook, one spectrum recompute, n=15:
- request to worker start: median 18.1 ms (9-35 ms)
- the compute itself: 0.54 ms
- compute end to the postthread on the main thread: 42.4 ms (40-51 ms)
- request to idle: 73 ms
Every point move runs the worker 2 times (9/9 runs for both a time step and a click) and draws the spectrum 3 times (8 ms each).

**Cause.**

glue_qt/viewers/matplotlib/compute_worker.py:33: the run loop sleeps 1/25 s before reading the queue. compute_end is emitted only on the next empty poll (lines 40-46), so every result waits for at least one more sleep.
glue/viewers/profile/layer_artist.py:82: _calculate_profile_postthread calls state.update_limits() (profile/state.py:494-500), which changes v_min/v_max. _update_profile (layer_artist.py:123-136) treats v_min/v_max as a reason to call _calculate_profile again, so a second worker round trip and an extra draw follow even with normalize off.
The first spectrum draw comes from Viewer._update_subset. It redraws the stale line before the worker has run.

**Upstream main.**

Unchanged: glue-qt main 9780eaf9 compute_worker.py and glue main profile/layer_artist.py and state.py are identical to the installed versions.

**Candidate fix.**

glue-qt: block on work_queue.get(timeout=...) instead of sleep-polling. Drain the queue, compute, and emit compute_end immediately when the queue is empty after the run.
glue-core: re-run _calculate_profile on v_min/v_max only when viewer_state.normalize is on. Alternatively, call update_limits in postthread under ignore_callback(self.state, 'v_min', 'v_max') and just set the line.

**Gain.**

Removes about 40-60 ms of polling latency per round trip and 1 of the 2 round trips. That is about -45 to -50 ms (-20%) on a time step, and 2 fewer spectrum draws (about 16 ms of main thread) per point move. This is an estimate from the measured latencies; the fix was not run. It matters most for Pixel drags, where every mouse event queues a recompute.

**Evidence.**

Files under perf_survey_20261001/events/:
- bench_fixes.log section C: worker latency.
- bench_tail.log: the tail and worker runs, n=9.
- run_all.out: the global callback 'ProfileLayerState -> ProfileLayerArtist._update_profile {v_max,v_min}' (1 per action) and 3 spectrum draws per move.
- trace_*.log: the worker begin/end and postthread timestamps.

**Second measurement.** Idle recompute of the Point profile, n=15. The layer size is 1.75e8, so it takes the threaded path:
- request to worker start: median 23.1 ms (10-33)
- compute: 0.48 ms
- compute end to postthread: 42.9 ms (42-51)
- request to idle: 84.6 ms

Every time step and every click: 2 worker runs (9/9) and 3 spectrum draws (9/9) of 8.0-8.4 ms each. I captured the stack of each request: in 3 time steps there were 3 requests from _update_subset -> update -> _update_profile and 3 from inside postthread -> update_limits (v_min/v_max). That confirms the second round trip.

Tail (time from the last image-panel draw to the last spectrum draw) on a time step:
- median 34.2 ms (n=9, range 30-76)
- median 38.1 ms (n=15, range 26-82; bimodal with the poll phase)
- click: 22.4-22.7 ms

Zero-latency worker emulated by an instance override that computes synchronously (in this process only), n=9 alternating:
- time step: 255 -> 192 ms (-63 ms; against the usual 234-247 ms baseline, about -42 to -55 ms), spectrum draws 3 -> 1
- click: 374 -> 355 ms (-19 ms)

**Correction.** The latency numbers, the cause and the line numbers (compute_worker.py:33 and 40-46; profile/layer_artist.py:82 and 123-136; state.py:494-500) all hold. Upstream main is identical.

The tail share is overstated. My median tail on a time step is 34-38 ms, about 15% of the action, not 56.7 ms (24%). The original's 56.7 ms falls within my bimodal range of 26-82 ms.

The claimed gain of about -45 to -50 ms per time step agrees with the emulated -42 to -63 ms. The emulation also showed the 3 spectrum draws collapsing to 1. On a click the gain is about -19 ms today; finding 5 showed this tail grows to about 71 ms once the image draws finish earlier.

#### events#3. A hidden subset layer still gets a full update and a full canvas redraw on every subset change (the SJI's Point layer) (confirmed)

- **Slows:** Raster time step and Pixel click: every point move redraws the SJI
- **Repository:** glue-core (generic fix); glue-solar (workaround); **confidence:** high; **share:** 15% of a time step; 8% of a Pixel click

**Cost.**

The SJI Point layer that glue-solar hides costs about 4 ms of crosshair get_xy through the lon/lat links, plus a 28 ms SJI draw, per point move. Measured by removing that layer from the SJI viewer (n=7, SJI draws 2 -> 1):
- time step: 260.5 -> 222.5 ms (-38 ms)
- click: 376.9 -> 348.3 ms (-29 ms)

**Cause.**

glue/viewers/common/viewer.py:309-314: Viewer._update_subset calls layer_artist.update() for every layer of the subset, whatever its visible state.
ImageSubsetLayerArtist.update (glue/viewers/image/layer_artist.py:391-396) clears the caches, runs _update_image(force=True), which calls _update_data and PixelSubsetState.get_xy on the linked SJI (lines 317-335), then redraw(). That schedules a full SJI draw although nothing visible changes.
glue-solar hides rather than removes the Point layer on SJI viewers: quicklook.py:857-870 (_show_point) and 399-402.

**Upstream main.**

Unchanged in glue main (viewer.py and image/layer_artist.py are identical). glue-solar main has the same _show_point.

**Candidate fix.**

glue-core: in _update_subset or ImageSubsetLayerArtist.update, skip the work and the redraw for a layer whose state.visible is False. Mark it stale and do the forced update when visible turns on; today a 'visible' change only runs _update_visual_attributes.
glue-solar workaround: remove the Point layer from viewers where it must not show (viewer.remove_subset) instead of hiding it, or apply the point before draws (see the coordinator timing finding), which merges the two SJI draws.

**Gain.**

-29 to -38 ms per point move, measured. Bigger at dpr 2, where an SJI draw costs more. Not additive with the coordinator-timing fix for the SJI draw.

**Evidence.**

Files under perf_survey_20261001/events/:
- bench_fixes.log section B.
- trace_pixel_click_map_*.log: 'schedule draw sji by SubsetUpdateMessage->glue.viewers.common.viewer.Viewer._update_subset' at 6 ms, about 4 ms after the SJI's SubsetUpdateMessage.
- run_all.out: draws {'sji': 2.0} for the exposure step and the click.

**Second measurement.** Per point move:
- ImageSubsetLayerArtist.update on the hidden SJI layer: 3.6 ms
- the extra SJI draw: 27.4-28.4 ms (SJI draws 2 -> 1 when the layer is removed)
- main-thread total: about 31 ms

Wall to idle, hidden vs removed (alternating):
- click: 388.5 -> 353.3 ms (-35.1, n=9) and 379.8 -> 344.3 ms (-35.6, n=15)
- time step: 234.4 -> 208.0 ms (-26.5, n=9) and 238.9 -> 224.8 ms (-14.0, n=15)

**Correction.** The cause holds: Viewer._update_subset (common/viewer.py:309-314) calls update() whatever the layer's visibility, and image/layer_artist.py:392 update -> _update_image(force=True) -> redraw. glue-solar's _show_point and the visibility loop in _update hide the layer rather than removing it.

The click gain is confirmed: about -35 ms, 9%. The time-step gain is smaller than claimed: -14 to -27 ms (6-11%), not -38 ms (15%). The time step's end is bounded by the profile worker tail (finding 2), so the 31 ms of main-thread savings shows up only partly in the wall time. The gain overlaps with finding 5's SJI-draw saving.

#### events#4. Every new image layer renders an icon for each of the 189 registered colormaps, once on creation and again on resize (not confirmed)

- **Slows:** Adding a data layer to an Image viewer (drag a dataset on); opening the quicklook (4 image layers)
- **Repository:** glue-qt (primary); glue-solar (number of registered colormaps); **confidence:** high; **share:** About 49% of adding a layer (55.9 of 114 ms); 16% of quicklook() (431 ms of 2.67 s)

**Cost.**

QColormapCombo._update_icons takes 53-56 ms per call: 189 colormaps, cmap2pixmap with 200 steps each.
- add_layer: 1 call, 55.9 ms
- quicklook open: 8 calls for 4 image layers, 431 ms
- constructing one QColormapCombo: median 54.6 ms (n=5)
glue alone registers 15 colormaps; glue_solar.setup() adds 174 from sunpy.

**Cause.**

glue_qt/utils/colors.py:
- QColormapCombo.__init__ (lines 190-196) and _update_icons (lines 210-215) re-render every colormap with cmap2pixmap (line 63).
- resizeEvent re-renders them all again (lines 217-219).
glue_qt/core/layer_artist_model.py:357 (on_artist_add) builds the layer style editor, and with it the combo, eagerly for every new layer artist, even if the editor is never shown.
glue_solar/__init__.py:14-17 (setup) registers every sunpy colormap, which multiplies the cost by about 12.6x.

**Upstream main.**

Unchanged on glue-qt main (colors.py and layer_artist_model.py are identical to 0.4.2); glue-solar main's setup() is unchanged.

**Candidate fix.**

glue-qt: cache the icon pixmaps at module level, keyed by (colormap, width), so each colormap renders once per size per session. Skip re-rendering on resize when the width is unchanged, and/or render icons lazily when the popup opens or when the style editor is first shown.
glue-solar: register only the colormaps IRIS/AIA use (irissji*, sdoaia* and similar) rather than all of sunpy's.

**Gain.**

About -50 ms per added image layer (-45%) and about -0.4 s off quicklook open with either fix. This is an estimate from the measured per-call cost.

**Evidence.**

Files under perf_survey_20261001/events/:
- bench_fixes.log section E: 8 calls, 431 ms; 189 vs 15 colormaps; 54.6 ms construction.
- run_all.out add_layer_sji: 'QColormapCombo._update_icons': (1.0, 55.87).
- prof_add_layer_sji.txt: glue_qt self-time 15%, cmap2pixmap.
- trace_axis_swap_map_map_wavelength_step_add_layer_sji.log: _update_icons from 12.6 to 65.6 ms in a 108 ms add.

**Second measurement.** In a real session glue's load_plugins guards against loading a plugin twice, so glue_solar.setup() runs once and the registry holds 102 colormaps: glue's 15 plus sunpy's 87.

With 102 colormaps:
- QColormapCombo() construction: median 29.9 ms (n=7)
- _update_icons: about 0.29 ms per colormap (4.4 ms for 15, 29.9 ms for 102)
- quicklook open: 8 _update_icons calls, 238.7 ms, of which 4 calls (111.7 ms) were in resizeEvent. That is about 10% of quicklook() (2.41 s).
- adding a data layer to the SJI viewer: 84.7 ms wall (n=7), of which 29.6 ms (35%) was the single _update_icons call
- setting icons from cached pixmaps: 0.06 ms for 102 items

**Correction.** The cause holds: icons are re-rendered in __init__ and resizeEvent (colors.py:190-219), and on_artist_add (layer_artist_model.py:357-373) builds every layer's style editor eagerly. Upstream is unchanged.

The cost is inflated about 1.85x by the original harness. It called glue_solar.setup() explicitly and then GlueApplication() loaded the glue_solar plugin entry point, which calls setup() again. That registered sunpy's 87 colormaps twice: 189 items instead of 102.

Real costs:
- per call: about 30 ms, not 53-56 ms
- per added layer: about 30 ms of 85 ms (35%), not 56 of 114 ms (49%)
- quicklook open: about 0.24 s (10%), not 0.43 s (16%)
- the glue-solar multiplier is 6.8x, not 12.6x

Expected gains:
- glue-qt pixmap cache: about -30 ms per layer after the first of each width, and about -0.18 s at open (one render per width instead of 8)
- glue-solar registering only glue's plus irissji/sdoaia colormaps (about 34): about -20 ms per call

The finding is still real and worth fixing, but the numbers need halving.

#### events#5. glue-solar's coordinator moves the sliders after glue has already scheduled the click's draws, so 3 panels draw twice (confirmed)

- **Slows:** Pixel click on the map (likewise a Pixel drag)
- **Repository:** glue-solar; **confidence:** medium; **share:** About 10% of a Pixel click (-39 ms measured)

**Cost.**

Draws per click: spectrogram 2, wavelength 2, sji 2 (first with stale sliders), map 1, spectrum 3 (n=7 recorded). Calling the coordinator's own _update() right after the click, before the event loop runs the draws: 380.0 -> 341.1 ms and draws 10 -> 7 (n=9 alternating, no code changed). On a time step: no measurable gain (231 vs 261 ms, SJI draws 2 -> 1), because the end is set by the profile worker. Of Coordinator._update's 160 ms per click, about 141 ms is glue's _set_wcs that it triggers (finding 1); about 19 ms is glue-solar's own work.

**Cause.**

glue_solar/quicklook.py:
- Coordinator._subset_changed (lines 318-331) and slices_changed (lines 246-254) defer the work to a 0 ms single-shot QTimer (lines 216-219).
- _update (lines 386-402) then moves the spectrogram, wavelength and SJI sliders in a later event-loop turn. By then glue's SubsetUpdateMessage handlers have already drawn those canvases with the new crosshair and the old slices.

**Upstream main.**

glue-solar origin/main 5eae565: quicklook.py is unchanged since 2fdb847.

**Candidate fix.**

Apply the point synchronously in _subset_changed when the event is a single click, or from a timer that fires before glue's draw_idle callbacks. Keep the coalescing timer only while a Pixel drag is in progress.

**Gain.**

-39 ms (-10%) per click, measured with the harness calling _update early. More at dpr 2, and more once finding 1 makes the image work cheaper.

**Evidence.**

Files under perf_survey_20261001/events/:
- bench_sync.log.
- trace_pixel_click_map_*.log: the draws of map/spectrogram/wavelength/spectrum/sji at 6-115 ms, then Coordinator._update at 117-275 ms, then sji/spectrogram/wavelength redrawn at 277-360 ms.
- run_all.out pixel_click_map: draws and 'glue_solar outer time 159.9 ms'.

**Second measurement.** Click, as is vs coordinator _update called right after the click with the timer stopped (alternating):
- n=9: 379.9 -> 354.7 ms (-25.2)
- n=15: 380.0 -> 355.6 ms (-24.4)

Draws per click go from 10 to 7: spectrogram 2 -> 1, wavelength 2 -> 1, SJI 2 -> 1; map 1 and spectrum 3 are unchanged. Main-thread draw time drops from 204 to 124 ms. The last image-panel draw ends at 274 ms instead of 359 ms (-84 ms), but the spectrum then finishes 71 ms after the images instead of 22 ms.

Coordinator._update takes 159-162 ms per click, of which _set_wcs is about 140 ms (70 + 32 + 38). Time step: no gain (+5 ms), SJI draws 2 -> 1.

**Correction.** The mechanism, the draw counts, the line numbers and the 141 / 19 ms split all hold.

The wall-clock gain is about -25 ms (6-7%), not -39 ms (10%). That is 1.6x lower, at the edge of the tolerance. The gain is capped because the profile worker's polling (finding 2) becomes the critical path once the duplicate draws go. The image panels themselves become final about 84 ms sooner, which is what the user sees, and the wall gain should approach that once finding 2 is fixed.

#### events#6. A wavelength-slider step runs glue-solar's full time sync, and the SJI point is projected twice per sync (confirmed)

- **Slows:** Wavelength slider step on the map (any slider step on the time master's viewers); every time sync
- **Repository:** glue-solar; **confidence:** high; **share:** 31% of a wavelength step (10.3 of 33.6 ms); about 4% of a time step (11 of 237 ms)

**Cost.**

Coordinator._update took 10.3 ms with nothing moved (n=15) and 10.3 ms inside a map wavelength step (n=7). In _update, _sji_pixels (gwcs world_to_pixel through dkist models) accounts for about 60% of the cProfile time. It is called 2 times per sync for the same SJI frame and point: once from FrameTimeTool._refresh ("outside SJI FOV") and once from CoordinateTool._draw (marker).

**Cause.**

glue_solar/quicklook.py:253-254: slices_changed starts the timer whenever the time master's viewer changes any slider, wavelength included. _sync (lines 464-495) then calls every listener even when the master time, step and point are unchanged.
The listeners FrameTimeTool._synced/_refresh (tools.py:108-150) and CoordinateTool._synced/_draw (tools.py:310-338) each call Coordinator.point_on (quicklook.py:529-543), which calls _sji_pixels (lines 103-112).

**Upstream main.**

Unchanged on glue-solar origin/main 5eae565 (quicklook.py identical; tools.py adds _label_exposures but keeps both point_on calls).

**Candidate fix.**

Start the timer only when the slider of the master's time axis changed (use echo_old to compare). Alternatively, in _sync, return before calling the listeners when (master, time index, step, point) equals the last _master_times entry. Memoize point_on per (point slices, SJI frame) so the SJI's two tools share one gwcs inverse.

**Gain.**

About -10 ms (-30%) per wavelength step; about -3 ms per time sync from the memoization. Estimate from _update timing and the cProfile split.

**Evidence.**

Files under perf_survey_20261001/events/:
- bench_fixes.log section D: _update median and the cProfile restricted to glue_solar (40 point_on, 10 _sji_pixels per 5 updates).
- run_all.out map_wavelength_step: 'Coordinator._update': (1.0, 10.33); 'glue_solar outer time 13.2 ms'.
- trace_axis_swap_map_map_wavelength_step_add_layer_sji.log.

**Second measurement.** Map wavelength step: 35.1 ms wall to idle (n=9), of which Coordinator._update is 11.0 ms (31%) and the map draw 19.5 ms. Stopping the coordinator's timer right after the step (what the proposed guard would do), alternating n=9: 35.1 -> 23.9 ms (-11.1 ms, -32%).

_update with nothing moved: 11.0 ms (n=15). Per sync: point_on 8 calls (4.8 ms); _sji_pixels 2 calls (4.5 ms, about 41% of _update's wall time). _sji_pixels alone: median 1.84 ms (n=30).

**Correction.** The cause and the line numbers hold (quicklook.py:253-254, 464-495, 529-543 and 103-112; tools.py:108-150 and 310-338). The timer starts for any slider change on the master's viewer.

Two small corrections:
- _sji_pixels is about 40% of _update by wall time, not 60%; cProfile overstated it.
- Memoizing point_on saves one _sji_pixels call, about 2 ms per sync, not 3 ms.

The headline gain, about -10 to -11 ms (-30%) per wavelength step, is confirmed.

Scripts and logs are in perf_survey_20261001/events-verify/:
- scripts: verify.py, verify2.py
- logs: verify_all_glue-solar-main.log, verify2_rep_glue-solar-main.log, verify_click_glue-solar-main.log, verify_click_gs_origin_main.log

#### events#7. Measured and not a problem: the echo and hub dispatch machinery (not re-measured)

- **Slows:** All actions
- **Repository:** glue-core / echo / glue-qt (low priority); **confidence:** high; **share:** Under 1% of every action

**Cost.**

Per action:
- hub: 0-8 broadcasts over about 51 subscribers; _find_handlers filtering 0.26-0.30 ms (about 37 µs per broadcast).
- echo: 2-29 notifications and 5-54 callbacks; _get_aliases_for (dir() on every global notify) 0.07-0.6 ms.
- cProfile self-time of echo + glue/core + glue/viewers + glue_qt: 1.5-3.5% of each action, and the profiler inflates that.
Some subscribers react to every message but are cheap: DataCollectionView._update_viewport on every Message (0.01 ms), ProfileLayerState._on_subset_update (unfiltered), and EditSubsetModeToolBar._update_subset_combo, which rebuilds the subset combo on every SubsetUpdateMessage (0.5 ms per point move).

**Cause.**

glue/core/hub.py:165-189 scans all subscribers per message. echo/core.py:317-338 (_get_aliases_for and _notify_global) runs dir() per notify. glue_qt/app/edit_subset_mode_toolbar.py:46 and 54 subscribe to every SubsetMessage.

**Upstream main.**

hub.py is identical on glue main; echo upstream not checked (no local checkout).

**Candidate fix.**

None needed now. Optional: cache the alias lookup per class in echo, and update the edit-subset combo only for label/style or create/delete messages.

**Gain.**

Under 1 ms per action

**Evidence.**

Files under perf_survey_20261001/events/:
- run_all.out: the 'hub broadcasts', 'echo' and 'hub handlers' rows per action.
- prof_*.txt: the 'tottime by package' tables.

**Not measured in this area.** Not measured:
- A real screen. All numbers are offscreen Agg at devicePixelRatio 1 (paint about 0.2-0.3 ms). At dpr 2 or under Wayland, each redundant draw costs more, so findings 1, 3 and 5 gain more. The user's 28 ms X11 slider tick compares with the 33.6 ms map wavelength step here.
- Continuous interaction. Slider drags (glue-solar throttles them to 100 ms) and Pixel drags were not timed, though the worker latency and coordinator timer compound there.
- Adding a subset layer via an ROI on the SJI. It is dominated by mask computation, not events.
- The real deconvolved SJI. "Adding a layer" used a pixel-linked copy of the SJI 1400 that shares its array. A copy linked only by lon/lat (as link_hpc does) got disabled as incompatible. I did not check whether the quicklook's "drag the deconvolved SJI onto a slit-jaw viewer" hint hits the same problem on 4000005156.
- Worker-thread CPU and GIL contention.
- Draw internals. Each WCSAxes tick computation costs 6-16 ms inside every draw because the IRIS gwcs is slow; that belongs to the draw area.
- Two draws per viewer about 250 ms after the quicklook opens (canvas resize timers); seen but not investigated.

Other caveats:
- Gains for findings 1, 2, 4 and 6 are estimates from component timings, not end-to-end runs with fixes applied. Findings 3 and 5 were measured by removing the hidden layer, or calling the coordinator early, at runtime.
- glue-solar upstream main (5eae565) was measured from a git-archive copy for 5 actions only.
- The trace logs come from an earlier run that had the extra copy dataset in the collection, adding a 3rd SubsetUpdateMessage per point move. The final timings (run_all.out) and bench_* runs were made without it.
- glue-core and glue-qt upstream main were compared file by file and are identical for every file cited.

Scripts and logs are in perf_survey_20261001/events/:
- harness.py, run_actions.py, bench_fixes.py, bench_sync.py, bench_tail.py
- run_all.out, actions_all.log, run_origin_main.out, bench_*.log, trace_*.log, prof_*.txt and prof_*.pstats

Peak RSS was 2.79 GB.

### Area: profile-stats

**Setup and baselines.** Profile viewer and statistics (glue-core 1.27.0, glue-qt 0.4.2, numpy 2.5.3; glue-solar-main at 2fdb847, which is #84 and 3 merges behind origin/main 5eae565). Runs were offscreen Agg at devicePixelRatio 1 with a 1600x1000 app. Data: the 4000255147 Si IV 1403 cube (1600x417x262, float32, 15.8% NaN) and the 4000005156 Si IV 1403 stack (2x64x771x536). Scripts and logs are in perf_survey_20261001/profile-stats/. Main scripts: bench_profile.py, gui_quicklook.py, gui_spectrum.py, gui_worker_variants.py, gui_collapse.py, gui_function_change.py, proto_stats.py. Each has a matching *_ss.log / *_stack.log. Every glue/glue-qt file cited is byte-identical to upstream origin/main as last fetched locally: glue dae530c3 (2026-07-13), glue-qt 9780eaf9 (2026-02-17). A gh search found no upstream PRs on these topics.

#### profile-stats#1. The threaded profile worker adds about 60 ms to every point move for a 262-sample spectrum (confirmed)

- **Slows:** Moving the point (Pixel tool click or drag, or a slider) until the spectrum panel shows the new spectrum. Also applies to dragging an ROI.
- **Repository:** glue-qt (worker polling, 1e7 threshold) and glue-core (v_min/v_max trigger in glue/viewers/profile/layer_artist.py); **confidence:** high; **share:** About 85% of a lone Profile viewer's update latency (about 61 of 74 ms). 20-28% of a quicklook point move (63 of 309 ms, 98 of 349 ms). The rest of a quicklook move is mostly other viewers redrawing (see not_measured).

**Cost.**

Glue-only Profile viewer, Si IV 1403 sit-and-stare cube (median of 20-30 moves): 73.6-78.3 ms to the first spectrum redraw. Running the same layer synchronously (in-process comparison) takes 12.7 ms. On the stack: 76.9-81.2 ms against 10.6 ms. The statistic itself takes 0.1-0.3 ms. Each move costs 2 worker runs, 2 ComputationEnded messages and 3 spectrum draws (25.6 ms of main-thread drawing); synchronous needs 1 draw (8.8 ms). A 40x40 ROI move takes 84 ms against 18.5 ms. In the full quicklook the spectrum is drawn after 309 ms threaded against 246 ms synchronous on the sit-and-stare cube, and 349 against 251 ms on the stack.

**Cause.**

Three causes stack up:
- glue_qt/viewers/matplotlib/compute_worker.py:33 polls its queue with time.sleep(1/25), and lines 40-46 emit compute_end only on the next poll that finds the queue empty. That sets a 40-80 ms floor on every round trip.
- glue_qt/viewers/profile/layer_artist.py:50 sends a layer to the worker when state.layer.size > 1e7. Subset.size is the parent data's size (glue/core/subset.py:406), so a one-pixel 262-sample profile goes through the thread.
- glue/viewers/profile/layer_artist.py:82: the post-thread step calls update_limits(), which changes v_min/v_max. Lines 134-135 list v_min/v_max as recompute triggers, so every move makes a second worker round trip and 2 extra draws.

**Upstream main.**

Same code on glue and glue-qt origin/main (files identical).

**Candidate fix.**

(a) glue-qt ComputeWorker: block on work_queue.get() and emit compute_end as soon as the queue is empty after a job, instead of polling. (b) glue-core ProfileLayerArtist._update_profile: drop 'v_min' and 'v_max' from the recompute triggers; they only affect normalisation, which can be reapplied to the cached profile. (c) glue-qt: decide whether to use the thread from the work size (for a SliceSubsetState, the product of the sliced shape) rather than the parent data's size.

**Gain.**

Measured with in-process variants (gui_worker_variants.py, n=30): (a)+(b) cut the latency from 78.3 to 23.2 ms on the sit-and-stare cube and from 76.9 to 22.8 ms on the stack, with one fewer draw per move (25.6 to 17.1 ms of drawing). (b) alone keeps the latency but saves a draw. (c), the synchronous path, gives 12.7 / 10.6 ms. Expect about 55-65 ms less per point move, which is 63-98 ms in the quicklook.

**Evidence.**

Logs: gui_spectrum_ss.log and gui_spectrum_stack.log (worker runs, messages and draws per move, synchronous comparison); gui_worker_variants_ss.log and gui_worker_variants_stack.log (fix variants; the plotted spectrum equals the numpy mean in all variants); gui_ss.log and gui_stack.log (quicklook moves). Timing: perf_counter from setting group.subset_state to the first MplCanvas.draw of the spectrum after its ComputationEndedMessage; 2 warm-up moves dropped.

**Second measurement.** Glue-only Profile viewer, 788x352 canvas, offscreen Agg, n=20 moves after 2 warm-up moves. Timed from setting group.subset_state to the end of the first spectrum-canvas draw whose plotted y equals the pixel's spectrum (gui_profile.py).
- Sit-and-stare cube: 80.9 ms median (min 55.8, max 105.9). Per move: 2 worker runs, 2 ComputationEnded messages, 3 draws (26.8 ms of drawing).
- Same layer synchronous: 10.8 ms, 1 draw.
- In-process fix (a)+(b): 20.5 ms, 1 run, 2 draws (18.1 ms).
- (b) alone: 90.7 ms, 1 run, 2 draws.
- Stack: 66.5 / 8.7 / 16.5 ms.
- The subset artist reports layer.size 174,806,400, the parent's size.
Quicklook, sit-and-stare (gui_quicklook.py, n=10). First correct spectrum draw: 360-382 ms threaded, 87-90 ms synchronous, 124-126 ms with (a)+(b). The spectrum canvas's paintEvent comes at 368 / 117 / 372 ms. Stack: drawn at 336-339 / 84-87 / 119-125 ms, painted at 348 / 112 / 320 ms.

**Correction.** The lone-viewer cost, the three causes and the gain of (a)+(b) all hold (about 60 ms saved). Cited code is identical on glue origin/main dae530c3 and glue-qt origin/main 9780eaf9.

The quicklook numbers are wrong:
- The synchronous baseline (246/251 ms) is an artifact of how it was measured. The original pump checked only after processEvents() returned, and that pass includes a ~160 ms main-thread block. In fact the synchronous spectrum is drawn at about 85-90 ms and painted at 112-117 ms.
- So the worker costs about 250-290 ms of the quicklook's spectrum latency (about 75%), not 63-98 ms (20-28%).
- Fix (a)+(b) does not bring the spectrum onto the screen sooner in the quicklook. Its new draw lands at about 120 ms, just after the first paint pass, and the paint then waits behind the block (paintEvent at 372/320 ms against 368/348 ms installed).
- Only (c), running a small slice synchronously, shows the spectrum at about 115 ms. Rank (c) first for the quicklook.

The block, found with a 2 ms main-thread stack sampler, is glue's ImageViewer._on_slice_change -> _set_wcs(relim=False) (glue/viewers/image/viewer.py:96-124: reset_wcs and axis-label resets). It runs on the viewers whose slices glue-solar's coordinator moves (glue_solar/quicklook.py:384 _set_slices), with the time in glue_solar/sources/loaders/iris.py:88 pixel_to_world_values. It deserves its own item.

The 40x40 ROI-move figures were not re-measured.

Conditions: glue-solar-main was at 2fdb847 (#84), behind origin/main 5eae565 (#85-#88). Other agents were running at load average 4-5.

#### profile-stats#2. ProfileViewerState._reset_y_limits computes whole-cube profiles on the main thread, bypassing the worker (confirmed)

- **Slows:** Opening the IRIS quicklook (the spectrum panel's add_data). In plain glue: dragging a cube into a Profile viewer, or changing Function, Normalize or the y unit while the cube's own layer is visible.
- **Repository:** glue-core (with glue-qt's layer artist signalling the y-limit reset); **confidence:** high; **share:** About 10% of quicklook() on the sit-and-stare cube, 3% on the stack. All of the freeze when Function changes. Mg II k 2796, the quicklook's default window, is 2.1x larger; extrapolated to about 0.86 s at open, not measured.

**Cost.**

Quicklook open: one whole-cube 'mean' profile on the main thread took 408 ms of the 4.13 s quicklook() on the sit-and-stare cube and 111.5 ms of 3.74 s on the stack. The result is then discarded, because glue-solar hides the layer and switches x_att to Wavelength. Plain glue add_data blocks the main thread for 194 ms ('maximum'), then the worker recomputes the same profile (188 ms). Changing Function with the cube layer visible blocks the main thread for 655 ms (mean), 2778 ms (median) and 425 ms (maximum), one run each. On the stack, a median profile takes 566 ms.

**Cause.**

glue/viewers/profile/state.py:212-228: _reset_y_limits reads layer.profile, which calls update_profile and then compute_statistic (line 473), for every layer, synchronously.
- It is called from the 'normalize' and 'function' callbacks (lines 66-67) and from reset_limits (line 161), which runs on every reference_data change (line 331).
- None of this goes through glue-qt's QThreadedProfileLayerArtist.
- On add, the artist also queues its own job with reset=True (force), so the same profile is computed twice.
Stack traces were captured.

**Upstream main.**

Same code on glue origin/main.

**Candidate fix.**

In _reset_y_limits, use only profiles already cached (layer._profile_cache) and skip uncomputed ones. Let the glue-qt artist reset the y limits when its computation ends. Do not force reset=True when the cache was just filled. For glue-solar, adding the raster without ever computing its hidden layer would need glue's help; no workaround was tested.

**Gain.**

Removes 0.4-2.8 s main-thread freezes on a 175M-element cube in plain glue, and 408 ms (10%) of quicklook open on the sit-and-stare cube (112 ms on the stack). Also halves the CPU spent on add_data.

**Evidence.**

Logs: gui_spectrum_ss.log (add_data blocked 194 ms, main and worker 'maximum' passes, stack trace through state.py:331, 161, 221, 473); gui_function_change_ss.log (setter blocking times); gui_ss.log and gui_stack.log (main-thread 'mean' pass during quicklook open). Calls were recorded by wrapping Data.compute_statistic in-process, with thread names.

**Second measurement.** Plain glue add_data of the sit-and-stare cube (function maximum, large-data prompt bypassed): the main thread is blocked for 199 ms (185 ms in a main-thread compute_statistic), then the worker recomputes the same profile (183 ms). Stack: 65 ms, then 53 ms on the worker.

Changing Function with the cube layer visible (main-thread setter time, one run each):
- Sit-and-stare: mean 661/663 ms, median 2804 ms, maximum 430 ms.
- Stack: mean 147 ms, median 574 ms, maximum 86 ms.

Quicklook open:
- Sit-and-stare: one main-thread 'mean' over axes (1,2) takes 368-400 ms of a 4.00 s quicklook(). cProfile shows _reset_y_limits at 414 ms cumulative under quicklook._profile (516 ms).
- Stack: 119 ms of 3.76 s.

**Correction.** No material correction; the costs and the call path through state.py:331 -> 161 -> 221 -> 427 -> 473 hold.
- The double computation happens only on add_data. On a Function change the worker does not recompute, because the main thread has already filled the cache.
- The 'synchronous' variant from finding 1 must not apply to the whole-cube layer: run that way, add_data computed the profile twice on the main thread (365 ms).
- The Mg II extrapolation was not measured.

#### profile-stats#3. Collapse (AggregateSlice) re-aggregates on every redraw and applies the data's function to subset masks (confirmed)

- **Slows:** After Collapse sets an AggregateSlice on the map: every redraw, including pan/zoom, point moves and the quicklook's Point crosshair layer.
- **Repository:** glue-core (numpy for the nanmedian speed); **confidence:** high; **share:** The gathers and aggregations are about 93% of a 334 ms collapsed redraw. On a point move, the data layer's buffer is a cache hit, but its 170 ms nanmedian still runs again.

**Cost.**

Glue-only Image viewer on the sit-and-stare cube (588x347 canvas, median of 6 pans), redraw time:
- Plain slice: 17.5 ms.
- nanmean over 20 px: 31.8 ms. nanmedian over 20 px: 63.9 ms.
- nanmean over 100 px: 59.5 ms. nanmedian over 100 px: 225 ms.
- With the Point subset layer as well: 22.8 / 52.9 / 95.1 / 119.7 / 333.6 ms.
Point move while collapsed (nanmedian, 100 px): 303 ms of map drawing per move. In the quicklook the spectrum is drawn after 646 ms instead of 266 ms; map drawing is 176 ms per move (180 ms on the stack).
Breakdown for a 333x196x100 buffer (n=5 medians): data gather 35 ms; np.nanmedian 173 ms (nanmean 7.7 ms); subset-mask gather 52 ms, of which view_shape is 22.6 ms; np.nanmedian on the bool mask 50 ms (np.any takes 0.4 ms).

**Cause.**

- glue/viewers/image/state.py:474-479: get_sliced_data applies agg_func after compute_fixed_resolution_buffer on every call. The cache (glue/core/fixed_resolution_buffer.py:341) holds the 3D float64 buffer from before aggregation (astype(float) at line 309), so the aggregation reruns on every draw.
- Subset layers (state.py:463) aggregate a boolean mask with the data's function, for example nanmedian over booleans.
- glue/utils/array.py:121: view_shape materialises np.broadcast_to(1, shape)[view] for index-array views.
- glue/core/subset.py:1382: to_mask allocates a full-cube bool mask for array views.
- numpy 2.5.3's np.nanmedian takes the np.ma.median/argsort path for axes shorter than 600. It is 2.5x slower than a sort-and-count version.

**Upstream main.**

Same code on glue origin/main. The numpy nanmedian path was not checked on numpy main.

**Candidate fix.**

- Cache the aggregated 2D result, keyed on bounds and functions, or collapse once at native resolution and run the fixed-resolution buffer on the 2D result.
- Aggregate subset masks with np.any, or skip the aggregation when the subset does not depend on that axis.
- Compute view_shape with np.broadcast_shapes for index arrays.
- Use a faster nanmedian (sort plus count of non-NaN values), or raise it with numpy.

**Gain.**

Point move while collapsed: 303 ms to about 50 ms of map drawing (cached aggregate, np.any, view_shape fix). Pan redraw with nanmedian over 100 px: 334 ms to about 130 ms with the sort-based nanmedian, or to the plain-slice level of about 20 ms with a cached native-resolution collapse. That collapse costs once: 78 ms nanmean or 255 ms nanmedian on the sit-and-stare cube, 9.5 / 21 ms on the stack. The stack's buffer oversamples its 64 steps about 5x.

**Evidence.**

Confidence is high for the cost and breakdown; the native-resolution gain was prototyped but not integrated, so treat that number as medium. Logs: gui_collapse_ss.log (redraw medians; cProfile shows nanmedian, then np.ma sort/argsort, under get_sliced_data); proto_stats_ss.log and proto_stats_stack.log (component timings; sort-nanmedian and np.any results agree with glue); gui_ss.log and gui_stack.log (quicklook moves with Collapse).

**Second measurement.** Glue-only Image viewer on the sit-and-stare cube: 588x347 canvas, 333x196 buffer. Canvas draw time, median of 6 pans after 2 warm-up pans:
- Plain slice 16.9 ms; nanmean 20 px 33.0; nanmedian 20 px 59.7; nanmean 100 px 60.8; nanmedian 100 px 218 ms.
- With the Point subset layer: 24.7 / 51.6 / 90.9 / 120.3 / 316.5 ms.

Point move while collapsed (nanmedian, 100 px): 275 ms of map drawing, 1 draw. A counting wrapper on the AggregateSlice function shows every draw re-running nanmedian on the float64 (333,196,100) data buffer (156 ms) and on the bool subset mask (50 ms).

Components (n=5 medians): FRB data gather 36.4 ms; np.nanmedian 175 ms; nanmean 7.7 ms; sort-based nanmedian 67.5 ms (results equal); mask gather 51.6 ms, of which view_shape is 24.5 ms; nanmedian on the bool mask 53.7 ms; np.any 0.4 ms.

Quicklook map drawing per move with Collapse: 171 ms (sit-and-stare), 179 ms (stack).

**Correction.** The cost and the cause hold.

The one-time native-resolution collapse costs 255 ms only with the sort-based nanmedian (246 ms measured). With np.nanmedian it takes 1.72 s on the sit-and-stare cube, and 274 ms on the stack for both scans (about 137 ms per scan). nanmean is 80 ms, as claimed. The claim's stack figures are per scan.

The pan estimate of 'about 130 ms' is optimistic. Summing the components, the sort-based nanmedian alone gives about 190-200 ms; reaching about 150 ms needs np.any for the masks and the view_shape fix as well.

The point-move estimate of about 50 ms is consistent with the components.

The quicklook figure '646 vs 266 ms' was measured with the same pump artifact as finding 1. I measured the spectrum drawn at 752 vs 378 ms (threaded) and 242 vs 87 ms (synchronous).

#### profile-stats#4. Histogram viewer builds a full-cube mask for the Point subset on every move, and copies the cube for the data histogram (confirmed)

- **Slows:** Moving the point with a Histogram viewer of the raster open (the Point subset joins every viewer). Adding the cube to a Histogram viewer.
- **Repository:** glue-core; **confidence:** high; **share:** The subset histogram is all of the histogram layer's per-move work. It runs on the worker, so it adds CPU and memory churn but little UI latency: a point move took 266 ms against 246 ms, and the extra 20 ms is 2 histogram draws.

**Cost.**

Point subset histogram: 35.4 ms on the sit-and-stare cube and 10.5 ms on the stack per move (n=10), on the worker thread. Each one allocates a transient full-size bool mask (tracemalloc peak 167 MB / 50 MB). In the GUI: 6 calls, 220 ms in total. Whole-cube histogram: add_data took 1.36 s until idle; compute_histogram took 712-725 ms (tracemalloc peak 728 MB; RSS grew 2651 to 3161 MB). On the stack: 209 ms and 229 MB.

**Cause.**

- glue/core/data.py:1936-1954: compute_histogram turns a subset into self.get_mask(subset_state), a full-shape mask from SliceSubsetState.to_mask, then x[mask] over the whole cube. Unlike compute_statistic (data.py:1752), it has no SliceSubsetState.to_array path.
- glue/utils/array.py:546-568 builds keep from two comparisons and ~isnan (full-size bool temporaries) and copies x[keep] before fast-histogram. histogram1d already drops out-of-range values and NaN (verified).
- HistogramViewerState.random_subset defaults to None (glue/viewers/histogram/state.py:45).

**Upstream main.**

Same code on glue origin/main.

**Candidate fix.**

- Use subset_state.to_array for SliceSubsetState, as compute_statistic does.
- For 1-D, unweighted, non-datetime numpy input, pass the raw array to histogram1d without the keep mask; keep the current path for dask and datetime.
- Optionally default random_subset for large data. That is a UX choice, because the histogram becomes approximate.

**Gain.**

Subset histogram: 35.4 ms to under 0.1 ms, with no 167 MB allocation; results are identical. Whole cube: 725 to 504 ms (-30%), peak memory 728 MB to about 0 (stack: 211 to 137 ms); results are identical. With random_subset=1e6: 24 ms.

**Evidence.**

Logs: proto_stats_ss.log and proto_stats_stack.log (glue against the prototype, equality checks, tracemalloc); gui_ss.log and gui_stack.log (Histogram viewer add and moves, worker-thread compute_histogram calls).

**Second measurement.** Point-subset compute_histogram (n=10): 35.4 ms on the sit-and-stare cube, 10.0 ms on the stack; tracemalloc peak 167 / 50 MiB. to_array plus histogram1d takes under 0.1 ms and gives identical counts at 15 and 30 bins.

Whole cube, with the viewer's default range (min/max from 10000 samples), n=3: glue takes 679 ms with a 728 MiB peak. histogram1d on the raw array takes 490 ms with 0.1 MiB, identical counts. Stack: 217 to 151 ms, 229 MiB. random_subset=1e6: 23.6 ms.

In the GUI:
- Histogram add_data is idle after 1.24 s, with a 693 ms worker compute_histogram; RSS grows 2659 to 3143 MB.
- Each point move adds 1 worker call of about 36 ms.
- The spectrum appears 3 ms later (synchronous) or 11-15 ms later (threaded); total drawing grows by about 20 ms.

**Correction.** Line references:
- compute_statistic's SliceSubsetState path is at data.py:1733-1735, not 1752.
- compute_histogram's mask path is at data.py:1938-1953.

The prototype must keep glue's 10*spacing xmax nudge (utils/array.py:605) to give identical counts.

The quicklook '266 vs 246 ms' used the pump artifact, but the conclusion (little UI latency) still holds.

#### profile-stats#5. compute_statistic copies each chunk to float64 for whole-data profiles: 3x slower and 10x more memory than needed (confirmed)

- **Slows:** Any profile of a whole cube: a visible data layer in a Profile viewer, the quicklook-open pass (finding 2), or Function changes.
- **Repository:** glue-core; **confidence:** high; **share:** cProfile of one 704 ms 'mean': the float64 copy (numpy.array) is 249 ms, glue's keep/assign 214 ms and nanmean (with its own _replace_nan copy) 302 ms.

**Cost.**

Sit-and-stare cube, 'mean' along wavelength (n=3): 662-701 ms. A numpy float32 nanmean takes 210 ms. Tracemalloc peak 713 MB for a 667 MB component. 'maximum': 426 ms, 375 MB. Stack 'mean': 150-155 ms against 57 ms in numpy, peak 724 MB for a 202 MB component.

**Cause.**

glue/utils/array.py:465-486: with finite=True and an axis, compute_statistic builds keep = np.ones(...) & np.isfinite, makes a float64 copy (np.array(data, dtype=float)), sets data[~keep] = nan, then calls the nan-function, which copies again. glue/core/data.py:1675-1730 splits the work into 4e7-element chunks along the profile axis.

**Upstream main.**

Same code on glue origin/main.

**Candidate fix.**

Reduce the native dtype with where=np.isfinite(chunk). For the mean: np.sum(..., dtype=float64, where=fin) / np.count_nonzero(fin). For max and min: initial=±inf, then NaN where the count is 0. Fold the subset mask into the same where=. Keep the copy only for median and percentile.

**Gain.**

Mean: 662 to 439 ms on the sit-and-stare cube (-34%) and 155 to 79 ms on the stack (-49%). Peak memory: 713 to 75 MB and 724 to 50 MB. Results agree (rtol 1e-5). Maximum: 426 to 399 ms and 82 to 48 ms. The prototype maximum differs only where a whole column is NaN; it returns -inf there and still needs the NaN rule.

**Evidence.**

Logs: bench_profile_ss.log and bench_profile_stack.log (timings, cProfile, tracemalloc); proto_stats_ss.log and proto_stats_stack.log (prototype timings and result check).

**Second measurement.** Sit-and-stare cube, profile along wavelength, n=3:
- glue 'mean': 673 ms (670-705), tracemalloc peak 713 MiB. 'maximum': 433 ms, 375 MiB. numpy float32 nanmean: 194 ms.
- cProfile of one mean: numpy.array 245 ms, glue utils compute_statistic's own time 206 ms, nanmean 283 ms (including _replace_nan, 138 ms).
- Prototype with where= and the same 5 chunks: mean 441 ms, 75 MiB peak, allclose at rtol 1e-5. Max with the all-NaN rule: 423 ms, identical to glue.
- Stack: mean 151 ms, 724 MiB, against the prototype's 79 ms, 50 MiB; numpy 57 ms. Max 85 ms against 54 ms.

**Correction.** None. The gain for maximum on the sit-and-stare cube is small (433 to 423 ms). Applying the all-NaN rule (NaN where fin.any() is false) makes the prototype maximum match glue exactly.

#### profile-stats#6. Percentile colour limits, pixel-point and ROI statistics: measured and cheap, no fix needed (confirmed)

- **Slows:** Creating image layers (quicklook open, percentile 99.5) and moving a wavelength slider, with stretch_global True or False. Also computing a pixel-point or 40x40 ROI mean profile.
- **Repository:** glue-core; **confidence:** high; **share:** Under 3% of each action's time.

**Cost.**

Quicklook open: 6 percentile, 4 minimum and 4 maximum calls, about 4.5 ms in total (random_subset=10000). Slider tick: 0 ms with global stretch, 0.5-0.6 ms with per-slice stretch; the map draw is 19.5 ms either way. Pixel-point profile: 0.3 ms through ProfileLayerState.update_profile. 40x40 ROI: 6.6 ms on the sit-and-stare cube and 4.1 ms on the stack.

**Cause.**

Already efficient. StateAttributeLimitsHelper samples 10000 values (glue/core/state_objects.py:334). Per-slice stretch reads only the slice via SliceSubsetState.to_array. PixelSubsetState skips chunking (data.py:1681) and reads only the slice. A pixel-space ROI is evaluated on one 2D slice and broadcast (subset.py:563-581).

**Upstream main.**

Same code on glue origin/main.

**Candidate fix.**

None needed. Minor: the chunked ROI path recomputes the same mask for each of 5 chunks (roi.contains is 5 of the 6.6 ms).

**Gain.**

Negligible; listed so this path is not chased.

**Evidence.**

Logs: gui_ss.log and gui_stack.log (statistics calls during open; slider ticks with stretch_global True and False); bench_profile_ss.log and bench_profile_stack.log (pixel and ROI timings, cProfile).

**Second measurement.** - Quicklook open: 4 minimum, 4 maximum and 8 percentile calls, 4.8-5.0 ms in total.
- Slider tick: statistics take 0 ms with global stretch and 0.48-0.55 ms per slice. The map draw is 18.0-19.0 ms (sit-and-stare) and 24.3-24.4 ms (stack).
- Pixel-point mean profile: compute_statistic under 0.1 ms.
- 40x40 ROI mean profile: 6.5 ms (sit-and-stare), 4.5 ms (stack), of which roi.contains is about 4.8 ms. Percentile with random_subset=10000: 0.1 ms.

**Correction.** - There are 8 percentile calls at open, not 6; the total is still about 5 ms.
- The chunked ROI path calls to_mask twice per chunk: at data.py:1737, and again at data.py:1874 only to get the chunk shape. That makes 10 roi.contains calls per profile, not 5.
- The PixelSubsetState no-chunk check is at data.py:1680.

**Not measured in this area.** - Mg II k 2796, the quicklook's default window (1600x417x555, 2.1x Si IV 1403), was not loaded because it would exceed the 4 GB budget. The full-cube costs above scale roughly linearly with size, so expect about 2x; that is extrapolated, not measured.
- 3602506433 and 3824262996 were not used, and dask or memmap data was not tested (glue-solar loads with memmap=False).
- Timings are offscreen Agg at devicePixelRatio 1. On HiDPI Wayland or X11, the draw portions (spectrum about 9 ms, map about 18-20 ms) will be larger. The worker-polling floor and the compute costs do not depend on the display.
- Context outside this area: in the quicklook, about 230 ms of a point move goes to glue's ImageViewer._on_slice_change, then _set_wcs (glue/viewers/image/viewer.py:96-100, about 117 ms per call), plus WCSAxes tick updates. These run on the slit-jaw and raster viewers when glue-solar's coordinator syncs time. That is the main reason a quicklook point move takes about 250 ms even with a synchronous spectrum; it is left to the draw/WCS investigation.
- Not root-caused: on the stack, changing x_att to Wavelength with the data layer visible ran the whole-cube profile twice on the worker (2 x 82 ms). It is possibly a cache reset from the x_display_unit callback during the first job.
- Worker-thread GIL contention with main-thread drawing was not isolated.
- The fixes were measured as in-process monkeypatches or standalone prototypes; nothing on disk was changed.
- glue-solar's quicklook was measured at 2fdb847, not re-run at origin/main 5eae565 (#86-#88, including the time-wavelength panels).
- Upstream main means origin/main as last fetched locally; nothing was fetched.

### Area: startup

**Setup and baselines.** Startup and import time: python -X importtime for glue, glue_qt and glue_solar; GlueApplication creation; load_plugins with and without glue-solar; first viewer and first draw; observation browser and quicklook on 4000005156. Setup: Apple M4 Pro, macOS, Python 3.13.15, iris-plan env (glue-core 1.27.0, glue-qt 0.4.2, PyQt5 5.15.11, matplotlib 3.11.2, astropy 8.0.1, irispy 0.9.1), offscreen QPA, warm caches (pyc in a scratch PYTHONPYCACHEPREFIX so nothing was written into repos, a warmed MPLCONFIGDIR, warm OS file cache). glue-solar came from /Users/nabil/Git/glue-solar-main at 2fdb847 (merge of #84). That is 3 merges (#86-#88) behind origin/main 5eae565, but every glue-solar file named below is unchanged on origin/main (checked). glue_solar.__file__ = /Users/nabil/Git/glue-solar-main/glue_solar/__init__.py.

BASELINE, phases as glue_qt.main.start_glue runs them (phases.py, n=7, medians). Time to window with glue-solar is 2.442 s (MAD 0.013); without glue-solar it is 1.674 s. The 2.442 s splits as: import glue 1.086 s (44%), splash, which really is the import of glue_qt.app, 0.274 s (11%), load_plugins 0.954 s (39%, of which glue-solar adds 0.78 s), GlueApplication() 0.023 s, show 0.007 s. RSS at the window is 415 MB (327 MB without glue-solar); 4007 modules are loaded (3126 without). First ImageViewer on a 50x400x400 cube: 0.177 s, first draw 17 ms, warm draw 11.8 ms (588x297 canvas, dpr 1). First ProfileViewer: 0.10 s. Every later ImageViewer: 0.140 s with glue-solar, 0.090 s without.

QUICKLOOK on 4000005156 (quicklook_open.py, n=5). Opening the observation browser on /Users/nabil/DATA/IRIS (130 FITS files, 14 observations, recursive) takes 0.979 s. Loading Mg II k 2796 (2 scans of 64x771x560) plus SJI 2796 deconvolved (32x771x1506) takes 0.924 s. The quicklook() call takes 1.848 s, and its last draw lands 2.388 s after the call starts (23 draws, 0.516 s of drawing). Peak RSS is 1.69 GB.

COMBINED what-if (whatif.py stubs, n=7): making all of the import items below lazy together cuts time to window from 2.442 s to 1.528 s with glue-solar (-0.915 s, 37%) and from 1.674 s to 1.004 s without (-0.670 s, 40%).

#### startup#1. glue-solar imports irispy and sunpy.map when the plugin loads (confirmed)

- **Slows:** Launching glue with glue-solar installed (load_plugins at startup, before the window appears)
- **Repository:** glue-solar; **confidence:** high; **share:** 22.5% of time to window (58% of load_plugins). glue-solar adds 0.78 s to load_plugins in total (0.954 s with it, 0.179 s without).

**Cost.**

0.550 s (time to window 2.442 to 1.893 s, median of 7, MAD 0.008; also 49 MB less RSS and 591 fewer modules). With glue-core's dask import also lazy (finding 7), the saving is 0.655 s. Measured by stubbing irispy, irispy.io and sunpy.map in-process and running the real startup (whatif.py lazy_irispy).

**Cause.**

glue_solar/sources/loaders/iris.py:16 runs `from irispy.io import read_files` at import time, and glue_solar/__init__.py pulls it in through tools.py:13 -> quicklook.py:23 -> loaders/iris.py. irispy/__init__ imports irispy.sji, which imports sunpy.map. That brings in reproject (which needs dask and astropy_healpix), sunpy.image.transform -> scipy.signal -> scipy.stats (0.28 s), gwcs (0.18 s), dkist, and sunpy.data -> parfive/aiohttp (0.16 s). glue_solar/sources/maps.py:10-11 also imports sunpy.map, because @qglue_parser(GenericMap) needs the class when the module is imported. None of this is needed until a file is read.

**Upstream main.**

Same on glue-solar origin/main 5eae565: loaders/iris.py:16, maps.py:10 and __init__.py:4 are unchanged.

**Candidate fix.**

Import read_files inside image_data, iris_data and raster_data (scan.py already imports irispy.obsid lazily). Register the sunpy-map qglue parser without importing sunpy.map: duck-type the check, or register only when sunpy.map is already in sys.modules. Keep only sunpy.visualization.colormaps (0.12 s, needed by setup()). Then check that quicklook and tools never touch irispy at import.

**Gain.**

About 0.55 s per launch (time to window 2.44 to 1.89 s), and about 0.65 s together with finding 7. The cost moves to the first IRIS file read, where the user already expects a wait.

**Evidence.**

perf_survey_20261001/startup/whatif_summary.txt (rows none:with and lazy_irispy:with); whatif.py; it_solar_after_app.txt (import tree of glue_solar after glue_qt.app: 0.95 s, of which scipy 0.53 s, aiohttp/urllib3 0.1 s, reproject 0.08 s, gwcs 0.19 s); perplugin.jsonl (glue_solar import 1.06 s as the first entry point).

**Second measurement.** 0.51 to 0.56 s per launch. Time to window went from 2.446 to 1.934 s (n=7, MAD 0.008/0.010) and, in a second interleaved batch, from 2.506 to 1.942 s (n=7). load_plugins went from 0.964 to 0.428 s, with 596 fewer modules and 49 MB less maxrss. Unlike the earlier stubs, these runs applied the real fix in memory: overlay.py reloads glue_solar.sources.loaders.iris with read_files imported lazily and glue_solar.sources.maps with a placeholder GenericMap and sunpy.map imported inside read_sunpy_map. The harness was startup-verify/startup.py, which follows start_glue's sequence: QtWebEngine, get_qapp, splash, load_plugins, GlueApplication, start, resize(1600,1000), 30 processEvents. The glue-solar-main checkout is at 2fdb847 (#84), one merge behind origin/main 5eae565 (#88); the cited lines are the same on both.

**Correction.** The cause list overstates what the fix removes. gwcs (and ndcube) stay loaded: glue_solar/sources/loaders/stack_spectrograms.py:7-8 imports ndcube at module level, through loaders/iris.py:26. ndcube/extra_coords/table_coord.py:11 imports gwcs, and gwcs/wcs/_wcs.py:25 imports scipy.optimize. I checked sys.modules with the fix applied. irispy, sunpy.map, reproject, dkist, aiohttp/parfive, scipy.signal/stats and astropy_healpix are gone; gwcs, ndcube and scipy.optimize remain. Also deferring the ndcube import inside stack_spectrogram_sequence saves another 0.075 s (1.942 to 1.868 s, n=7) and removes gwcs. That deferral is also needed before finding 6 saves anything with glue-solar installed. Evidence: startup-verify/runs.jsonl, runs2.jsonl, overlay.py, who_imports.py, which_mods.py.

#### startup#2. Each WCSAxes axis label set recomputes ticks, and glue sets labels 16 times per new image viewer (confirmed)

- **Slows:** Opening the IRIS quicklook (5 viewers); creating any image viewer; also any state change that resets the WCS (x_att, y_att, slices, reference_data)
- **Repository:** astropy, glue-core; **confidence:** high; **share:** Labels are 38% of the quicklook call (25% of time to last draw) and 30% of a plain image viewer's creation.

**Cost.**

Quicklook call on 4000005156: 42 set_xlabel + 42 set_ylabel calls take 0.714 s, and _update_tick_and_label_positions runs 95 times for 0.813 s, with 3888 IRIS WCS pixel_to_world calls (0.549 s). Measured with main-thread perf_counter wrappers, n=3. Plain 50x400x400 cube, per viewer (median of viewers 2-11): 8+8 label calls take 33 ms of 111 ms, with 17 tick recomputations and 5 _set_wcs calls. What-if (setting a label no longer recomputes ticks): quicklook call 1.858 to 1.258 s, last draw 2.364 to 1.771 s (n=3); draw time rises only 0.07 s.

**Cause.**

astropy/visualization/wcsaxes/core.py:596-598 and 613-615 (installed): set_xlabel and set_ylabel each call self._update_tick_and_label_positions(), which samples the frame through the WCS. glue/viewers/image/viewer.py:100-125 _set_wcs sets x_axislabel and y_axislabel to '' and then _update_axes (lines 74-81) sets them to the world labels. Each set fires update_x_axislabel or update_y_axislabel (glue/viewers/matplotlib/viewer.py:152-162), which calls set_*label. _set_wcs runs about 5 times per viewer: from add_data and from the x_att, y_att, slices and reference_data callbacks (viewer.py:47-54, 89). The IRIS WCSes (gWCS/dkist models behind glue-solar's _GlueWCS and its lock) make each recomputation expensive.

**Upstream main.**

Still present. astropy origin/main 1f930be7c4 calls _update_tick_and_label_positions in set_xlabel/set_ylabel (core.py:685, 715). glue origin/main dae530c3 still clears and resets both labels in _set_wcs (viewer.py:120-121) with the same update_*_axislabel.

**Candidate fix.**

astropy: mark ticks stale in set_xlabel/set_ylabel and recompute once in draw(). glue-core: in _set_wcs, set the final labels directly instead of '' then label, and wrap the reset in delay_callback for the label properties. Do not rerun _set_wcs for x_att, y_att, slices and reference_data changes made in one state update; coalesce them.

**Gain.**

About 0.6 s per quicklook open (25-32%) and about 30 ms per plain image viewer. More for SJI/AIA WCSes, which are slower to evaluate.

**Evidence.**

quicklook_instrumented.jsonl; quicklook_whatif.jsonl (none vs whatif_labels); viewer_parts.jsonl; prof/quicklook-quicklook_call.pstats; all under perf_survey_20261001/startup/

**Second measurement.** Quicklook on 4000005156: both Mg II k 2796 scans loaded with raster_data(windows=[...]) and the deconvolved SJI 2796 with image_data, app at 1600x1000, n=3 fresh processes, medians. The quicklook call took 1.908 s. In it, 42 set_xlabel + 42 set_ylabel calls took 0.766 s (40%), and 95 _update_tick_and_label_positions calls took 0.864 s. In the what-if, setting a label skips the tick update: the call drops to 1.293 s (-0.615 s), the last draw moves from 2.459 to 1.847 s (-0.612 s), and total draw time rises by only 0.07 s. One tick recomputation on its own (median of 15) costs 5.8 ms on the map, 7.1 ms on the spectrogram and 16 ms on the SJI, against about 2 ms on a plain cube. Plain 50x400x400 cube, median of viewers 2-11, 3 runs: 8+8 label calls take 34 ms and 17 tick recomputations take 36 ms per viewer. The what-if saves 35-36 ms: 0.089 to 0.054 s per viewer without glue-solar (0.112 to 0.075 s including settle, 30-39%), and 0.145 to 0.108 s with glue-solar. cProfile shows every set_xlabel/set_ylabel call comes from glue's update_x/y_axislabel, with 5 _set_wcs calls per viewer.

**Correction.** The cause holds. Two refinements. (1) The astropy fix cannot just mark ticks stale. set_xlabel picks which coord gets the label from the visible axes that the tick update assigns (core.py:604-611), so the pending label has to be stored and applied at draw time. The what-if is an upper bound. (2) glue_qt's ImageViewer re-wraps every method through decorate_all_methods(defer_draw) (glue_qt/viewers/image/data_viewer.py:24). Instrumenting MatplotlibImageMixin._set_wcs therefore sees no calls; count them on glue_qt's ImageViewer or with cProfile. Evidence: startup-verify/labels.jsonl, viewers.jsonl, label_callers.py.

#### startup#3. Observation browser and File->Open decompress whole .fits.gz files just to read a header (confirmed)

- **Slows:** Opening Plugins -> IRIS: browse observations (and every rescan: toggling 'Search subfolders', after extraction); File -> Open of a gzipped SJI or AIA file
- **Repository:** glue-solar, glue-core, astropy; **confidence:** high; **share:** About 89% of the browser open time; 100% of the File->Open identification step (0.17-0.39 s per gz file, before the read itself).

**Cost.**

Browser open on /Users/nabil/DATA/IRIS: 0.979 s (n=5), of which scan_directory takes 1.04 s standalone. fits.getheader over the 130 files takes 0.956 s; reading only the primary header takes 0.089 s, with identical headers (n=5). The 7 .fits.gz files alone: 0.890 s vs 0.002 s. File->Open identification (find_factory, before any reading, n=5): 0.388 s for SJI 1400 4000255147 (67 MB gz) and 0.168 s for SJI 2796 deconvolved. glue's own is_fits costs the same.

**Cause.**

astropy/io/fits/hdu/base.py:364 (installed): after parsing an HDU header, `fileobj.seek(hdu._data_offset + hdu._data_size)` moves to the next HDU. On a gzip stream that decompresses the whole primary data array, even for getheader(ext=0), because HDUList._readfrom always reads the first HDU (hdulist.py:1263). Callers: glue_solar/sources/loaders/scan.py:154 (fits.getheader per file), glue_solar/sources/iris.py:21 (is_iris_fits identifier) and glue/core/data_factories/fits.py:35 (is_fits opens the file with fits.open).

**Upstream main.**

Same on astropy origin/main (base.py:364), glue origin/main (fits.py: fits.open in is_fits) and glue-solar origin/main (scan.py:154, iris.py:21).

**Candidate fix.**

glue-solar: read only the primary header, e.g. `fits.Header.fromfile(gzip.open(p, 'rb') if gz else open(p, 'rb'))`, in scan_directory and is_iris_fits. glue-core: is_fits already checks 'SIMPLE  ='; parsing the header blocks is enough, without fits.open. astropy: defer the seek past the data until the next HDU is requested.

**Gain.**

About 0.87 s per browser open or rescan (0.98 to about 0.1 s). 0.17-0.39 s per gzipped SJI or AIA file opened through File->Open.

**Evidence.**

headers.py output: '130 files (7 gz): getheader 0.956s, primary_header 0.089s; gz only: 0.890s vs 0.002s; same headers: True'; identify.py output; prof/quicklook-scan_directory_all.pstats (zlib decompress 0.835 s of 1.247 s, called from base.py readfrom seek); quicklook_runs.jsonl; all under perf_survey_20261001/startup/

**Second measurement.** Over the 130 FITS files (7 gz), n=5: fits.getheader took 0.965 s and a primary-header-only read 0.096 s, with identical headers. The 7 gz files alone took 0.892 s against 0.002 s. A cProfile of getheader on the 67.6 MB SJI 1400 gz (129.6 MB raw) puts 0.403 of 0.404 s in GzipFile.seek, called through _File.seek from BaseHDU.readfrom (base.py:364). Browser open (QtIRISImporter constructed and shown, QSettings redirected to an ini file, n=5 alternating) went from 0.983 to 0.179 s once primary-header reads replaced scan.fits.getheader in-process. That saves 0.80 s, about 82% of the open; scan_directory alone went from 0.979 to 0.108 s, with the same 14 observations. find_factory took 0.388 s on SJI 1400 4000255147 and 0.164 s on SJI 2796 deconvolved, both equal to is_iris_fits alone; the other SJI 2832 gz files took 0.05-0.14 s.

**Correction.** For IRIS files only glue-solar's is_iris_fits runs during identification. Its priority-200 match ends find_factory's loop before glue's is_fits (priority 100). glue-core's is_fits only matters for non-IRIS gzipped FITS, where it adds a second full decompression after is_iris_fits fails. All the AIA cutouts in /Users/nabil/DATA/IRIS are uncompressed .fits, so the gzipped-AIA case is unmeasured here. The expected browser gain is about 0.80 s rather than 0.87 s. Evidence: startup-verify/headers.out, headers.py, browser.py.

#### startup#4. glue imports IPython, ipykernel and qtconsole at startup though the terminal opens only on click (confirmed)

- **Slows:** Launching glue (with or without glue-solar)
- **Repository:** glue-core, glue-qt; **confidence:** high; **share:** 6.8% of time to window with glue-solar, 9.9% without.

**Cost.**

0.167 s with glue-solar (2.442 to 2.275 s, n=7, MAD 0.010) and 0.165 s without (1.674 to 1.509 s); 565-574 fewer modules and about 28-30 MB less RSS. Making only the terminal module lazy saves 0.045 s (noisy, MAD 0.039). The splash phase drops from 0.274 to 0.122 s.

**Cause.**

glue/viewers/common/viewer.py:4 runs `from IPython import get_ipython`, used only in Viewer.cleanup (line 429). glue_qt/app/application.py:39 imports glue_qt.app.terminal at module level; terminal.py:18-28 imports IPython.core, ipykernel.inprocess, ipykernel.connect and qtconsole (jupyter_client and zmq come with them). The terminal widget is only built in GlueApplication._create_terminal (application.py:1149-1166). In importtime, IPython is 0.10 s and glue_qt.app.terminal 0.059 s.

**Upstream main.**

Same on glue origin/main (viewer.py:4) and glue-qt origin/main (application.py:39).

**Candidate fix.**

glue-core: in cleanup, use `shell = sys.modules.get('IPython') and sys.modules['IPython'].get_ipython()`, since no shell can exist if IPython was never imported. glue-qt: import glue_terminal and IPythonTerminalError inside _create_terminal. Note that matplotlib checks sys.modules['IPython'] too (pyplot.py:321, backend_bases.py:1799), so not importing IPython also stops matplotlib's REPL-hook probing.

**Gain.**

About 0.17 s per launch. The terminal's import cost (about 0.15 s) moves to the first click of the IPython button.

**Evidence.**

perf_survey_20261001/startup/whatif_summary.txt (lazy_terminal, lazy_ipython rows); it_app_1..3.txt (IPython 98-106 ms, glue_qt.app.terminal 55-59 ms under glue_qt.app); prof/with-splash.pstats

**Second measurement.** With the complete fix applied in memory (overlay ipy_full): 0.154 s with glue-solar (2.446 to 2.291 s, n=7, MAD 0.016) and 0.155 s without it (1.679 to 1.524 s, n=7). IPython, qtconsole and zmq are no longer imported, 568-597 fewer modules load and maxrss drops 28 MB. The fix exactly as the finding describes it (viewer.py cleanup checks sys.modules; the terminal is imported inside _create_terminal) saves only 0.072 s (2.446 to 2.374 s, n=7). IPython is still imported in that case, and the start/show phase rises from 0.030 to 0.120 s.

**Correction.** The fix misses a third import site. GlueApplication.start() calls _fix_ipython_pylab() (glue_qt/app/application.py:1222), which runs `from IPython import get_ipython` (application.py:50-51) on every launch. With only the two changes the finding proposes, the IPython import moves from the splash phase to start() and less than half of the saving appears. _fix_ipython_pylab also has to return early when 'IPython' is not in sys.modules. Then the measured 0.155 s matches the claimed 0.165-0.167 s. Upstream glue-qt origin/main 9780eaf9 still has the same code at lines 48-51 and 1222. Evidence: startup-verify/runs.jsonl (ipy_written vs ipy_full rows), overlay.py.

#### startup#5. Colormap combo draws an icon for every colormap at creation and on every resize, once per image layer (confirmed)

- **Slows:** Creating an image viewer or adding a dataset to one (each data layer gets a style editor); resizing; opening the quicklook
- **Repository:** glue-qt; **confidence:** high; **share:** About 30% of a new image viewer's creation with glue-solar; 13% of the quicklook call.

**Cost.**

With glue-solar's 102 colormaps: building a QColormapCombo takes 27.4 ms and each width change rebuilds the icons in another 27.4 ms. With glue's 15 colormaps both take 4.1 ms (n=15 per run, 3 runs; cmap2pixmap is 0.26 ms each). Per new image viewer: 158 ms with glue-solar vs 111 ms without; _update_icons takes 54.8 vs 8.5 ms (median of viewers 2-11). Quicklook call: 8 _update_icons calls, 0.247 s. What-if with icons cached per (colormap, size): quicklook call 1.858 to 1.716 s (n=3).

**Cause.**

glue_qt/utils/colors.py:190-219: QColormapCombo.__init__ adds every config.colormaps entry and calls _update_icons, which runs cmap2pixmap (ScalarMappable plus QImage, steps=200) for every item. resizeEvent calls _update_icons again on every resize, with no cache. glue_qt/core/layer_artist_model.py:357-373 (LayerArtistWidget.on_artist_add) builds the layer style editor eagerly for every layer artist; the image one (layer_style_editor.ui:95) contains the combo. glue-solar setup() registers about 87 sunpy colormaps on top of glue's 15.

**Upstream main.**

Same on glue-qt origin/main 9780eaf9 (colors.py identical to 0.4.2; on_artist_add at layer_artist_model.py:357).

**Candidate fix.**

Cache pixmaps per (cmap name, width, steps) at module level. Build the icons lazily, in showPopup or through an item delegate that paints only the visible rows. In resizeEvent, rebuild only when the width actually changed. Optionally build the style editors in on_selection_change rather than on_artist_add.

**Gain.**

About 45 ms per image viewer or dataset added with glue-solar installed, about 27 ms per combo per resize, and about 0.25 s per quicklook open with lazy icons (0.14 s with caching alone).

**Evidence.**

cmap_combo.jsonl; viewer_parts.jsonl; quicklook_instrumented.jsonl; quicklook_whatif.jsonl (whatif_cmapcache); phases_runs.jsonl (second_image_viewer 0.139 vs 0.088 s); all under perf_survey_20261001/startup/

**Second measurement.** With glue-solar's 102 colormaps, building a QColormapCombo takes 28.3-30.1 ms and one width change takes 27.9-29.9 ms. With glue's 15 colormaps both take 4.2-4.4 ms (n=15 per run, 3 runs); cmap2pixmap costs 0.27 ms. Per new image viewer (plain cube, median of viewers 2-11, 3 runs): new_data_viewer takes 0.145 s with glue-solar and 0.089 s without (0.168 vs 0.112 s including settle). _update_icons runs twice per viewer (construction and one resize) and takes 57 ms with glue-solar vs 8.5 ms without. With pixmaps cached per (cmap, steps, size), a viewer takes 0.085 s (-60 ms, about 40%). Quicklook on 4000005156 (n=3): 8 _update_icons calls take 0.241 s, 12.6% of the 1.908 s call. The cache what-if brings the call to 1.737 s (-0.17 s; the finding claimed 0.14 s).

**Correction.** No correction needed. The extra cost with glue-solar is 56 ms per viewer here, against the claimed 45 ms. The per-combo resize cost was measured on a shown combo. I did not count how many resize events hidden layer-style editors receive during a window resize. Evidence: startup-verify/viewers.jsonl, labels.jsonl.

#### startup#6. The WCS autolinking plugin imports scipy.optimize at plugin load (confirmed)

- **Slows:** Launching glue
- **Repository:** glue-core; **confidence:** high; **share:** 10.9% of time to window without glue-solar; about 90% of load_plugins without glue-solar.

**Cost.**

Without glue-solar: 0.182 s (1.674 to 1.492 s, n=7, MAD 0.011); load_plugins drops from 0.179 to 0.019 s. With glue-solar today: no saving (-0.007 s), because sunpy and irispy import scipy.optimize anyway. Once finding 1 is fixed the cost reappears; it is part of the 0.26 s that stubbing IPython, autolinking and QtQuick saves on top of lazy irispy plus no dask (1.788 to 1.528 s).

**Cause.**

glue/plugins/wcs_autolinking/wcs_autolinking.py:6 runs `from scipy.optimize import leastsq` at module level. The plugin's setup() imports the module at startup, but leastsq is used only in two functions (lines 287 and 302) when an autolink is computed.

**Upstream main.**

Same on glue origin/main (wcs_autolinking.py:6).

**Candidate fix.**

Import leastsq inside the two functions that call it.

**Gain.**

About 0.16-0.18 s per launch without glue-solar, and with glue-solar once glue-solar defers irispy.

**Evidence.**

perf_survey_20261001/startup/whatif_summary.txt (lazy_wcs_autolinking rows); prof/without-load_plugins.pstats (wcs_autolinking module 0.182 of 0.218 s profiled)

**Second measurement.** Without glue-solar the saving is 0.169 s: time to window goes from 1.679 to 1.510 s (n=7, MAD 0.011) and load_plugins from 0.177 to 0.022 s. This applied the real fix in memory: leastsq imported inside the two methods of glue/plugins/wcs_autolinking/wcs_autolinking.py. With glue-solar as it is now, the saving is nothing (-0.038 s). With glue-solar's finding-1 fix also applied, there is still no saving (1.944 s with the autolinking fix vs 1.934 s without it, n=7). It returns only once glue-solar also defers ndcube: 1.868 to 1.696 s (-0.171 s, n=7).

**Correction.** The claim that the cost reappears once finding 1 is fixed is wrong. Even with irispy and sunpy.map deferred, glue_solar/sources/loaders/stack_spectrograms.py:7 imports ndcube at module level. ndcube/extra_coords/table_coord.py:11 imports gwcs, and gwcs/wcs/_wcs.py:25 imports scipy.optimize. So glue-core's fix saves about 0.17 s with glue-solar installed only once glue-solar defers both irispy and ndcube. The cause in glue-core and the 0.17 s figure without glue-solar hold. Evidence: startup-verify/runs.jsonl, runs2.jsonl, who_imports.py.

#### startup#7. glue imports dask.array (an optional dependency) at import time just for isinstance checks (not re-measured)

- **Slows:** Launching glue; `import glue`
- **Repository:** glue-core; **confidence:** medium; **share:** 8.1% of time to window without glue-solar; 4.3% with glue-solar after finding 1.

**Cost.**

Without glue-solar: 0.136 s (1.674 to 1.538 s, n=7, MAD 0.006); import glue 1.10 to 0.77 s, part of which moves later. With glue-solar today: none, because reproject (imported by sunpy.map) requires dask. With glue-solar's irispy made lazy: a further 0.105 s (1.893 to 1.788 s). In importtime, dask.array is 0.30 s cumulative, pulling scipy.fft/fftpack through dask.array.fft.

**Cause.**

glue/utils/array.py:10-14, glue/core/data.py:42 and glue/core/component.py:11 import dask.array at module level (inside try/except ImportError). It is used only for isinstance(x, da.Array) checks and the random_views_for_dask_array helper.

**Upstream main.**

Same on glue origin/main (utils/array.py:10-14).

**Candidate fix.**

Check `'dask.array' in sys.modules and isinstance(x, sys.modules['dask.array'].Array)`: an array cannot be a dask array if dask was never imported. Import dask.array inside the functions that build dask arrays.

**Gain.**

0.10-0.14 s per launch (only for IRIS users once sunpy.map is no longer imported at startup).

**Evidence.**

perf_survey_20261001/startup/whatif_summary.txt (no_dask:without; lazy_irispy,no_dask:with; no_dask:with failed to load glue_solar, the traceback pointing at reproject/_common.py:6); imports_warm.log (glue.utils.array 0.62 s cumulative: pandas 0.31 + dask.array 0.30)

#### startup#8. `import glue` imports glue_qt, and through it all of glue.core (not re-measured)

- **Slows:** `import glue` or `import glue.config` from non-Qt code (scripts, glue-jupyter or jdaviz with glue-qt installed)
- **Repository:** glue-core; **confidence:** high; **share:** 25% of `import glue`; 0% of the Qt app's time to window.

**Cost.**

import glue: 1.112 s vs 0.831 s with glue_qt blocked (n=7, in-process perf_counter), 501 more modules. Under -X importtime: 1.231 vs 0.949 s (n=9). No saving for the Qt application, which imports glue_qt anyway.

**Cause.**

glue/config.py:949-958 runs `from glue_qt.config import ...` as a backwards-compatible re-export. That executes glue_qt/__init__.py -> qglue -> glue.core, with all data factories, astropy.table/coordinates/wcs, glue.core.parsers and matplotlib.axes.

**Upstream main.**

Same on glue origin/main.

**Candidate fix.**

Provide the re-exports through a module-level __getattr__ (PEP 562) on glue.config that imports glue_qt.config on first access, with a DeprecationWarning.

**Gain.**

About 0.28 s for non-Qt users of glue-core; none for the IRIS Qt workflow.

**Evidence.**

perf_survey_20261001/startup/imports_warm.log (glue vs glue_without_glue_qt; glue_qt.config 0.252 s under glue.config)

#### startup#9. The splash screen appears only after glue and the whole Qt app are imported (not re-measured)

- **Slows:** Launching glue: when the user first sees anything
- **Repository:** glue-qt; **confidence:** medium; **share:** About 56% of time to window passes with nothing on screen. Only perceived latency; the total does not change.

**Cost.**

The splash shows about 1.36 s after start (import glue 1.086 s plus the splash phase 0.274 s, which is almost entirely the import of glue_qt.app); the window shows at 2.44 s. With finding 4 fixed, the splash phase drops to 0.12 s. Measured from phases.py, n=7.

**Cause.**

glue_qt/main.py:207-211 get_splash imports glue_qt.app.splash_screen. glue_qt/app/__init__.py:1-2 imports application (all viewers and the terminal) before the splash module runs. glue_qt/main.py:6-8 also imports glue (1.09 s) before anything can be shown.

**Upstream main.**

Same on glue-qt origin/main (app/__init__.py and main.py unchanged).

**Candidate fix.**

Move QtSplashScreen into a module outside the glue_qt.app package, or make glue_qt/app/__init__.py lazy with __getattr__. In glue_qt.main, create the QApplication and the splash before importing glue.

**Gain.**

The splash appears about 0.27 s earlier (more if glue's import is deferred too); no change to time to window.

**Evidence.**

perf_survey_20261001/startup/prof/with-splash.pstats (glue_qt/app/__init__ 0.372 of 0.453 s profiled; QtSplashScreen.__init__ 0.058 s); phases_runs.jsonl

#### startup#10. Small glue-qt one-off costs: QtQuick imported on Qt5, and QFont('Courier') on macOS (not re-measured)

- **Slows:** Launching glue (QtQuick); opening the first Profile viewer (Courier)
- **Repository:** glue-qt; **confidence:** medium; **share:** 1.4% of time to window; about 50 ms of the first profile viewer.

**Cost.**

Not importing qtpy.QtQuick: 0.035 s off time to window (n=7, MAD 0.020); in importtime it is 31 ms (QtQuick, QtQml and QtNetwork). QFont('Courier') as the fit-log font: 54.6 ms on first use vs 2.6 ms for QFontDatabase.systemFont(FixedFont) (n=5 fresh processes). Qt itself logs 'Populating font family aliases took 40-48 ms. Replace uses of missing font family "Courier"'.

**Cause.**

glue_qt/utils/app.py:3 imports QtQuick unconditionally, but uses it only under QT6 at line 54. glue_qt/viewers/profile/profile_tools.py:112 calls QtGui.QFont('Courier'), a family macOS lacks, which makes Qt build its alias table.

**Upstream main.**

Same on glue-qt origin/main (utils/app.py:3, profile_tools.py:112).

**Candidate fix.**

Import QtQuick inside the `if QT6:` branch of get_qapp. Use QFontDatabase.systemFont(QFontDatabase.FixedFont) for the log font.

**Gain.**

About 35 ms per launch on Qt5 (none on Qt6) and about 50 ms on the first profile viewer on macOS. Linux not measured.

**Evidence.**

perf_survey_20261001/startup/whatif_summary.txt (no_qtquick); it_app_2.txt (qtpy.QtQuick 31.7 ms under glue_qt.utils.app); courier.py output; ql_trial.err

#### startup#11. First launch rebuilds matplotlib's font cache inside `import glue`, with no splash (not re-measured)

- **Slows:** The first launch after installing or upgrading matplotlib, or any launch where MPLCONFIGDIR/~/.cache/matplotlib is missing or not writable
- **Repository:** matplotlib, glue-qt; **confidence:** medium; **share:** About 87% of `import glue` on such launches; 0% on normal launches.

**Cost.**

import glue: 9.345 s with an empty matplotlib cache vs 1.231 s warm (n=7 each, -X importtime); matplotlib.font_manager self time is 8.28 s.

**Cause.**

glue imports matplotlib.axes eagerly (glue.core.util -> matplotlib.projections -> axes -> offsetbox -> text -> font_manager), and font_manager rebuilds fontlist JSON by scanning every system font. glue starts this before the QApplication or the splash exists (finding 9), so the user sees nothing for about 10 s.

**Upstream main.**

glue and glue-qt import order unchanged on main; the rebuild is matplotlib's own behaviour.

**Candidate fix.**

glue-qt: show the splash (or a 'building font cache' message) before importing glue and matplotlib. matplotlib: nothing glue-specific. Docs: tell packagers and installers to warm the cache.

**Gain.**

No time saved. The wait becomes visible instead of looking like a hung launch.

**Evidence.**

perf_survey_20261001/startup/imports.log (fresh HOME, no MPLCONFIGDIR) vs imports_warm.log

**Not measured in this area.** Not measured:
- Real screen timings. Everything ran on offscreen QPA with Agg at dpr 1 on macOS, so Wayland/X11 at dpr 2 (where the user's Linux machine measured 0.068 s vs 0.028 s per slider tick) will differ, mostly in the draw and resize numbers. Window maximize and first paint on a real compositor were not measured.
- Cold starts. All timings use warm caches; the first launch after a reboot was not measured.
- Qt6. The QtQuick item applies to Qt5 only. Linux font behaviour (Courier aliasing, size of the font cache rebuild) was not measured.
- How firm the gains are. The what-if savings come from in-process stubs (whatif.py) that skip the deferred modules entirely, so they are upper bounds. Deferred costs move to first use: the terminal's about 0.15 s goes to the first IPython-button click, and in the combined no-glue-solar scenario the first profile viewer went from 0.127 to 0.198 s.
- Colormap combo resizes in a real session. Only synthetic widget resizes were timed, not how many combo resizes a main-window resize actually triggers.
- Profiler caveat. In Python 3.13, cProfile also records worker-thread work (glue computes profiles and histograms on threads), so shares come from main-thread perf_counter wrappers, not from pstats.
- Out of scope, seen but not pursued (IO area): irispy's SJI reader decompresses the .gz SJI a second time when it reaches HDU1 after reading the data (irispy/io/sji.py _t_obs; the gzip seek costs about 0.35-0.5 s of the 0.84 s SJI 2796 load).
- Minor items under about 25 ms:
  - entry_points(group='glue.plugins') takes 4.9 ms per call and runs 4 times per launch, because load_plugins is called by both start_glue and GlueApplication.__init__. plugins.cfg is rewritten each time; upstream main now skips that write when nothing changed.
  - astropy.visualization.wcsaxes imports pytest at runtime when pytest is installed (21 ms).
  - start_glue's failed QtWebEngineWidgets import takes 19 ms.
- Correctness aside, not performance: glue/main.py:59-77 load_plugins(plugins_to_load=[...]) still imports and sets up plugins that are not in the list, because the try block sits outside the `if item.module in plugins_to_load` check. The same code is on main.

Scripts and logs are in perf_survey_20261001/startup/. Nothing was changed in any repo.

### Area: draw

**Setup and baselines.** Image viewer draw path in the IRIS quicklook. Versions: glue-core 1.27.0, glue-qt 0.4.2, astropy 8.0.1, matplotlib 3.11.2, mpl-scatter-density 0.8. glue-solar-main is at 2fdb847 (Merge #84), 3 merges behind glue-solar origin/main 5eae565 (#86-#88); the key results were re-run on a read-only git-archive export of 5eae565. Setup: offscreen Qt, app 1600x1000, quicklook panels 402x327 px (SJI 609x327), DPR1 and DPR2 (QT_SCALE_FACTOR=2). Medians of 15 steps after 2 warm-ups, or 30 static redraws. Timing comes from perf_counter wrappers on the draw-path boundaries; cProfile was used only to see structure (it inflated times about 4.6x).

Baselines at DPR1:
- Case A (4000255147, Si IV 1403 + SJI 1400):
  - Spectrogram exposure step: 203 ms. Of that, the sync set phase is 38 ms and 7 canvas draws are 148 ms (map 18, spectrogram 24, λ-time 35, SJI 2x28, spectrum 2x16).
  - λ-time slit step: 212 ms. Slit-vs-time wavelength step: 35 ms.
  - SJI frame step: 105 ms (set 76 + draw 28).
  - Pan drag: 23 ms per motion event. Contrast/bias: 18 ms per event (map), 31 ms (SJI).
  - At DPR2: exposure step 241 ms, SJI frame step 110 ms.
- Case B (4000005156 stack 2x64x771x536 + deconvolved SJI 2796): raster step 244 ms, SJI frame step 108 ms.

Per-draw split at quicklook size:
- WCSAxes ticks, labels and frame: 74-88% of each draw (37-59 pixel_to_world_values calls per draw; 434 per exposure step).
- Image artists: 11-22%. Within that:
  - glue's fixed-resolution buffer: 0.2-0.3 ms on a cache miss, about 0 on a hit.
  - CompositeArray colormap/stretch: 0.6-1.2 ms.
  - mpl-scatter-density/matplotlib resample: 1.9-2.4 ms.
  - Point mask: 0.5-2.5 ms.
- Rest of matplotlib: under 1 ms. Qt paint: 0.2-0.3 ms.
- The fixed-resolution buffer is not a bottleneck: 2-5.5 ms even on a maximized viewer.

Maximized viewers (1258x810): the image path is 46-58% (SJI) and 65-71% (spectrogram) of 54-134 ms draws, mostly matplotlib's resample.

Redraw count: glue's defer_draw plus Qt draw_idle coalescing give one draw per affected canvas per change. The exceptions are hidden subset layers (finding 3), glue-solar's coordinator timer (finding 8), and the profile viewer's two draws per point move.

Combined what-if of findings 1+2+3, with tick texts, positions and axis labels identical to baseline:
- A at DPR1: exposure step 203 -> 131 ms, SJI frame step 105 -> 32 ms.
- A at DPR2: 241 -> 161 ms and 110 -> 39 ms.
- B: raster step 244 -> 147 ms, SJI 2796 frame step 108 -> 34 ms.

Scripts and logs are in perf_survey_20261001/draw/.

#### draw#1. A slider step re-runs glue's _set_wcs: reset_wcs plus four axis-label sets, each of which recomputes every WCSAxes tick (confirmed)

- **Slows:** Stepping a slider whose axis the displayed coordinates depend on. That covers the SJI frame (pointing changes with time), the sit-and-stare spectrogram exposure step, the λ-time slit step and the stack raster step. It does not cover the slit-vs-time wavelength step.
- **Repository:** glue-core (astropy for the eager set_xlabel/set_ylabel); **confidence:** high; **share:** About 70% of an SJI frame step. 15-22% of raster slider steps (32% for the λ-time slit step on glue-solar main).

**Cost.**

Measured with perf_counter boundary wrappers, n=15 steps after 2 warm-ups, medians, DPR1.
- SJI 1400 frame step (A): set phase 75.6 ms of a 104.7 ms total (DPR2: 74 of 110 ms).
- SJI 2796 deconvolved (B): glue._set_wcs takes 70.1 ms of 108.4 ms. It splits into reset_wcs 0.6 ms, 2x set_xlabel 32.5 ms and 2x set_ylabel 32.3 ms. 140 of the step's 177 pixel_to_world_values calls happen here, outside the draw.
- Spectrogram exposure step (A): set 38 ms of 203 ms.
- Stack raster step (B): _set_wcs 42.6 ms of 244 ms.
- λ-time slit step (A): set 47 ms of 212 ms. On glue-solar origin/main 5eae565 it is 76 ms of 238 ms, because #87 re-labels again after every glue reset.

**Cause.**

1. glue/viewers/image/viewer.py:96-98 `_on_slice_change` calls `_set_wcs(relim=False)` (viewer.py:100-150) whenever `_changing_slice_requires_wcs_update` is true.
2. `_set_wcs` calls `axes.reset_wcs` (a new CoordinatesMap). It then sets `state.x_axislabel` and `y_axislabel` to '' (lines 120-121), and `_update_axes` (124 -> 74-82) sets them back. It also calls `update_x/y_ticklabel` (126-127).
3. Each label change goes to astropy `WCSAxes.set_xlabel`/`set_ylabel` (astropy/visualization/wcsaxes/core.py:596-598 and 613-615). Each of those runs `_update_tick_and_label_positions()` (core.py:490-515), a full tick computation for all coordinates, before the draw computes the ticks once more.
4. glue-qt's ImageViewer copies these methods through `decorate_all_methods(defer_draw)` (glue_qt/viewers/matplotlib/data_viewer.py:17).

**Upstream main.**

glue origin/main dae530c3, the same as GitHub main (checked with ls-remote): viewer.py is identical. astropy local origin/main 6d36964 (2026-09-07; GitHub main is ahead of it): set_xlabel and set_ylabel still call `_update_tick_and_label_positions()`.

**Candidate fix.**

glue: on a slice change, update only the slice of the WCS view WCSAxes already holds, then request a draw. Two ways to do that: keep a glue-owned sliced low-level WCS and update its fixed pixel indices in place, or add an astropy call that changes the slices without rebuilding coords. Labels and appearance stay as they are. The minimum change is to drop the '' -> label round-trip.
astropy: make set_xlabel/set_ylabel attach the label at draw time instead of computing ticks eagerly.

**Gain.**

Runtime what-if (variant inplace): instead of calling _set_wcs, mutate the slice of the existing SlicedLowLevelWCS.
- SJI frame step: 105.1 -> 39.0 ms (A), 107.7 -> 43.2 ms (B).
- Spectrogram exposure step: 203.4 -> 170.4 ms.
- λ-time slit step: 212.5 -> 172.0 ms (237.5 -> 170.1 ms on glue-solar 5eae565).
- Stack raster step: 244.1 -> 194.7 ms.
Tick texts, tick data positions and axis labels match the baseline in 15/15 steps of all 7 actions. They change at every baseline step, so the comparison does detect a stale slice.

**Evidence.**

In perf_survey_20261001/draw/:
- whatif.py (variant inplace), compare_prints.py
- whatif_A_base_dpr1.log, whatif_A_inplace_dpr1.log
- whatif_B_base_dpr1.log, whatif_B_inplace_dpr1.log
- whatif_A_base_dpr1_gs5eae565.log, whatif_A_inplace_dpr1_gs5eae565.log
- quicklook_steps_B_dpr1.log (glue._set_wcs, set_xlabel and reset_wcs lines)
- why_draws_A.log (draw requests from viewer.py:98 -> _set_wcs)

**Second measurement.** Method: perf_counter wrappers that attribute nested calls to their context (draw-verify/h.py, v1.py, v1what.py). DPR1, n=15 after 2 warm-ups, medians. glue-solar-main is at 2fdb847 (#84), three merges behind origin/main 5eae565.
- SJI frame step (A): 103.5-109.0 ms total, set phase 74-79 ms. _set_wcs is 69.2 ms of that: reset_wcs 0.55, 2x set_xlabel 32.0, 2x set_ylabel 31.7. That is four _update_tick_and_label_positions calls. 132 of the step's 177 p2w calls happen inside the label sets, plus 4 directly in _set_wcs.
- SJI frame step (B): 106.3 ms total, _set_wcs 69.1 ms (labels 32.3 + 31.9, reset_wcs 0.57).
- Raster steps: _set_wcs takes 32.4 of 204.6 ms (16%) in the exposure step (A), 40.3 of 214.4 ms (19%) in the λ-time slit step (A) and 41.2 of 233.3 ms (18%) in the stack raster step (B).
- glue-solar 5eae565 (from a git-archive copy), λ-time slit step: set 72.7 ms and _set_wcs 65.5 ms (4 set_ylabel calls) of 229.6 ms.
My own what-if: keep reset_wcs, copy each coord's label with coord.set_axislabel, never call WCSAxes.set_xlabel/set_ylabel.
- SJI step: 109.0 -> 40.2 ms (A), 107.9 -> 41.1 ms (B).
- Exposure step: 216.5 -> 181.4 ms. λ-time slit step: 219.8 -> 184.3 ms. Stack raster step: 238.5 -> 206.2 ms.
- Tick texts, tick positions and axis labels are identical in 15/15 steps of every action, and they change at every step.

**Correction.** Cost, cause and gain hold. Corrections:
1. The in-place slice change is not needed. reset_wcs costs only 0.6 ms; all the cost is the four eager tick computations in WCSAxes.set_xlabel/set_ylabel. Putting the labels on the new coords directly gave the full gain with identical output. Dropping only the ''->label round-trip, while still calling set_xlabel and set_ylabel once each, would save only about half (about 32 ms on the SJI).
2. Medians understate raster steps. In 1 of every 4 exposure steps (A) and raster steps (B), the time sync also moves the SJI frame. That runs a second _set_wcs and adds 70-75 ms (A: 274 vs 200 ms; B: 306 vs 230 ms). The mean exposure step is 219.8 ms against a median of 203.7 ms.
3. The decorator that copies _set_wcs onto the Qt class is at glue_qt/viewers/image/data_viewer.py:24. The cited matplotlib/data_viewer.py:17 is the base viewer's.
4. GitHub glue main has moved on to 77dc9b88 (local origin/main dae530c3 is behind). I fetched the cited glue files from it by raw URL: they are identical. Local astropy origin/main is now 1f930be7c4 (2026-09-28), and its set_xlabel/set_ylabel still compute ticks eagerly.
Not re-measured: the DPR2 numbers.

#### draw#2. WCSAxes evaluates the WCS 37-59 times per draw, mostly the same frame points once per coordinate (confirmed)

- **Slows:** Every draw of an Image viewer with a WCS: slider steps, pan-drag motion events, contrast/bias drags.
- **Repository:** astropy; **confidence:** high; **share:** 74-88% of every quicklook-size draw is WCSAxes. WCS evaluation alone is 55% of an SJI draw, 21-27% of a raster draw and 32% of an exposure step.

**Cost.**

Per draw at quicklook size (DPR1, 30 redraws, medians), WCSAxes ticks, labels and frame take:
- map: 11.3 of 15.3 ms
- spectrogram: 18.8 of 23.0 ms
- λ-time: 29.9 of 34.1 ms
- SJI: 23.5 of 27.6 ms
pixel_to_world_values calls per draw: 43, 53, 59 and 37.
Cost per call:
- SJI gWCS: about 0.35 ms whatever the point count (0.29 ms in irispy's gWCS plus 0.05 ms in glue-solar's wrapper; wcs_calls.log). WCS evaluation is therefore 15.3 ms of the 27.6 ms SJI draw.
- Raster FITS WCS: about 0.06 ms.
One exposure step makes 434 calls (66 ms).
Pan drag, per motion event: draw 21 ms (spectrogram) or 26 ms (SJI), of which draw_wcsaxes is 17.9 or 22.0 ms. mpl-scatter-density does not recompute the buffer during the drag.

**Cause.**

In astropy/visualization/wcsaxes:
1. WCSAxes.draw (core.py:560) calls frame._update_patch_path (frame.py:192), which transforms 4 spines.
2. draw_wcsaxes (core.py:517) calls `_update_tick_and_label_positions`, which runs CoordinateHelper._update_ticks for each coordinate (coordinate_helpers.py:966, marked 'TODO: this method should be optimized for speed').
3. That calls frame.sample (frame.py:224). sample transforms 4 spines in update_spines (frame.py:373), then 4 resampled spines again through the Spine.data setter (frame.py:57-64).
4. shifted_pixel_to_world (coordinate_helpers.py:1023-1027) transforms each spine 2-4 more times.
Each evaluation computes every world axis and keeps one column, so the same points are evaluated again for each of the 2-3 coordinates.

**Upstream main.**

Same structure on astropy origin/main 6d36964 (frame.sample at coordinate_helpers.py:1013, shifted_pixel_to_world at 1041).

**Candidate fix.**

astropy: sample the frame and evaluate the shifted-pixel transforms once per tick update and share the results between coordinates. Memoizing WCSPixel2WorldTransform.transform for the length of one draw or label update would also do it.

**Gain.**

What-if (variant wcscache) that memoizes identical evaluations within one draw or tick update:
- SJI draw: 27.7 -> 20.8 ms (-25%). SJI contrast/bias event: 30.7 -> 24.0 ms.
- SJI frame step, with finding 1 still unfixed: 105 -> 69 ms (A), 108 -> 75 ms (B).
- Spectrogram exposure step: 203 -> 172.5 ms.
- Raster draws: 1.5-3 ms faster.
Tick fingerprints identical in 15/15 steps. The exact shape of the astropy change is less certain than the measured gain.

**Evidence.**

draw_breakdown.py, draw_breakdown_A_dpr1.log and draw_breakdown_A_dpr2.log (per-boundary split, call counts); wcs_calls.py and wcs_calls.log; pan_drag_A_dpr1.log and pan_drag_A_dpr2.log; whatif_A_wcscache_dpr1.log and whatif_B_wcscache_dpr1.log

**Second measurement.** Method: forced canvas.draw at quicklook size, DPR1, n=30 after 3 warm-ups, medians (v1.py, v2.py).
- WCSAxes share of the draw (draw_wcsaxes plus frame patch): map 12.7 of 17.0 ms (75%), spectrogram 20.1 of 24.3 ms (82%), λ-time 29.9 of 34.0 ms (88%), SJI 24.5 of 28.4 ms (86%).
- p2w calls per draw: 43, 53, 59 and 37. Only 20, 17, 20 and 17 of them have distinct inputs.
- p2w time per draw: SJI 15.4 ms (54%), raster 4.0-5.5 ms (16-24%). Of that, repeated inputs take 8.0 ms (SJI) and 2.1-3.6 ms (raster).
- Cost per call: SJI gWCS 0.36-0.41 ms (inner gWCS 0.31-0.36 plus wrapper 0.05), raster FITS WCS 0.06-0.08 ms, B stack CompoundLowLevelWCS 0.09-0.11 ms.
- Exposure step: 435 calls, 65.5 ms (32% of the step).
- Pan event with the images held pressed: spectrogram draw 21.9 ms (draw_wcsaxes 18.4), SJI 26.4 ms (21.9).
Where the 37 calls of one SJI draw come from:
- 8 from the Spine.data setter in sample
- 8 from update_spines in sample
- 16 from shifted_pixel_to_world
- 4 from update_spines in _update_patch_path
- 1 from find_coordinate_range
My own memo what-if (cache in _GlueWCS.pixel_to_world_values, cleared per draw and per tick update):
- SJI draw: 28.1 -> 21.4 ms. SJI contrast event: 31.0 -> 24.9 ms. SJI frame step: 104.9 -> 71.9 ms.
- Exposure step: 205.0 -> 178.5 ms. Raster draws: 1.3-2.6 ms faster.
- Fingerprints identical in 15/15 steps of all 5 actions.

**Correction.** Holds. Minor corrections: WCS evaluation is 16-25% of a raster draw here, not 21-27%, and case B raster calls cost 0.09-0.12 ms each. Local astropy origin/main is now 1f930be7c4 (2026-09-28); the frame.sample and shifted_pixel_to_world code at coordinate_helpers.py:1013 and 1041 is unchanged.

#### draw#3. A hidden subset layer still redraws its viewer every time the subset changes (confirmed)

- **Slows:** Any raster slider step in the quicklook. The Point moves, and the slit-jaw viewer, where the quicklook hides the Point layer, redraws once for nothing before its real time-sync redraw.
- **Repository:** glue-core; **confidence:** high; **share:** 14% of the exposure step (A, 203 ms), 16% of the stack raster step (B, 244 ms), 20% of the stack λ-scan slit step (B, 173 ms).

**Cost.**

One extra SJI draw per raster step: 27-28 ms at DPR1, about 33 ms at DPR2. The SJI draws twice per exposure step (55.5 ms). In the draw-request trace, the first SJI draw is requested only by glue/viewers/image/layer_artist.py:357 and :396, from the hub's subset broadcast.

**Cause.**

glue/viewers/common/viewer.py:309-314 `_update_subset` calls update() on every layer artist of the subset. ImageSubsetLayerArtist.update (glue/viewers/image/layer_artist.py:390-396) and `_update_visual_attributes` (337-357) both call self.redraw() (glue/viewers/matplotlib/layer_artist.py:73-74 -> canvas.draw_idle), whether or not state.visible is true.

**Upstream main.**

glue main dae530c3: same code.

**Candidate fix.**

glue: when a subset layer is not visible, and was not visible at the last draw, update its data and cache but do not request a canvas draw. This can go in ImageSubsetLayerArtist.update/_update_visual_attributes or in MatplotlibLayerArtist.redraw.

**Gain.**

What-if (variant nohidden) that suppresses the redraw for invisible subset layers:
- Exposure step: 203.4 -> 174.1 ms (A).
- Stack raster step: 244.1 -> 203.9 ms (B).
- λ-scan slit step: 173.3 -> 138.5 ms (B).
Tick fingerprints identical.

**Evidence.**

why_draws.py, why_draws_A.log and why_draws_B.log (ordered draw requests with stacks); whatif_A_nohidden_dpr1.log and whatif_B_nohidden_dpr1.log

**Second measurement.** Method: v3.py, DPR1, medians.
- A exposure step (n=40): 203.7 ms with 2 SJI draws (54.3 ms). With my own variant, where ImageSubsetLayerArtist.redraw does nothing while state.visible is False: 174.1 ms with 1 SJI draw (27.1 ms). That is -29.6 ms, 14.5% of the step.
- B stack raster step (n=20): 231.1 -> 195.3 ms.
- B λ-scan slit step (n=15): 160.9 -> 134.0 ms.
Request trace over 5 consecutive steps (v3trace.py): in every step, the first SJI draw is requested only by layer_artist.py:357 and :396, through common/viewer.py:314 _update_subset, from the hub broadcast.

**Correction.** Holds. On the second SJI draw, the one that is needed:
- In 3 of 4 steps it is requested by glue-solar's slit/point overlay (tools.py:338 _draw, called from _synced on the coordinator's 0 ms QTimer), not by a frame change.
- In 1 of 4 steps the SJI frame changes, and the SJI's own _set_wcs requests it.
There are two draws because glue flushes its deferred draw before glue-solar's 0 ms timer runs.
A real fix still has to redraw once when a layer goes from visible to hidden. My variant skipped that case, and these tests never exercise it.

#### draw#4. The Pixel point is drawn as a full-view RGBA image, and its mask allocates a cube-sized boolean array on every draw (confirmed)

- **Slows:** Every draw of a raster panel that shows the Point (all quicklook raster panels). Worst on large or HiDPI canvases.
- **Repository:** glue-core; **confidence:** high; **share:** 32-33% of a maximized raster-panel draw, 8-19% of a quicklook-size raster draw, about 3.5% of an exposure step at quicklook size.

**Cost.**

Overlay image:
- Maximized spectrogram (1258x810, A, n=20): draw 68.6 ms at DPR1 and 133.7 ms at DPR2. About 22 ms and 44 ms of that is matplotlib resampling the Point's second full-canvas image.
- Quicklook-size raster draws: 1.8-3.4 ms (map 17.6 -> 14.2 ms without it).
Mask:
- 0.5-2.2 ms per draw, against 0.2-0.3 ms for the data buffer itself.
- tracemalloc peak per mask: 175 MB on the Si IV 1403 sit-and-stare cube (1600x417x262), 53 MB on the stack (2x64x771x536).

**Cause.**

Overlay image:
- glue/viewers/image/layer_artist.py:307-309 gives every subset layer an imshow of ImageSubsetArray, PixelSubsetState included, on top of the crosshair lines (311-315).
- ImageSubsetArray (253-277) builds a full-view (ny, nx, 4) uint8 RGBA at alpha 0.5.
- matplotlib/image.py:517-557 converts that to float32, premultiplies it (alpha is not 1), resamples to device pixels and demultiplies.
Mask:
- glue/core/subset.py:1380-1384 SliceSubsetState.to_mask allocates np.zeros(data.shape, bool) for index-array views, then fancy-indexes it.

**Upstream main.**

glue main: same (layer_artist.py and subset.py identical).

**Candidate fix.**

glue: for a PixelSubsetState, draw only the crosshair, or an image whose extent covers just the bounding box of the selected pixels. Build SliceSubsetState masks directly from the index arrays (start <= index < stop on each sliced axis).

**Gain.**

What-if, hiding the Point image:
- Maximized spectrogram: 68.6 -> 46.7 ms (DPR1), 133.7 -> 89.8 ms (DPR2).
- Exposure step at quicklook size: 203 -> 196 ms.
What-if, mask built from the index arrays:
- 1.72 -> 0.36 ms (map), 2.2 -> 0.55 ms (stack panels).
- Peak memory 175 MB or 53 MB -> 2.5 MB.
- Identical RGBA output.
The costs are measured. Less certain is whether a crosshair-only point is visually acceptable, since the mask also highlights the selected row or pixel; the cropped image avoids that question.

**Evidence.**

big_viewer.py, big_viewer_A_dpr1.log, big_viewer_A_dpr2.log and big_viewer_A_dpr{1,2}_nopixmask.log; frb_profile.py, frb_profile_A.log and frb_profile_B.log (timings, tracemalloc, equality check); whatif_A_nopixmask_dpr1.log

**Second measurement.** Method: v4.py. Point image shown and hidden alternate A/B/A/B in one process, n=20 each, forced canvas.draw, medians.
- Maximized spectrogram (1258x810), DPR1: 66.9 -> 44.6 ms with new data, 61.9 -> 43.2 ms colour-only.
- Same, DPR2: 125.2 -> 78.5 ms with new data, 124.0 -> 79.3 ms colour-only. The Point image is 33-37% of the draw.
- Its parts: building the RGBA takes 7.3 ms, including the 3.2 ms mask, with new data (3.9 ms colour-only). The resample takes 12.7 ms at DPR1 and 33.5 ms at DPR2.
- Quicklook size, DPR2: map 23.2 -> 17.3 ms, spectrogram 28.3 -> 24.4 ms, λ-time 39.5 -> 35.2 ms. DPR1 not re-measured.
Mask, SliceSubsetState.to_mask with the index-array view on the 1600x417x262 cube:
- glue: 1.51 ms (map), 0.30 ms (spectrogram), 0.50 ms (λ-time).
- Built from the index arrays (start <= index < stop): 0.04 ms, identical output.
- tracemalloc peak: 175 MB against 0.2 MB.

**Correction.** Cost and cause hold, with two corrections.
1. The mask is not rebuilt on every draw. get_sliced_data's ARRAY_CACHE serves it unless the subset, the slice or the limits changed, so on colour-only draws the mask costs 0 ms. What does run on every draw is the RGBA build (0.3-3.9 ms) and the resample of the 50%-alpha full-view image.
2. The 175 MB is tracemalloc counting the np.zeros calloc, most of whose pages are never touched. A call makes about 1500 minor page faults on the map (about 24 MB at 16 KB pages) and about 8 on the spectrogram, so the effect on RSS is far below 175 MB.
The plain start <= index < stop mask takes 0.04 ms, against the 0.36 ms the finding measured for its version.

#### draw#5. glue redraws the whole WCSAxes figure for changes that only affect the image (confirmed)

- **Slows:** Contrast/bias drag events, the slit-vs-time map's wavelength step, and any redraw where the limits and the WCS slice are unchanged.
- **Repository:** glue-core / glue-qt; **confidence:** medium; **share:** Upper bound: 63% of a map contrast event, 73% of an SJI contrast event, 35% of a map wavelength step.

**Cost.**

Contrast/bias drag event: map 18.2 ms, SJI 30.7 ms per event at DPR1 (25.7 and 38.8 ms at DPR2). Slit-vs-time wavelength step: 35 ms. WCSAxes is 74-85% of those draws.

**Cause.**

Every glue change goes through canvas.draw_idle (glue/viewers/matplotlib/layer_artist.py:73-74, viewer.py:223-224) into a full figure draw by FigureCanvasQTAgg. WCSAxes recomputes ticks, labels and frame each time (see finding 2). No artist is animated or blitted (glue_qt/viewers/matplotlib/widget.py MplCanvas).

**Upstream main.**

glue and glue-qt main: same.

**Candidate fix.**

glue/glue-qt: cache the axes decoration and blit only the image artists while the limits, WCS slice and size are unchanged. For example, mark the image artists animated and keep a background from copy_from_bbox, invalidated on limit, slice or size changes.

**Gain.**

Upper bound from a what-if (variant floor) that skips all WCSAxes decoration: map contrast event 18.2 -> 6.8 ms, SJI contrast event 30.7 -> 8.3 ms, map wavelength step 35.2 -> 22.8 ms. A real blit would add a background copy, roughly the 0.3-5.6 ms the Qt paint costs here.

**Evidence.**

whatif_A_floor_dpr1.log compared with whatif_A_base_dpr1.log; draw_breakdown_A_dpr1.log

**Second measurement.** Method: a decomposition from v1.py, not a floor what-if. DPR1, n=15, medians.
- Map contrast event: 18.5 ms total, draw 15.5 ms, of which draw_wcsaxes 11.0 + frame patch 0.4 ms. WCSAxes is 62% of the event.
- SJI contrast event: 31.0 ms total, draw 27.9 ms, of which 22.0 + 1.8 ms. WCSAxes is 77%.
- Map wavelength step: 34.7 ms total, of which 11.1 + 0.4 ms. WCSAxes is 33%.
Tick computation inside those draws is 6.1 ms (map) and 16.4 ms (SJI). The rest of the WCSAxes time is rendering the ticks and labels.
No blit, animated artist or copy_from_bbox exists in glue or glue-qt, and the glue-qt files match upstream.

**Correction.** The upper bound holds: without WCSAxes, about 7 ms are left for each contrast event and about 23 ms for the wavelength step.
Caveat on the fix: WCSAxes draws its ticks and frame over the image. A blit therefore needs a cached background below the image plus the decorations redrawn on top (or a cached overlay), not a single copy_from_bbox.
A simpler partial fix would go in astropy WCSAxes rather than glue: reuse the tick positions while the limits, WCS slice and size are unchanged. That saves the tick computation, 6 ms (map) and 16 ms (SJI) here.

#### draw#6. On maximized or HiDPI viewers the image path dominates: glue's float64 RGBA composite and matplotlib's resample of it (confirmed)

- **Slows:** Any redraw of a large viewer, such as a maximized SJI or raster panel.
- **Repository:** glue-core (matplotlib for the resample); **confidence:** medium; **share:** 46% (DPR1) and 58% (DPR2) of a maximized SJI draw. The fixed-resolution buffer alone is 4%.

**Cost.**

Maximized SJI (1258x810, n=20): draw 53.6 ms at DPR1 and 92.1 ms at DPR2. The image artists take 24.9 and 53.3 ms of that:
- FRB: 2.1 ms
- CompositeArray: about 8.5-10.7 ms
- matplotlib resample: 13.2 ms (DPR1), 42 ms (DPR2)
CompositeArray takes 8.5 ms for a 529x816 buffer. About 3.6 ms of that is its own float64 array work (np.ones, zeroing, +=, clip), and 2.2 ms is the colormap lookup.

**Cause.**

glue/viewers/image/composite_array.py:93-228 builds a float64 RGBA even for a single opaque colormap layer (np.ones at 166, img[...]=0 at 176, img += plane at 221, np.clip at 226). mpl_scatter_density/base_image_artist.py:52 computes the buffer at a fixed 72 dpi. matplotlib/image.py:543 therefore resamples it 1.4x (DPR1) or 2.8x (DPR2) up to device pixels in floating point, then demultiplies and converts to bytes (557).

**Upstream main.**

glue main: composite_array.py identical. mpl-scatter-density 0.8 and matplotlib 3.11.2 were not compared with their mains (no local clones).

**Candidate fix.**

glue: for a single opaque layer, return float32 (or the colormap's own output) and skip the accumulation and clip. matplotlib: add a faster path for nearest-neighbour upsampling of opaque RGBA.

**Gain.**

What-if with a float32 composite:
- Maximized SJI: 53.6 -> 46.6 ms (DPR1), 92.1 -> 82.6 ms (DPR2).
- Spectrogram: 133.7 -> 125.6 ms (DPR2).
- Rendered pixels differ by at most 1/255 in 10-15% of pixels.
The single-layer shortcut would save about 4 ms more by profile estimate, not measured as a what-if.

**Evidence.**

big_viewer_A_dpr1.log and big_viewer_A_dpr2.log; big_viewer_A_dpr{1,2}_f32.log; composite_profile.py and profile_composite_sji_max.txt; checks.py and checks_A.log (pixel comparison)

**Second measurement.** Method: v4.py on the maximized SJI (1258x810), forced draw + repaint, n=20 per variant with variants alternating, medians.
- DPR1: draw 50.6 + paint 1.3 ms. Composite (including the FRB) 10.6 ms with new data, 8.6-8.8 ms colour-only. Matplotlib resample 12.2 ms. The image path is about 44% of the draw.
- DPR2: draw 86.9 + paint 5.6 ms. Composite 10.5 ms, resample 42.3 ms. The image path is about 57%.
cProfile of 20 composite calls (529x816 buffer), per call: CompositeArray's own time 3.8 ms, np.ones 0.8 ms, clip 0.9 ms, colormap take/_get_rgba about 2.2 ms.
Float32 what-if (composite output cast to float32):
- SJI DPR1: 50.6 -> 47.3 ms (-3.2), colour-only -3.0 ms.
- SJI DPR2: 86.9 -> 75.3 ms (-11.4).
- Spectrogram DPR2: 125.0 -> 114.4/118.7 ms with new data, 124.2 -> 110.5 ms colour-only.
- Rendered pixels differ by at most 1/255 in 13.6-20.8% of pixels.

**Correction.** Cost, shares and cause hold, with three corrections.
1. At DPR1 the float32 gain is about half the claim: -3.2 ms in my in-process A/B over two rounds, not -7.0 ms. The finding's 53.6 -> 46.6 ms came from two separate processes. At DPR2 the gain holds (-11.4 ms against the claimed -9.5).
2. All of the measured gain comes from matplotlib's resample (42 -> 30 ms at DPR2). A cast leaves the composite's own time unchanged.
3. Pixels differ in 14-21% of pixels, not 10-15%.

#### draw#7. glue-solar's WCS wrapper triples the cost of each raster WCS call (not re-measured)

- **Slows:** Every draw and every label set: all WCS-based tick work on IRIS data.
- **Repository:** glue-solar; **confidence:** high; **share:** About 10% of raster slider steps, 8% of an SJI frame step, 12% of a map contrast event.

**Cost.**

_GlueWCS.pixel_to_world_values takes 0.056-0.059 ms, against 0.017-0.019 ms for irispy's FITS WCS inside it (2-50 points, medians of 200 calls). It adds about 0.05 ms to the SJI's 0.29 ms gWCS call. The overhead comes from three places:
- u.Unit(self._wcs.world_axis_units[i]) for each helioprojective axis on every call (world_axis_units on a FITS WCS costs 0.011 ms per access).
- world_axis_physical_types recomputed on every call.
- Quantity round-trips.

**Cause.**

glue_solar/sources/loaders/iris.py:86-97 (_GlueWCS.pixel_to_world_values).

**Upstream main.**

glue-solar origin/main 5eae565: iris.py unchanged.

**Candidate fix.**

Compute each axis's arcsec factor and the longitude wrap once per wrapper (cache them), then apply plain numpy arithmetic on each call.

**Gain.**

What-if (variant gluewcs) with cached factors:
- Exposure step: 203.4 -> 183.7 ms.
- λ-time slit step: 212.5 -> 188.1 ms.
- SJI frame step: 105.1 -> 96.2 ms.
- Map contrast event: 18.2 -> 16.0 ms.
Tick fingerprints identical.

**Evidence.**

wcs_calls.py and wcs_calls.log; whatif_A_gluewcs_dpr1.log

#### draw#8. The quicklook coordinator's 0 ms timer splits one step into two draw rounds (not re-measured)

- **Slows:** Raster slider steps, most visible on the stack raster step (B).
- **Repository:** glue-solar; **confidence:** medium; **share:** About 8% of the stack raster step (one ~20 ms λ-scan draw out of 244 ms). Coordinator._update is about 5%.

**Cost.**

On a B raster step the λ-scan panel draws twice: 40.7 ms for the two draws, about 20 ms each. The first draw is for the Point subset change. The second comes from Coordinator._update -> _apply_point -> _set_slices on the next event-loop turn. The SJI's real second draw also comes from that turn (tools.py:338 via quicklook.py:495). Coordinator._update itself takes 10.7-12.4 ms per step.

**Cause.**

glue_solar/quicklook.py:216-219 uses a single-shot QTimer with a 0 ms interval. Its callback _update (386-402) moves the sliders after glue has already drawn the subset change.

**Upstream main.**

glue-solar origin/main 5eae565: quicklook.py unchanged.

**Candidate fix.**

For a point change, apply the slider moves inside the same defer_draw block as the subset update, synchronously. Keep the timer only for drags.

**Gain.**

Estimated at one λ-scan draw (about 20 ms) per stack raster step. Not measured as a what-if.

**Evidence.**

why_draws_B.log (ordered requests and draws); quicklook_steps_B_dpr1.log

**Not measured in this area.** - Real screens. Every number comes from offscreen Qt with Agg on this Mac. DPR2 was emulated with QT_SCALE_FACTOR=2. Wayland/X11 compositor and blit costs were not measured, so the user's 0.068 s / 0.028 s per tick are not reproduced directly. The offscreen Qt paint is 0.2-5.7 ms.
- Slider widget. Steps were applied by setting viewer.state.slices. The real QSlider path, including glue-solar's 100 ms drag throttle, was not exercised.
- Datasets and windows. Only Si IV 1403 on 4000255147 and the 4000005156 stack were run, as assigned. Mg II k, 3602506433 and 3824262996 were not run. The Point-mask transient for Mg II k (about 370 MB, 1600x417x555 bool) is an extrapolation.
- Finding 5's gain is an upper bound from removing all WCSAxes decoration, not a blit implementation.
- Finding 6: the single-opaque-layer shortcut was estimated from a profile, not measured. The float32 change is not bit-exact (it differs by at most 1/255).
- Finding 8 was not what-if tested.
- The ProfileViewer spectrum draws twice per point move (16-19 ms each: once when the computation starts, once when the worker thread ends). This was observed but not analysed, since it is outside this area.
- First open of the quicklook (2.5-3.6 s) and window/tab resizes were not broken down. mpl-scatter-density holds stale images for 500 ms after a resize; measurements waited for that.
- glue-solar-main 2fdb847 is 3 merges behind origin/main 5eae565. On 5eae565, #87 already removes a cost measured on 2fdb847: about 48 jittery latitude tick labels on the λ-time panel, about 11 ms per draw (34.4 -> 23.6 ms when hidden). That is why it is not a finding. On 5eae565 the λ-time draw is 27 ms, but the map draw is slower (17.6 -> 21 ms) because of its pixel-index tick overlay, and the λ-time slit step set phase grows to 76 ms (see finding 1).
- astropy's local origin/main 6d36964 is behind GitHub main, so the astropy upstream comparison is as of 2026-09-07. mpl-scatter-density and matplotlib mains were not compared.
- Run-to-run noise between separate processes is about ±2-3 ms per step. cProfile output was used only for structure (about 4.6x overhead).

### Area: hidpi-many

**Setup and baselines.** Drawing at scale (hidpi-many). I measured four things: draw time as viewer count grows, canvas size and devicePixelRatio, tick-label text compared with image resampling, and slider drags in glue-qt compared with glue-solar. Setup: glue-core 1.27.0, glue-qt 0.4.2, matplotlib 3.11.2, astropy 8.0.1, PyQt5 5.15, iris-plan env, offscreen QPA, app 1600x1000. DPR 2 came from QT_SCALE_FACTOR=2, which offscreen accepts: canvas dpr 2.0, figure dpi 200, renderer 2x. glue_solar.__file__ is /Users/nabil/Git/glue-solar-main/glue_solar/__init__.py at 2fdb847 ("Merge pull request #84"). That is 3 merges behind origin/main 5eae565 (#86-#88). quicklook.py and sources/loaders/iris.py are identical between the two. tools.py differs (sit-and-stare exposure labels), but the slider throttle is the same code. Data: 4000255147 SJI 1400 (400x417x388, gWCS) and Si IV 1403 sit-and-stare (1600x417x262, FITS WCS); 4000005156 Si IV r00000 and SJI 2796 deconvolved only for the two-quicklook test. Peak RSS was 3.1 GB. Scripts and logs are in perf_survey_20261001/hidpi-many/; common.py wraps MplCanvas.draw and paintEvent in-process to count and time real canvas draws. Overall picture: one SJI slider tick costs about 100 ms on a quicklook-sized panel. Of that, about 65 ms comes before any drawing, from WCSAxes re-placing ticks 4 times while glue resets the axis labels. Drawing grows with panel area and DPR mostly through the image path (make_image 31 ms at DPR 1 to 72 ms at DPR 2 on a full tab). Tick-label text itself costs only 5-7.5 ms per draw. With many viewers, the per-draw floor is WCSAxes tick placement (about 16 ms per SJI viewer). Viewers in hidden tabs and viewers whose subset layer is hidden still redraw in full. Answer to (1): a slider tick redraws only its own viewer, but any subset or point change redraws all N viewers (N=1/5/10: 78/185/324 ms), and hidden tabs redraw at the same cost.

#### hidpi-many#1. Each slider tick on IRIS data re-places every WCSAxes tick 4 extra times because glue resets the axis labels in a round trip (confirmed)

- **Slows:** Stepping or dragging the frame slider of an SJI viewer, or the exposure slider of a sit-and-stare raster panel (any slice the displayed helioprojective coordinates depend on)
- **Repository:** glue-core (astropy alternative); **confidence:** high; **share:** SJI setter as a share of the tick: 69% at 508x317, 65% at 800x500, 51% at full tab (1568x797), 37% at full tab DPR 2. Si IV: 55%, 52%, 35%, 23% for the same sizes. The cost is constant, so it dominates the quicklook-sized panels users actually drag.

**Cost.**

25 ticks per configuration, medians, 800x500 panel, DPR 1. SJI 1400: tick 103.0 ms, of which the state.slices setter takes 67.2 ms before any draw. Si IV 1403 spectrogram: tick 60.5 ms, setter 31.7 ms. The setter calls WCSAxes._update_tick_and_label_positions 4 times and the draw calls it a 5th time; each call is 16.0 ms for SJI (33 WCS transform calls) and 7.2 ms for Si IV (49 calls). Per tick that is 169 / 249 WCS transform calls; 68.5 ms of the SJI tick is spent inside them. reset_wcs itself is only 0.6-0.8 ms.

**Cause.**

glue/viewers/image/viewer.py:96-98 _on_slice_change calls _set_wcs(relim=False) whenever _changing_slice_requires_wcs_update is true (set at viewer.py:132-148; true for both datasets because lon/lat depend on the frame/exposure axis). viewer.py:117 reset_wcs, then viewer.py:120-121 sets state.x_axislabel and y_axislabel to '', then viewer.py:124 _update_axes (74-82) sets them back to the world labels. Each of the 4 assignments fires glue/viewers/matplotlib/viewer.py:152-162 update_x/y_axislabel, which calls axes.set_xlabel/set_ylabel. astropy/visualization/wcsaxes/core.py:596-598 (set_ylabel at 613) calls _update_tick_and_label_positions() (core.py:490-515) unconditionally. cProfile of 20 ticks: 80 calls from set_xlabel (40) and set_ylabel (40), 2.99 s of the 3.06 s setter time.

**Upstream main.**

Same code. glue origin/main dae530c3 (2026-07-13): glue/viewers/image/viewer.py and glue/viewers/matplotlib/viewer.py are byte-identical to 1.27.0. astropy origin/main 1f930be7c4 (2026-09-28): set_xlabel (core.py:670-697) still calls _update_tick_and_label_positions() first.

**Candidate fix.**

glue-core _set_wcs: drop the '' round trip. After reset_wcs, put the current labels straight onto the new coordinate helpers with axes.coords[ndim-1-att.axis].set_axislabel(label, weight=..., size=...), the same axis mapping update_x_ticklabel already uses (viewer.py:56-72). Notify x/y_axislabel listeners only when the text actually changes. Coordinates whose label position is not the default may need a fallback to set_xlabel. Cheaper variant A: keep set_xlabel but set each label once. Astropy-side alternative that helps every caller: let WCSAxes.set_xlabel/set_ylabel store the label and choose its coordinate at draw time, where tick placement already runs.

**Gain.**

Measured with instance-level overrides (labelfix.py, 25 ticks, medians). Variant B (labels on coordinate helpers): SJI tick 103.0 to 37.7 ms (-63%), Si IV 60.5 to 30.6 ms (-49%); setter 67.2 to 1.8 ms and 31.7 to 1.7 ms. Rendered canvas pixel-identical (0.000% of pixels differ), same axis labels. Variant A: SJI 70.7 ms (-31%), Si IV 44.9 ms (-26%). The saving is about 65 ms (SJI) and 30 ms (Si IV) per tick at any size or DPR.

**Evidence.**

hidpi-many/labelfix.py and labelfix.log; breakdown.py with breakdown_{sji,siiv}_dpr{1,2}.log (setter vs draw split and wrapped timers); prof_tick.py with prof_tick_sji.log and prof_sji_setter.pstats (callers of _update_tick_and_label_positions); wcscost.log and wrapcost.log (calls and time per tick).

**Second measurement.** glue-solar-main 2fdb847 (origin/main is 5eae565, three merges ahead). One viewer, 25 ticks after 2 warm-up ticks, medians, offscreen, DPR 1. SJI 1400 at 800x500 (canvas 788x397): tick 103.8 ms, of which 68.0 ms is the state.slices setter. Per tick there are 5 placements (set_xlabel 2, set_ylabel 2, draw_wcsaxes 1), 16.5 ms each, with 169 WCS transform calls taking 71.3 ms. Si IV 1403 at 800x500: tick 60.5 ms, setter 31.7 ms, 7.4 ms per placement, 249 transform calls taking 23.2 ms. SJI maximized (canvas 1258x832): tick 118.5 ms, setter 65.1 ms (55% of the tick). I emulated the fix myself with instance overrides of WCSAxes.set_xlabel/set_ylabel that put the label on coords[ndim-1-att.axis] and skip placement. Result: SJI tick 37.9 ms (-63%) with a 2.2 ms setter; Si IV 30.3 ms (-50%) with a 2.1 ms setter. The canvas is pixel-identical (0.000% of pixels differ) and the labels are the same. Variant A (skip the '' labels): SJI 70.9 ms, Si IV 45.8 ms. Placement timed alone, 20 calls: 16.2 ms (SJI) and 7.3 ms (Si IV).

**Correction.** No substantive correction: cost, call counts and cause (viewer.py:96-124 into matplotlib/viewer.py:152-162 into astropy core.py:596-598/613-615) all reproduce. The cited files are byte-identical on glue origin/main dae530c3, and astropy origin/main 1f930be7c4 still places ticks first in set_xlabel. Caveat, not measured: glue-solar origin/main 5eae565 adds x/y_axislabel listeners and a pixel coords overlay in tools.py (FrameTimeTool._label_exposures). That may add work to each of the 4 label assignments on current main. Evidence: hidpi-many-verify/v_tick.py with v_tick_{sji_800,siiv_800,sji_max}.log.

#### hidpi-many#2. glue-qt's slider applies every dragged position synchronously, and glue-solar's 100 ms throttle caps redraws at 5-6 per second (confirmed)

- **Slows:** Dragging a slice slider (SJI frames, raster exposures) in an Image viewer
- **Repository:** glue-qt (upstream), glue-solar (throttle); **confidence:** high; **share:** Without the throttle the backlog is 100% excess: about 6 s (SJI) and 2 s (Si IV) of lag after a 2 s drag. With the throttle, the app draws at only 50% (SJI) and 37% (Si IV) of the rate it can sustain with latest-position coalescing.

**Cost.**

Simulated 2 s drag of 120 positions at 60 Hz, 800x500, DPR 1, 3 runs per configuration, medians. Positions are posted as Qt events that queue while the app is busy. glue-qt's own slider (tracking on, glue-solar throttle undone in-process), every position delivered (Wayland/macOS-like): all 120 positions applied, each running the full setter. SJI: 0.5 draws/s, the 2 s drag takes 8.2 s to finish, display lag median 1315 ms (max 6223). Si IV: 1.5 draws/s, 4.0 s, lag median 389 ms (max 2020). With X11-like motion compression: SJI 10 draws/s at lag 116 ms; Si IV 17.1 draws/s at lag 66 ms. glue-solar's throttle (setTracking(False) plus a 100 ms timer), either delivery: SJI 5.0 draws/s at lag 106-110 ms; Si IV 6.0-6.3 draws/s at lag 65 ms; no backlog.

**Cause.**

glue_qt/viewers/common/data_slice_widget.py:43 autoconnects QSlider.valueChanged to SliceState.slice_center (echo/qt/connect.py:354). slice_widget.py:123 then runs sync_state_from_sliders (54-61), which sets viewer_state.slices synchronously for every value, so the full tick setter runs per position (see the label-reset finding). Draws are deferred (draw_idle schedules QTimer.singleShot(0), matplotlib backend_qt.py:494-504), so queued input starves redraws. The slider has no tracking override in data_slice_widget.ui. glue-solar tools.py:21,24-44 at 2fdb847 (origin/main tools.py:29,32-52): the single-shot timer is started on the first sliderMoved after an apply, so the period is 100 ms plus the tick cost (about 200 ms SJI, about 160 ms Si IV).

**Upstream main.**

glue-qt origin/main 9780eaf9 (2026-02-17): data_slice_widget.py and slice_widget.py identical to 0.4.2. glue-solar origin/main 5eae565 has the same 100 ms throttle.

**Candidate fix.**

glue-solar now: keep tracking off, but replace the 100 ms interval with a 0 ms single-shot timer that applies slider.sliderPosition() once pending input has been handled (latest-position coalescing, no fixed wait). Release still applies the final value. Upstream: the same coalescing inside glue-qt's SliceWidget while sliderDown, so every glue user gets bounded lag.

**Gain.**

Coalescing (3 runs, medians): SJI 9.9-10.1 draws/s (2x the throttle) at lag 108 ms; Si IV 16.9-17.1 draws/s (2.7x) at lag 121-122 ms, against 65 ms with the throttle, so this is a smoothness-versus-latency trade for the raster. Combined with the label-reset fix B (1 run each): SJI 29 draws/s at lag 43 ms and Si IV 34 draws/s at lag 36 ms with coalescing; 7.5 draws/s at lag 46 / 34 ms with the current throttle. Final values were correct in all modes.

**Evidence.**

Confidence is high for the mechanism and medium for the absolute rates, because input is simulated with posted Qt events on the offscreen platform. hidpi-many/drag.py; drag_repeats.log (36 runs) summarized by drag_summary.py into drag_summary.log; drag_coalesce.log; drag_labelfix.log (LABELFIX=1 with labelfix_fn.py).

**Second measurement.** Own simulation: 120 positions over 2 s at 60 Hz, 800x500, 2 runs per configuration. Throttle as loaded (tracking False): SJI 4.9-5.0 draws/s, display lag 108-113 ms; Si IV 6.0 draws/s, lag 64-73 ms, for either delivery mode. glue-qt with tracking on and every position delivered: SJI 0.5 draws/s, release processed at 8.23-8.30 s, lag median 1340-1407 ms (max 6.3 s); Si IV 1.2 draws/s, 4.0-4.1 s, lag median 401-710 ms (max 2.0-2.1 s). glue-qt with latest-only (compressed) delivery: SJI 9.3-9.5 draws/s at 133-135 ms lag; Si IV 16.9-17.1 draws/s at 66 ms. Coalesce (0 ms timer): SJI 9.7 draws/s at 110-112 ms; Si IV 16.4-17.1 draws/s at 120-127 ms. The final value was correct in every run.

**Correction.** The mechanism and rates reproduce. The throttle period equals 100 ms plus the tick cost (SJI 68 ms setter plus 32 ms draw is about 200 ms; Si IV is about 160 ms), consistent with the tick finding. Minor differences: Si IV uncompressed glue-qt measured 1.2 draws/s rather than 1.5, and its lag varied between runs (401-710 ms against 389). With compressed (X11-like) delivery, glue-qt's own tracking already matches coalescing in rate and beats it on Si IV lag (66 against 120 ms). Coalescing therefore helps over tracking only when input is not compressed, and over the throttle it doubles to nearly triples the rate. I did not re-run the combined label-fix numbers; they agree by arithmetic with the 30-38 ms remeasured ticks (about 26-33 draws/s). Absolute rates rest on posted Qt events on the offscreen platform. Cited code holds: data_slice_widget.py:43, slice_widget.py:54-61/123, backend_qt.py:494-504; glue-qt origin/main 9780eaf9 is identical. Evidence: hidpi-many-verify/v_drag.py with v_drag_{sji,siiv}.log.

#### hidpi-many#3. WCSAxes re-places all ticks on every draw and repeats the same WCS transforms for each world coordinate; this sets the per-viewer draw floor (confirmed)

- **Slows:** Any redraw of an IRIS Image viewer (point moves, subset edits, slider ticks, pans), multiplied by the number of viewers redrawn, for example a Pixel point move in a tab of N viewers
- **Repository:** astropy; **confidence:** medium; **share:** 51% of a point move with 10 viewers; 22% with one large viewer; about 50-60% of a draw at quicklook panel sizes (16 of 27-32 ms).

**Cost.**

One placement: SJI 16.0 ms with 33 WCS calls (16 per displayed coordinate plus 1 range grid; 13.6 ms inside transforms; the gWCS costs about 0.46 ms per call whatever the point count). Si IV 7.2 ms with 49 calls (16 x 3 coordinates plus 1; 4.6 ms in transforms). Point move with N tiled SJI viewers (15 moves, medians): N=1 (1250x799) 78.5 ms of which placement 16.4 ms; N=10 (302x197 each) 323 ms of which placement 164.7 ms; N=1/5/10 point moves 78/185/324 ms. Draws still cost about 28-30 ms each at 302x197. For comparison, tick-label text itself is small: static redraws with and without ticks/labels are 26.4 vs 21.0 ms (508x317), 59.5 vs 54.0 ms (1568x797) and 107.4 vs 99.9 ms (DPR 2), so text costs 5-7.5 ms per draw at any size; Text.draw totals 4-5 ms (SJI) and 7-9 ms (Si IV).

**Cause.**

astropy/visualization/wcsaxes/core.py:517-528: draw_wcsaxes calls _update_tick_and_label_positions on every draw, with no cache when limits and transform are unchanged. coordinate_helpers.py:966-1050: _update_ticks re-samples the frame for each coordinate helper (line 995 self.frame.sample; frame.py:57-67 transforms per spine). The +-2 px shifted_pixel_to_world calls (1023-1030) transform all world axes and keep one column. The same pixels are therefore transformed once per coordinate (2 coordinates for SJI, 3 for Si IV).

**Upstream main.**

astropy origin/main 1f930be7c4 (2026-09-28): unchanged; frame.sample is still per coordinate (coordinate_helpers.py:1013) and draw_wcsaxes still re-places ticks on every draw.

**Candidate fix.**

astropy: compute the frame samples, their world coordinates and the shifted samples once per update and share them across CoordinateHelpers (33 to 17 calls for SJI, 49 to 17 for Si IV). Cache tick placement while xlim/ylim, the axes bbox and the transform are unchanged, so subset-only redraws skip it.

**Gain.**

Estimated from the measured attribution, not prototyped. Sharing saves about 6.5 ms per SJI placement (-40%) and about 3 ms for Si IV. Caching removes about 16 ms per redrawn SJI viewer on subset-only redraws: about 165 of 323 ms (-51%) for a 10-viewer point move.

**Evidence.**

The attribution is measured; the gains are estimates. hidpi-many/tickcalls.py with tickcalls.log; point_split.py with point_split.log; many.py with many_{1,5,10}.log; static.py with static_sji_dpr{1,2}.log; wcscost.log.

**Second measurement.** One placement: SJI 16.2-16.5 ms with 33 transform calls. These are 1 coordinate-range call of 2601 points, plus per coordinate 4 calls of 2 points (frame.update_spines inside frame.sample), 4 of 1000 points (sampled spines) and 8 of 1000 points (shifted by ±2 px); each coordinate spends 6.6 ms in transforms. Si IV: 7.3-7.5 ms with 49 calls, 1.5 ms per coordinate. Point moves with N tiled SJI viewers, 15 moves, medians: N=1 (1250x799) 78.8 ms, placement 16.8 ms (23% of draw time); N=5 (408x347) 181.5 ms, placement 83.3 ms (50%); N=10 (302x197) 324.8 ms, placement 167.0 ms (56%). The SJI gWCS transform costs 0.36 ms for 1 to 50 points, 0.50 ms for 1000 and 0.70 ms for 5000.

**Correction.** Cost and cause hold (core.py:529 places ticks on every draw; coordinate_helpers.py:995 samples the frame per coordinate; astropy main still has it at :1013). The sharing estimate holds: 6.6 ms per SJI placement and 3.0 ms for Si IV. Two corrections. (1) The '50-60% of a draw' share is SJI-only; for Si IV placement is about 30% of a draw (7.4 of 24.5 ms at 800x500). (2) The transform costs mostly per call rather than per point, so a bigger astropy fix is batching. Concatenating all spine samples and shifted samples (and the 2-point update_spines calls) into one transform call per update would replace 33 calls with about 2. I estimate (not prototyped) about 12-13 ms saved per SJI placement (about 80%) against 6.6 ms for sharing alone; the gain is largest for WCSes with per-call overhead such as gWCS. I did not re-measure the tick-label text cost. Evidence: hidpi-many-verify/v_tick.py logs ('placement alone'), v_wcscall.py with v_wcscall.log, v_points.py with v_points_{1,5,10}.log.

#### hidpi-many#4. Viewers in hidden tabs do full Agg redraws that are never painted (confirmed)

- **Slows:** Moving the point or a slider in one quicklook while other quicklook tabs (observations) are open; any subset change while viewers sit in a non-current tab
- **Repository:** glue-qt (or matplotlib); **confidence:** high; **share:** 25-28% of each action with one other quicklook open, growing by about 20-30 ms per hidden viewer for each additional tab. 92-100% when the moved point only affects hidden viewers.

**Cost.**

Two quicklooks, 15 repeats, medians. Tab A (4000255147 Si IV + SJI 1400) hidden, tab B (4000005156 Si IV + SJI 2796) shown. B point move: 421.6 ms wall, of which tab A's 5 hidden viewers do 6 draws costing 117.7 ms with 0 paints. B spectrogram slider tick: 461.7 ms, of which hidden tab A takes 6 draws and 115.6 ms (glue-solar's coordinator moves the shared point group, and its subsets exist on A's datasets). SJI viewers in a hidden tab: N=5 point move 178 ms and N=10 320 ms, all of it hidden draws (168 / 296 ms), 0 paints.

**Cause.**

matplotlib/backends/backend_qt.py:494-526: draw_idle schedules _draw_idle, which only checks width and height > 0, not visibility. glue_qt/viewers/matplotlib/widget.py:27-125 MplCanvas does not override this, so every glue redraw (glue/viewers/matplotlib/viewer.py:223-224, layer_artist.py:73-74 draw_idle) renders hidden canvases in full.

**Upstream main.**

glue-qt origin/main 9780eaf9: widget.py identical to 0.4.2. Not checked against matplotlib main (no local clone).

**Candidate fix.**

glue-qt MplCanvas: while the canvas is not visible, drop the pending draw and mark the canvas dirty; in showEvent call draw_idle once if dirty. This could also go upstream to matplotlib's FigureCanvasQT.

**Gain.**

Prototype as an in-process override on synthetic data, 5 viewers in a hidden tab: draws per point move 5 to 0, wall 81.5 to 8.6 ms; showing the tab again does exactly 5 draws once. On the IRIS case that is about 115 ms saved per point move or slider tick for each hidden quicklook tab (-25-28%).

**Evidence.**

hidpi-many/quick2.py with quick2.log; many.py with many_{1,5,10}.log ('hidden point' rows); hiddenfix.py with hiddenfix.log.

**Second measurement.** Two quicklooks (A: 4000255147 Si IV + SJI 1400, hidden; B: 4000005156 Si IV + SJI 2796, shown), 15 reps after 1 warm-up, medians, 2 runs. B point move 416-431 ms, of which hidden tab A does 6 draws taking 117-120 ms (28%) with 0 paints. B spectrogram tick 490-493 ms, of which hidden A takes 118-120 ms (24%). My own canvas-fix emulation (MplCanvas._draw_idle drops the draw while not visible) brings the point move to 312-323 ms (-25%) and the tick to 351-353 ms (-28%), with 0 hidden draws. N SJI viewers in a hidden tab, point move: N=1 81 to 2.7 ms; N=5 188 to 8.9 ms; N=10 328 to 17.3 ms. Showing the tab again costs 1 draw per dirty canvas.

**Correction.** Confirmed, but it overlaps with the hidden-subset-layer finding. In the quicklook every layer of B's point group in tab A's viewers is hidden (glue-solar quicklook.py:402/868 sets layer.visible False). So 4 of tab A's 6 hidden draws are also the hidden-subset-layer redraws of the next finding. That fix alone leaves 2 hidden draws (16.6 ms, the spectrum profile viewer) and cuts the point move to 277 ms (-33%), more than the canvas fix, because it also skips tab B's own hidden-layer draw. The two gains are not additive in the quicklook. The canvas fix still covers hidden tabs whose subset layers are visible. Cited code holds (backend_qt.py:494-526, glue-qt widget.py has no _draw_idle override, identical on origin/main 9780eaf9). Evidence: hidpi-many-verify/v_quick2.py with v_quick2.log and v_quick2b.log; v_points_{1,5,10}.log.

#### hidpi-many#5. Subset updates fully redraw viewers whose subset layer is hidden (confirmed)

- **Slows:** Moving the Pixel point or editing any subset when several viewers show the data with that subset layer hidden. The glue-solar quicklook hides the point on its other datasets' panels, such as the slit-jaw.
- **Repository:** glue-core; **confidence:** high; **share:** 4 of 5 draws (about 110 of 156 ms, about 70%) are for viewers whose picture does not change.

**Cost.**

5 tiled SJI viewers (408x347), subset layer hidden in 4 of them, 15 moves, medians: every move still draws all 5 canvases, 142.8 ms of draw and 156.3 ms wall (185.5 ms with all visible).

**Cause.**

glue/viewers/common/viewer.py:309-314 _update_subset calls layer_artist.update() for every artist of the subset. glue/viewers/image/layer_artist.py:391-396 ImageSubsetLayerArtist.update pops the caches, runs _update_image(force=True) and then redraw() whatever self.state.visible is. The artist's own comment at layer_artist.py:260-264 shows the mask is meant to stay current while hidden, but the canvas redraw is not needed.

**Upstream main.**

glue origin/main dae530c3: viewer.py and layer_artist.py identical to 1.27.0.

**Candidate fix.**

In ImageSubsetLayerArtist.update (or Viewer._update_subset), when the layer is not visible, drop the caches and mark it stale, and skip the redraw. Redo _update_data (crosshair) when visible turns true; the existing visibility path already redraws.

**Gain.**

Prototype as an in-process override on synthetic data (5 viewers, subset hidden in 4): 5 to 1 draws per move, 68.9 to 23.4 ms (-66%). About one full draw (28-35 ms at quicklook panel sizes) saved per viewer with a hidden subset, per point move.

**Evidence.**

Confidence is high for the mechanism and medium for the quicklook share, because I did not count how many quicklook layers are hidden. hidpi-many/many.py with many_5.log ('subset layer hidden in viewers 1..N-1'); hiddenfix.py with hiddenfix.log.

**Second measurement.** 5 tiled SJI 1400 viewers (408x347), subset layer hidden in 4, 15 moves, medians: 157.6 ms wall, all 5 canvases drawn (144.2 ms of draw). With my own fix emulation (ImageSubsetLayerArtist.update drops ARRAY_CACHE/PIXEL_CACHE and returns when the layer is not visible), on the real IRIS data: 44.3 ms with 1 draw (-72%). N=10: 283.0 ms to 49.3 ms (-83%). In the real two-quicklook case: point move 416 to 277 ms (-33%), spectrogram tick 490 to 324 ms (-34%).

**Correction.** Cost and cause reproduce (common/viewer.py:309-314 into layer_artist.py:391-396 redraws regardless of visible; identical on glue origin/main). The quicklook share the finding left unmeasured is now measured: glue-solar hides the point layer in its other datasets' panels and in other quicklooks' panels, which gives the -33% above. Most of the roughly 28 ms saved per hidden-layer viewer is WCSAxes tick placement (16 ms), not the mask, because a hidden artist is not rasterized. Not validated: my emulation does not redo _update_data (crosshair) when the layer is shown again, which a real fix must do. Evidence: hidpi-many-verify/v_points.py with v_points_{5,10}.log; v_quick2.py with v_quick2b.log.

#### hidpi-many#6. A one-pixel Pixel point is drawn by computing a full-view mask image on every redraw, and the unchanged main image is re-colormapped too (confirmed)

- **Slows:** Moving the Pixel point (quicklook point, or slider ticks that move it); every viewer showing the point redraws
- **Repository:** glue-core; **confidence:** medium; **share:** Mask 32% of a large viewer's point-move draw and 14% with 10 small viewers. Composite recompute about 11%.

**Cost.**

Point move, 1 SJI viewer 1250x799, 15 moves, medians: canvas draw 73.1 ms. Of that, the subset mask make_image takes 23.5 ms (get_mask FRB 10.1 ms, plus the RGBA dstack, uint8 conversion and resample), and the main image make_image takes 21.3 ms (FRB plus colormap 8.2 ms; the FRB array cache hits, the composite is still recomputed). With N=10 small viewers the mask takes 41.5 of 299 ms.

**Cause.**

glue/viewers/image/layer_artist.py:253-278 ImageSubsetArray.__call__ computes get_sliced_data(bounds) over the whole view and builds a float RGBA with np.dstack on every draw, for a PixelSubsetState that selects one pixel per frame; the crosshair at layer_artist.py:309-331 already marks it. glue/viewers/image/composite_array.py:93-200 re-applies interval, stretch and colormap on every draw with no output cache.

**Upstream main.**

glue origin/main dae530c3: layer_artist.py and composite_array.py identical to 1.27.0.

**Candidate fix.**

For PixelSubsetState, draw only the crosshair, or compute the mask only inside the point's bounding box. Cache the CompositeArray output keyed on bounds and layer settings, so a subset-only redraw reuses the main image RGBA.

**Gain.**

Estimated from the measured split, not prototyped: about 23 ms per large redrawn viewer from the mask, plus up to about 8 ms from the composite cache (about 40% of a point-move draw).

**Evidence.**

hidpi-many/point_split.py with point_split.log.

**Second measurement.** 1 SJI viewer at 1250x799, 15 point moves, medians, 2 runs. Canvas draw 71.0-73.4 ms. The subset FRBArtist.make_image takes 22.4-23.4 ms (32%): ImageSubsetArray() 9.7-10.1 ms (get_sliced_data 6.0 ms plus dstack/uint8 3.7 ms) and matplotlib _make_image resample/composite 12.3 ms. The image make_image takes 20.7-21.2 ms: CompositeArray() 7.9-8.2 ms (get_image_data 0.0 ms, a cache hit) and matplotlib resample 11.8 ms. N=10 (302x197): subset make_image 40.1 ms of 300 ms of draw time (13%).

**Correction.** Cost and cause hold (layer_artist.py:253-278, composite_array.py:93-200; identical on glue origin/main). Two corrections. (1) The '10.1 ms get_mask FRB' figure is all of ImageSubsetArray(), dstack and uint8 included; the mask FRB itself is about 6 ms. (2) The 23 ms gain needs the subset image artist not to rasterize a full-view image at all. Options are drawing only the crosshair, which also drops the 50%-alpha tint of the selected pixel that is visible when zoomed in, or giving the mask artist a bbox-sized extent. Computing the mask only inside the bbox but still returning a full-view array saves only about 6 ms; matplotlib's 12 ms resample and most of the 3.7 ms dstack remain. The composite cache saves at most about 8 ms, since the main image's 11.8 ms matplotlib resample still runs. So the realistic gain is about 14-31 ms per large viewer (about 20-43% of the draw), depending on the approach, against 'about 40%'. Evidence: hidpi-many-verify/v_mask.py with v_mask.log; v_points_{1,10}.log.

#### hidpi-many#7. At devicePixelRatio 2, image draw time grows with device pixels because matplotlib resamples glue's float64 RGBA composite at device resolution (not re-measured)

- **Slows:** Every image redraw on a HiDPI screen, and on large panels (slider ticks, point moves, pans)
- **Repository:** glue-core (matplotlib for the RGBA resample path); **confidence:** high; **share:** Image path about 67% of a full-tab static draw at DPR 2 and about 39% of the tick. Small at quicklook panel sizes (6 to 14 ms).

**Cost.**

SJI full tab (1568x797 logical), static redraw (15 draws, median): 58 ms at DPR 1 and 104 ms at DPR 2. Slider tick: 137 ms at DPR 1 and 185 ms at DPR 2. Si IV tick: 95.6 to 146.4 ms. Same splits from the breakdown and clip.py runs: make_image 30.7 to 71.7 ms (output 722x1443 to 1444x2886). The composite (FRB plus colormap) stays at 13-14 ms because the FRB is computed at 72 dpi independent of DPR; matplotlib resample 6.7 to 17.6 ms; Qt paintEvent 1.2 to 4.9 ms; Agg draw_image 2.4 to 9.1 ms. Clipping to the axes patch path adds only 1.6-6 ms. At 788x397 the draw goes 32.6 to 42.7 ms.

**Cause.**

glue/viewers/image/composite_array.py:166 allocates float64 RGBA (np.ones(data.shape + (4,))) and colormaps in float64. matplotlib/image.py _make_image RGBA path (lines 533-557) resamples float64 to the output size, demultiplies the whole array and converts to uint8 at device resolution (about 133 MB float64 per full-tab draw at DPR 2). Agg's option_scale_image is False (backend_agg.py:335-337), so interpolation='none' gives no unsampled shortcut (tested: no gain). The FRB is computed at axes size x 72 dpi (frb_artist.py:16-18 passes no dpi to mpl_scatter_density, base_image_artist.py:52,153-164) even when that exceeds the data pixels in view: 520x1039 bins for a 388x417 frame.

**Upstream main.**

glue origin/main dae530c3: composite_array.py and frb_artist.py identical to 1.27.0. matplotlib main not checked (no local clone).

**Candidate fix.**

(a) Build the composite in float32 (or uint8 when there is a single opaque layer). (b) Cap FRB bins at the reference-data pixels in view, aligned to pixel centres, in FRBArtist.array_func_wrapper (frb_artist.py:20-31), and let nearest-neighbour upsampling do the rest. Optionally ask matplotlib to skip the demultiply when alpha is 1.

**Gain.**

Measured with in-process toggles (imagefix.py; 15 static draws and 10 ticks per configuration). Float32: static draw -14 ms at DPR 2 full tab (104.0 to 90.2 ms) and -6 ms at DPR 1; uint8 output differs by at most 2 levels. Cap: -10 ms at full tab, 0 at panel sizes; my un-aligned prototype shifts edges by 1 screen pixel in 3-3.5% of pixels, which needs fixing. Both together: 104.0 to 79.8 ms static (-23%) and 181.7 to 156.6 ms tick (-14%) at DPR 2 full tab; 58.1 to 43.7 ms at DPR 1.

**Evidence.**

Confidence is high for the offscreen measurements and medium for how well the gains carry over to real screens. hidpi-many/breakdown_{sji,siiv}_dpr{1,2}.log; static_sji_dpr{1,2}.log; clip.py with clip_sji.log; imagefix.py with imagefix_sji.log; probe.py (QT_SCALE_FACTOR=2 gives dpr 2.0 and fig dpi 200).

#### hidpi-many#8. glue-solar's _GlueWCS wrapper spends more time than the FITS WCS it wraps (not re-measured)

- **Slows:** Slider ticks and redraws of IRIS raster viewers; every WCSAxes tick placement and glue link evaluation goes through it
- **Repository:** glue-solar; **confidence:** medium; **share:** 21% of a Si IV tick and 8% of an SJI tick. After the label-reset fix, which removes 4 of the 5 placements, about 2.5 ms (8%) of a Si IV tick remains.

**Cost.**

Per tick (800x500, 20 ticks, medians). Si IV (astropy FITS WCS): 249 transform calls; 20.9 ms inside _GlueWCS.pixel_to_world_values, of which only 8.4 ms is in the wrapped WCS, so the wrapper overhead is 12.5 ms of a 60.6 ms tick. SJI (gWCS): 169 calls, 68.5 ms inside the wrapper, 60.7 ms in the gWCS, overhead 7.8 ms of a 103.1 ms tick. Microbenchmark: Si IV 0.057 ms per call wrapped vs 0.017 ms raw for 2 points, 0.080 vs 0.036 ms for 1000 points.

**Cause.**

glue_solar/sources/loaders/iris.py:86-97 (identical at 2fdb847 and origin/main 5eae565): each call walks self.world_axis_physical_types and re-reads self._wcs.world_axis_units[i], building u.Unit(...) per axis, then converts via Quantity (values * unit).to_value(u.arcsec), all under WCS_LOCK. The astropy WCS regenerates physical types and units strings on every access.

**Upstream main.**

glue-solar origin/main 5eae565: the _GlueWCS code is the same.

**Candidate fix.**

Precompute per world axis, once (the WCS is immutable): whether it is helioprojective lon or lat, the scale factor from its unit to arcsec, and the wrap constant. pixel_to_world_values then only does numpy multiplications and the modulo; world_to_pixel_values uses the same factors.

**Gain.**

Estimated, not prototyped: most of the 12.5 ms per Si IV tick (about -20%) and 7.8 ms per SJI tick (about -7%) today; about 2.5 / 1.5 ms after the label-reset fix.

**Evidence.**

hidpi-many/wrapcost.py with wrapcost.log; wcscost.py with wcscost.log.

**Not measured in this area.** 1) Real screens. Everything ran on the offscreen platform. DPR 2 came from QT_SCALE_FACTOR=2, not a real HiDPI QWindow, so there is no compositor, vsync, GPU or Wayland/X11 difference here. I could not reproduce the user's 0.068 s (Wayland, DPR 2) versus 0.028 s (X11) slider tick. On this machine, DPR 2 adds 11 ms per SJI tick on a 788x397 panel and 48 ms on a full tab. The drag simulation suggests the uncompressed (Wayland-like) event delivery also matters, but it posts Qt events rather than using real mouse input. 2) The drag runs with the label fix and with coalescing+fix are 1 run each; all other configurations are 3 runs. 3) Not measured: Profile and spectrum viewer draws in detail (seen only as 2 draws per point move in the quicklook), pan/zoom drags, Mg II windows, the 3602506433 and 3824262996 datasets, glue-solar origin/main's sit-and-stare exposure-label callbacks (tools.py _label_exposures, which listens to the same x/y_axislabel round trip and may make that finding worse on panels that display the exposure axis), and transient memory per draw at DPR 2 (about 133 MB of float64 RGBA computed, not measured with tracemalloc). 4) Not checked against upstream: matplotlib main (no local clone), and the astropy fixes (frame-transform sharing and placement caching are estimates, not prototypes). 5) Prototypes run only in-process: the hidden-canvas and hidden-subset fixes were checked on a synthetic 100x400x400 cube, not IRIS data. 6) Timing noise: other agents ran concurrently (load average about 4.6 on 12 cores) and one drag run overlapped my own synthetic test, so expect a few ms of noise; medians were stable across repeats. Nothing in ~/Git was edited, installed or checked out. I only read upstream via git show; the astropy origin/main ref moved during the session, apparently fetched by another process, and I report the newer 1f930be7c4.

### Area: io-model

**Setup and baselines.** IO and glue's data model: loading IRIS files, Data/Component creation, DataCollection append/remove, links, autolinking, get_data/get_mask and session saving. glue-solar was the ~/Git/glue-solar-main checkout at 2fdb847 (#84), three merges behind origin/main 5eae565 (#86-#88). Those merges only touch glue_patches.py, tools.py and tests, so the loaders and quicklook.py I measured are the same as on main. glue_solar.__file__ was /Users/nabil/Git/glue-solar-main/glue_solar/__init__.py. Versions: glue-core 1.27.0, glue-qt 0.4.2, irispy 0.9.1, astropy 8.0.1, numpy 2.5.3. Machine: Apple M4 Pro, macOS, offscreen Qt, Agg, page cache warm. Every glue-core and glue-qt file I cite is byte-identical to upstream main (glue dae530c3, glue-qt 9780eaf9). Scripts and logs are in perf_survey_20261001/io-model/: common.py, load.py, gz.py, gz_alt.py, model.py, model2.py, proto_discover.py, app_add.py, session.py, session_proto.py, getdata.py, autolink.py, plus their *.log files. Nothing in any repo was edited or installed. Measurement-only stub savers (for _GlueWCS and Quantity) and the candidate-fix prototypes were registered or subclassed inside the scratch processes only. Loading is not where glue is slow. A 1600x417x262 Si IV window loads in 0.39 s (median of 4). glue keeps the irispy/astropy float32 array without copying it: the Component is a read-only view (owndata=False). Data and Component creation cost about 0.7 ms per dataset. The cost sits in the link manager, removal, session saving, the glue-qt data tree and the decompression of .gz files.

#### io-model#1. LinkManager.discover_links rescans every link after each link it accepts, about O(N^3) with link_hpc's star (confirmed)

- **Slows:** Loading a second observation into an open app (IRIS browser: extend, then keep_hpc_linked). Also: adding any dataset (a derived map, a stack, another file) to a collection of linked IRIS data, and running keep_hpc_linked or 'IRIS: link helioprojective coordinates'.
- **Repository:** glue-core; **confidence:** high; **share:** discover_links is 15.8 of 16.4 s of cProfile cumtime of the update during a single append (96%). In the app browser path, the link manager is about 7 of 9.1 s wall (77%), or 16.7 of 19.0 s under cProfile (88%).

**Cost.**

Headless, with fresh Data objects sharing the loaded arrays, each timed with perf_counter. keep_hpc_linked on 102 datasets (99 Si IV scans of 3602506433, 2 of 4000005156, SJI 2796): median 6.96 s of 5. Appending 1 dataset to a linked collection of 101: median 6.87 s of 5. Scaling of that append: 12 datasets 0.012 s, 27: 0.131 s, 52: 0.927 s, 101: 6.87 s (all medians of 3 or 5). In the glue-qt app (1600x1000, 4000005156 quicklook open): adding the 99 scans by the browser path takes 9.12, 9.13 and 8.96 s (3 fresh processes, median 9.12 s). Appending one dataset and relinking takes a median of 14.3 s (14.34, 15.39, 13.87).

**Cause.**

glue/core/link_manager.py:54-96 (discover_links). After each accepted link, the 'break' at line 90 restarts 'while True' at line 77, which calls accessible_links (lines 38-51) again. That function rebuilds set(link.get_from_ids()) for every link. update_externally_derivable_components (line 218) runs this for every dataset over self._links | self._inverse_links (line 249). link_hpc's star makes every dataset able to derive the lon/lat of every other one, a mean of 402 derivable cids at 102 datasets across 1016 links. Profile: 41,230 accessible_links calls and 54M get_from_ids calls for one update.

**Upstream main.**

Same code on glue main (dae530c3). link_manager.py is byte-identical to the installed 1.27.0, and git history shows no branch touching discover_links since 'Refactor how data collection and link manager handle links'.

**Candidate fix.**

Replace the restart loop with a worklist. Index the links by input ComponentID, keep a per-link count of missing inputs, and add a link to the frontier when its last input becomes known, expanding by depth level so each cid keeps its minimum depth as now. Also compute self._links | self._inverse_links once per update instead of rebuilding the sets.

**Gain.**

Prototype in proto_discover.py, run side by side with glue's function on the same links, gives the same derivable cid sets. 10 datasets: 0.005 to 0.0006 s. 25: 0.093 to 0.0035 s. 50: 0.78 to 0.014 s. 102: 7.22 to 0.059 s (median of 3; 122x). Expected effect: the 9.1 s browser load drops to about 1.5 s (the remainder is glue-qt, see the DataCollectionModel finding), and a single append on 102 datasets drops from 6.9 s to about 0.16 s (worklist plus the existing equivalent_pixel_cids pass).

**Evidence.**

io-model/model_run1_N102.log, model2_small.log, model2_k50.log, proto_discover.log, app_add_time.log, app_add.log

**Second measurement.** Headless, iris-plan env, glue-solar-main 2fdb847 (15 commits behind origin/main 5eae565, but quicklook.py and sources/ are unchanged). Fresh Data objects shared the loaded arrays: 2 Si IV scans of 4000005156, deconvolved SJI 2796, and 99 Si IV scans of 3602506433, RSS about 1.9 GB. keep_hpc_linked on 102 datasets: median 6.84 s of 3 (6.84, 6.82, 7.10). Appending 1 dataset to a linked collection, median of 3 each: 11 datasets 0.010 s, 26: 0.114 s, 51: 0.838 s, 101: 6.71 s. That is about 8x per doubling, so O(N^3). cProfile of the 101 append: discover_links 14.64 of 15.21 s (96%), 40,302 accessible_links calls, 53.3M get_from_ids calls; 1016 links, mean 402 derivable cids. glue-qt app at 1600x1000 with the 4000005156 quicklook open, wall time, one fresh process per run: browser path (extend 99 scans, then keep_hpc_linked) 8.65, 9.20, 8.44 s, median 8.65 s. Appending one dataset and relinking: 14.67 and 14.70 s. Under cProfile, update_externally_derivable_components is 16.37 of 18.6 s of wall (88%). My own independent worklist (level-by-level, missing-input counters) gives the same derivable cid sets for every dataset at k=10, 25, 50 and 102. Its time against glue's discover over all datasets: 0.0053 to 0.0004 s, 0.094 to 0.0022 s, 0.77 to 0.0087 s, and 6.87 to 0.037 s (188x at 102).

**Correction.** Cost, cause (link_manager.py:54-96, 218-265; byte-identical on glue main dae530c3) and fix all hold. Gain: the worklist is 188x on discover alone (claim 122x). A full update after the fix also keeps about 0.19 s of other work at 102 datasets (pairwise pixel pass 0.14 s plus DerivedComponent setup), so a single append drops to about 0.23 s rather than 0.16 s. The browser load drops from 8.65 s to about 1.6 s (extend with the tree work 1.37 s, plus the fixed relink 0.23 s), in line with the claimed 1.5 s. Caveat: in the app, cProfile's own accounting is unreliable (total_tt 37 s against an 18.6 s wall, and discover_links shows only 4.15 s cum), so the in-app share above comes from the wall time and the update cumtime.

#### io-model#2. Removing a linked dataset runs a full link-manager update for every link it drops, and clear() does not batch (confirmed)

- **Slows:** Deleting data in the glue-qt layer tree (Delete calls dc.remove once per selected dataset), removing link_hpc's first (anchor) dataset, and DataCollection.clear().
- **Repository:** glue-core; **confidence:** high; **share:** Effectively all of it. Removing the anchor at 53 datasets: remove_link 72.7 s of 72.7 s profiled, 104 remove_link calls giving 105 full updates (5,460 discover_links calls and 2,808 ExternallyDerivableComponentsChangedMessage).

**Cost.**

Headless, link_hpc-linked collections. Removing 1 non-anchor dataset: 13 datasets 0.023 s, 28: 0.264 s, 53: 1.86 s (median of 3). Removing the anchor, including glue-solar's relink: 13 datasets 0.127 s, 28: 2.44 s (median of 3), 53: 31.3 s (1 run). clear() of 53: 29.3 s (1 run). Deleting the 50 scans one by one from 53: 24.8 s (1 run). In the app, deleting 25 scans from 28 takes a median of 2.61 s (3 processes; 1.9 s headless). Removing from an unlinked collection takes under 1 ms. Not run at 102 datasets: extrapolated from the scaling, removing the anchor would take several minutes.

**Cause.**

glue/core/link_manager.py:158-166 (_data_removed) calls self.remove_link(link) once per link. remove_link (line 194) defaults to update_external=True, so each call runs update_externally_derivable_components over every dataset. DataCollection.clear (glue/core/data_collection.py:128-131) wraps the removals in _ignore_link_manager_update, but LinkManager.remove_link never checks that flag. The anchor carries 2 links per other dataset.

**Upstream main.**

Same code on glue main. link_manager.py and data_collection.py are identical to 1.27.0.

**Candidate fix.**

In _data_removed, collect the links and call self.remove_link(remove) once. remove_link already accepts a list and updates once. Also skip the update while the DataCollection is inside _ignore_link_manager_update (clear, extend) and sync once on exit, as delay_link_manager_update does.

**Gain.**

Anchor removal at 53 datasets drops from 104 updates to 1: about 31 s to about 0.9 s with today's discover_links, or under 0.1 s together with the worklist fix. Deleting a non-anchor dataset drops from 2 updates to 1 (about 2x). clear() needs no update at all.

**Evidence.**

io-model/model2_small.log, model2_k50.log, model2_k50_anchor.log, app_add_time.log

**Second measurement.** Headless, link_hpc-linked collections, median of 3 unless noted. Removing 1 non-anchor dataset: 13 datasets 0.023 s, 28: 0.249 s, 53: 1.79 s. Removing the anchor, including glue-solar's relink: 13: 0.124 s, 28: 2.40 s, 53: 30.0 s (1 run). clear(): 28 datasets 2.27 s, 53: 29.1 s (1 run). Deleting the 50 scans one by one from 53: 24.0 s (1 run). Removing from an unlinked collection of 53: under 1 ms. In the app (3 fresh processes), deleting 25 scans from 28: 2.60, 2.57 and 2.51 s, median 2.57 s. cProfile of the anchor removal at 28 datasets: 54 remove_link calls and 55 full update_externally_derivable_components calls, so 2 links per other dataset plus 1 relink, which scales to the claimed 104/105 at 53. The batched fix was simulated without patching: one lm.remove_link(list) of the anchor's links, then dc.remove, then the relink. It took 0.014 s at 13 datasets, 0.135 s at 28 and 0.93 s at 53 (median of 3), against 0.124, 2.40 and 30.0 s today.

**Correction.** None material. The cause holds: _data_removed calls remove_link once per link, and remove_link ignores _disable_sync_link_manager, so clear() pays per link. Code is identical on glue main. The measured gain of the batched fix at 53 datasets (30 s to 0.93 s, 32x) matches the claimed ~0.9 s. The several-minute figure at 102 datasets is still an extrapolation: the measured scaling is about 12x per doubling, which predicts about 6 min. Not run.

#### io-model#3. Session save serializes every object on each do_all pass and writes broadcast components out at full size (confirmed)

- **Slows:** File > Save Session (app.save_session) with IRIS data, with include_data True or False. Without stub savers, glue-solar datasets fail to save today: _GlueWCS has no saver, and Quantity meta raises TypeError in np.save.
- **Repository:** glue-core (do_all, _save_numpy); glue-solar for LoadLog and the stub savers; **confidence:** high; **share:** Time and Exposure time are zero-stride broadcast components (strides (8, 0, 0)). They are saved as full arrays: 538 MB plus about 564 MB of the 1412 MB, about 78%. Each Component is serialized 2x for a DataCollection (_save_component 16 calls for 8 components) and 3x for the app (24 calls for 8). The base64 encoding of components dominates the profile (1.45 of 1.99 s).

**Cost.**

With in-process stub savers. Two Si IV 1403 scans of 4000005156 (252 MB of real arrays): DataCollection save median 3.6 s of 3, app save with the quicklook median 4.6 s of 3, each producing 1412 MB of JSON. RSS peaked at 4.2-4.3 GB, slightly over the 4 GB budget. include_data=False gives the same 1412 MB because browser-loaded datasets have no LoadLog. Memory-safe repeats: 10 scans of 3602506433: 0.654 s and 274 MB; app with a 2-scan quicklook: 0.170 s and 55 MB.

**Cause.**

glue/core/state.py:326-334 (GlueSerializer.do_all) re-runs self.do(obj) on every registered object on each pass until no new objects are registered. Components registered early are therefore base64-encoded again on every later pass. glue/core/state.py:1266-1271 (_save_numpy) calls np.save on the array as given, which writes a broadcast_to view out in full.

**Upstream main.**

Same code on glue main. state.py is identical to 1.27.0.

**Candidate fix.**

(1) In do_all, serialize only objects not yet serialized, and loop while new ones appear. (2) In _save_numpy, save glue.utils.unbroadcast(arr) plus the original shape, and broadcast back in _load_numpy. This needs a small loader change. glue-solar's planned D13 (added components saved as 1-D vectors) and wp3-file-references (LoadLog) address the same symptom on the glue-solar side.

**Gain.**

Measured with in-process subclasses, glue not patched. One pass per object: 0.654 to 0.462 s (10 scans) and 0.170 to 0.098 s (app), with byte-identical JSON. Adding unbroadcast: 0.110 s and 65 MB (10 scans), 0.028 s and 13 MB (app), about 6x faster and 4x smaller. For the 2-scan 4000005156 app session, expect about 4.6 s and 1.4 GB to become under 1 s and about 350 MB.

**Evidence.**

io-model/session.log, session2.log, session_proto.log, session_proto2.log

**Second measurement.** Stub savers registered only in my process. Without them, save fails with TypeError (np.save on a Quantity). With only the Quantity stub it fails with GlueSerializeError: no saver for _GlueWCS. Both blockers confirmed. 10 Si IV scans of 3602506433: GlueSerializer.dumps median 0.681 s of 3, 287 MB JSON (274 MiB). Same size with include_data=True. _save_component ran 80 times for 40 components (2x). App with a 2-scan quicklook: dumps median 0.175 s of 3; app.save_session median 0.194 s of 3; 57 MB; _save_component 24 times for 8 components (3x). Large case, kept under the memory budget at 1 scan of 4000005156 Si IV (RSS peak 2.56 GB): 1.93 s and 741 MB JSON, same size with include_data=True. b64encode 0.72 s and json.dumps 0.80 s of 1.78 s profiled. That is half of the claimed 2-scan figure (1412 MiB, 3.6 s), as expected. Zero-stride Time/Exposure time, strides (8,0,0): 76% of the component bytes in all three cases (claim 78%). One-pass do_all subclass gives byte-identical JSON: 0.681 to 0.477 s (dc10), 0.175 to 0.105 s (app2), 1.93 to 1.33 s (1 scan of 4000005156).

**Correction.** Holds. The one-pass fix alone gives only 1.4-1.7x. Most of the gain comes from unbroadcasting: about 76% of the bytes, and with them the base64 and json.dumps time, which scale with size. Sizes in the claim are MiB (1412 MiB = 1482 MB). I did not re-run the 2-scan 4000005156 save (it peaks above the 4 GB budget) or time the unbroadcast variant. Its size reduction (to about 24% of today's) follows from the measured array bytes.

#### io-model#4. Opening an SJI .fits.gz decompresses the whole file 4-5 times (confirmed)

- **Slows:** Opening a slit-jaw (or deconvolved SJI, or AIA cutout) .fits.gz through File > Open (glue load_data, which uses glue-solar's factory), through the IRIS browser (image_data), or through glue's own FITS reader.
- **Repository:** astropy (root cause), irispy, glue-solar (identifier), glue-core (fits_reader); **confidence:** high; **share:** zlib decompress is 1.78 of 2.38 s in the cProfile of load_data (75%). Against a decompress-once read (0.41 s for open plus all HDU data), about 80% of the 2.15 s is repeated decompression.

**Cost.**

SJI 1400 of 4000255147 (124 MB uncompressed), median of 3 after a warm-up, with decompressed bytes counted. One gzip decompression: 0.337 s. glue load_data(auto): 2.15 s (5.0x the file). image_data / irispy read_files: 1.78 s / 1.63 s (4x). glue fits_reader: 1.58 s (4x). glue-solar is_iris_fits for one header: 0.39 s (1x). fits.open plus primary data: 0.79 s (2x).

**Cause.**

astropy.io.fits on gzip files: reaching any HDU after the large primary data seeks forward through it, which decompresses it, and reading the data then seeks back, which rewinds and decompresses again (Python gzip). Every fits.open or getheader therefore costs at least one full decompression. Callers open the same file repeatedly: glue-solar sources/iris.py:19-21 (is_iris_fits uses fits.getheader); irispy io/utils.py:34 getheader, then io/sji.py:200 fits.open plus verify, then data and aux reads; glue core/data_factories/fits.py (fits.open plus verify('fix'), then data per HDU).

**Upstream main.**

irispy io/utils.py, sji.py and spectrograph.py are identical to LM-SAL main. astropy upstream main's io/fits/file.py differs only by an is_url rename, and hdulist.py and base.py are identical. glue fits.py and helpers.py are identical to main.

**Candidate fix.**

glue-solar: read only the primary header in the identifier, with fits.Header.fromfile(gzip.open(path)) (measured 0.4 ms instead of 0.39 s). irispy and glue fits_reader: when the file is gzip, decompress once into BytesIO and open that. astropy: optionally keep the decompressed stream for read-only gzip opens, since gzip files are never memory-mapped anyway.

**Gain.**

Decompress once and read all HDUs: 0.414 s (median of 3) against 2.15 s for load_data, about 1.7 s saved per SJI file (5x). The identifier alone saves 0.39 s per .gz file, including during File > Open's format detection.

**Evidence.**

io-model/gz.log (decompression passes counted per path), gz_callers.log, load_time.log

**Second measurement.** SJI 1400 of 4000255147 (129.6 MB uncompressed). Median of 3 after a warm-up; decompressed bytes counted by wrapping gzip._GzipReader.read in my process. One gzip decompress: 0.357 s. glue load_data (auto): 2.18 s (5.00x the file). glue-solar image_data: 1.78 s (4x). irispy read_files: 1.64 s (4x). glue fits_reader: 1.56 s (4x). glue-solar is_iris_fits: 0.39 s (1x). fits.open plus primary data: 0.77 s (2x). Decompress once into BytesIO, then fits.open and all HDU data: 0.417 s (1x). Header.fromfile(gzip.open) for the identifier: about 1 ms (0x, it stops after the header). cProfile of load_data: zlib decompress 1.79 of 2.40 s (74%), in 64,627 calls. Upstream: irispy io/utils.py, sji.py and spectrograph.py are identical to LM-SAL main 813f4cc. astropy upstream main's file.py differs only by the is_url rename; hdulist.py and base.py are identical. glue fits.py and helpers.py are identical to main.

**Correction.** Cost and cause confirmed, but the gain is overstated. The 0.414 s decompress-once read is not comparable to a full load_data, which also builds the WCS and glue Data (about 0.39 s of non-decompression work). Decompressing once saves 4 x 0.357 = about 1.43 s, taking load_data from 2.18 s to about 0.75 s (about 2.9x), not 1.7 s and 5x. The identifier change saves about 0.39 s per .gz file, as claimed.

#### io-model#5. glue-qt's data tree rebuilds itself and reloads icons from disk for every dataset or subset added (confirmed)

- **Slows:** Adding many datasets in the app: File > Open of many files (app.add_datasets) or the IRIS browser loading 99 scans, here with a quicklook (Point subset group) open.
- **Repository:** glue-qt; **confidence:** medium; **share:** Under cProfile, DataCollectionModel._on_add_data plus _on_add_subset are 1.82 of 2.41 s of extend (75%), so about 1.0 s of the 1.36 s wall. For 99 datasets: 11,401 layer_icon calls, 125k lstat calls and 198 full invalidations.

**Cost.**

app.add_datasets of 99 Si IV scans (no links): 1.359, 1.340 and 1.369 s wall in 3 fresh processes (median 1.36 s). Headless DataCollection.extend of the same data: 0.16 s.

**Cause.**

glue_qt/core/data_collection_model.py:413-426. Each DataCollectionAddMessage, and each SubsetCreateMessage (the open Point group adds a subset to every new dataset), rebuilds the whole tree (invalidate, then layoutChanged) and emits new_item. new_item calls select_indices (line 468), and selection_changed then re-queries every row. Each DecorationRole query calls layer_icon (glue_qt/icons/helpers.py:26), which loads the PNG from disk through glue.icons.icon_path (realpath and lstat) and tints it, with no cache. The work is O(N^2) in datasets added.

**Upstream main.**

Same on glue-qt main. data_collection_model.py and icons/helpers.py are identical to 0.4.2.

**Candidate fix.**

Cache icons per (marker, colour), for example with lru_cache on the tinted pixmap. Insert rows (beginInsertRows/endInsertRows) instead of rebuilding the model, and select only the newest item once. Alternatively, have DataCollection.extend coalesce the add messages with hub.delay_callbacks.

**Gain.**

About 1.0 s to under 0.1 s for 99 datasets (estimated from the profile share, not prototyped). It grows quadratically with the number of datasets loaded at once.

**Evidence.**

io-model/app_add.log (cProfile), app_add_time.log

**Second measurement.** app.add_datasets of 99 Si IV scans (3602506433) with the 4000005156 quicklook and its Point group open, app at 1600x1000, one fresh process per run: 1.361, 1.371, 1.365 and 1.364 s, median 1.365 s. The fix's upper bound was measured without patching: the app's DataCollectionModel was unsubscribed from DataCollectionAddMessage and SubsetCreateMessage before the add, and the same add then took 0.185 and 0.183 s. The model's per-message reactions therefore cost about 1.18 s (87% of wall). cProfile: _on_add_data 99 calls, cum 0.91 s; _on_add_subset 99 calls, cum 0.84 s (198 rebuilds); select_indices 198 calls, 1.31 s cum (nested); layer_icon 11,401 calls, 1.03 s cum; 125,411 lstat calls. The profiled wall was 2.61 s. data_collection_model.py and icons/helpers.py are identical on glue-qt main.

**Correction.** Holds, and the measured cost is slightly larger than the claimed ~1.0 s: about 1.18 s of 1.365 s. Confidence can rise to high for the cost and cause. The claimed gain to under 0.1 s for the tree is still an estimate: unsubscribing is an upper bound, because a real row-insert fix keeps some per-row cost.

#### io-model#6. Every single append runs a full link-manager update with an all-pairs equivalent_pixel_cids pass; the glue-solar quicklook appends one dataset at a time (confirmed)

- **Slows:** quicklook(app, datasets) called with datasets not yet in the collection (quicklook.py adds them one by one), scripts that append in a loop, and every append in general.
- **Repository:** glue-core; glue-solar (quicklook loop); **confidence:** high; **share:** equivalent_pixel_cids is 16.1 of 18.6 s profiled (353,702 calls) in the one-at-a-time case, and 0.46 of 0.53 s in a single extend.

**Cost.**

Headless, 102 datasets with no links. Appending one at a time: median 5.53 s of 3 (5.55, 5.50, 5.53), against 0.161 s for one extend (median of 5; 34x). A single all-pairs equivalent_pixel_cids pass at 102 datasets takes 0.103 s.

**Cause.**

glue/core/data_collection.py:59-90: append calls _sync_link_manager, a full update_externally_derivable_components. Its loop at glue/core/link_manager.py:257-264 calls equivalent_pixel_cids for every ordered pair of datasets. Each call runs is_equivalent_cid and _find_identical_reference_cid, which rebuild the main, coordinate and derived component lists. glue-solar quicklook.py:792-794 calls collection.append(data) in a loop.

**Upstream main.**

glue code same on main. glue-solar quicklook.py is unchanged between 2fdb847 and origin/main.

**Candidate fix.**

glue-solar: collection.extend([d for d in datasets if d not in collection]), a one-line change. glue-core: skip the pairwise pass when no identity link touches a pixel ComponentID (collect those cids once per update), or recompute pixel alignment only for datasets whose links changed.

**Gain.**

glue-solar: 99 new scans in a quicklook drop from about 5.5 s to about 0.16 s. glue-core: each update drops by about 0.1 s at 100 datasets, up to the full 5.5 s on loops of appends.

**Evidence.**

io-model/model_run1_N102.log, proto_discover.log

**Second measurement.** Headless, 102 unlinked datasets. Appending one at a time: 5.39, 5.38 and 5.38 s, median 5.38 s. One extend: median 0.158 s of 5 (34x). cProfile of the one-at-a-time case: equivalent_pixel_cids 15.69 of 18.08 s, 353,702 calls (exactly the claimed count). In a single extend it is 0.46 of 0.53 s. One all-pairs pass at 102 datasets: median 0.142 s of 5 unlinked, 0.138 s linked. Cause check inside the pass: _find_identical_reference_cid is 1.35 of 1.41 s cum, spent rebuilding main_components (185,742 calls), coordinate_components and derived_components. It also makes 1.39M ComponentID.__eq__ calls through 'cid in list' and 6.7M isinstance calls. glue-solar quicklook.py:791-793 appends in a loop, unchanged on origin/main.

**Correction.** Holds. The pass costs 0.14 s at 102 datasets, not 0.103 s, so the glue-core saving per update is about 0.14 s. Note that the quicklook loop only bites when quicklook() gets datasets not yet in the collection. The IRIS browser extends first, so its quicklook call appends nothing.

#### io-model#7. glue's WCS autolinker suggests and accepts links for every pair of datasets (not re-measured)

- **Slows:** File > Open of many raster files through glue's own FITS reader (or any FITS cubes), where glue-qt's add_datasets runs the 'Astronomy WCS' autolinker. glue-solar data is not affected today: _GlueWCS is low-level only, so the autolinker skips it (0 suggestions measured). The comment in glue_solar/sources/iris.py says glue-viz/glue#2595 would change that.
- **Repository:** glue-core; **confidence:** medium; **share:** Accepting the suggestions (add_link, which goes through discover_links) is 91% of the 3.1 s at 25 scans.

**Cost.**

Si IV headers of 3602506433 as WCSCoordinates, with glue plugins loaded, median of 3. 10 scans: find_possible_links 0.046 s, 45 links, accepting them 0.068 s. 25 scans: 0.275 s, 300 links, accepting them 2.87 s. 50 and 99 scans not run (more than a minute expected).

**Cause.**

glue/plugins/wcs_autolinking/wcs_autolinking.py:316-345 builds a WCSLink for every pair (the code's own comment at lines 333-335 says 'PERF: in practice we don't actually have to link all pairs'). glue-qt dialogs/autolinker (AutoLinkPreview.suggest_links) then adds them all.

**Upstream main.**

Same code on glue main and glue-qt main.

**Candidate fix.**

Suggest one link per dataset to a reference dataset in each compatible group (a star, as link_hpc does), and keep the all-pairs search only for detecting compatibility.

**Gain.**

Measured at 25 scans: accepting the 24 star links takes 0.215 s against 2.87 s for all 300 pairs (13x). The gap widens with N, and the discover_links fix lowers both.

**Evidence.**

io-model/autolink.log

**Not measured in this area.** Not measured, or measured and not reported as a finding:

1. **Session restore.** Load time was not measured. Saving glue-solar data needed in-process stub savers for _GlueWCS and Quantity, so the WCS saving cost is not known. The File > Open (load_data) session failed to save with "LinearSegmentedColormap is not JSON serializable", a known WP3 issue. A 4000255147 Si IV session was not attempted: it would be about 4 GB of JSON. The 4000005156 session runs peaked at 4.2-4.3 GB RSS, slightly over the budget.

2. **Runs at 102 datasets.** Removing the anchor and clear() were not run at this size (extrapolated to several minutes); 53 datasets is the largest measured.

3. **Measurement conditions.** All timings are with a warm page cache on an M4 Pro with offscreen Qt and Agg. Cold-disk IO and real-screen draws were not measured. The glue-qt File > Open wizard and the IRIS browser dialog were not driven by hand; I called app.add_datasets and the extend + keep_hpc_linked path directly. The app scenarios cannot be repeated inside one process, so each is a median of 3 fresh processes.

4. **Measured, no fix needed.**
   - **Load time.** Si IV 1403 of 4000255147 loads in 0.39 s (median of 4). irispy read and glue-solar conversion are about half each.
   - **Copies.** glue keeps the irispy/astropy float32 array without copying it (the Component is a read-only view).
   - **Memory.** astropy's BSCALE scaling creates a transient int16 buffer: tracemalloc peaks at 1.17 GB while retaining 835 MB (667 MB float32 plus glue-solar's 167 MB uint8 mask). RSS peaks at 1.55 GB. memmap=False in glue-solar; glue's FITS reader memory-maps, but BSCALE forces scaling into memory anyway.
   - **The 99 scans.** They load in 1.6 s. irispy's read_files is 1.3 s of that, with hdulist.verify('silentfix') and astropy config lookups about a third of the profile: irispy and astropy, small.
   - **Data and Component creation.** About 0.7 ms per dataset.
   - **get_data.** World coordinates are recomputed on each call (about 18 ms for the raster's lon/lat over 1600x417).
   - **get_mask.** Pixel-axis ROIs take 0.5 ms (rectangle) and 6 ms (polygon). A RangeSubsetState over the full cube takes 0.11 s and 333 MB, which is inherent. A RectangularROI on world lon/lat over the full cube takes 0.25 s with a 344 MB peak, because RectangularROI.contains does not unbroadcast while points_inside_poly does. Image-viewer ROIs use pixel cids, so IRIS users rarely hit this.
   - **Hub.** Broadcast overhead with 51 subscribers is small next to the handlers it calls (message counts per action are in the logs).

5. **Not investigated.**
   - irispy/ndcube cubes sit in reference cycles, so their masks (113 MB for one 4000005156 file via load_data) stay alive until the cyclic GC runs.
   - The ExternallyDerivableComponentsChangedMessage that every dataset receives after each link change triggers updates in open viewers and image layers; I did not separate that redraw cost from the link manager.

### Area: links

**Setup and baselines.** Linked subsets and link resolution (glue-core 1.27.0, glue-qt 0.4.2, irispy 0.9.1, astropy 8.0.1, numpy 2.5.3, Python 3.13, PyQt5 offscreen, Agg, devicePixelRatio 1, app 1600x1000). glue_solar was imported from /Users/nabil/Git/glue-solar-main at 2fdb847 (PR #84). That is 3 PRs behind origin/main 5eae565 (#86-#88). quicklook.py and sources/loaders/iris.py are the same in both; glue_patches.py gained the Pixel crosshair workaround, which this run does not include. Upstream comparisons used the local refs without a new fetch: glue origin/main dae530c3 (2026-07-13) and glue-qt origin/main 9780eaf9 (2026-02-17). Every installed file cited below (link_manager.py, component_link.py, coordinate_helpers.py, subset.py, data.py, data_collection.py, fixed_resolution_buffer.py, viewers/image/{layer_artist,viewer,state}.py, dialogs/link_editor/state.py, glue-qt compute_worker.py and link_editor.py) is byte-identical to upstream main. Scripts and logs are in perf_survey_20261001/links/ (common.py, 01-10 *.py with matching *.log and *.prof). Nothing was patched or installed. Profiling note: in Python 3.13, cProfile records every thread. glue-qt's ComputeWorker threads loop on time.sleep(1/25) forever (glue_qt/viewers/matplotlib/compute_worker.py:31-33), so in-app cProfile output attributes their time to the main thread's frames and is unusable. For profiles I used single-threaded runs without Qt (02, 03, 05-10) and a main-thread stack sampler (common.Sampler, 1 ms) in the app runs.

#### links#1. A raster ROI's mask on a linked slit-jaw viewer runs the same world-to-pixel inversion once per ROI attribute (confirmed)

- **Slows:** Changing the frame of an SJI viewer (slider, play, or the quicklook moving it) while a subset drawn on a raster map is shown on it; also any redraw after the mask cache is dropped
- **Repository:** glue-core; **confidence:** high; **share:** The mask is 98% of an SJI frame change for 4000255147 and 82% for 4000005156. Each of the two attribute evaluations is 48-49% (4000255147) or 45% (4000005156) of the mask, and both run the identical inversion.

**Cost.**

In the app (01, n=5 medians, SJI axes 484x252 px giving a 348x181 FRB): 4000255147 SJI 1400 took 4.87 s per frame with the ROI against 0.10 s without it. 4000005156 SJI 2796 deconvolved took 0.58 s against 0.10 s. Hiding the ROI layer on the SJI viewer gave 0.10 s. Single-threaded with the same bounds (02, n=3): FRB mask 4.79 s; sji[raster Pixel Axis 0] 2.33 s; sji[raster Pixel Axis 1] 2.31 s; one raster world_to_pixel_values call on the same points 2.31 s. The SJI's own world coordinates took 4.5 ms each and roi.contains 0.1 ms. For 4000005156: 0.48 s total, 0.218 s and 0.216 s per attribute. At a doubled FRB (696x362, standing in for dpr 2) the 4000255147 mask took 31.0 s.

**Cause.**

glue/core/subset.py:563-564 (RoiSubsetStateNd.to_mask) evaluates data[att, view] separately for xatt and yatt. Each call goes through DerivedComponent -> ComponentLink.compute (glue/core/component_link.py:166, recursive with no memo) -> CoordinateComponentLink.using (component_link.py:395) -> world2pixel_single_axis (glue/core/coordinate_helpers.py:122-124). That function calls the full wcs.world_to_pixel_values for all axes and keeps one. At runtime glue-solar's gated copy (glue_solar/glue_patches.py:52-54) does the same. The SJI world coordinates are also recomputed four times (once per raster world input per attribute), but that costs only about 18 ms. get_data in 07 shows the same pattern: the single-axis sji[raster pixel 1] and sji[raster pixel 0] cost 2.04 s and 2.05 s for 100x100 pixels, and the single-axis SJI lon costs the same as all three axes at once (0.0122 s against 0.0116 s per frame).

**Upstream main.**

Same code on glue origin/main (subset.py, component_link.py and coordinate_helpers.py are identical to the installed files).

**Candidate fix.**

Compute every needed pixel axis of the linked dataset from one world_to_pixel_values call. Options: a cache local to one to_mask/get_mask call, keyed on (coords, input cids, view identity), shared by sibling CoordinateComponentLinks of the same WCS; or have CoordinateComponentLink keep its last full result keyed on the identities of its input arrays.

**Gain.**

About 2x per frame: 4.79 s to about 2.4 s (4000255147, dpr 1) and 0.48 s to about 0.27 s (4000005156). This is estimated from the per-piece timings, not prototyped inside glue.

**Evidence.**

perf_survey_20261001/links/01_roi_sji_4000255147.log, 01_roi_sji_4000005156.log, 02_roi_core_4000255147_s1.log, 02_roi_core_4000005156_s1.log, 02_roi_core_4000255147_s2.log, 02_roi_core_4000255147_484x252.log (cProfile: 26.586 of 26.629 s in 2 calls of Wcsprm.s2p), 07_get_data.log

**Second measurement.** In the app (links-verify/v2_app.py, quicklook, 1600x1000 window, SJI axes 484x252 px, dpr 1, offscreen Agg, n=5 frame changes each). 4000255147: 4.789 s with the raster ROI shown, 0.098 s without it and 0.101 s with the ROI layer hidden, so the mask is 98% of the action. 4000005156: 0.571 s, 0.100 s and 0.102 s (83%). Single-threaded (links-verify/v1_core.py, same FRB bounds, n=3). 4000255147: the FRB mask took 4.641 s; cProfile shows 2 calls of Wcsprm.s2p for 4.639 of 4.663 s (99.5%); sji[Pixel Axis 0] alone 2.245 s and sji[Pixel Axis 1] alone 2.256 s (48% and 49%). 4000005156: 0.463 s, with the two attributes at 0.208 s and 0.210 s. At a doubled 696x362 buffer (4000255147, n=1) the mask took 29.7 s, again 2 s2p calls (99.7%). I timed the fix directly, without patching: one SJI pixel_to_world_values, one raster world_to_pixel_values and roi.contains. It took 2.256 s (2.06x faster), 0.205 s for 4000005156 (2.26x) and 14.3 s at the doubled buffer (2.07x). The masks were 100.000% identical to glue's in all three cases.

**Correction.** Cost, share and cause all hold. The installed subset.py:564, component_link.py:166/375 and coordinate_helpers.py:122-124 match the cited code, and glue-solar's gated copy is at glue_patches.py:52-54. All of them are identical on glue origin/main (last fetched 2026-07-13, dae530c3). The 4000005156 gain is better than estimated: 0.463 s to 0.205 s, not about 0.27 s. glue-solar-main is at 2fdb847 (PR #84), 15 commits behind its origin/main (#88). The only relevant later change adds a crosshair workaround to ImageSubsetLayerArtist._update_visual_attributes, which does not touch the mask computation. Some runs overlapped another single-threaded job on the 12-core machine; the numbers still match the original within 5%.

#### links#2. Linked ROI masks are evaluated for every screen pixel, though the ROI covers 2-9% of the buffer (confirmed)

- **Slows:** Same action as above: each SJI frame change or redraw with a raster ROI shown on the SJI
- **Repository:** glue-core; **confidence:** medium; **share:** The bounding box covers 1.9% (4000255147) and 9.2% (4000005156) of the buffer. The other 90-98% of the inversion work produces False.

**Cost.**

Prototype outside glue (02, n=3). It maps the ROI outline forward (raster pixel -> world -> SJI pixel at the current frame, which is cheap) and inverts only the screen pixels inside its bounding box plus a 2 px margin. Results: 4000255147 4.79 s to 0.22 s (348x181 buffer) and 31.0 s to 3.06 s (696x362). 4000005156: 0.48 s to 0.049 s. The masks were identical to glue's in all three cases (100.000% agreement).

**Cause.**

glue/core/fixed_resolution_buffer.py:312 asks data.get_mask for every screen pixel of the FRB. The RoiSubsetStateNd.to_mask shortcut (glue/core/subset.py:569) applies only when the ROI attributes are the data's own pixel components. On a linked dataset the inverse link chain is therefore evaluated everywhere, including far outside the raster footprint.

**Upstream main.**

Same code on glue origin/main.

**Candidate fix.**

In RoiSubsetState(Nd).to_mask, or in compute_fixed_resolution_buffer for subset states: when the ROI attributes are pixel or world components of another dataset with a forward chain to the displayed one, transform the ROI vertices forward and evaluate the inverse chain only inside their bounding box (plus margin). Everything else is False. Fall back to the current path when the forward chain is missing or not finite.

**Gain.**

10-22x on top of the 2x above. Measured as 4.79 s to 0.22 s per frame at dpr 1 and 31 s to 3.1 s at dpr 2 for 4000255147.

**Evidence.**

02_roi_core_4000255147_s1.log, 02_roi_core_4000255147_s2.log, 02_roi_core_4000005156_s1.log (the 'candidate (b)' line). The prototype covers only a rectangular ROI in raster pixel space; polygon ROIs, world-attribute ROIs and wrap-around were not tested.

**Second measurement.** I wrote my own culling prototype (links-verify/v1_core.py step E, n=3; n=2 at the doubled buffer). It maps the ROI outline forward from raster pixel to raster world to SJI pixel at the frame, then inverts only the screen pixels inside that bounding box plus 2 px. 4000255147: 0.213 s against glue's 4.641 s, with the box covering 1.88% of the 348x181 buffer. At 696x362: 2.92 s against 29.7 s, box 1.93%. 4000005156: 0.0475 s against 0.463 s, box 9.17%. The masks were 100.000% identical to glue's in all three cases. The cause also shows on the real screen grid (one inversion, 4000255147): the 58 810 pixels outside the raster footprint cost 25.5 us each (1.50 s) and the 4 178 inside cost 176 us each (0.74 s). So 67% of each inversion is spent on pixels that can only produce False.

**Correction.** The gain is overstated. The prototype already does a single inversion, so its 10-22x is the total gain over today's glue, not a gain on top of the 2x from the finding above. Measured against today's glue the gain is 21.8x (4000255147 dpr 1), 10.2x (dpr 2) and 9.8x (4000005156). Measured against glue with the single-inversion fix it is 10.6x, 4.9x and 4.3x. The cause holds: fixed_resolution_buffer.py:312 calls get_mask for every screen pixel, and the pixel-space shortcut at subset.py:569 applies only to the data's own pixel components; both are unchanged on origin/main. Medium confidence is right: only rectangular raster-pixel ROIs were tested. The outline bounding box bounds the interior only because each IRIS exposure maps the slit affinely; that is not guaranteed for general folded mappings.

#### links#3. Inverting irispy's -TAB raster WCS costs microseconds to milliseconds per point, and is ill-posed for sit-and-stare rasters (confirmed)

- **Slows:** Any linked SJI-to-raster pixel lookup: the raster-ROI mask on the SJI (above) and, in principle, any per-pixel reverse link to a raster
- **Repository:** astropy; **confidence:** high; **share:** Wcsprm.s2p is 99.8% of the ROI mask time (26.586 of 26.629 s in 02's full-SJI cProfile), so it is about 98% of an SJI frame change for 4000255147.

**Cost.**

03: 20 000 random raster points, n=3, via the astropy low-level WCS. world->pixel inside the footprint: 4000255147 sit-and-stare 7355 us/point, 4000005156 (64 steps) 8.0 us, 3824262996 (400 steps) 31.5 us. pixel->world is 0.02 us/point for all three. Outside the footprint (2 000 points): 13.2, 0.62 and 3.38 us. The round trip on sit-and-stare is off by up to 6.2 pixels; the others are off by 2e-6.

**Cause.**

irispy builds the raster WCS as CTYPE WAVE, HPLT-TAB, HPLN-TAB, with one table of 1600 entries for 4000255147. wcslib's table inverse (tabs2x, called through astropy/wcs/wcs.py:2566 wcs_world2pix -> Wcsprm.s2p) searches the table for each point. For a sit-and-stare raster all exposures point at nearly the same place, so the search cannot settle on an exposure: it is the slowest case and the answer is ambiguous.

**Upstream main.**

Not checked against astropy or irispy main; astropy 8.0.1 is installed.

**Candidate fix.**

irispy: give sit-and-stare rasters a WCS in which the exposure axis does not drive longitude and latitude, so lon/lat do not depend on exposure. astropy/wcslib: speed up the -TAB inverse, for example by starting the search from the cell of the previous point or using a spatial index. glue cannot remove this cost, only call it less often (the findings above).

**Gain.**

Not prototyped. For sit-and-stare it would turn the 4.8 s per frame (31 s at dpr 2) into roughly the 0.1 s frame cost; for scanning rasters the 8-31 us/point would fall toward the forward cost.

**Evidence.**

03_tab_inverse.log; 02_roi_core_4000255147_s1.log (raster WCS printout and finite fraction)

**Second measurement.** links-verify/v3_tab.py, astropy 8.0.1 with bundled wcslib 8.6, n=3, random raster points. world->pixel inside the footprint: 4000255147 6154 us/pt (1000 points), 4000005156 7.6 us/pt, 3824262996 29.7 us/pt (20 000 points each). 0.2 deg off the raster: 12.85, 0.60 and 3.27 us/pt. pixel->world: 0.02-0.04 us/pt. The sit-and-stare round trip is off by up to 6 steps, and 55% of points are off by more than 0.01 px; the scans are exact to 2e-6. I also tested the cause: the same 1600-entry table with its steps spread at 0.35 arcsec per step inverts at 20.9 us/pt, about 300x faster. The real table spans 13 arcsec in lon over 1600 exposures, with a median step of 0.000 arcsec. s2p is 99.5% of the mask time at dpr 1 and 99.7% at dpr 2.

**Correction.** The per-point numbers agree within 1.2x. The cause is now evidenced, not just inferred. wcslib's tabs2x (cextern/wcslib/C/tab.c, unchanged through the wcslib 8.9 bundled on astropy main 1f930be7c4; its CHANGES since 8.6 show no tabs2x change) loops over every voxel for each point. For each voxel that could contain the point it runs tabvox's recursive dissection, up to 31 levels, and it stops at the first voxel that contains the point. On a sit-and-stare all 1600 voxels overlap, which explains both the cost and the first-match ambiguity; table size alone does not, as the synthetic scan shows. Corrections: (1) The 7355 us/pt describes random raster points, not the action. On the real SJI screen grid the cost is 176 us/pt for the 6.6% of pixels inside the footprint and 25.5 us/pt outside, and the outside pixels are 67% of the time. (2) The fix belongs in wcslib (Calabretta), which astropy bundles, and in irispy for how the WCS is built. Even a well-posed 1600-entry -TAB costs 13-21 us/pt, roughly 1 s per 63k-pixel inversion (estimated, not measured on the grid). Only a non-TAB or separable WCS would approach the 0.1 s frame cost. That irispy change could also stop the step axis being derivable from lon/lat, which changes what an ROI on step means. (3) irispy main was not checked.

#### links#4. glue's discover_links restarts its scan of every link after each discovery, and every change runs it for every dataset (confirmed)

- **Slows:** Loading or linking IRIS datasets, keep_hpc_linked, the quicklook's add_link, adding a component (arithmetic editor), and pressing OK in Link Data. Every such action runs one full update.
- **Repository:** glue-core; **confidence:** high; **share:** discover_links is 97-98% of each update: 0.301 of 0.325 s (36 star), 4.577 of 4.596 s (36 pairs), 6.297 of 6.492 s (99 star). The pixel-aligned pair loop is 0.02-0.14 s and building the link set 3 ms.

**Cost.**

05 (Si IV 1394 scans of 3602506433; median of 3, except N=99 all-pairs n=1). One update_externally_derivable_components took: N=9 star 0.005 s, all-pairs 0.020 s; N=36 star 0.325 s, all-pairs 4.60 s; N=99 star 6.49 s, all-pairs 272.7 s. Each dataset can derive 32, 140 and 392 cids at N=9, 36 and 99.

**Cause.**

glue/core/link_manager.py:77-90. Each pass calls accessible_links(cids, links) (lines 38-51), which builds set(l.get_from_ids()) for every link, takes the first link that adds or improves a cid, then breaks and starts over. That is O(K*L) per dataset, and update_externally_derivable_components (lines 249-255) repeats it for each of the N datasets. Measured growth was about N^3 for the star topology and about N^4 for all pairs.

**Upstream main.**

Same code on glue origin/main.

**Candidate fix.**

Index the links by input cid once per update and expand level by level (BFS on depth = max(input depth) + 1). Prototyped in 06_discover_proto.py with the same contract. Further options: compute identity-link equivalence classes once for the whole collection, and skip datasets whose reachable links did not change.

**Gain.**

06 (single runs) gave the same derivable cids and the same depths as glue's in all 7 configurations compared: N=9 10x (star) and 19x (pairs); N=36 0.296 s to 0.007 s (43x) and 4.32 s to 0.046 s (94x); N=99 star 6.53 s to 0.053 s (123x). For N=99 all-pairs only the prototype was timed: 0.96 s, against glue's 272.7 s measured in 05.

**Evidence.**

05_link_discovery_small.log, 05_link_discovery_99.log, 06_discover_proto.log. This matches the 0.3 s and 4 s that glue_solar/sources/loaders/iris.py:270-271 already records.

**Second measurement.** links-verify/v4_links.py, Si IV 1394 scans of 3602506433, links added without an update and then each update timed (median of 3 unless noted). One update_externally_derivable_components: N=9 star 0.006 s, all-pairs 0.021 s; N=36 star 0.325 s, all-pairs 3.98 s; N=99 star 6.58 s, all-pairs 249.0 s (n=1). Derivable cids per dataset: 32, 140 and 392. discover_links run over every dataset is 77% (N=9 star), 93% (N=36 star), 95% (N=9 pairs), 98% (N=99 star) and 99% (N=36 and N=99 pairs) of an update. I wrote an independent prototype that indexes links by input and expands level by level. It gave the same cids and depths as glue on sampled datasets at N=9, 36 and 99 star and at N=9 and 36 all-pairs. Speedups: 14x, 40x, 64x, 201x and 187x. For N=99 all-pairs it took 0.37 s against glue's 247.5 s (664x).

**Correction.** Cost, cause (link_manager.py:38-51 and the restart loop at 77-90, run per dataset at 249-255) and fix all hold, and the code is unchanged on origin/main. My level-by-level prototype gains at least as much as the finding's (64-664x against 43-123x). One share figure is wrong: discover_links is 93% of an update at N=36 star (the finding's own 0.301 of 0.325 s), not 97-98%, and 77% at N=9 star. 97-99% holds for N=99 star and for all-pairs. The measured growth matches the claim: about N^3 for star and about N^4 for all-pairs.

#### links#5. Removing a dataset runs one full link update per removed link, and clear() is not batched (confirmed)

- **Slows:** Deleting a dataset from the data collection, especially the first one (the anchor of glue-solar's link_hpc star), and clearing the collection
- **Repository:** glue-core; **confidence:** high; **share:** N-fold redundant work: at N=99 the anchor removal costs 54x a single update (353 s against 6.5 s); in N=36 all-pairs a leaf removal costs 64x (293 s against 4.6 s).

**Cost.**

Real runs: removing a non-anchor dataset (05) takes 2 updates in a star (N=36 0.60 s, N=99 12.6 s) and 70 updates in all-pairs at N=36 (293.3 s). Removing the anchor (10, single run) takes 16 updates at N=9 (0.03 s), 70 at N=36 (6.74 s) and 196 at N=99 (353.4 s), against 0.329 s and 6.50 s for one update. Counted but not run: clear() of 36 all-pairs datasets makes 1122 updates, of 99 all-pairs 9312. glue-solar's _Relinker then adds one more update.

**Cause.**

glue/core/link_manager.py:158-166. LinkManager._data_removed calls self.remove_link(link) once per link, and the default update_external=True triggers update_externally_derivable_components each time (lines 213-215). DataCollection.clear() (glue/core/data_collection.py:125-128) sets _ignore_link_manager_update, but LinkManager.remove_link never checks that flag.

**Upstream main.**

Same code on glue origin/main.

**Candidate fix.**

In _data_removed call self.remove_link(remove) once with the list, which already defers to a single update at line 199. Have LinkManager honour DataCollection's _disable_sync_link_manager, so clear() and batched removals sync once at the end.

**Gain.**

From 2(N-1) updates to 1 per removal. N=99 anchor removal goes from 353 s to about 6.5 s (to about 0.05 s with the discover_links fix); N=36 all-pairs leaf removal from 293 s to about 4.6 s.

**Evidence.**

05_link_discovery_small.log, 05_link_discovery_99.log, 10_remove_anchor.log

**Second measurement.** links-verify/v4_links.py remove mode; update calls counted by wrapping the LinkManager instance in my process. Leaf removal: N=36 star 2 updates, 0.59 s; N=99 star 2 updates, 13.00 s; N=36 all-pairs 70 updates, 318.6 s (a single update took 4.0-5.1 s while another job ran). Anchor removal after one leaf had gone: 35 datasets, 68 updates, 5.80 s; 98 datasets, 194 updates, 361.8 s. clear() of the 34 all-pairs datasets left: 1122 updates (counted, not run). Cost of the one deferred update the fix would make (timed afterwards): leaf removal 0.296 s (N=36 star), 6.43 s (N=99 star) and 4.46 s (N=36 pairs); anchor removal 0.018 s (N=36) and 0.153 s (N=99), because no links remain.

**Correction.** Counts, costs and cause hold, and the code is unchanged on origin/main: _data_removed at link_manager.py:158-166 calls remove_link per link, the per-call update is at 214-215, and the list path that updates once is at 198. Three corrections. (1) The clear() counts (1122 and 9312) are for the 34 and 97 datasets left after two removals; clear() of N all-pairs datasets makes N(N-1) updates, one per LinkSame link. (2) The fix gains more for anchor removal than estimated: the single deferred update costs 0.15 s at N=99, not about 6.5 s. The about 6.5 s returns only when glue-solar's _Relinker re-links the new star with one full update (about 6.4 s at N=98, from the star update cost; the Qt relink was not timed). With the discover_links fix that drops to about 0.03 s. (3) Line numbers: DataCollection.clear is data_collection.py:128-131, not 125-128.

#### links#6. Any change to a dataset's derivable components recomputes every image layer's subset mask, even when the subset's own link chain did not change (confirmed)

- **Slows:** Loading and linking another dataset (even from another observation), or pressing OK in Link Data without changing anything, while an ROI on linked data is shown (for example a raster ROI on the SJI)
- **Repository:** glue-core; **confidence:** medium; **share:** 99% of the next SJI draw is the recomputed mask (4.7 s against 0.03 s); at dpr 2 that is about 31 s (02).

**Cost.**

01 (4000255147, app): appending one unrelated 3602506433 scan and calling keep_hpc_linked took 0.017 s, then the next SJI draw took 4.775 s and 4.698 s (2 trials). A redraw with nothing changed took 0.032 s (n=3). 08: Link Data OK with no edits at N=36 ran 1 full update (0.327 s) and broadcast ExternallyDerivableComponentsChangedMessage 36 times, once per dataset; at N=9 it was 9 messages.

**Cause.**

glue/core/data.py:640-660 (_set_externally_derivable_components) broadcasts ExternallyDerivableComponentsChangedMessage when any key is added or any link object differs by identity (line 649). glue/dialogs/link_editor/state.py:318-331 creates new link objects on every OK, so every dataset reports a change. glue/viewers/image/layer_artist.py:42-44 subscribes update() to that message, and update() (lines 392-396) pops ARRAY_CACHE and PIXEL_CACHE for subsets. The common viewer (glue/viewers/common/viewer.py:362, 288-293) also calls layer_artist.update() for every subset layer of that data.

**Upstream main.**

Same code on glue origin/main.

**Candidate fix.**

Have _set_externally_derivable_components report which cids changed, comparing links by from/to ids and function rather than identity. Have the link editor reuse unchanged link objects. Have ImageSubsetLayerArtist.update keep its cached mask unless a component its subset_state.attributes resolve through actually changed.

**Gain.**

Loading or linking unrelated data with a linked ROI visible: about 4.7 s to about 0.03 s per affected viewer (about 31 s at dpr 2). Link Data OK without edits: no recomputation. Not prototyped.

**Evidence.**

01_roi_sji_4000255147.log (lines 'append + link an unrelated scan'), 08_link_editor.log

**Second measurement.** In the app (links-verify/v2_app.py, raster ROI shown on the SJI, 2 trials each). Appending an unrelated 3602506433 scan and running keep_hpc_linked took 0.016 s and sent the SJI 1 ExternallyDerivableComponentsChangedMessage. The next SJI draw took 4.712 s and 4.737 s for 4000255147, and 0.509 s and 0.501 s for 4000005156. An unchanged redraw took 0.030 s (n=3), as did the redraw after. Link Data opened and OK'd with no edits (LinkEditor.accept, then state.update_links_in_collection, then set_links: one update) took 0.011 s and sent 1 message for the SJI. The next draw took 4.721 s and 4.725 s for 4000255147, and 0.501 s and 0.501 s for 4000005156.

**Correction.** Confirmed, and the Link Data OK case is now measured directly in the app: 4.7 s per affected viewer for 4000255147, where the finding had only a message count. The cause holds and is unchanged on origin/main. data.py:649 compares links by identity, and state.py:318-331 builds new link objects on each OK. Both layer_artist.py:42-44 (whose _is_data_object filter matches subset layers whose data sent the message) and viewer.py:288-293 call ImageSubsetLayerArtist.update (392-396), which drops ARRAY_CACHE. One nuance for the fix: on append plus link, the SJI's derivable set really does grow, with new cids, so the message is legitimate. Only the artist-side check (do the subset attributes' chains still resolve to the same links?) avoids that recompute. Comparing links by from/to ids and function, rather than identity, fixes only the Link Data OK case. The estimated gain of 4.7 s to about 0.03 s matches the measured cached redraw of 0.030 s.

#### links#7. A Pixel point move spends little in link evaluation; most goes to _set_wcs on each slice change and to repeated redraws (not re-measured)

- **Slows:** Clicking or dragging the Pixel point on the quicklook's raster map (the coordinator moves the SJI frame and the other panels follow)
- **Repository:** glue-core; **confidence:** medium; **share:** Sampler (about 2 100 main-thread samples): link evaluation (get_xy, _to_linked_pixel_coords, pixel_cid_to_pixel_cid_matrix) about 1.6%; subset broadcast 1.2%; FRB masks 2.5-3%; glue's ImageViewer._set_wcs 33% (about 140 ms); canvas draws 55% (about 223 ms, against about 105 ms if each canvas drew once).

**Cost.**

04 (quicklook, n=8): 0.41-0.44 s wall per move (4000255147), 0.40 s (4000005156); main-thread CPU 0.38-0.41 s; synchronous part 5 ms. Link pieces (n=5): pixel_cid_to_pixel_cid_matrix(raster, SJI) 3.1 ms; get_xy on the SJI 3.1 ms, ending in IncompatibleAttribute because time is not linked; Point FRB masks 0.4-1.8 ms. Per move each viewer gets one _set_wcs: SJI 66 ms, spectrogram 31 ms, lambda-time 40 ms (n=5). axes.reset_wcs alone is under 1 ms in each. Canvas draws per move: map 1.25, spectrogram 2.25, lambda 2.25, spectrum 3.0, SJI 2.1. One draw each takes 15/22/34/7/27 ms.

**Cause.**

glue/viewers/image/viewer.py:96-98 runs _set_wcs on every slice change when the WCS couples the sliced axis to the displayed ones; that is true for the SJI and for the spectrogram and lambda panels. _set_wcs (lines 100-128) also clears and re-sets the axis labels, appearance settings and tick label sizes, which costs 24-65 ms and is unchanged by a slice change. Which component causes the repeated draws was not isolated: candidates are the glue-solar coordinator's QTimer second pass (quicklook.py:219, 386-402, 372-385) and the profile viewer's compute start/end redraws.

**Upstream main.**

Same code on glue origin/main (viewers/image/viewer.py).

**Candidate fix.**

On a slice change, call only axes.reset_wcs(slices=..., wcs=...) and restore labels and ticklabel sizes without re-running _update_appearance_from_settings and _update_axes, or only when they changed. Separately, coalesce the coordinator's follow-up slice moves into the same draw cycle.

**Gain.**

About 130 ms of a 0.41-0.44 s point move (about 30%) from _set_wcs, which would also apply to every slider tick on viewers with coupled WCS. Up to about 118 ms more (about 27%) if each canvas drew once per move. Both are estimates from the measured pieces.

**Evidence.**

04_point_4000255147.log, 04_point_4000005156.log. This overlaps with the draw/slider area. Current glue-solar main adds the crosshair workaround, about one more 3 ms get_xy per Pixel-layer visual update, which was not measured here.

#### links#8. Derived arithmetic components with a numeric constant turn float32 data into float64 (not re-measured)

- **Slows:** Reading a component made in the arithmetic editor (for example 'x * 2') on IRIS float32 cubes: histogram, image or statistics of the derived attribute
- **Repository:** glue-core; **confidence:** high; **share:** 2.3x the time and 2x the memory of the same operation in numpy.

**Cost.**

09 (n=5, cube of shape 1600x417x262 float32, the 4000255147 Si IV 1403 size): glue get_data(x * 2) gives float64 in 0.093 s with a 1334 MB peak allocation. numpy a * 2 gives float32 in 0.041 s with a 667 MB peak. On the real raster (07, n=3): 0.104 s and 1334 MB per call, recomputed every call because derived components are not cached.

**Cause.**

glue/core/component_link.py:483 (BinaryComponentLink.compute) runs np.broadcast_arrays(left, right) even when one operand is a Python scalar. That turns 2 into an int64 array, so numpy 2's weak-scalar rule (NEP 50) no longer applies and float32 * int64 gives float64.

**Upstream main.**

Same code on glue origin/main.

**Candidate fix.**

Unbroadcast and broadcast only the ndarray operands; pass Python or numpy scalars straight to self._op.

**Gain.**

About 2.3x faster and half the peak memory for derived components with constants on float32 data (0.093 s and 1334 MB to 0.041 s and 667 MB per full read of a 175M-element cube).

**Evidence.**

09_binary_dtype.log, 07_get_data.log

**Not measured in this area.** Draws on a real screen: every app timing is offscreen Agg at devicePixelRatio 1, and dpr 2 was only approximated by doubling the FRB bins in the single-threaded run (31 s per SJI frame for 4000255147, against the user's reported 10-20 s, whose viewer size I do not know). None of the candidate fixes was applied inside glue. Only the discover_links level-BFS and the ROI bounding-box cull were prototyped, and only outside glue (06 and 02); the 2x single-inversion gain, the cache-cascade fix and the _set_wcs fix are estimates from measured pieces. The cause of the repeated per-move canvas draws (1.25-3 per viewer) was not attributed between the glue-solar coordinator and the glue-qt profile compute signals. Not measured: CPU use of glue-qt's idle ComputeWorker polling (25 wakeups/s per profile layer). The N=99 all-pairs removal and clear() were counted (196 and 9312 updates) but not timed, and N=99 star clear() was not timed. get_data of linked components over a whole SJI cube (65M points) was not run because of memory; only 1 and 10 frames were. At 1 frame a LinkSame-linked component costs the same as the dataset's own component (0.0118 s against 0.0122 s), so identity links add no measurable overhead. glue's WCS autolinker (find_possible_links, which glue-qt's add_datasets runs) returned no suggestions in under 1 ms for 2-36 IRIS datasets, so it costs nothing here. No Pixel point was placed on the SJI, so the SJI-to-raster point direction is not covered. The crosshair workaround in current glue-solar main (#86-#88) is not covered. irispy and astropy main were not checked for the -TAB inverse. The upstream glue and glue-qt refs were not re-fetched.
