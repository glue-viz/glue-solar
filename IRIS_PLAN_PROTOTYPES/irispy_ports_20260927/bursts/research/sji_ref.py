# Stream only the header + first frame of the 1.3 GB gz SJI 1400 file (Young's reference example).
import gzip, urllib.request, numpy as np
from astropy.io import fits
from scipy import ndimage
url = "https://iris.aws.lmsal.com/data/level2_compressed/2013/10/22/20131022_205938_3820259443/iris_l2_20131022_205938_3820259443_SJI_1400_t000.fits.gz"
g = gzip.GzipFile(fileobj=urllib.request.urlopen(url))
buf = b""
while True:
    buf += g.read(2880)
    if b"END" + b" " * 77 in [buf[i:i + 80] for i in range(len(buf) - 2880, len(buf), 80)]:
        break
hdr = fits.Header.fromstring(buf.decode("ascii"))
nx, ny, bitpix = hdr["NAXIS1"], hdr["NAXIS2"], hdr["BITPIX"]
nbytes = nx * ny * abs(bitpix) // 8
raw = np.frombuffer(g.read(nbytes), dtype=">i2" if bitpix == 16 else ">f4").reshape(ny, nx)
img = raw * hdr.get("BSCALE", 1.0) + hdr.get("BZERO", 0.0)
print("NAXIS", nx, ny, hdr["NAXIS3"], "BSCALE", hdr.get("BSCALE"), "BZERO", hdr.get("BZERO"), "EXPTIME", hdr.get("EXPTIME"), "L2", hdr.get("VER_RF2"), hdr.get("DATE_RF2"))
good = img != -200.0
med_np, sig = np.median(img[good]), np.std(img[good], ddof=1)
srt = np.sort(img[good]); med_idl = srt[srt.size // 2]  # IDL MEDIAN without /EVEN
for name, med in (("np.median", med_np), ("IDL upper median", med_idl)):
    mask = img >= 10.0 * sig + med
    lab, n = ndimage.label(mask, structure=np.ones((3, 3), bool))
    sizes = np.bincount(lab.ravel()); keep = sizes >= 2; keep[0] = False
    print(f"{name}: med {med:.2f} sig {sig:.2f} thr {med + 10 * sig:.1f}  npix(>=2-pixel groups) {int(keep[lab].sum())}  nevents {int(keep.sum())}   (IDL doc example: npix 798, nevents 25, nx 1393, ny 1093)")
