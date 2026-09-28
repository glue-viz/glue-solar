import glob, warnings, traceback
import matplotlib.pyplot as plt
import irispy
from irispy.io import read_files
from irispy.io.sji import read_sji_lvl2
print(irispy.__file__)
B = "<scratch>/features/itn32-sot/"
fg = B + "small/x/sot_l2_20150830_070953_3603259402_20150830100400_Gband4305_FG.fits"
mg = B + "small/x/sot_l2_20160108_191211_3680100932_20160108181400_TFNaI5896_MG.fits"
sp = B + "small/x/sotsp_l2_20160108_191211_3680100932_20160108_185006_blapp_index.fits"
try:
    read_files([fg, mg, sp])
except Exception as e:
    print("read_files:", type(e).__name__, e)
for f in (fg, mg, sp):
    try:
        c = read_sji_lvl2(f)
        print(type(c).__name__, c.unit, c.shape)
        try:
            c.to_maps(0).plot(); plt.close("all"); print(" to_maps plot ok")
        except Exception as e:
            print(" to_maps plot:", type(e).__name__, str(e)[:120])
    except Exception as e:
        print("read_sji_lvl2:", f.split("/")[-1], type(e).__name__, str(e)[:150])
