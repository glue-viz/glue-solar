pro drv_sjiburst, date, tag
  gdlssw_setup
  setenv, 'IRIS_DATA=' + getenv('IRIS_DATA_LOCAL')
  t0 = systime(1)
  output = 0  ; the routine starts with junk=temporary(output); GDL errors on an undefined argument
  iris_sji_burst_check, date, output=output
  print, 'elapsed s: ' + string(systime(1) - t0)
  if n_elements(output) eq 0 then begin & print, 'no bursts' & return & endif
  print, 'images with bursts: ' + string(n_elements(output))
  ; flatten the LIST of structures for SAVE
  im_index = [] & index = [] & group = [] & int = []
  foreach s, output do begin
    im_index = [im_index, replicate(s.im_index, s.npix)]
    index = [index, s.index] & group = [group, s.group] & int = [int, s.int]
  endforeach
  save, im_index, index, group, int, filename='out/sjiburst_' + tag + '_gdl.sav'
end
