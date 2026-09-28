pro run_burst
  f = '~/DATA/IRIS/0598beef2a051b4f371a4b09e439c4e4-iris_l2_20130902_182935_4000005156_raster/iris_l2_20130902_182935_4000005156_raster_t000_r00000.fits'
  t0 = systime(1)
  iris_burst_check, f, output=output
  print, 'burst seconds: ', systime(1)-t0
  help, output
  if n_tags(output) gt 0 then save, output, file=getenv('SSWGDL_OUT')+'/burst_4000005156_r00000.sav'
end
