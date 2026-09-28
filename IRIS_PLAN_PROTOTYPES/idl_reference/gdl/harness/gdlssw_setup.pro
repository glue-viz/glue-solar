; Minimal SolarSoft emulation for GDL: env vars from iris/setup/setup.iris_env and an
; SSW-like !path (iris first, then gen), in front of GDL's own library.
pro gdlssw_setup
  ssw = getenv('SSW')
  setenv, 'SSW_IRIS=' + ssw + '/iris'
  setenv, 'SSW_IRIS_DATA=' + ssw + '/iris/data'
  setenv, 'IRIS_RESPONSE=' + ssw + '/iris/response'
  setenv, 'IRIS_ANCILLARY=' + ssw + '/iris/idl/uio/ancillary/'
  dirs = ssw + '/iris/idl/' + ['lmsal', 'uio', 'nrl', 'sao', 'mssl', 'msu', 'nso', 'ucar']
  dirs = [getenv('HARNESS'), dirs, ssw + '/vobs/ontology/idl', ssw + '/gen/idl', ssw + '/gen/idl_libs']
  p = ''
  foreach d, dirs do p += expand_path('+' + d) + ':'
  !path = p + !path
  !quiet = 1
end
