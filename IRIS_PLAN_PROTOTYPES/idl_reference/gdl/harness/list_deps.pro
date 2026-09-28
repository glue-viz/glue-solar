pro list_deps
  drv_mg & drv_wavecorr & drv_burst
  output = 0 & setenv, 'IRIS_DATA=' + getenv('IRIS_DATA_LOCAL')
  iris_sji_burst_check, '2013-09-02 17:00', output=output
  openw, u, 'deps.txt', /get_lun
  foreach isf, [0, 1] do begin
    names = isf ? routine_info(/functions) : routine_info()
    foreach n, names do begin
      s = routine_info(n, /source, functions=isf)
      printf, u, s.path
    endforeach
  endforeach
  free_lun, u
end
