# -*- mode: python; coding: utf-8 -*-
# Copyright 2013-2019 Chris Beaumont and the AAS WorldWide Telescope project
# Licensed under the MIT License.

from __future__ import absolute_import, division, print_function

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


def read_png(pth):
    """
    load a PNG image into an array

    Parameters
    ----------
    pth : str
       Path to write read
    """
    return np.asarray(Image.open(pth))
