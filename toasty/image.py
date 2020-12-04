# -*- mode: python; coding: utf-8 -*-
# Copyright 2020 the AAS WorldWide Telescope project
# Licensed under the MIT License.

"""
Low-level loading and handling of images.

Here, images are defined as 2D data buffers stored in memory. Images might be
small, if dealing with an individual tile, or extremely large, if loading up a
large study for tiling.

"""
from __future__ import absolute_import, division, print_function

__all__ = '''
Image
ImageLoader
ImageMode
'''.split()

from enum import Enum
from PIL import Image as pil_image
import numpy as np
import sys

try:
    from astropy.io import fits
    ASTROPY_INSTALLED = True
except ImportError:
    ASTROPY_INSTALLED = False

PIL_RGB_FORMATS = {'jpg': 'JPEG'}
PIL_RGBA_FORMATS = {'png': 'PNG'}
PIL_FORMATS = PIL_RGB_FORMATS.copy()
PIL_FORMATS.update(PIL_RGBA_FORMATS)
SUPPORTED_FORMATS = list(PIL_RGB_FORMATS) + list(PIL_RGBA_FORMATS) + ['npy']

if ASTROPY_INSTALLED:
    SUPPORTED_FORMATS += ['fits']


def _validate_format(name, fmt):
    if fmt is not None and fmt not in SUPPORTED_FORMATS:
        raise ValueError('{0} should be one of {1}'.format(name, '/'.join(sorted(SUPPORTED_FORMATS))))


def _array_to_mode(array):
    if array.ndim == 2 and array.dtype.kind == 'f':
        if array.dtype.itemsize == 4:
            return ImageMode.F32
        elif array.dtype.itemsize == 8:
            return ImageMode.F64
    elif array.ndim == 3:
        if array.shape[2] == 3:
            if array.dtype.kind == 'f' and array.itemsize == 2:
                return ImageMode.F16x3
            elif array.dtype.kind == 'u' and array.dtype.itemsize == 1:
                return ImageMode.RGB
        elif array.shape[2] == 4:
            if array.dtype.kind == 'u' and array.dtype.itemsize == 1:
                return ImageMode.RGBA
    raise ValueError('Could not determine mode for array with dtype {0} and shape {1}'.format(array.dtype, array.shape))


class ImageMode(Enum):
    """
    Allowed image "modes", describing their pixel data formats.

    These align with PIL modes when possible, but we expect to need to support
    modes that aren't present in PIL (namely, float64). There are also various
    obscure PIL modes that we do not support.

    """
    RGB = 'RGB'
    RGBA = 'RGBA'
    F32 = 'F'
    F64 = 'D'
    F16x3 = 'F16x3'

    def make_maskable_buffer(self, buf_height, buf_width):
        """
        Return a new, uninitialized buffer of the specified shape, with a mode
        compatible with this one but able to accept undefined values.

        Parameters
        ----------
        buf_height : int
            The height of the new buffer
        buf_width : int
            The width of the new buffer

        Returns
        -------
        An uninitialized :class:`Image` instance.

        Notes
        -----
        "Maskable" means that the buffer can accommodate undefined values.
        If the image is RGB or RGBA, that means that the buffer will have an
        alpha channel. If the image is scientific, that means that the buffer
        will be able to accept NaNs.

        """

        if self in (ImageMode.RGB, ImageMode.RGBA):
            arr = np.empty((buf_height, buf_width, 4), dtype=np.uint8)
        elif self == ImageMode.F32:
            arr = np.empty((buf_height, buf_width), dtype=np.float32)
        elif self == ImageMode.F64:
            arr = np.empty((buf_height, buf_width), dtype=np.float64)
        elif self == ImageMode.F16x3:
            arr = np.empty((buf_height, buf_width, 3), dtype=np.float16)
        else:
            raise Exception('unhandled mode in make_maskable_buffer()')

        return Image.from_array(arr)

    def try_as_pil(self):
        """
        Attempt to convert this mode into a PIL image mode string.

        Returns
        -------
        A PIL image mode string, or None if there is no exact counterpart.
        """
        if self == ImageMode.F16x3:
            return None
        return self.value


