import io, numpy as np, matplotlib; matplotlib.use("QtAgg")
import matplotlib.pyplot as plt, mpl_scatter_density
rng = np.random.default_rng(0); x, y = rng.normal(size=(2, 200000))
fig = plt.figure(figsize=(4, 4)); ax = fig.add_subplot(111, projection="scatter_density"); art = ax.scatter_density(x, y)
fig.canvas.draw()
def png(): b = io.BytesIO(); fig.savefig(b, format="png"); return b.getvalue()
ax.set_xlim(-1, 1); ax.set_ylim(-1, 1)  # a view change, as a pan or a resize of the figure
art._resize_start()  # what the Qt canvas's resize event calls; its 500 ms timer then calls on_release
print("pressed:", art._pressed, "| extent while held:", art.get_extent(), "| view:", ax.get_xlim(), ax.get_ylim())
held = png(); art.on_release(); released = png()
print("saved during the hold == saved after release:", held == released)
