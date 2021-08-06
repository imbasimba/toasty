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
RubinDirectoryCollection
SimpleFitsCollection
'''.split()

from abc import ABC
from glob import glob
import numpy as np
from os.path import join
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


class RubinDirectoryCollection(ImageCollection):
    """
    Load up imagery from a directory containing FITS files capturing a Rubin
    Observatory tract.

    The directory will be searched for files whose names end in ``.fits``. In
    each of those files, the HDUs beyond the first will be treated as separate
    science images that should be individually loaded. The images will be
    trimmed according to their ``DATASEC`` specification before being returned.

    This class requires the ``ccdproc``  package to trim FITS CCD datasets.
    """

    def __init__(self, dirname, unit=None):
        self._dirname = dirname
        self._unit = unit

    def _load(self, actually_load_data):
        from astropy.io import fits
        from astropy.nddata import ccddata
        import ccdproc

        for fits_path in glob(join(self._dirname, '*.fits')):
            # `astropy.nddata.ccddata.fits_ccddata_reader` only opens FITS from
            # filenames, not from an open HDUList, which means that creating
            # multiple CCDDatas from the same FITS file rapidly becomes
            # inefficient. So, we emulate its logic.

            with fits.open(fits_path) as hdu_list:
                for idx, hdu in enumerate(hdu_list):
                    if idx == 0:
                        header0 = hdu.header
                    else:
                        hdr = hdu.header
                        hdr.extend(header0, unique=True)

                        # This ccddata function often generates annoying warnings
                        with warnings.catch_warnings():
                            warnings.simplefilter('ignore')
                            hdr, wcs = ccddata._generate_wcs_and_update_header(hdr)

                        # We can't use `ccdproc.trim_image()` without having a
                        # CCDData in hand, so we have to create a fake empty
                        # array even when we're not actually loading any data.
                        #
                        # Note: we skip all the unit-handling logic from
                        # `fits_ccddata_reader` here basically since the LSST
                        # sim data I'm using don't have anything useful.

                        if actually_load_data:
                            data = hdu.data

                            if data.dtype.kind == 'i':
                                data = data.astype(np.float32)
                        else:
                            data = np.empty(hdu.shape, dtype=np.void)

                        ccd = ccddata.CCDData(data, meta=hdr, unit=self._unit, wcs=wcs)
                        ccd = ccdproc.trim_image(ccd, fits_section=ccd.header['DATASEC'])
                        data = ccd.data
                        shape = data.shape
                        wcs = ccd.wcs

                        if actually_load_data:
                            mode = ImageMode.from_array_info(shape, data.dtype)
                        elif hasattr(hdu, 'dtype'):
                            mode = ImageMode.from_array_info(shape, hdu.dtype)
                        else:
                            mode = None  # CompImageHDU doesn't have dtype

                        if actually_load_data:
                            result = Image.from_array(data, wcs=wcs, default_format='fits')
                        else:
                            result = ImageDescription(mode=mode, shape=shape, wcs=wcs)

                        result.collection_id = f'{fits_path}:{idx}'
                        yield result

    def descriptions(self):
        return self._load(False)

    def images(self):
        return self._load(True)