class ImageLoader(object):
    """
    A class defining how to load an image.

    This is implemented as its own class since there can be some options
    involved, and we want to provide a centralized place for handling them all.
    """
    black_to_transparent = False
    colorspace_processing = 'srgb'
    crop = None
    psd_single_layer = None

    @classmethod
    def add_arguments(cls, parser):
        """
        Add standard image-loading options to an argparse parser object.

        Parameters
        ----------
        parser : :class:`argparse.ArgumentParser`
            The argument parser to modify

        Returns
        -------
        The :class:`ImageLoader` class (for chainability).

        Notes
        -----
        If you are writing a command-line interface that takes a single image as
        an input, use this function to wire in to standardized image-loading
        infrastructure and options.

        """
        parser.add_argument(
            '--black-to-transparent',
            action = 'store_true',
            help = 'Convert full black colors to be transparent',
        )
        parser.add_argument(
            '--colorspace-processing',
            metavar = 'MODE',
            default = 'srgb',
            help = 'What kind of RGB colorspace processing to perform (default: %(default)s; choices: %(choices)s)',
            choices = ['srgb', 'none'],
        )
        parser.add_argument(
            '--crop',
            metavar = 'TOP,RIGHT,BOTTOM,LEFT',
            help = 'Crop the input image by discarding pixels from each edge (default: 0,0,0,0)',
        )
        parser.add_argument(
            '--psd-single-layer',
            type = int,
            metavar = 'NUMBER',
            help = 'If loading a Photoshop image, the (0-based) layer number to load -- saves memory',
        )
        return cls

    @classmethod
    def create_from_args(cls, settings):
        """
        Process standard image-loading options to create an :class:`ImageLoader`.

        Parameters
        ----------
        settings : :class:`argparse.Namespace`
            Settings from processing command-line arguments

        Returns
        -------
        A new :class:`ImageLoader` initialized with the settings.
        """
        loader = cls()
        loader.black_to_transparent = settings.black_to_transparent
        loader.colorspace_processing = settings.colorspace_processing
        loader.psd_single_layer = settings.psd_single_layer

        if settings.crop is not None:
            try:
                crop = list(map(int, settings.crop.split(',')))
                assert all(c >= 0 for c in crop)
                assert len(crop) in (1, 2, 4)
            except Exception:
                raise Exception('cannot parse `--crop` setting `{settings.crop!r}`: should be a comma-separated list of 1, 2, or 4 non-negative integers')

            if len(crop) == 1:
                c = crop[0]
                crop = [c, c, c, c]
            elif len(crop) == 2:
                cv, ch = crop
                crop = [cv, ch, cv, ch]

            loader.crop = crop

        return loader

    def load_pil(self, pil_img):
        """
        Load an already opened PIL image.

        Parameters
        ----------
        pil_img : :class:`PIL.Image.Image`
            The image.

        Returns
        -------
        A new :class:`Image`.

        Notes
        -----
        This function should be used instead of :meth:`Image.from_pil` because
        may postprocess the image in various ways, depending on the loader
        configuration.

        """
        # If we're cropping, do it.
        if self.crop is not None:
            upper = self.crop[0]
            right = pil_img.width - self.crop[1]
            lower = pil_img.height - self.crop[2]
            left = self.crop[3]

            # This operation can trigger PIL decompression-bomb aborts, so
            # avoid them in the standard, non-thread-safe, way.
            old_max = pil_image.MAX_IMAGE_PIXELS
            try:
                pil_image.MAX_IMAGE_PIXELS = None
                pil_img = pil_img.crop((left, upper, right, lower))
            finally:
                pil_image.MAX_IMAGE_PIXELS = old_max

        # If 8-bit grayscale, convert to RGB. Added for
        # https://www.flickr.com/photos/10795027@N08/43023455582 . That file
        # also comes with an ICC profile so we do the conversion before
        # colorspace processing. TODO: if/when we do FITS to RGB conversion, we
        # should probably use that codepath rather than this manual hack.

        if pil_img.mode == 'L':
            pil_img = pil_img.convert('RGBA')

        # Convert pure black to transparent -- make sure to do this before any
        # colorspace processing.
        #
        # As far as I can tell, PIL has no good way to modify an image on a
        # pixel-by-pixel level in-place, which is really annoying. For now I'm
        # doing this processing in Numpy space, but for an image that almost
        # fills up memory we might have to use a different approach since this
        # one will involve holding two buffers at once.

        if self.black_to_transparent:
            if pil_img.mode != 'RGBA':
                pil_img = pil_img.convert('RGBA')
            a = np.asarray(pil_img)
            a = a.copy()  # read-only buffer => writeable

            for i in range(a.shape[0]):
                nonblack = (a[i,...,0] > 0)
                np.logical_or(nonblack, a[i,...,1] > 0, out=nonblack)
                np.logical_or(nonblack, a[i,...,2] > 0, out=nonblack)
                a[i,...,3] *= nonblack

            # This is my attempt to preserve the image metadata and other
            # attributes, swapping out the pixel data only. There is probably
            # a better way to do this
            new_img = pil_image.fromarray(a, mode=pil_img.mode)
            pil_img.im = new_img.im
            del a, new_img

        # Make sure that we end up in the right color space. From experience, some
        # EPO images have funky colorspaces and we need to convert to sRGB to get
        # the tiled versions to appear correctly.

        if self.colorspace_processing != 'none' and 'icc_profile' in pil_img.info:
            assert self.colorspace_processing == 'srgb' # more modes, one day?

            try:
                from PIL import ImageCms
                # ImageCms doesn't raise import error if the implementation is unavailable
                # "for doc purposes". To see if it's available we need to actually try to
                # do something:
                out_prof = ImageCms.createProfile('sRGB')
            except ImportError:
                print('''warning: colorspace processing requested, but no `ImageCms` module found in PIL.
    Your installation of PIL probably does not have colorspace support.
    Colors will not be transformed to sRGB and therefore may not appear as intended.
    Compare toasty's output to your source image and decide if this is acceptable to you.
    Consider a different setting of the `--colorspace-processing` argument to avoid this warning.''',
                    file=sys.stderr)
            else:
                from io import BytesIO
                in_prof = ImageCms.getOpenProfile(BytesIO(pil_img.info['icc_profile']))
                xform = ImageCms.buildTransform(in_prof, out_prof, pil_img.mode, pil_img.mode)
                ImageCms.applyTransform(pil_img, xform, inPlace=True)

        return Image.from_pil(pil_img)

    def load_stream(self, stream):
        """
        Load an image into memory from a file-like stream.

        Parameters
        ----------
        stream : file-like
            The data to load. Reads should yield bytes.

        Returns
        -------
        A new :class:`Image`.

        """
        # TODO: one day, we'll support FITS files and whatnot and we'll have a
        # mode where we get a Numpy array but not a PIL image. For now, just
        # pass it off to PIL and hope for the best.

        # Prevent PIL decompression-bomb aborts. Not thread-safe, of course.
        old_max = pil_image.MAX_IMAGE_PIXELS

        try:
            pil_image.MAX_IMAGE_PIXELS = None
            pilimg = pil_image.open(stream)
        finally:
            pil_image.MAX_IMAGE_PIXELS = old_max

        # Now pass it off to generic PIL handling ...
        return self.load_pil(pilimg)

    def load_path(self, path):
        """
        Load an image into memory from a filesystem path.

        Parameters
        ----------
        path : str
            The filesystem path to load.

        Returns
        -------
        A new :class:`Image`.
        """
        # Special handling for Numpy arrays. TODO: it would be better to sniff
        # filetypes instead of just looking at extensions. But, lazy.

        if path.endswith('.npy'):
            arr = np.load(path)
            return Image.from_array(arr, default_format='npy')

        if path.lower().endswith(('.fits', '.fts', '.fits.gz', '.fts.gz')):

            # TODO: implement a better way to recognize FITS files
            # TODO: decide how to handle multiple HDUs
            # TODO: decide how to handle non-TAN projections

            hdu = fits.open(path)[0]
            arr = hdu.data
            if ASTROPY_INSTALLED:
                from astropy.wcs import WCS
                wcs = WCS(hdu.header)
            else:
                wcs = None

            return Image.from_array(arr, wcs=wcs, default_format='fits')

        # Special handling for Photoshop files, used for some very large mosaics
        # with transparency (e.g. the PHAT M31/M33 images).

        # TODO: check for AVM in following formats and set WCS using this if needed.

        if path.endswith('.psd') or path.endswith('.psb'):
            try:
                from psd_tools import PSDImage
            except ImportError:
                pass
            else:
                psd = PSDImage.open(path)

                # If the Photoshop image is a single layer, we can save a lot of
                # memory by not using the composite() function. This has helped
                # me process very large Photoshop files.
                if self.psd_single_layer is not None:
                    pilimg = psd[self.psd_single_layer].topil()
                else:
                    pilimg = psd.composite()

                return self.load_pil(pilimg)

        # Special handling for OpenEXR files, used for large images with high
        # dynamic range.

        if path.endswith('.exr'):
            from .openexr import load_openexr
            img = load_openexr(path)
            if img.dtype != np.float16:
                raise Exception('only half-precision OpenEXR images are currently supported')
            return Image.from_array(img)

        # (One day, maybe we'll do more kinds of sniffing.) No special handling
        # came into play; just open the file and auto-detect.

        with open(path, 'rb') as f:
            return self.load_stream(f)


