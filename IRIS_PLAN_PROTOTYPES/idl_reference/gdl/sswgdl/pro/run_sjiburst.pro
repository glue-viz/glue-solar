pro run_sjiburst
  setenv, 'IRIS_DATA=' + getenv('SSWGDL_IRISDATA')
  t0 = systime(1)
  output = 0  ; GDL: TEMPORARY() on an undefined arg errors (routine line 83)
  iris_sji_burst_check, '2-sep-2013 17:00', output=output
  print, 'sji burst seconds: ', systime(1)-t0
  help, output
  if n_elements(output) gt 0 then begin
    openw, u, getenv('SSWGDL_OUT')+'/sji_burst_4000255147.txt', /get_lun
    printf, u, '# im_index nevents npix  then pixel index,group,int per event pixel'
    for i = 0, n_elements(output)-1 do begin
      s = output[i]
      printf, u, s.im_index, s.nevents, s.npix
      for j = 0, s.npix-1 do printf, u, s.index[j], s.group[j], s.int[j]
    endfor
    free_lun, u
  endif
end
