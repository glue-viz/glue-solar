import astropy.units as u
from glue.core import Data, DataCollection
from glue.core.state import GlueSerializer
d = Data(x=[1, 2, 3], label='d')
d.meta['exposure time'] = 4 * u.s          # irispy SGMeta carries Quantity values
try:
    GlueSerializer(DataCollection([d])).dumps(); print('save OK')
except Exception as e:
    print('save FAILS:', type(e).__name__, str(e)[:90])
d2 = Data(x=[1, 2, 3], label="d2"); d2.meta["exposure time"] = object()   # unserializable but raises GlueSerializeError -> silently dropped
print("object() value: saved", len(GlueSerializer(DataCollection([d2])).dumps()), 'bytes (filtered)')
