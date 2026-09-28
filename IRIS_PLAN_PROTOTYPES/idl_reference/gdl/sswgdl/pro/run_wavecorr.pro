pro run_wavecorr
  f = '~/DATA/IRIS/0598beef2a051b4f371a4b09e439c4e4-iris_l2_20130902_182935_4000005156_raster/iris_l2_20130902_182935_4000005156_raster_t000_r00000.fits'
  t0 = systime(1)
  r = iris_prep_wavecorr_l2(f)
  print, 'wavecorr seconds: ', systime(1)-t0
  help, r, /str
  out = getenv('SSWGDL_OUT')
  save, r, file=out+'/wavecorr_4000005156_r00000.sav'
  openw, u, out+'/wavecorr_4000005156_r00000.txt', /get_lun
  printf, u, '# corr_tai corr_nuv corr_fuv  (iris_prep_wavecorr_l2, GDL)'
  for i = 0, n_elements(r.corr_tai)-1 do printf, u, r.corr_tai[i], r.corr_nuv[i], r.corr_fuv[i], format='(f20.6,2e16.7)'
  free_lun, u
  print, 'corrs[0,*,*] (step, line) first 5 steps:'
  print, reform(r.corrs[0, 0:4, *])
end
