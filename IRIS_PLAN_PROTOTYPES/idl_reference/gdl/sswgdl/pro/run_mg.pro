pro run_mg
  f = '~/DATA/IRIS/0598beef2a051b4f371a4b09e439c4e4-iris_l2_20130902_182935_4000005156_raster/iris_l2_20130902_182935_4000005156_raster_t000_r00000.fits'
  d = iris_obj(f)
  n = d->getnwin()
  iwin = -1
  for i = 0, n-1 do begin
    lam = d->getlam(i)
    print, i, ' ', d->getline_id(i), min(lam), max(lam)
    if min(lam) lt 2796.35 and max(lam) gt 2803.53 then iwin = i
  endfor
  obj_destroy, d
  print, 'Mg II window: ', iwin
  t0 = systime(1)
  iris_get_mg_features_lev2, f, iwin, [-40, 40], lc, rp, bp
  print, 'mg seconds: ', systime(1)-t0
  help, lc, rp, bp
  save, lc, rp, bp, iwin, file=getenv('SSWGDL_OUT')+'/mg_features_4000005156_r00000.sav'
  print, 'k lc vel/int at slit 0..4, raster 0:'
  print, lc[0, *, 0:4, 0]
end
