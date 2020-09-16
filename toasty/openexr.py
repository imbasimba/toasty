# -*- mode: python; coding: utf-8 -*-
# Copyright 2020 the AAS WorldWide Telescope project
# Licensed under the MIT License.

"""
Loading OpenEXR files.

This is very primitive support. Implemented for:

https://svs.gsfc.nasa.gov/4851

"""
from __future__ import absolute_import, division, print_function

__all__ = '''
load_openexr
'''.split()

import numpy as np
import sys


def _util_load_openexr_float(path):
    """
    A diagnostic/utility function to load OpenEXR as float data.

    """
    import OpenEXR
    import Imath

    EXR_TO_NUMPY = {
        Imath.PixelType.FLOAT: np.float32,
        Imath.PixelType.HALF: np.float16,
    }

    exr = OpenEXR.InputFile(path)
    header = exr.header()
    dw = header['dataWindow']
    width = dw.max.x - dw.min.x + 1
    height = dw.max.y - dw.min.y + 1

    img = None

    for idx, chan in enumerate('RGB'):
        ctype = header['channels'][chan].type
        cbytes = exr.channel(chan)
        dtype = EXR_TO_NUMPY[ctype.v]

        if img is None:
            img = np.empty((height, width, 3), dtype=dtype)

        img[...,idx] = np.frombuffer(cbytes, dtype=dtype).reshape((height, width))

    return img


def load_openexr(path):
    """
    Load an OpenEXR file

    Parameters
    ----------
    path : path-like
        The path to the file

    Returns
    -------
    An image-like Numpy array with shape ``(height, width, planes)``
    and a dtype of uint8.

    """
    try:
        import OpenEXR
        import Imath
    except ImportError as e:
        raise Exception('cannot load OpenEXR file: needed support libraries are not available') from e

    EXR_TO_NUMPY = {
        Imath.PixelType.FLOAT: np.float32,
        Imath.PixelType.HALF: np.float16,
    }

    exr = OpenEXR.InputFile(path)
    header = exr.header()
    dw = header['dataWindow']
    width = dw.max.x - dw.min.x + 1
    height = dw.max.y - dw.min.y + 1

    if header['lineOrder'] != Imath.LineOrder(Imath.LineOrder.INCREASING_Y):
        raise Exception('cannot load OpenEXR file: unsupported lineOrder')
    if len(header['channels']) != 3:
        raise Exception('cannot load OpenEXR file: expected exactly 3 channels')
    if 'chromaticities' in header:
        print('warning: ignoring chromaticities in OpenEXR file; colors will be distorted',
              file=sys.stderr)
    if 'whiteLuminance' in header:
        print('warning: ignoring whiteLuminance in OpenEXR file; colors will be distorted',
              file=sys.stderr)

    img = np.empty((height, width, 3), dtype=np.uint8)

    try:
        for idx, chan in enumerate('RGB'):
            ctype = header['channels'][chan].type
            cbytes = exr.channel(chan)
            carr = np.frombuffer(cbytes, dtype=EXR_TO_NUMPY[ctype.v]).reshape((height, width))

            # XXX: manually implemented sRGB conversion is not awesome, and also
            # ideally this wouldn't be done here. Equations from
            # https://discourse.techart.online/t/converting-linear-exr-to-srgb-jpeg-with-python/2267/3

            # Need a read-write buffer:
            work = carr.copy()

            # Small-value branch of sGRB. Assume that there aren't many of
            # these, and avoid modifying non-small values.
            mask = (carr <= 0.0031308)
            del carr
            work[mask] *= 12.92 * 255
            np.copyto(img[...,idx], work, where=mask, casting='unsafe')

            # Main branch. Replace small values with something that won't
            # give math errors.
            work[mask] = 0.0032
            np.power(work, 1 / 2.4, out=work)
            np.multiply(work, 1.055, out=work)
            np.subtract(work, 0.055, out=work)
            np.multiply(work, 255, out=work)
            np.logical_not(mask, out=mask)
            np.copyto(img[...,idx], work, where=mask, casting='unsafe')
    except Exception as e:
        raise Exception('cannot load OpenEXR file: unexpected file structure') from e

    return img