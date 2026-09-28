; GDL shim for IDL's REGION_GROW ($IDL_DIR/lib/region_grow.pro, not in GDL or SSW).
; Only the default THRESHOLD path used by iris_burst_check/iris_sji_burst_check:
; threshold = [min, max] of the ROI pixel values, connected via LABEL_REGION.
; ponytail: no STDDEV_MULTIPLIER; edge pixels follow LABEL_REGION (background), as IDL's does.
function region_grow, arr, roi, all_neighbors=alln, threshold=thr
  compile_opt idl2
  if n_elements(thr) eq 0 then thr = [min(arr[roi]), max(arr[roi])]
  lab = label_region(arr ge thr[0] and arr le thr[1], all_neighbors=keyword_set(alln), /ulong)
  ids = lab[roi]
  ids = ids[uniq(ids, sort(ids))]
  k = where(ids ne 0, nk)
  if nk eq 0 then return, -1L
  keep = bytarr(max(lab) + 1)
  keep[ids[k]] = 1b
  return, where(keep[lab])
end
