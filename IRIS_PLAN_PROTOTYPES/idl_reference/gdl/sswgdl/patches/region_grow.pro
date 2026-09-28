; sswgdl-work patch: GDL has no REGION_GROW. Minimal clean-room stand-in covering the
; THRESHOLD path only (default threshold = [min,max] of the ROI pixels), via LABEL_REGION,
; which (as in IDL) leaves array-edge pixels unlabelled.
; ponytail: no STDDEV_MULTIPLIER / NAN handling; add if a caller needs them.
function region_grow, array, roipixels, all_neighbors=all_neighbors, threshold=threshold, $
                      stddev_multiplier=stddev_multiplier, nan=nan
  compile_opt idl2
  if n_elements(stddev_multiplier) gt 0 then message, 'STDDEV_MULTIPLIER not supported by this stand-in'
  thr = n_elements(threshold) eq 2 ? threshold : [min(array[roipixels]), max(array[roipixels])]
  lab = label_region(array ge thr[0] and array le thr[1], all_neighbors=keyword_set(all_neighbors))
  seeds = lab[roipixels]
  seeds = seeds[uniq(seeds, sort(seeds))]
  seeds = seeds[where(seeds gt 0, ns)]
  if ns eq 0 then return, -1L
  keep = bytarr(size(array, /dim))
  for i = 0L, ns-1 do keep or= (lab eq seeds[i])
  return, where(keep)
end
