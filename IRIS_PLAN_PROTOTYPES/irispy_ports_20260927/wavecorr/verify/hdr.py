import sys, glob
from astropy.io import fits
for f in sorted(glob.glob('~/DATA/IRIS/*_raster/*raster*.fits')):
    with fits.open(f, memmap=True, do_not_scale_image_data=True) as h:
        p = h[0].header
        keys = [k for k in p.keys() if any(s in k for s in ('VR','WAVE','CORR','VER','STEPS','LVL','PROC','THERM','DATE'))]
        print('==', f.split('/')[-1], 'NWIN', p['NWIN'], 'STEPS_AV', p.get('STEPS_AV'), 'OBS_VR' in p)
        print({k: p[k] for k in keys if not k.startswith('TWAVE')})
        aux = h[-2].header
        print('aux cols with VR/PZ:', [k for k in aux if k.endswith('IX') and ('VR' in k or 'PZ' in k or 'PHASE' in k)])
        pz = h[-2].data[:, aux['PZTXIX']] if 'PZTXIX' in aux else None
        if pz is not None and len(pz) > 1:
            print('pztx[0:3]', pz[:3], 'dx0', pz[1]-pz[0])
        hist = [str(x) for x in p.get('HISTORY', [])]
        print('HISTORY n', len(hist), [x for x in hist if 'wav' in x.lower() or 'orb' in x.lower() or 'therm' in x.lower()][:5])
