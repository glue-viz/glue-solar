import gzip, urllib.request, socket, numpy as np
socket.setdefaulttimeout(60)
from astropy.io import fits
from scipy import ndimage
url = "https://iris.aws.lmsal.com/data/level2_compressed/2013/10/22/20131022_205938_3820259443/iris_l2_20131022_205938_3820259443_SJI_1400_t000.fits.gz"
g = gzip.GzipFile(fileobj=urllib.request.urlopen(url))
buf = b""
while True:
    buf += g.read(2880)
    if b"END" + b" " * 77 in [buf[i:i + 80] for i in range(len(buf) - 2880, len(buf), 80)]: break
hdr = fits.Header.fromstring(buf.decode("ascii"))
nx, ny = hdr["NAXIS1"], hdr["NAXIS2"]
raw = np.frombuffer(g.read(nx * ny * 2), dtype=">i2").reshape(ny, nx)
img = raw * hdr["BSCALE"] + hdr["BZERO"]
print(nx, ny, hdr["NAXIS3"], hdr.get("VER_RF2"), hdr.get("DATE_RF2"), "DATE_OBS", hdr.get("DATE_OBS"))
good = img != -200.0
v = np.sort(img[good]); med = v[v.size // 2]; sig = v.std(ddof=1)
m = img >= med + 10 * sig
b = np.zeros_like(m); b[0, :] = b[-1, :] = b[:, 0] = b[:, -1] = True
print("flagged", int(m.sum()), "edge flagged", int((m & b).sum()))
for name, mm in (("all", m), ("edges removed", m & ~b)):
    lab, n = ndimage.label(mm, structure=np.ones((3, 3), bool)); sz = np.bincount(lab.ravel()); keep = sz >= 2; keep[0] = False
    print(name, "npix", int(keep[lab].sum()), "nevents", int(keep.sum()))
