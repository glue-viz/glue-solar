"""
A reader for 'La Palma' datacubes from the Swedish 1-m Solar Telescope
"""
import numpy as np
from glue.config import data_factory
from glue.core.data_factories import has_extension
from glue.core import Data


def lp_getheader(filename):
    """
    Reads header from La Palma format cube.

    Parameters
    ----------
    filename : str
        File to read header from.

    Returns
    -------
    result : list
        List with shape tuple (nx, ny [, nt]),
        datatype (with endianness), header string.
    """
    # read header and convert to string
    h = np.fromfile(filename, dtype='uint8', count=512)
    header = ''
    for s in h[h > 0]:
        header += chr(s)
    # start reading at 'datatype'
    hd = header[header.lower().find('datatype'):]
    hd = hd.split(':')[0].replace(',', ' ').split()
    # Types:   uint8  int16 int32 float32
    typelist = ['u1', 'i2', 'i4', 'f4']
    # extract datatype
    try:
        dtype = typelist[int(hd[0].split('=')[1]) - 1]
    except:
        print(header)
        raise IOError('lp_getheader: datatype invalid or missing')
    # extract endianness
    try:
        if hd[-1].split('=')[0].lower() != 'endian':
            raise IndexError()
        endian = hd[-1].split('=')[1]
    except IndexError:
        print(header)
        raise IOError('lp_getheader: endianess missing.')
    if endian.lower() == 'l':
        dtype = '<' + dtype
    else:
        dtype = '>' + dtype
    # extract dims
    try:
        if hd[2].split('=')[0].lower() != 'dims':
            raise IndexError()
        dims = int(hd[2].split('=')[1])
        if dims not in [2, 3]:
            raise ValueError('Invalid dims=%i (must be 2 or 3)' % dims)
    except IndexError:
        print(header)
        raise IOError('lp_getheader: dims invalid or missing.')
    try:
        if hd[3].split('=')[0].lower() != 'nx':
            raise IndexError()
        nx = int(hd[3].split('=')[1])
    except:
        print(header)
        raise IOError('lp_getheader: nx invalid or missing.')
    try:
        if hd[4].split('=')[0].lower() != 'ny':
            raise IndexError()
        ny = int(hd[4].split('=')[1])
    except:
        print(header)
        raise IOError('lp_getheader: ny invalid or missing.')
    if dims == 3:
        try:
            if hd[5].split('=')[0].lower() != 'nt':
                raise IndexError()
            nt = int(hd[5].split('=')[1])
        except:
            print(header)
            raise IOError('lp_getheader: nt invalid or missing.')
        shape = (nx, ny, nt)
    else:
        shape = (nx, ny)
    return [shape, dtype, header]


def lp_getdata(filename, rw=False, verbose=False):
    """
    Reads La Palma format cube into a memmap object.

    Parameters
    ----------
    filename : str
        File to read.
    rw : bool, optional
        If True, then any change to the data will be written to file.
    verbose : bool, optional
        If True, will print out additional information.

    Returns
    -------
    data : ndarray
        Numpy memmap object with data.
    """
    sh, dt, header = lp_getheader(filename)
    if verbose:
        print(('Reading %s...\n%s' % (filename, header)))
    mode = ['c', 'r+']
    return np.memmap(filename, mode=mode[rw], shape=sh, dtype=dt, order='F',
                     offset=512)


@data_factory('La Palma cube', has_extension('fcube icube'), default='fcube icube')
def read_lapalma(file_name):
    data = lp_getdata(file_name)
    return Data(cube=data)
