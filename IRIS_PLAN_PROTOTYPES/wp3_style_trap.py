"""Auditor's version-2 VisualAttributes override: works in-process, but every session saved while glue-solar is
installed then needs glue-solar to load, even with no solar data in it. Compare with the subclass form."""
import os, sys, json, subprocess, textwrap, warnings
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("MPLBACKEND", "agg"); warnings.simplefilter("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from glue.core import Data, DataCollection
from glue.core.state import GlueSerializer, GlueUnSerializer, saver, loader
from glue.core.visual import VisualAttributes
plain = Data(x=[1, 2, 3], label="plain")
stock = GlueSerializer(DataCollection([plain])).dumps()
@saver(VisualAttributes, version=2)
def _save_style2(style, context):
    r = {a: getattr(style, a) for a in style._atts}; r["preferred_cmap"] = getattr(r["preferred_cmap"], "name", r["preferred_cmap"]); return r
@loader(VisualAttributes, version=2)
def _load_style2(rec, context):
    result = VisualAttributes()
    for attr in result._atts: setattr(result, attr, rec[attr])
    return result
v2 = GlueSerializer(DataCollection([Data(x=[1, 2, 3], label="plain")])).dumps()
print("v2 style record of a plain dataset:", [v["style"] for v in json.loads(v2).values() if isinstance(v, dict) and "style" in v][0])
print("in-process reload with v2 registered:", GlueUnSerializer.loads(v2).object("__main__")[0].label)
open(os.path.join(HERE, "wp3_v2.glu"), "w").write(v2); open(os.path.join(HERE, "wp3_stock.glu"), "w").write(stock)
code = textwrap.dedent("""
    import sys, warnings; warnings.simplefilter("ignore")
    from glue.core.state import GlueUnSerializer
    for fn in ("wp3_stock.glu", "wp3_v2.glu"):
        try: print(fn, "->", GlueUnSerializer.loads(open(sys.argv[1] + "/" + fn).read()).object("__main__")[0].label)
        except Exception as e: print(fn, "-> FAIL", type(e).__name__ + ":", str(e)[:80])
    print("glue_solar imported:", "glue_solar" in sys.modules)
""")
print("-- fresh interpreter WITHOUT glue_solar --")
print(subprocess.run([sys.executable, "-c", code, HERE], capture_output=True, text=True).stdout.strip())
