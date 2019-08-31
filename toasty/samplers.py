# Copyright 2013-2019 Chris Beaumont and the AAS WorldWide Telescope project
# Licensed under the MIT License.

"""“Sampler” functions that fetch image data as a function of sky coordinates.

"""
from __future__ import absolute_import, division, print_function

__all__ = '''
cartesian_sampler
healpix_fits_file_sampler
healpix_sampler
normalizer
'''.split()

import numpy as np


def healpix_sampler(data, nest=False, coord='C', interpolation='nearest'):
    """Create a sampler for HEALPix image data.

    Parameters
    ----------
    data : array
      The HEALPix data
    nest : bool (default: False)
      Whether the data is ordered in the nested HEALPix style
    coord : 'C' | 'G'
      Whether the image is in Celestial (C) or Galactic (G) coordinates
    interpolation : 'nearest' | 'bilinear'
      What interpolation scheme to use.

      WARNING: bilinear uses healpy's get_interp_val,
               which seems prone to segfaults

    Returns
    -------
    A function that samples the HEALPix data; the call signature is
    ``vec2pix(lon, lat) -> data``, where the inputs and output are 2D arrays
    and *lon* and *lat* are in radians.

    """
    from healpy import ang2pix, get_interp_val, npix2nside
    from astropy.coordinates import Galactic, FK5
    import astropy.units as u

    interp_opts = ['nearest', 'bilinear']
    if interpolation not in interp_opts:
        raise ValueError("Invalid interpolation %s. Must be one of %s" %
                         (interpolation, interp_opts))
    if coord.upper() not in 'CG':
        raise ValueError("Invalid coord %s. Must be 'C' or 'G'" % coord)

    galactic = coord.upper() == 'G'
    interp = interpolation == 'bilinear'
    nside = npix2nside(data.size)

    def vec2pix(l, b):
        if galactic:
            f = FK5(l * u.rad, b * u.rad)
            g = f.transform_to(Galactic)
            l, b = g.l.rad, g.b.rad

        theta = np.pi / 2 - b
        phi = l

        if interp:
            return get_interp_val(data, theta, phi, nest=nest)

        return data[ang2pix(nside, theta, phi, nest=nest)]

    return vec2pix


def _find_healpix_extension_index(pth):
    """Find the first HEALPIX extension in a FITS file and return the extension
    number. Raises IndexError if none is found.

    """
    for i, hdu in enumerate(pth):
        if hdu.header.get('PIXTYPE') == 'HEALPIX':
            return i
    else:
        raise IndexError("No HEALPIX extensions found in %s" % pth.filename())


def healpix_fits_file_sampler(path, extension=None, interpolation='nearest'):
    """Create a sampler for HEALPix data read from a FITS file.

    Parameters
    ----------
    path : string
      The path to the FITS file.
    extension : integer or None (default: None)
      Which extension in the FITS file to read. If not specified, the first
      extension with PIXTYPE = "HEALPIX" will be used.
    interpolation : 'nearest' | 'bilinear'
      What interpolation scheme to use.

      WARNING: bilinear uses healpy's get_interp_val,
               which seems prone to segfaults

    Returns
    -------
    A function that samples the HEALPix image; the call signature is
    ``vec2pix(lon, lat) -> data``, where the inputs and output are 2D arrays
    and *lon* and *lat* are in radians.

    """
    from astropy.io import fits

    with fits.open(path) as f:
        if extension is None:
            extension = _find_healpix_extension_index(f)

        data, hdr = f[extension].data, f[extension].header
        # grab the first healpix parameter
        data = data[data.dtype.names[0]]
        nest = hdr.get('ORDERING') == 'NESTED'
        coord = hdr.get('COORDSYS', 'C')

    return healpix_sampler(data, nest, coord, interpolation)


def cartesian_sampler(data):
    """Create a sampler function for all-sky data in a Cartesian projection.

    The image is assumed to be oriented with longitude increasing to the left,
    with (l,b) = (0,0) at the center pixel

    Parameters
    ----------
    data : 2D array-like
      The map to sample. The height of the map must be exactly twice its with.

    Returns
    -------
    A function that samples the image; the call signature is
    ``vec2pix(lon, lat) -> data``, where the inputs and output are 2D arrays
    and *lon* and *lat* are in radians.

    """
    data = np.asarray(data)
    ny, nx = data.shape[:2]

    if ny * 2 != nx:
        raise ValueError("Map must be twice as wide as it is tall")

    def vec2pix(l, b):
        l = (l + np.pi) % (2 * np.pi)
        l[l < 0] += 2 * np.pi
        l = nx * (1 - l / (2 * np.pi))
        l = np.clip(l.astype(np.int), 0, nx - 1)
        b = ny * (1 - (b + 0.5 * np.pi) / np.pi)
        b = np.clip(b.astype(np.int), 0, ny - 1)
        return data[b, l]

    return vec2pix


def normalizer(sampler, vmin, vmax, scaling='linear', bias=0.5, contrast=1):
    """Create a sampler that applies an intensity scaling to another sampler.

    Parameters
    ----------
    sampler : function
       An input sampler function with call signature ``vec2pix(lon, lat) -> data``.
    vmin : float
      The data value to assign to 0 (black).
    vmin : float
      The data value to assign to 255 (white).
    bias : float between 0-1, default: 0.5
      Where to assign middle-grey, relative to (vmin, vmax).
    contrast : float, default: 1
      How quickly to ramp from black to white. The default of 1
      ramps over a data range of (vmax - vmin)
    scaling : 'linear' | 'log' | 'arcsinh' | 'sqrt' | 'power'
      The type of intensity scaling to apply

    Returns
    -------
    A function that scales the input sampler; the call signature is
    ``vec2pix(lon, lat) -> data``, where the inputs and output are 2D arrays
    and *lon* and *lat* are in radians. The output has a dtype of ``np.uint8``.

    """
    from .norm import normalize

    def result(x, y):
        raw = sampler(x, y)
        if raw is None:
            return raw

        r = normalize(raw, vmin, vmax, bias, contrast, scaling)
        return r

    return result
