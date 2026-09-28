;+
; Reference outputs of four IRIS SolarSoft routines for the irispy ports, plus small probes of
; the library routines where GDL and IDL may differ. See README.md.
;
; Usage (IDL with SSW and the IRIS package on the path):
;   IDL> .run iris_ref_run
;   IDL> iris_ref_run, data_dir='iris_ref_data', out_dir='iris_ref_out', iris_data='iris_ref_tree'
;
; Every task runs even if another fails; failures are printed and listed in status.txt.
;-

function iris_ref_find, data_dir, pattern
  f = file_search(data_dir + '/' + pattern, count=n)
  if n eq 0 then begin
    print, 'No file matches ' + data_dir + '/' + pattern
    return, ''
  endif
  return, f[0]
end

pro iris_ref_wavecorr, file, tag, out_dir
  if file eq '' then message, 'Input file not found'
  t0 = systime(1)
  r = iris_prep_wavecorr_l2(file)
  seconds = systime(1) - t0
  save, r, file, seconds, filename=out_dir + '/wavecorr_' + tag + '.sav'
end

pro iris_ref_mg, file, tag, out_dir
  if file eq '' then message, 'Input file not found'
  d = iris_obj(file)
  iwin = -1
  for i = 0, d->getnwin() - 1 do begin
    lam = d->getlam(i)
    if min(lam) lt 2796.35 and max(lam) gt 2803.53 then iwin = i
  endfor
  obj_destroy, d
  if iwin lt 0 then message, 'No window covers Mg II k and h in ' + file
  vrange = [-40, 40]
  t0 = systime(1)
  iris_get_mg_features_lev2, file, iwin, vrange, lc, rp, bp
  seconds = systime(1) - t0
  save, lc, rp, bp, iwin, vrange, file, seconds, filename=out_dir + '/mg_features_' + tag + '.sav'
end

pro iris_ref_burst, file, tag, out_dir, threshold=threshold
  if file eq '' then message, 'Input file not found'
  ; iris_burst_check sets THRESHOLD when it is undefined, so the saved value is the one it used
  t0 = systime(1)
  iris_burst_check, file, output=output, threshold=threshold
  seconds = systime(1) - t0
  nevents = n_tags(output) gt 0 ? n_elements(output) : 0
  if nevents eq 0 then output = 0
  save, output, nevents, threshold, file, seconds, filename=out_dir + '/burst_' + tag + '.sav'
end

pro iris_ref_sjiburst, date, tag, out_dir
  t0 = systime(1)
  output = 0  ; the routine starts with junk=temporary(output); GDL needs it defined
  iris_sji_burst_check, date, output=output
  seconds = systime(1) - t0
  openw, u, out_dir + '/sji_burst_' + tag + '.txt', /get_lun
  printf, u, '# im_index nevents npix  then pixel index,group,int per event pixel; seconds', seconds
  if obj_valid(output) then begin
    for i = 0, n_elements(output) - 1 do begin
      s = output[i]
      printf, u, s.im_index, s.nevents, s.npix
      for j = 0, s.npix - 1 do printf, u, s.index[j], s.group[j], s.int[j]
    endfor
  endif
  free_lun, u
end

function iris_ref_where_minus_one
  ; iris_get_mg_features does lcc[where(~finite(lcc))] = 0.0 even when nothing matches
  a = findgen(5)
  catch, err
  if err ne 0 then begin
    catch, /cancel
    return, {a: a, error: !error_state.msg}
  endif
  a[where(a lt 0)] = -1.
  catch, /cancel
  return, {a: a, error: ''}
end

function iris_ref_region_grow, mask, seed
  ; the burst checks call region_grow(mask, seed, /all_neigh) on a byte mask
  catch, err
  if err ne 0 then begin
    catch, /cancel
    return, {pixels: [-2L], error: !error_state.msg}
  endif
  roi = region_grow(mask, seed, /all_neigh)
  catch, /cancel
  return, {pixels: long(roi), error: ''}
end

