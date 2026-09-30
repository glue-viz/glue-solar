import sys, tarfile
from astropy.io import fits
tf = tarfile.open(fileobj=sys.stdin.buffer, mode='r|gz')
for m in tf:
    if not m.isfile(): continue
    f = tf.extractfile(m)
    raw = f.read(2880*6)
    txt = raw.decode('ascii','replace')
    end = txt.find('END' + ' '*77)
    h = fits.Header.fromstring(txt[:end+80])
    print(f"{m.name:80s} {m.size/1e6:8.1f}MB INSTRUME={h.get('INSTRUME')!r} TELESCOP={h.get('TELESCOP')!r} TDESC1={h.get('TDESC1')!r} BTYPE={h.get('BTYPE')!r} BUNIT={h.get('BUNIT')!r} NAXIS={[h.get(f'NAXIS{i}') for i in (1,2,3)]} BITPIX={h.get('BITPIX')}")
