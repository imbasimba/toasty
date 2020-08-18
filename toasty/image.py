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

    def get_default_save_extension(self):
        """
        Get the file extension to be used in this mode's "default" save format.

        Returns
        -------
        The extension, without a period; either "png" or "npy"

        """
        # For RGB, could use JPG? But would complexify lots of things downstream.

        if self in (ImageMode.RGB, ImageMode.RGBA):
            return 'png'
        elif self == ImageMode.F32:
            return 'npy'
        else:
            raise Exception('unhandled mode in get_default_save_extension')

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
        else:
            raise Exception('unhandled mode in make_maskable_buffer()')

        return Image.from_array(arr)


class ImageLoader(object):
    """
    A class defining how to load an image.

    This is implemented as its own class since there can be some options
    involved, and we want to provide a centralized place for handling them all.

    TODO: support FITS, Numpy, etc.

    """
    psd_single_layer = None
    colorspace_processing = 'srgb'

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
            '--psd-single-layer',
            type = int,
            metavar = 'NUMBER',
            help = 'If loading a Photoshop image, the (0-based) layer number to load -- saves memory',
        )
        parser.add_argument(
            '--colorspace-processing',
            metavar = 'MODE',
            default = 'srgb',
            help = 'What kind of RGB colorspace processing to perform: '
                '"none", "srgb" to convert to sRGB (the default)',
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
        loader.psd_single_layer = settings.psd_single_layer
        loader.colorspace_processing = settings.colorspace_processing
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
        # Make sure that we end up in the right color space. From experience, some
        # EPO images have funky colorspaces and we need to convert to sRGB to get
        # the tiled versions to appear correctly.

        if self.colorspace_processing != 'none' and 'icc_profile' in pil_img.info:
            assert self.colorspace_processing == 'srgb' # more modes, one day?
            from io import BytesIO
            from PIL import ImageCms
            in_prof = ImageCms.getOpenProfile(BytesIO(pil_img.info['icc_profile']))
            out_prof = ImageCms.createProfile('sRGB')
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
        # Special handling for Photoshop files, used for some very large mosaics
        # with transparency (e.g. the PHAT M31/M33 images). TODO: it would be
        # better to sniff the PSD filetype instead of just looking at
        # extensions. But, lazy.

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

        # (One day, maybe we'll do more kinds of sniffing.) No special handling
        # came into play; just open the file and auto-detect.

        with open(path, 'rb') as f:
            return self.load_stream(f)


class Image(object):
    """A 2D data array stored in memory.

    This class primarily exists to help us abstract between the cases where we
    have "bitmap" RGB(A) images and "science" floating-point images.

    """
    _mode = None
    _pil = None
    _array = None

    @classmethod
    def from_pil(cls, pil_img):
        """Create a new Image from a PIL image.

        Parameters
        ----------
        pil_img : :class:`PIL.Image.Image`
            The source image.

        Returns
        -------
        A new :class:`Image` wrapping the PIL image.
        """
        inst = cls()
        inst._pil = pil_img

        try:
            inst._mode = ImageMode(pil_img.mode)
        except ValueError:
            raise Exception('image mode {} is not supported'.format(pil_img.mode))

        return inst

    @classmethod
    def from_array(cls, array):
        """Create a new Image from an array-like data variable.

        Parameters
        ----------
        array : array-like object
            The source data.

        Returns
        -------
        A new :class:`Image` wrapping the data.

        Notes
        -----
        The array will be converted to be at least two-dimensional. If it is
        strictly 2D and has a dtype of float32, it will be treated as science
        data. If it has shape ``(H, W, 3)`` and has type uint8, it will be
        treated as RGB data. If it has shape ``(H, W, 4)`` and has type uint8,
        it will be treated as RGBA data. Other combinations are not allowed.

        """
        inst = cls()
        inst._array = array = np.atleast_2d(array)

        if array.ndim == 2 and array.dtype == np.dtype(np.float32):
            inst._mode = ImageMode.F32
        elif array.ndim == 3 and array.shape[2] == 3 and array.dtype == np.dtype(np.uint8):
            inst._mode = ImageMode.RGB
        elif array.ndim == 3 and array.shape[2] == 4 and array.dtype == np.dtype(np.uint8):
            inst._mode = ImageMode.RGBA
        else:
            raise ValueError('unsupported shape/dtype combination {}/{}'.format(array.shape, array.dtype))

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
        if self._pil is not None:
            return np.asarray(self._pil)
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
        return pil_image.fromarray(self._array)

    @property
    def mode(self):
        return self._mode

    @property
    def dtype(self):
        # TODO: can this be more efficient? Does it need to be?
        return self.asarray().dtype

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
        elif self.mode == ImageMode.F32:
            b.fill(np.nan)
            b[by_idx,bx_idx] = i[iy_idx,ix_idx]
        else:
            raise Exception('unhandled mode in fill_into_maskable_buffer')

    def save_default(self, path_or_stream):
        """
        Save this image to a filesystem path or stream

        Parameters
        ----------
        path_or_stream : path-like object or file-like object
            The destination into which the data should be written. If file-like,
            the stream should accept bytes.

        """
        if self.mode in (ImageMode.RGB, ImageMode.RGBA):
            self.aspil().save(path_or_stream, format='PNG')
        elif self.mode == ImageMode.F32:
            np.save(path_or_stream, self.asarray())
        else:
            raise Exception('unhandled mode in save_default')

    def make_thumbnail_bitmap(self):
        """Create a thumbnail bitmap from the image.

        Returns
        -------
        An RGB :class:`PIL.Image.Image` representing a thumbnail of the input
        image. WWT thumbnails are 96 pixels wide and 45 pixels tall and should
        be saved in JPEG format.

        """
        if self.mode == ImageMode.F32:
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

        thumb = self.aspil().crop(crop_box)
        thumb.thumbnail(THUMB_SHAPE)

        # Depending on the source image, the mode might be RGBA, which can't
        # be JPEG-ified.
        thumb = thumb.convert('RGB')

        return thumb