class Image(object):
    """A 2D data array stored in memory.

    This class primarily exists to help us abstract between the cases where we
    have "bitmap" RGB(A) images and "science" floating-point images.

    """
    _pil = None
    _array = None
    _mode = None
    _default_format = 'png'
    _wcs = None

    @classmethod
    def from_pil(cls, pil_img, wcs=None, default_format=None):
        """
        Create a new Image from a PIL image.

        Parameters
        ----------
        pil_img : :class:`PIL.Image.Image`
            The source image.
        wcs : :class:`~astropy.wcs.WCS`, optional
            The WCS coordinate system for the image.
        default_format : str, optional
            The default format to use when writing the image if none is
            specified explicitly.

        Returns
        -------
        A new :class:`Image` wrapping the PIL image.
        """

        _validate_format('default_format', default_format)

        # Make sure that the image data are actually loaded from disk. Pillow
        # lazy-loads such that sometimes `np.asarray(img)` ends up failing
        # mysteriously if the image is loaded from a file handle that is closed
        # promptly.
        pil_img.load()

        inst = cls()
        inst._pil = pil_img
        inst._wcs = wcs
        inst._default_format = default_format or cls._default_format

        try:
            inst._mode = ImageMode(pil_img.mode)
        except ValueError:
            raise Exception('image mode {} is not supported'.format(pil_img.mode))

        return inst

    @classmethod
    def from_array(cls, array, wcs=None, default_format=None):
        """Create a new Image from an array-like data variable.

        Parameters
        ----------
        array : array-like object
            The source data. This should either be a 2-d floating point array a
            3-d floating-point or uint8 array with shape (3, ny, nx), or a 3-d
            uint8 array with shape (4, ny, nx).
        wcs : :class:`~astropy.wcs.WCS`, optional
            The WCS coordinate system for the image.
        default_format : str, optional
            The default format to use when writing the image if none is
            specified explicitly. If not specified, this is automatically
            chosen at write time based on the array type.

        Returns
        -------
        A new :class:`Image` wrapping the data.

        Notes
        -----
        The array will be converted to be at least two-dimensional.

        """

        _validate_format('default_format', default_format)

        array = np.atleast_2d(array)

        inst = cls()
        inst._mode = _array_to_mode(array)
        inst._default_format = default_format or cls._default_format
        inst._array = array
        inst._wcs = wcs
        return inst

    def asarray(self):
        """Obtain the image data as a Numpy array.

        Returns
        -------
        If the image is an RGB(A) bitmap, the array will have shape ``(height, width, planes)``
        and a dtype of ``uint8``, where ``planes`` is either 3
        or 4 depending on whether the image has an alpha channel. If the image
        is science data, it will have shape ``(height, width)`` and have a
        floating-point dtype.

        """
        # NOTE: it turns out that np.asarray() on a PIL image has to copy the
        # entire image data. So, on a large image, it becomes super slow.
        # Therefore we cache the array. The array is marked read-only so we
        # don't have to worry about it and the PIL image getting out of sync
        # with modifications.
        if self._array is None:
            self._array = np.asarray(self._pil)
        return self._array

    def aspil(self):
        """Obtain the image data as :class:`PIL.Image.Image`.

        Returns
        -------
        If the image was loaded as a PIL image, the underlying object will be
        returned. Otherwise the data array will be converted into a PIL image,
        which requires that the array have an RGB(A) format with a shape of
        ``(height, width, planes)``, where ``planes`` is 3 or 4, and a dtype of
        ``uint8``.

        """
        if self._pil is not None:
            return self._pil
        if self.mode.try_as_pil() is None:
            raise Exception(f'Toasty image with mode {self.mode} cannot be converted to PIL')
        return pil_image.fromarray(self._array)

    @property
    def mode(self):
        return self._mode

    @property
    def dtype(self):
        # TODO: can this be more efficient? Does it need to be?
        return self.asarray().dtype

    @property
    def wcs(self):
        return self._wcs

    @property
    def shape(self):
        if self._array is not None:
            return self._array.shape

        return (self._pil.height, self._pil.width, len(self._pil.getbands()))

    @property
    def width(self):
        return self.shape[1]

    @property
    def height(self):
        return self.shape[0]

    @property
    def default_format(self):
        if self._default_format is None:
            if self.mode in (ImageMode.RGB, ImageMode.RGBA):
                return 'png'
            elif self.mode in (ImageMode.F32, ImageMode.F16x3):
                return 'npy'
        else:
            return self._default_format

    @default_format.setter
    def default_format(self, value):
        if value in SUPPORTED_FORMATS:
            self._default_format = value
        else:
            raise ValueError('Unrecognized format: {0}'.format(value))

    def fill_into_maskable_buffer(self, buffer, iy_idx, ix_idx, by_idx, bx_idx):
        """
        Fill a maskable buffer with a rectangle of data from this image.

        Parameters
        ----------
        buffer : :class:`Image`
            The destination buffer image, created with :meth:`ImageMode.make_maskable_buffer`.
        iy_idx : slice or other indexer
            The indexer into the Y axis of the source image (self).
        ix_idx : slice or other indexer
            The indexer into the X axis of the source image (self).
        by_idx : slice or other indexer
            The indexer into the Y axis of the destination *buffer*.
        bx_idx : slice or other indexer
            The indexer into the X axis of the destination *buffer*.

        Notes
        -----
        This highly specialized function is used to tile images efficiently. No
        bounds checking is performed. The rectangles defined by the indexers in
        the source and destination are assumed to agree in size. The regions of
        the buffer not filled by source data are masked, namely: either filled
        with alpha=0 or with NaN, depending on the image mode.

        """
        i = self.asarray()
        b = buffer.asarray()

        if self.mode == ImageMode.RGB:
            b.fill(0)
            b[by_idx,bx_idx,:3] = i[iy_idx,ix_idx]
            b[by_idx,bx_idx,3] = 255
        elif self.mode == ImageMode.RGBA:
            b.fill(0)
            b[by_idx,bx_idx] = i[iy_idx,ix_idx]
        elif self.mode in (ImageMode.F32, ImageMode.F16x3):
            b.fill(np.nan)
            b[by_idx,bx_idx] = i[iy_idx,ix_idx]
        else:
            raise Exception('unhandled mode in fill_into_maskable_buffer')

    def update_into_maskable_buffer(self, buffer, iy_idx, ix_idx, by_idx, bx_idx):
        """
        Update a maskable buffer with data from this image.

        Parameters
        ----------
        buffer : :class:`Image`
            The destination buffer image, created with :meth:`ImageMode.make_maskable_buffer`.
        iy_idx : slice or other indexer
            The indexer into the Y axis of the source image (self).
        ix_idx : slice or other indexer
            The indexer into the X axis of the source image (self).
        by_idx : slice or other indexer
            The indexer into the Y axis of the destination *buffer*.
        bx_idx : slice or other indexer
            The indexer into the X axis of the destination *buffer*.

        Notes
        -----
        Unlike :meth:`fill_into_maskable_buffer`, this function does not clear
        the entire buffer. It only overwrites the portion of the buffer covered
        by non-NaN-like values of the input image.

        """
        i = self.asarray()
        b = buffer.asarray()

        sub_b = b[by_idx,bx_idx]
        sub_i = i[iy_idx,ix_idx]

        if self.mode == ImageMode.RGB:
            sub_b[...,:3] = sub_i
            sub_b[...,3] = 255
        elif self.mode == ImageMode.RGBA:
            valid = (sub_i[...,3] != 0)
            valid = np.broadcast_to(valid[...,None], sub_i.shape)
            np.putmask(sub_b, valid, sub_i)
        elif self.mode == ImageMode.F32:
            valid = ~np.isnan(sub_i)
            np.putmask(sub_b, valid, sub_i)
        elif self.mode == ImageMode.F16x3:
            valid = ~np.any(np.isnan(sub_i), axis=2)
            valid = np.broadcast_to(valid[...,None], sub_i.shape)
            np.putmask(sub_b, valid, sub_i)
        else:
            raise Exception('unhandled mode in update_into_maskable_buffer')

    def save(self, path_or_stream, format=None, mode=None):
        """
        Save this image to a filesystem path or stream

        Parameters
        ----------
        path_or_stream : path-like object or file-like object
            The destination into which the data should be written. If file-like,
            the stream should accept bytes.

        """

        _validate_format('format', format)

        format = format or self._default_format

        if format in PIL_FORMATS:
            pil_image = self.aspil()
            if format in PIL_RGB_FORMATS and mode is None:
                mode = ImageMode.RGB
            if mode is not None:
                pil_image = pil_image.convert(mode.try_as_pil())
            pil_image.save(path_or_stream, format=PIL_FORMATS[format])
        elif format == 'npy':
            np.save(path_or_stream, self.asarray())
        elif format == 'fits':
            if self._wcs is None:
                header = None if self._wcs is None else self._wcs.toheader()
            fits.writeto(path_or_stream, self.asarray(),
                         header=header, overwrite=True)

    def make_thumbnail_bitmap(self):
        """Create a thumbnail bitmap from the image.

        Returns
        -------
        An RGB :class:`PIL.Image.Image` representing a thumbnail of the input
        image. WWT thumbnails are 96 pixels wide and 45 pixels tall and should
        be saved in JPEG format.

        """
        if self.mode in (ImageMode.F32, ImageMode.F64, ImageMode.F16x3):
            raise Exception('cannot thumbnail-ify non-RGB Image')

        THUMB_SHAPE = (96, 45)
        THUMB_ASPECT = THUMB_SHAPE[0] / THUMB_SHAPE[1]

        if self.width / self.height > THUMB_ASPECT:
            # The image is wider than desired; we'll need to crop off the sides.
            target_width = int(round(self.height * THUMB_ASPECT))
            dx = (self.width - target_width) // 2
            crop_box = (dx, 0, dx + target_width, self.height)
        else:
            # The image is taller than desired; crop off top and bottom.
            target_height = int(round(self.width / THUMB_ASPECT))
            dy = (self.height - target_height) // 2
            crop_box = (0, dy, self.width, dy + target_height)

        # Turns out that PIL the decompression-bomb checks happen here too.
        # Disable in our usual, not thread-safe, way.

        old_max = pil_image.MAX_IMAGE_PIXELS

        try:
            pil_image.MAX_IMAGE_PIXELS = None
            thumb = self.aspil().crop(crop_box)
        finally:
            pil_image.MAX_IMAGE_PIXELS = old_max

        thumb.thumbnail(THUMB_SHAPE)

        # Depending on the source image, the mode might be RGBA, which can't
        # be JPEG-ified.
        thumb = thumb.convert('RGB')

        return thumb

    def clear(self):
        """
        Fill the image with whatever "empty" value is most appropriate for its
        mode.

        Notes
        -----
        The image is assumed to be writable, which will not be the case for
        images constructed from PIL. If the mode is RGB or RGBA, the buffer is
        filled with zeros. If the mode is floating-point, the buffer is filled
        with NaNs.

        """
        if self._mode in (ImageMode.RGB, ImageMode.RGBA):
            self.asarray().fill(0)
        elif self._mode in (ImageMode.F32, ImageMode.F64, ImageMode.F16x3):
            self.asarray().fill(np.nan)
        else:
            raise Exception('unhandled mode in clear()')
