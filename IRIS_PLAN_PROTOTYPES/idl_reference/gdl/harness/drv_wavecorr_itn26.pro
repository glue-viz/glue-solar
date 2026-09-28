pro drv_wavecorr_itn26
  gdlssw_setup
  f = getenv('WAVECORR_FILE')
  t0 = systime(1)
  r = iris_prep_wavecorr_l2(f)
  print, 'elapsed s: ' + string(systime(1) - t0)
  corrs = r.corrs & tais = r.tais & corr_tai = r.corr_tai & corr_nuv = r.corr_nuv & corr_fuv = r.corr_fuv
  save, corrs, tais, corr_tai, corr_nuv, corr_fuv, filename='out/wavecorr_itn26_gdl.sav'
end
