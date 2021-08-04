# -*- mode: python; coding: utf-8 -*-
# Copyright 2021 the AAS WorldWide Telescope project
# Licensed under the MIT License.

"""
Collections of related input images.

Some Toasty processing tasks operate over collections of input images that are
related in some way. This module provides standardized mechanisms for
manipulating such collections. In particular, it provides a framework for
scanning over image "descriptions" without reading in the complete image data.
This can be useful because many collection-related operations want to do an
initial pass over the collection to gather some global information, then a
second pass with the actual data processing.
"""

__all__ = '''
ImageCollection
SimpleFitsCollection
'''.split()

from abc import ABC
import numpy as np
import warnings

from .image import Image, ImageDescription, ImageMode
from .study import StudyTiling


class ImageCollection(ABC):
    def descriptions(self):
        """
        Generate a sequence of :class:`toasty.image.ImageDescription` items
        associated with this collection.

        Each description will have an added string attribute ``collection_id``
        that gives a unique textual identifer for the item in the collection.

        Unlike :meth:`ImageCollection.images`, this function does cause the full
        data for each image to be loaded.
        """
        raise NotImplementedError()

    def images(self):
        """
        Generate a sequence of :class:`toasty.image.Image` items associated with
        this collection.

        Each image will have an added string attribute ``collection_id`` that
        gives a unique textual identifer for the item in the collection.
        """
        raise NotImplementedError()


class SimpleFitsCollection(ImageCollection):
    def __init__(self, paths, hdu_index=None):
        self._paths = list(paths)
        self._hdu_index = hdu_index

    def _load(self, actually_load_data):
        from astropy.io import fits
        from astropy.wcs import WCS

        for fits_path in self._paths:
            with fits.open(fits_path) as hdul:
                if self._hdu_index is not None:
                    hdu = hdul[self._hdu_index]
                else:
                    for hdu in hdul:
                        if len(hdu.shape) > 1:
                            break

                wcs = WCS(hdu.header)

                if actually_load_data:
                    result = Image.from_array(hdu.data, wcs=wcs, default_format='fits')
                else:
                    shape = hdu.shape
                    
                    if hasattr(hdu, 'dtype'):
                        mode = ImageMode.from_array_info(shape, hdu.dtype)
                    else:
                        mode = None  # CompImageHDU doesn't have dtype

                    result = ImageDescription(mode=mode, shape=shape, wcs=wcs)

                result.collection_id = fits_path
                yield result

    def descriptions(self):
        return self._load(False)

    def images(self):
        return self._load(True)