pro iris_ref_probes, file, tag, out_dir
  ; SPLINE as iris_get_mg_features calls it: sigma 0. and a decreasing T (nvel), and sigma 1.
  x = dindgen(21) * 0.25d - 2.5d
  y = exp(-x^2) + 0.1d * x
  t_dec = dindgen(101) / 100d * (x[0] - x[20]) + x[20]
  t_inc = reverse(t_dec)
  spline_dec_s0 = spline(x, y, t_dec, 0.)
  spline_inc_s0 = spline(x, y, t_inc, 0.)
  spline_dec_s1 = spline(x, y, t_dec, 1.)
  spline_inc_s1 = spline(x, y, t_inc, 1.)
  spline_inc_default = spline(x, y, t_inc)
  spline_float_s0 = spline(float(x), float(y), float(t_inc), 0.)

  ; GAUSSFIT and SSW's SILENT_GAUSSFIT (CURVEFIT underneath), as iris_prep_wavecorr_l2 uses them
  xg = findgen(21) * 0.05 - 0.5
  yg = 3. + 0.1 * xg + 10. * exp(-((xg - 0.03) / 0.15)^2 / 2.) + 0.2 * sin(37. * xg)
  gauss5_fit = silent_gaussfit(xg, yg, gauss5_a, nterms=5, chisq=gauss5_chisq, status=gauss5_status)
  gauss4_fit = gaussfit(xg, yg, gauss4_a, nterms=4, chisq=gauss4_chisq)
  ya = 2. - 6. * exp(-((xg + 0.07) / 0.1)^2 / 2.) + 0.1 * cos(29. * xg)  ; absorption, as Ni I
  gauss_abs_fit = silent_gaussfit(xg, ya, gauss_abs_a, nterms=5, chisq=gauss_abs_chisq, status=gauss_abs_status)

  ; large float arrays, as the burst checks and moments use them
  big = float(sin(dindgen(200000) * 0.01d) * 100d + 7d)
  big_total = total(big)
  big_total_double = total(big, /double)
  big_stdev = stdev(big)
  big_median = median(big)
  big_median_even = median(big, /even)
  big_nan = big
  big_nan[5] = !values.f_nan
  big_nan_median = median(big_nan)
  big_nan_total = total(big_nan, /nan)

  where_minus_one = iris_ref_where_minus_one()

  mask = bytarr(9, 7)
  mask[0:2, 0:1] = 1b  ; touches the corner
  mask[3, 2] = 1b      ; diagonal neighbour of the corner blob
  mask[6:7, 4:5] = 1b  ; interior blob
  mask[8, 6] = 1b      ; diagonal neighbour on the far edge
  mask[5, 0] = 1b      ; isolated edge pixel
  rg_corner = iris_ref_region_grow(mask, 0L)
  rg_diagonal = iris_ref_region_grow(mask, 3L + 2L * 9L)
  rg_interior = iris_ref_region_grow(mask, 6L + 4L * 9L)
  rg_edge_single = iris_ref_region_grow(mask, 5L)

  save, x, y, t_dec, t_inc, spline_dec_s0, spline_inc_s0, spline_dec_s1, spline_inc_s1, $
    spline_inc_default, spline_float_s0, xg, yg, ya, gauss5_fit, gauss5_a, gauss5_chisq, gauss5_status, $
    gauss4_fit, gauss4_a, gauss4_chisq, gauss_abs_fit, gauss_abs_a, gauss_abs_chisq, gauss_abs_status, $
    big_total, big_total_double, big_stdev, big_median, big_median_even, big_nan_median, big_nan_total, $
    where_minus_one, mask, rg_corner, rg_diagonal, rg_interior, rg_edge_single, $
    filename=out_dir + '/probes.sav'
end

function iris_ref_try, name, a1, a2, a3, _extra=extra
  catch, err
  if err ne 0 then begin
    catch, /cancel
    print, 'FAILED ', name, ': ', !error_state.msg
    return, 'FAILED: ' + !error_state.msg
  endif
  print, '=== ', name, ' ', a2
  call_procedure, name, a1, a2, a3, _extra=extra
  catch, /cancel
  return, 'ok'
