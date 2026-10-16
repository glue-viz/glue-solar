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
- [x] Fixed (#227, 2026-10-10)

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
  - So an SST region selects no IRIS pixels even when linked: 0 of 161,796 SJI pixels got a position. D67 gave the fix to the SST loader, #227: a co-pointed SST rectangle now selects the IRIS pixels at its place, with 0 mismatches against wcslib, and 4846 linked beside 9 windows opens in 9.3 s (was 231-241 s), with SJI steps of 0.10 s (was 1.84 s).
- **Fix:** R2's footprint cull helps only where the region does not overlap. A faster inversion is ruled out (R8, D54). That leaves glue-solar's link scope: link non-IRIS data only on request ('IRIS: link helioprojective coordinates'), or keep foreign subsets off the quicklook's panels. The user chooses.

### SST4. The Profile button on a large cube reads the whole file, freezes the main thread for about 3/4 of the wait, and adds the file to RSS

- [x] Re-verified (2026-10-10; numbers corrected)
- [x] Worked around in glue-solar (#233, 2026-10-11): a Profile viewer adds the cube hidden. On 8542 the Profile button takes 0.17 s and reads 1 MB, against 29.6 s cold (a 20 s freeze, 11 GB read); a rectangle's profile is unchanged. Upstream R14, R21

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
- [x] Fixed (#227, 2026-10-10)

- **Cost:** restore fails within 5-12 ms on 8542, 6173, 6302, 3950 and obs171.
- **Autosave:** closing the app with an SST cube open writes a 65 KB `glue-solar-last-session.glu`. Its 1 MB guard lets it through, because glue's FITS components carry load logs. 'IRIS: restore last session' then fails the same way.
- **Cause:** glue saves the WCS as a header string and rebuilds it with `WCS(Header)` without the HDUList (`glue/core/state.py` `_save_wcs`/`_load_wcs`).
- **Fix:** a saver or session patch that rebuilds the WCS from the logged file.

### SST6. Restoring a multi-window stack reads every raster file once per window

- [x] Re-verified (2026-10-10; cost corrected)
- [x] Fixed in glue-solar (#234, 2026-10-11): a restore reads each raster file once for all its logged windows. 3602506433 with 7 windows restores in 7.1-7.2 s with 99 `read_files` calls, against 11.9-12.2 s and 693 calls on main 3cfac20, with the same data; main had already dropped from 19.8 s to 12 s since the survey.

- **Cost:** 3602506433 with 7 windows and 99 files restores in 19.8 s. Of that, 13.8 s is data, in 693 `read_files` calls (99 × 7). The browser loads it in 10.9 s with 99 calls. The survey's 49.3 s, and its 70.7 s for 3630104144, ran under cProfile.
- **Cause:** each window has its own load log, and restoring it (`raster_files_data` → `_raster_windows_data(files, [window])`) opens every file for that one window.
- **Fix:** read each file once for all logged windows of one restore, with a session patch that groups the raster logs or a per-restore cache. Tested directly: one call for all 7 windows takes 5.6-6.3 s against 13.5 s for one per window, so the restore should drop to about 12 s.

### SST7. Each ticked window multiplies the quicklook's redraws: about 4× per step with 9 windows

- [x] Re-verified (2026-10-10)
- [x] Worked around in glue-solar for panels out of sight (#235, 2026-10-11): they draw once in sight. 9-window 4000255147 at 1600×1000, axes hidden: step 270-278 → 196-201 ms (47 → 17 draws), move 312-322 → 213-220 ms; axes shown: step 497 → 246-249 ms. With every row in sight the cost is main's: of what is left, the repeated draws (glue drawing the point layer before the time sync, and R3's second worker run, about 55% of a step with axes hidden) and the per-draw cost R1, R5, R18

- **Cost:** on 4000255147, going from 1 window to 9:

  | Action | 1 window | 9 windows |
  |---|---|---|
  | Exposure step | 194-207 ms, 7 draws | 865-875 ms, 47 draws |
  | Click | 248-264 ms | 760-887 ms |
  | Move | 235-240 ms | 985-991 ms |
  | Open | 3.4-4.35 s | 13.4-13.6 s |

  The map λ step (95 ms) and the SJI frame step (48 ms) do not change. With the point curves, row and column open, a move takes 1668 ms.
- **Cause:** every other window's spectrum panel and λ panel redraws on each step and move.
- **Workaround (#228, 2026-10-10):** turning the other windows' panels off in the quicklook's Panels list brings the 9-window step to 188-195 ms (7 draws, none on hidden panels), a one-window quicklook's cost. With every panel shown, the step is unchanged (532-540 ms on today's main).
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
- **Covered by** R11, as its Profile data-layer case.
- [x] Worked around for large non-IRIS cubes (#233, 2026-10-11): with the data layer hidden, a Path Enter on 8542 settles in 0.24-0.27 s, against 3.6-4.7 s.

### SST10. A new Image viewer on a cold memory-mapped cube reads about 0.7 GB at random for its Min/Max limits

- [x] Re-verified (2026-10-10)
- [ ] Fixed upstream (`wp0-perf-core-stats-io`, as R32)
- [x] Worked around for SST cubes (#230, 2026-10-11, D70): `sst._Cube` answers glue's sampled statistics from 16 evenly spaced planes of 25 rows and 25 columns; the 3950 quicklook opens in 1.97 s cold (0.47 GB read), against 4.56 s (0.79 GB). Remove it once R32 is fixed.

- **Cost:** 1.75-1.82 s cold against 0.53-0.55 s warm, reading 0.68-0.74 GB in about 10,000 page-ins. `compute_statistic` takes 1.17-1.25 s.
- **Cause:** `StateAttributeLimitsHelper` (`glue/core/state_objects.py:405-422`) calls `random_subset`, which draws 10,000 uniform random indices with one `np.random.randint` per axis (`glue/core/data.py:1849-1851`, `glue/utils/array.py:756`). Each index lands on a different page of the mapped file.
- **Fix:** sample whole planes or rows, as glue-solar's `RawComponent._sample` does, or sort the indices by page.

### SST11. 'Light curves of every window and SJI…' is offered on a single-scan raster with no SJI, then refuses

- [x] Re-verified (2026-10-10, on 75b7a73)
- [x] Fixed in glue-solar (#236, 2026-10-11): the entry, now 'Light curves of the shown windows and SJI', runs `_point_curves`' own check and is not offered on 3824262996's raster alone; a 4000255147 quicklook of two windows and SJI 1400 gives those three curves in 0.47 s, against ten in 0.85 s.

- **Cost:** an error box on 3824262996 ('… has no exposures or scans, and its observation no slit-jaw image loaded').
- **Cause:** `_PointCurvesEntry.offered` checks only for an IRIS role.
- **Fix:** make `offered` run `_point_curves`' own check (D61: entries hide where they cannot act).

### SST12. File > Open makes 33 datasets per SST cube

- [x] Re-verified (2026-10-10; description corrected)
- [x] Fixed (#227, 2026-10-10)

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

Removed 2026-10-16 (D82); the raw findings that the R- and S-entries cite (draw#N, events#N and so on) are in `git show 8c64662:GLUE_SPEED.md`.
