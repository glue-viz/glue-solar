import sys
import numpy as np
import cmp_mg
from irispy.utils.mg_features import calculate_mg_features

def ours(cube, wave, steps):
    res = calculate_mg_features(cube[steps[0]:steps[-1] + 1])
    sel = np.array(steps) - steps[0]
    return {line: tuple(np.stack([res[f"{line}{f}_velocity"].data, res[f"{line}{f}_intensity"].data], -1)[sel] for f in ("3", "2v", "2r")) for line in "kh"}

obs = sys.argv[1]
n = int(sys.argv[2])
cmp_mg.run(obs, ours, list(range(0, n)))
