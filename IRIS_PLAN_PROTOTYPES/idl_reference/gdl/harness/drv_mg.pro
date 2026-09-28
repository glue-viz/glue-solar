pro drv_mg
  gdlssw_setup
  f = '~/DATA/IRIS/f783c3f42607685b74b3230d3c7cc427-iris_l2_20260209_215233_3602506433_raster/iris_l2_20260209_215233_3602506433_raster_t000_r00000.fits'
  t0 = systime(1)
  iris_get_mg_features_lev2, f, 6, [-40, 40], lc, rp, bp
  print, 'elapsed s: ', systime(1) - t0
  help, lc, rp, bp
  save, lc, rp, bp, filename='out/mg_features_gdl.sav'
end
