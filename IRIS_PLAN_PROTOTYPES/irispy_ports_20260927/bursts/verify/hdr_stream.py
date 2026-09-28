import sys, tarfile, urllib.request, socket
socket.setdefaulttimeout(60)
from astropy.io import fits
url=sys.argv[1]
tf=tarfile.open(fileobj=urllib.request.urlopen(url), mode="r|gz")
m=tf.next(); print(m.name, m.size)
f=tf.extractfile(m)
buf=b""
while b"END"+b" "*77 not in [buf[i:i+80] for i in range(max(0,len(buf)-2880),len(buf),80)]:
    buf+=f.read(2880)
h=fits.Header.fromstring(buf.decode("ascii"))
for k in ("OBSID","OBS_DESC","DATE_OBS","SUMSPAT","SUMSPTRF","STEPS_AV","NRASTERP","RASNRPT","EXPTIME","SAT_ROT","NWIN","VER_RF2","DATE_RF2"):
    print(k, h.get(k))
for i in range(1,h["NWIN"]+1): print(i, h[f"TDESC{i}"], h[f"TWMIN{i}"], h[f"TWMAX{i}"])
