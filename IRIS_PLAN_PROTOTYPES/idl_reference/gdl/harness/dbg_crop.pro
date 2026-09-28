pro dbg_crop
  gdlssw_setup
  d = obj_new('iris_data', getenv('WAVECORR_FILE'))
  iw = d->getwindx(2799.474)
  lam = d->getlam(iw)
  w = d->getvar(iw, /load)
  help, iw, lam, w
  print, 'lam range ' + strjoin(string(minmax(lam)), ' ')
  print, 'data mean/min/max ' + strjoin(string([mean(w), minmax(w)]), ' ')
  t = d->ti2utc()
  help, t
  print, t[0], ' ', t[-1]
end
