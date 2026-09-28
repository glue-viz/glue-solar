pro drv_burst
  gdlssw_setup
  f = '~/DATA/IRIS/f783c3f42607685b74b3230d3c7cc427-iris_l2_20260209_215233_3602506433_raster/iris_l2_20260209_215233_3602506433_raster_t000_r0000' + ['0', '1', '2', '3'] + '.fits'
  t0 = systime(1)
  iris_burst_check, f, output=output
  print, 'elapsed s: ', systime(1) - t0
  help, output
  if n_tags(output) ne 0 then save, output, filename='out/burst_gdl.sav'
  ; fixed threshold run (no response scaling) to exercise the grouping path
  iris_burst_check, f, output=out50, threshold=50., /quiet
  help, out50
  if n_tags(out50) ne 0 then save, out50, filename='out/burst50_gdl.sav'
end