end

pro iris_ref_run, data_dir=data_dir, out_dir=out_dir, iris_data=iris_data, skip=skip
  if n_elements(data_dir) eq 0 then data_dir = '~/DATA/IRIS'
  if n_elements(out_dir) eq 0 then out_dir = 'iris_ref_out'
  if n_elements(iris_data) gt 0 then setenv, 'IRIS_DATA=' + file_expand_path(iris_data)
  if n_elements(skip) eq 0 then skip = ''
  file_mkdir, out_dir

  r0 = iris_ref_find(data_dir, '*_4000005156_raster/*_raster_t000_r00000.fits')
  r3824 = iris_ref_find(data_dir, '*_3824262996_raster/*_raster_t000_r00000.fits')

  names = ['probes', 'wavecorr 4000005156', 'wavecorr 3824262996', 'mg 4000005156', 'mg 3824262996', $
           'burst 4000005156', 'burst 4000005156 threshold 40', 'sjiburst 4000255147']
  status = strarr(n_elements(names))
  missing = 'FAILED: input file not found'  ; checked here, not left to CATCH
  run = where(strmatch(names, skip) eq 0)  ; skip='mg*' skips the Mg II runs
  for k = 0, n_elements(run) - 1 do begin
    i = run[k]
    case i of
      0: status[i] = iris_ref_try('iris_ref_probes', '', 'probes', out_dir)
      1: status[i] = r0 eq '' ? missing : iris_ref_try('iris_ref_wavecorr', r0, '4000005156_r00000', out_dir)
      2: status[i] = r3824 eq '' ? missing : iris_ref_try('iris_ref_wavecorr', r3824, '3824262996_r00000', out_dir)
      3: status[i] = r0 eq '' ? missing : iris_ref_try('iris_ref_mg', r0, '4000005156_r00000', out_dir)
      4: status[i] = r3824 eq '' ? missing : iris_ref_try('iris_ref_mg', r3824, '3824262996_r00000', out_dir)
      5: status[i] = r0 eq '' ? missing : iris_ref_try('iris_ref_burst', r0, '4000005156_r00000', out_dir)
      6: status[i] = r0 eq '' ? missing : iris_ref_try('iris_ref_burst', r0, '4000005156_r00000_thr40', out_dir, threshold=40.)
      7: status[i] = iris_ref_try('iris_ref_sjiburst', '2-sep-2013 17:00', '4000255147', out_dir)
    endcase
  endfor

  ; provenance: interpreter, every compiled routine with its source file, and the response files
  openw, u, out_dir + '/status.txt', /get_lun
  printf, u, 'version: ' + !version.release + ' ' + !version.os + ' ' + !version.arch + ' ' + !version.build_date, format='(a)'
  printf, u, 'SSW_IRIS: ' + getenv('SSW_IRIS'), format='(a)'
  printf, u, 'IRIS_DATA: ' + getenv('IRIS_DATA'), format='(a)'
  for i = 0, n_elements(names) - 1 do printf, u, names[i] + ': ' + (status[i] eq '' ? 'skipped' : status[i]), format='(a)'
  free_lun, u
  s = [routine_info(/source), routine_info(/source, /functions)]
  openw, u, out_dir + '/compiled_sources.txt', /get_lun
  for i = 0, n_elements(s) - 1 do begin
    fi = file_info(s[i].path)
    printf, u, s[i].name + '  ' + s[i].path + '  ' + strtrim(fi.size, 2) + '  ' + systime(0, fi.mtime), format='(a)'
  endfor
  free_lun, u
  resp = file_search(getenv('SSW_IRIS') + '/response/iris_sra_c_*', count=nresp)
  openw, u, out_dir + '/response_files.txt', /get_lun
  for i = 0, nresp - 1 do printf, u, resp[i], format='(a)'
  free_lun, u
  print, 'Done. Send back the whole ', out_dir, ' directory and the console log.'
end
