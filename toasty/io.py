# -*- mode: python; coding: utf-8 -*-
# Copyright 2013-2020 Chris Beaumont and the AAS WorldWide Telescope project
# Licensed under the MIT License.

from __future__ import absolute_import, division, print_function

__all__ = '''
read_image
save_png
'''.split()

from PIL import Image
import numpy as np


def save_png(pth, array):
    """
    Save an array as a PNG image

    Parameters
    ----------
    pth : str
        Path to write to
    array : array-like
        Image to save
    """
    Image.fromarray(array).save(pth)


def read_image(path):
    """Load a bitmap image into a Numpy array.

    The loading is done using PIL (the Python Imaging Library, usually the
    "pillow" implementation these days) so it supports whatever image formats
    PIL does.

    Parameters
    ----------
    path : str
        The path of the image to read

    Returns
    -------
    data : :class:`numpy.ndarray`
        The image data. The array will have shape ``(height, width, planes)``, where
        the first two axes are the image shape and the third is the number of color planes:
        3 for RGB or potentially 4 for ARGB. The data type will be ``uint8``.

    """
    return np.asarray(Image.open(path))
