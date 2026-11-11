import numpy as np


def total():
    return float(np.arange(4).sum())  # a function reading a module-level name


print("X-SCRIPT-RAN", total())
