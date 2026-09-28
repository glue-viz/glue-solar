pro drv_wavecorr
  gdlssw_setup
  f = '~/DATA/IRIS/f783c3f42607685b74b3230d3c7cc427-iris_l2_20260209_215233_3602506433_raster/iris_l2_20260209_215233_3602506433_raster_t000_r0000' + ['0', '1', '2', '3'] + '.fits'
  t0 = systime(1)
  r = iris_prep_wavecorr_l2(f)
  print, 'elapsed s: ', systime(1) - t0
  help, r, /str
  corrs = r.corrs & chisq = r.chisq & tais = r.tais & corr_tai = r.corr_tai
  corr_nuv = r.corr_nuv & corr_fuv = r.corr_fuv & wave0s = r.wave0s
  save, corrs, chisq, tais, corr_tai, corr_nuv, corr_fuv, wave0s, filename='out/wavecorr_gdl.sav'
end
