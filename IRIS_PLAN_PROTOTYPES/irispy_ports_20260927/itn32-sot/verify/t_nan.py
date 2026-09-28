import glob
import matplotlib.pyplot as plt
from irispy.io.sji import read_sji_lvl2
f = glob.glob("<scratch>/features/verify-itn32-sot/dl/copy/*/*_I.fits")[0]
c = read_sji_lvl2(f)
for label, fn in (("cube.plot", lambda: c.plot()), ("cube[0].plot", lambda: c[0].plot()), ("to_maps(0).plot", lambda: c.to_maps(0).plot())):
    try:
        fn(); plt.gcf().canvas.draw(); print("OK", label)
    except Exception as e:
        print("FAIL", label, type(e).__name__, str(e)[:150])
    plt.close("all")
