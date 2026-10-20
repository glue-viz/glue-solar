# Glue speed

A to-do list of performance problems in glue-core 1.27.0, glue-qt 0.4.2 and the libraries under them (astropy, matplotlib, irispy), and in glue-solar itself, found by a profiling survey of real IRIS quicklook workflows on 2026-10-01. Nothing was patched: every item is a measured cost with a cause and a candidate fix, to be re-verified and then fixed (upstream on the user's direction, as M4 work in `IRIS_GLUE_GAP_PLAN.md`; glue-solar's own items were M0 work, merged as #90, #95 and #98).

**How it was measured.** Offscreen Qt with Agg on macOS (24 GB), app 1600x1000, device pixel ratio 1 and an emulated 2 (`QT_SCALE_FACTOR=2`), in the `iris-plan` env (glue-core 1.27.0, glue-qt 0.4.2, irispy 0.9.1, astropy 8.0.1, matplotlib 3.11.2, numpy 2.5.3), glue-solar at main 2fdb847 with key results re-run at 5eae565. Data from `~/DATA/IRIS`: 4000255147 (sit-and-stare Si IV 1403, 1600x417x262, and SJI 1400), 4000005156 (two-scan stack, deconvolved SJI 2796), 3602506433 (99 scans), 3824262996. Timings are medians of repeated steps after warm-up, taken with `perf_counter` wrappers at code boundaries (cProfile only for structure; it inflates times about 4.6x). Seven areas were profiled by one agent each, and a second agent re-measured each area's top findings. Offscreen Agg differs from a real screen; real-screen and Wayland numbers were not taken.

**Re-running.** The survey's scripts are in `IRIS_PLAN_PROTOTYPES/perf_survey_20261001.tar.gz` (132 scripts; extract it into a scratch directory). Evidence paths below are relative to that archive. Run with `env HOME="$(mktemp -d)" QT_QPA_PLATFORM=offscreen MPLBACKEND=agg ~/mamba/envs/iris-plan/bin/python <script>`, with a glue-solar checkout first on `sys.path` as the scripts do. Logs and profiles were not kept; the numbers below are the record.

**Second survey.** The large SST SOLARNET cubes and the biggest IRIS sets were measured on 2026-10-10, under 'SST and IRIS stress survey, 2026-10-10' below (SST1-SST13, verified the same day). **New upstream findings.** The slit-jaw gWCS path (dkist, gwcs, astropy.modeling), measured on 2026-10-20, is R33-R37 under 'New upstream findings, 2026-10-20'. **Third survey.** The same SST cubes on glue-solar main of 2026-10-20, with the quicklook-era parts, under 'SST performance survey 2, 2026-10-20'.

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

## New upstream findings, 2026-10-20

The slit-jaw gWCS path, which no earlier survey or UPSTREAM_REVIEW.md row covers: irispy main builds each slit-jaw cube's WCS as a gWCS around dkist's `VaryingCelestialTransform`, one pointing per frame, and every slit-jaw tick, readout, overlay, point and crosshair goes through it. **Measured and re-verified on 2026-10-20** with dkist 1.17.0, gwcs 1.0.3, astropy 8.0.2 and irispy main 0650517, on 4000255147's SJI 1400 (400 frames, 417x388), on this Mac (Apple Silicon); scripts in `IRIS_PLAN_PROTOTYPES/speed_20261020/` (`gwcs_findings.py SJI_FILE`, `sji_draw_calls.py SJI_FILE TREE`). One idea was measured and dropped: SST's big-endian float32 planes cost about 1 ms of byte swapping per 5-megapixel plane (`nanmean` 4.25 ms against 3.81 ms native), not worth a change.

### R33. dkist's VaryingCelestialTransform evaluates one compound model per frame

- [x] Re-verified (2026-10-20)
- [ ] Fixed upstream

**Repository:** dkist (`dkist/wcs/models.py`, `_map_transform`). **Confidence:** High for the cost and cause; the prototype gives the gain.

**Slows.** Anything that asks for positions across frames: light curves at a point, the slit overlay across frames, per-frame readouts, links from a raster's exposures to slit-jaw frames.

**Cost.** One point in each of the 400 frames: 57.7 ms (0.14 ms a frame), against 1.10 ms for 10,000 points of one frame.

**Cause.** `_map_transform` loops over every unique frame index, sets that frame's CRPIX, PC and CRVAL on its cached compound model (`transform_at_index`, `update_celestial_transform_parameters`) and evaluates it, so the per-call overhead of astropy.modeling (R37) is paid per frame.

**Candidate fix.** Evaluate the chain once for all elements, each with its own frame's tables: a prototype of the same Shift, PC, CDELT, TAN and native-to-celestial rotation (Calabretta & Greisen 2002, eq. 2) takes 0.051 ms for the 400 frames (1,100 times faster) and matches the gWCS to 8e-11 arcsec. astropy's `RotateNative2Celestial` takes scalar angles only, so the rotation is written elementwise.

### R34. dkist's inverse rebuilds a frame's inverse model on every call

- [x] Re-verified (2026-10-20)
- [ ] Fixed upstream

**Repository:** dkist (`_map_transform`, `sct.inverse`). **Confidence:** High.

**Slows.** Every world-to-pixel onto a slit-jaw image: a point or crosshair from other data, linked subsets, glue's world links.

**Cost.** One point: inverse 1.24 ms against forward 0.26 ms. Building a frame's inverse model takes 0.42 ms of it; evaluating a built one 0.098 ms.

**Candidate fix.** Cache each frame's inverse (or invert the vectorized chain of R33): about a third of the inverse's cost; the rest is gWCS's own inverse machinery.

### R35. dkist turns a NaN frame index into an int, which differs by CPU

- [x] Re-verified (2026-10-20; x86-64 seen in the user's traceback, ARM measured here)
- [x] Worked around in glue-solar (#342, `_GlueWCS.world_to_pixel_values` and `_off_frames`)
- [ ] Fixed upstream

**Repository:** dkist (`BaseVaryingCelestialTransform.sanitize_index`, `transform_at_index`). **Confidence:** High.

**Cause.** A world time off a slit-jaw image's frames gives a NaN frame index, and `np.array(np.round(ind), dtype=int)` casts it: to the least int64 on x86-64, off the table, where `transform_at_index` returns `Const1D(nan) & Const1D(nan)`, whose inverse raises NotImplementedError (the user's crash on Linux); to 0 on ARM, where it silently takes frame 0's pointing (a wrong x, a NaN frame).

**Candidate fix.** Treat a non-finite index as off the table in both directions, giving NaN, as the forward transform already does there.

### R36. A slit-jaw viewer asks the 3-D gWCS for every tick; a frame's FITS WCS answers 85 times faster

- [x] Re-verified (2026-10-20, glue-solar main dc7c25f)
- [ ] Fixed upstream

**Repository:** glue-core (the WCS a viewer gives WCSAxes for a slice), irispy (each frame's WCS). **Confidence:** High for the cost; the design is open.

**Cost.** An SJI 1400 frame step and draw with the axes shown: 19-21 ms, of which 17 gWCS calls take 5.6-6.0 ms (glue-solar's `_GlueWCS` memo already removed the repeats; the 2026-10-01 survey counted 37-59 calls before it). The quicklook's image panels hide their axes by default (D71) and make none of these calls.

**Cause.** WCSAxes and the readout ask the cube's 3-D gWCS, 264 us a call, though the viewer shows one frame, whose own FITS WCS irispy already builds (`meta["frame_wcs_headers"]`): an astropy WCS of frame 3's header answers in 3.1 us, at the same position to 4e-11 arcsec.

**Candidate fix.** A glue hook giving WCSAxes the shown frame's 2-D WCS where the cube's celestial axes vary along a sliced axis (or irispy exposing that frame WCS); about 6 ms of a 20 ms step on viewers with axes shown.

### R37. astropy.modeling's per-call overhead dominates a gWCS call

- [x] Re-verified (2026-10-20)
- [ ] Fixed upstream

**Repository:** astropy (`astropy/modeling/core.py`). **Confidence:** High for where the time goes; the fix needs design upstream.

**Cost.** One point forward through the slit-jaw gWCS: 0.26 ms, about 2,500 Python function calls (305 `isinstance`, 198 `len`), almost all in `Model.__call__`, `prepare_inputs`, `_validate_input_shape`, `_param_sets`, `Parameter` assignment and `Quantity` creation; the arithmetic is negligible.

**Candidate fix.** A fast path in `CompoundModel` evaluation for small, unitless inputs that skips the per-leaf input and parameter-set preparation; it would speed every gWCS user, R33 and R34 included.

## glue-solar's own costs

Entries fixed on main or cited by no open item were removed on 2026-10-17; they are in `git show 7b0234a:GLUE_SPEED.md`.

These are glue-solar code; the M0 work fixed most of them (#90, #95, #98).

### S13. The quicklook adds the raster to the spectrum panel and then hides it (confirmed, profile-stats#2).

- [ ] Re-verified
- [x] Fixed in glue-solar (#95, 2026-10-01)

- glue's _reset_y_limits computes the hidden layer's whole-cube profile on the main thread first: 368-400 ms of quicklook open on the sit-and-stare cube, 119 ms on the stack.
- No glue-solar workaround was tested; the fix is glue-core rank 14.

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

### SST13. A cold sit-and-stare in the browser reads the whole raster file

- [x] Re-verified (2026-10-10; cause corrected)

- **Cost:** 1.43 of 1.43 GB is read on 3660259102, during the browser's `_load`, on its worker thread behind the progress bar. The load takes 3.5-4.6 s cold against 2.8 s warm. The quicklook's own phase reads 5 MB.
- **Cause:** `_load` samples each shown dataset's colour limits with `RawComponent._sample`, up to `SAMPLE_BYTES` (512 MiB) of whole planes each. With 9 windows, the samples cover the file.
- **Decision** (D63, PROVISIONAL): no action. It costs 1-2 s cold on an SSD, off the main thread.

## SST performance survey 2, 2026-10-20

`wp10-perf-survey-2` (D100): the 2026-10-10 survey's steps again on glue-solar main dc7c25f (#343), and the quicklook-era parts, on this Mac. The user's Linux machine (larger cubes, 188 GB RAM) runs the same script; its numbers go here when pasted back.

**How it was measured.** `IRIS_PLAN_PROTOTYPES/scale_checks/run_survey.sh` (each cube's part in a fresh process, offscreen Qt and Agg, app 1600x1000 shown, glue's dialogs answered as a user clicks through them); raw lines in `scale_checks/results/mac_20261020.jsonl`. Env `iris-plan-qt6-802-0650`: glue-core 1.27.0, glue-qt 0.4.2, astropy 8.0.2, irispy main 0650517, Python 3.13, macOS on Apple Silicon, 24 GB. Times are seconds or ms to idle: no pending draw on a visible canvas, no profile computing, no coordinator timer. Unlike 2026-10-10 the files were not cold (earlier runs had read them), so the disk reads are small and the first-visit times are not cold reads.

**The 2026-10-10 steps, then and now.** Open is glue's File > Open with the autolinker; a slider step is first visit / warm; the Profile button is glue-qt's, with the main-thread freeze; the drag is a Pixel drag with that Profile open.

| Cube | GB | Open s | Viewer s | Step ms | Profile s (freeze) | Drag ms | Restore s |
|---|---|---|---|---|---|---|---|
| obs492 Ca II 8542 | 10.6 | 0.25 → 0.08 | 1.8 → 0.44 | 34-39 / 20 → 32-35 / 20 | 27.4 (21.2) → 0.60 (0.52) | 183-194 → 183 | fails → 0.24 |
| obs492 Fe I 6173 | 7.1 | 0.25 → 0.07 | 1.8 → 0.44 | 37-39 / 19 → 34-36 / 20 | 18.7 (14.9) → 0.55 (0.48) | 195 → 175 | fails → 0.23 |
| obs492 Fe I 6302 | 5.6 | 0.24 → 0.07 | 1.8 → 0.45 | 37-39 / 19 → 34-37 / 20 | 13.7 (10.5) → 0.59 (0.48) | 201 → 180 | fails → 0.24 |
| obs495 Ca II K 3950 | 3.5 | 0.24 → 0.06 | 1.75 → 0.43 | 27 / 17 → 26 / 19 | 8.2 (6.1) → 0.47 (0.42) | 182 → 188 | fails → 0.23 |
| obs498 H-beta 4846 | 1.1 | 0.35 → 0.06 | 1.6 → 0.43 | 25 / 17 → 26-27 / 18 | 3.3 (1.9) → 0.50 (0.43) | 170-198 → 174 | fails → 0.24 |
| obs167 Fe I 6173 (2020) | 2.1 | 0.38 → 0.06 | refused → 0.36 | 28-30 / 21 → 20 / 20 | 6.2 (3.7) → 0.49 (0.43) | 186 → 200 | fails → 0.30 |
| obs171 H-alpha (2020) | 0.4 | 0.33 → 0.06 | refused → 0.43 | 25 / 21 → 25 / 20 | 1.2 (0.5) → 1.38 (0.94) | 189 → 179 | fails → 0.44 |

- The Profile button no longer freezes the GUI for seconds: cubes of glue's `large_data_size` or more are added hidden (#233), so only H-alpha, under it, is profiled whole (1.4 s, peak 1.7 GB).
- Sessions restore on every cube (they failed on all of them on 2026-10-10), and the 2020 cubes open in an Image viewer (SST2's SPECSYS).
- A Pixel drag with a Profile open is unchanged, 175-200 ms a move: glue recomputes the profile at each move (R14, upstream).
- Peak memory stayed under 1.8 GB in every part, for files up to 10.6 GB.

**The quicklook-era parts.** An SST quicklook (D68): its open; a point click and each move of a drag, to the spectra, curve and slit following (D98's refits included); a scan step, which time-syncs every panel; a path diagram on the map; and the linked obs492 Ca II 8542 and Fe I 6173 quicklooks (D97).

| Cube | Quicklook open s | Click s | Drag ms (first) | Scan step ms | Path diagram s |
|---|---|---|---|---|---|
| obs492 Ca II 8542 | 2.6 | 0.20 | 215 (368) | 427 | 0.29 |
| obs492 Fe I 6173 | 2.5 | 0.21 | 213 (301) | 341 | 0.26 |
| obs492 Fe I 6302 | 2.5 | 0.21 | 213 (287) | 302 | 0.24 |
| obs495 Ca II K 3950 | 2.1 | 0.18 | 185 (350) | 515 | 0.25 |
| obs498 H-beta 4846 | 1.7 | 0.12 | 185 (130) | 201 | 0.17 |
| obs167 Fe I 6173 (2020) | 2.1 | 0.20 | 203 (209) | 118 | 0.22 |
| obs171 H-alpha (2020) | 1.5 | 0.10 | 181 (180) | 85 | 0.15 |

- Linking the two obs492 quicklooks took 0.02 s (2 links); a point moved on one, with the other's point following, took 263 ms.
- The slow spot is the quicklook's scan step on the 2023 mosaics, 0.3-0.5 s, against 85-120 ms on the 2020 cubes of one pointing: each scan re-reads every panel's plane of the bigger, per-scan-pointed cube (`wp10-l-sst-scan-step`).

## WCSAxes tick rendering

The 2026-10-01 study of WCSAxes tick placement (how it works, where IRIS WCSes spend the time, the prototypes, upstream context and open questions) and the study of decoupling WCSAxes from matplotlib (whose matplotlib-free core prototype is on the user's astropy fork) were cut to their PR and bug lists on 2026-10-17 (D82); the full text is in `git show 09be127:GLUE_SPEED.md`.

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

## Raw findings by area, with the second measurement

Removed 2026-10-16 (D82); the raw findings that the R- and S-entries cite (draw#N, events#N and so on) are in `git show 8c64662:GLUE_SPEED.md`.
